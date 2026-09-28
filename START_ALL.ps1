# Start the complete local railway application.
# Run from anywhere with:
# powershell -ExecutionPolicy Bypass -File ".\START_ALL.ps1"

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "Mastereverything - Copy"
$webRoot = Join-Path $projectRoot "railway-dashboard-staff-ui\railway-dashboard"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) { throw "Python environment not found: $python" }
if (-not (Test-Path (Join-Path $webRoot "package.json"))) { throw "Staff dashboard not found: $webRoot" }
if (-not (Test-Path (Join-Path $webRoot "node_modules"))) { throw "Run npm install in: $webRoot" }

function Test-PortInUse([int]$Port) {
    return $null -ne (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Start-ProjectApp([string]$Name, [string]$FilePath, [string]$WorkingDirectory, [string[]]$Arguments, [int]$Port, [string]$LogName) {
    if (Test-PortInUse $Port) {
        Write-Host ("READY   {0,-28} port {1} (already running)" -f $Name, $Port) -ForegroundColor DarkYellow
        return
    }

    $stdout = Join-Path $projectRoot "$LogName.out.log"
    $stderr = Join-Path $projectRoot "$LogName.err.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    Write-Host ("STARTED {0,-28} port {1}  PID {2}" -f $Name, $Port, $process.Id) -ForegroundColor Green
}

Start-ProjectApp "FastAPI backend" $python $backendRoot @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000") 8000 "api"
Start-ProjectApp "XGBoost ETA dashboard" $python $backendRoot @("-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true", "--server.fileWatcherType", "none", "--server.runOnSave", "false", "--browser.gatherUsageStats", "false") 8501 "xgb_eta"
Start-ProjectApp "Multimodal inspector" $python $backendRoot @("-m", "streamlit", "run", "multimodal_inspector_app.py", "--server.port", "8502", "--server.headless", "true", "--server.fileWatcherType", "none", "--server.runOnSave", "false", "--browser.gatherUsageStats", "false") 8502 "inspector"

$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
Start-ProjectApp "React staff dashboard" $npm $webRoot @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") 5173 "staff-dashboard-vite"

Write-Host ""
Write-Host "Waiting for local services..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(20)
do {
    Start-Sleep -Milliseconds 500
    $ready = @(8000, 8501, 8502, 5173) | Where-Object { Test-PortInUse $_ }
} while ($ready.Count -lt 4 -and (Get-Date) -lt $deadline)

if ($ready.Count -lt 4) {
    $missing = @(8000, 8501, 8502, 5173) | Where-Object { -not (Test-PortInUse $_) }
    throw ("Services did not start: port(s) {0}. Check the generated error logs." -f ($missing -join ", "))
}

Write-Host ""
Write-Host "Staff dashboard (open this): http://localhost:5173" -ForegroundColor Green
Write-Host "FastAPI documentation:       http://localhost:8000/docs" -ForegroundColor Green
Write-Host "XGBoost ETA dashboard:      http://localhost:8501" -ForegroundColor Green
Write-Host "Multimodal inspector:       http://localhost:8502" -ForegroundColor Green
Write-Host ""
Write-Host "Port 8000 is the API, not the React website." -ForegroundColor Yellow
