# Run all MarginOps test suites and validation checks
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   MarginOps System Verification & Test Suite Runner       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$RepoRoot = Split-Path -Parent $PSScriptRoot

# 1. Backend Pytest
Write-Host "`n[1/2] Running Backend Pytest Suite (134 Tests)..." -ForegroundColor Yellow
Set-Location "$RepoRoot\backend"
& ".\.venv\Scripts\pytest.exe" -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nBackend tests FAILED!" -ForegroundColor Red
    Set-Location $RepoRoot
    exit 1
}
Write-Host "Backend tests PASSED!" -ForegroundColor Green

# 2. Frontend Build & TypeScript Typecheck
Write-Host "`n[2/2] Running Frontend TypeScript Check & Vite Build..." -ForegroundColor Yellow
Set-Location "$RepoRoot\frontend"
& npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nFrontend build FAILED!" -ForegroundColor Red
    Set-Location $RepoRoot
    exit 1
}
Write-Host "Frontend build PASSED!" -ForegroundColor Green

Set-Location $RepoRoot
Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   ALL VERIFICATION GATES PASSED (100% OPERATIONAL)        " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
