import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from ngboost import NGBRegressor 
from ngboost.distns import Normal
import torch
import torch.nn as nn
import torch.optim as optim

# ==========================================
# 1. Evaluation Metrics
# ==========================================
def pinball_loss(y_true, y_pred, quantile):
    err = y_true - y_pred
    return np.mean(np.maximum(quantile * err, (quantile - 1) * err))

def probabilistic_metrics(y_true, y_lower, y_upper):
    # Prediction Interval Coverage Probability (PICP)
    picp = np.mean((y_true >= y_lower) & (y_true <= y_upper))
    # Mean Prediction Interval Width (MPIW)
    mpiw = np.mean(y_upper - y_lower)
    return picp, mpiw

# ==========================================
# 2. PyTorch LSTM with MC Dropout
# ==========================================
class MC_Dropout_LSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout_rate=0.2):
        super(MC_Dropout_LSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout_rate)
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :]) # Take last time step
        out = self.fc(out)
        return out

def train_and_predict_lstm(X_train, y_train, X_test):
    # Convert to PyTorch tensors (batch, sequence_length, features)
    X_tr = torch.tensor(X_train, dtype=torch.float32).unsqueeze(2) 
    y_tr = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    X_te = torch.tensor(X_test, dtype=torch.float32).unsqueeze(2)

    model = MC_Dropout_LSTM(input_size=1, hidden_size=32, num_layers=1)
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    # Train
    model.train()
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X_tr)
        loss = criterion(outputs, y_tr)
        loss.backward()
        optimizer.step()

    # Inference with MC Dropout (keep dropout active)
    model.train() 
    predictions = []
    with torch.no_grad():
        for _ in range(50): # 50 Monte Carlo forward passes
            preds = model(X_te).squeeze().numpy()
            predictions.append(preds)
    
    predictions = np.array(predictions)
    
    # Calculate quantiles from the distribution of predictions
    median_pred = np.percentile(predictions, 50, axis=0)
    lower_pred = np.percentile(predictions, 10, axis=0)
    upper_pred = np.percentile(predictions, 90, axis=0)
    
    return median_pred, lower_pred, upper_pred

# ==========================================
# 3. Main Benchmark Execution
# ==========================================
def run_benchmark():
    print("Generating synthetic transportation data...")
    # Generate mock data: distances and actual travel times
    np.random.seed(42)
    n_samples = 1000
    distances = np.random.uniform(5, 50, n_samples)
    traffic_factor = np.random.uniform(0.8, 1.5, n_samples)
    # y = Distance * base_speed * traffic + noise
    actual_eta = (distances * 1.2 * traffic_factor) + np.random.normal(0, 3, n_samples)
    
    X = distances.reshape(-1, 1)
    y = actual_eta
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = []

    # --- 1. Quantile Tree Boosting (XGBoost Alternative) ---
    print("Training Quantile Boosting...")
    gb_mid = GradientBoostingRegressor(loss='quantile', alpha=0.5).fit(X_train, y_train)
    gb_low = GradientBoostingRegressor(loss='quantile', alpha=0.1).fit(X_train, y_train)
    gb_high = GradientBoostingRegressor(loss='quantile', alpha=0.9).fit(X_train, y_train)

    preds_mid = gb_mid.predict(X_test)
    preds_low = gb_low.predict(X_test)
    preds_high = gb_high.predict(X_test)

    picp, mpiw = probabilistic_metrics(y_test, preds_low, preds_high)
    results.append({
        "Model": "Quantile Gradient Boosting",
        "MAE": mean_absolute_error(y_test, preds_mid),
        "MAPE": mean_absolute_percentage_error(y_test, preds_mid),
        "Pinball (10th)": pinball_loss(y_test, preds_low, 0.1),
        "PICP (Coverage)": picp,
        "MPIW (Width)": mpiw
    })

    # --- 2. NGBoost (Native Probabilistic) ---
    print("Training NGBoost...")
    ngb = NGBRegressor(Dist=Normal, verbose=False).fit(X_train, y_train)
    y_dists = ngb.pred_dist(X_test)
    
    ngb_mid = y_dists.loc
    ngb_low = y_dists.dist.ppf(0.1) # 10th percentile
    ngb_high = y_dists.dist.ppf(0.9) # 90th percentile

    picp, mpiw = probabilistic_metrics(y_test, ngb_low, ngb_high)
    results.append({
        "Model": "NGBoost",
        "MAE": mean_absolute_error(y_test, ngb_mid),
        "MAPE": mean_absolute_percentage_error(y_test, ngb_mid),
        "Pinball (10th)": pinball_loss(y_test, ngb_low, 0.1),
        "PICP (Coverage)": picp,
        "MPIW (Width)": mpiw
    })

    # --- 3. LSTM with MC Dropout ---
    print("Training LSTM with MC Dropout...")
    lstm_mid, lstm_low, lstm_high = train_and_predict_lstm(X_train, y_train, X_test)
    
    picp, mpiw = probabilistic_metrics(y_test, lstm_low, lstm_high)
    results.append({
        "Model": "LSTM (MC Dropout)",
        "MAE": mean_absolute_error(y_test, lstm_mid),
        "MAPE": mean_absolute_percentage_error(y_test, lstm_mid),
        "Pinball (10th)": pinball_loss(y_test, lstm_low, 0.1),
        "PICP (Coverage)": picp,
        "MPIW (Width)": mpiw
    })

    # --- Print Results ---
    print("\n" + "="*80)
    print("BENCHMARK RESULTS")
    print("="*80)
    results_df = pd.DataFrame(results).round(4)
    print(results_df.to_string(index=False))

if __name__ == "__main__":
    run_benchmark()