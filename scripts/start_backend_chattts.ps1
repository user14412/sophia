param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\UserApps\Anaconda3\envs\chattts\python.exe"

if (-not (Test-Path $Python)) {
    throw "chattts Python not found: $Python"
}

Set-Location $ProjectRoot

$ExistingListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ExistingListener) {
    $Process = Get-CimInstance Win32_Process -Filter "ProcessId=$($ExistingListener.OwningProcess)"
    Write-Host "Port $Port is already in use by PID $($ExistingListener.OwningProcess):"
    Write-Host $Process.CommandLine
    Write-Host ""
    Write-Host "Either stop that process, or start Sophia backend on another port, for example:"
    Write-Host ".\scripts\start_backend_chattts.ps1 -Port 8001"
    exit 1
}

Write-Host "Starting Sophia backend with chattts Python on http://127.0.0.1:$Port"
& $Python -m uvicorn web_api.app:app --app-dir src --host 127.0.0.1 --port $Port
