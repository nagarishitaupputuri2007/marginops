# Start MarginOps Local Development Servers
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Launching MarginOps Local Development Environment       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "`nStarting Backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd '$RepoRoot\backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Frontend on http://localhost:5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd '$RepoRoot\frontend'; npm run dev"

Write-Host "`nBoth services launched in dedicated PowerShell terminal windows." -ForegroundColor Green
Write-Host "Web UI:      http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "OpenAPI Doc: http://localhost:8000/docs" -ForegroundColor Cyan
