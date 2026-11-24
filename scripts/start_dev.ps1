# Start MarginOps Local Development Servers
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Launching MarginOps Local Development Environment       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "`nStarting Backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Frontend on http://localhost:5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\frontend'; npm run dev"

Write-Host "`nBoth services launched in background terminal windows." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "OpenAPI Docs: http://localhost:8000/docs" -ForegroundColor Cyan
