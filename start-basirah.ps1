#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the full BASIRAH local runtime (backend + frontend).
.DESCRIPTION
    Launches the FastAPI backend (http://127.0.0.1:8000) and the
    React/Vite frontend (http://127.0.0.1:5199) from the project root.
    Opens the frontend in the default browser. Paths are computed
    relative to this script, so it works from any working directory.
.NOTES
    Requires PowerShell 5.1+ and the project's Python venv to be set up:
        cd backend
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        pip install -r requirements.txt
#>

$ErrorActionPreference = 'Stop'

# --- Resolve paths relative to THIS script (project root) ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir '..')
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'basirah'

# --- Choose the Python interpreter from the project venv ---
$Python = Join-Path $BackendDir '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    Write-Warning "Python venv interpreter not found at $Python`n  Run: cd $BackendDir && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt"
    exit 1
}

# --- Pick a free frontend port (default: project dev port 5199) ---
$FrontendPort = 5199
$FrontendUrl = "http://127.0.0.1:$FrontendPort"

# --- Launch the backend (nohup-style: out-of-process, kept alive) ---
$BackendLog = Join-Path $ProjectRoot 'artifacts\backend.log'
New-Item -ItemType Directory -Path (Split-Path $BackendLog -Parent) -Force | Out-Null
$BackendProc = Start-Process -FilePath $Python -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--lifespan', 'on' `
    -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendLog -PassThru

Write-Host "Backend  : $BackendUrl"
Write-Host "Log      : $BackendLog"

# --- Give the backend a moment to bind before starting the frontend ---
Start-Sleep -Seconds 2
if ($BackendProc.HasExited) {
    Write-Error "Backend exited early (code $($BackendProc.ExitCode)). See $BackendLog"
    exit 1
}

# --- Launch the frontend ---
$FrontendLog = Join-Path $ProjectRoot 'artifacts\frontend.log'
$FrontendProc = Start-Process -FilePath 'npm' -ArgumentList 'run', 'dev', '--prefix', $FrontendDir `
    -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendLog -PassThru

Write-Host "Frontend : $FrontendUrl"
Write-Host "Log      : $FrontendLog"

# --- Open the browser ---
Start-Process $FrontendUrl

Write-Host "BASIRAH local runtime is starting. Press Ctrl+C to stop."
Wait-Process -Variable FrontendProc -Timeout -1 2>$null
exit 0
