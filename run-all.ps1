# run-all.ps1
# Script to setup and run both backend (FastAPI) and mobile frontend (React Native Expo)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       Starting LabelGuard AI Development        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Start Backend in a new terminal window
Write-Host "[*] Launching Backend Setup & Server..." -ForegroundColor Yellow
$backendCmd = "cd backend; if (-not (Test-Path '.venv')) { Write-Host 'Creating Python virtual environment...' -ForegroundColor Yellow; python -m venv .venv }; Write-Host 'Activating virtual environment...' -ForegroundColor Yellow; .\.venv\Scripts\Activate.ps1; Write-Host 'Installing Python dependencies...' -ForegroundColor Yellow; pip install -r requirements.txt; if (-not (Test-Path '.env')) { Write-Host 'Creating .env config...' -ForegroundColor Yellow; Copy-Item .env.example .env }; Write-Host 'Starting FastAPI Backend on http://127.0.0.1:8000...' -ForegroundColor Green; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 2. Start Frontend in a new terminal window
Write-Host "[*] Launching Mobile Frontend Setup & Server..." -ForegroundColor Yellow
$frontendCmd = "cd mobile; Write-Host 'Installing NPM dependencies...' -ForegroundColor Yellow; npm install; Write-Host 'Starting Expo server...' -ForegroundColor Green; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "==================================================" -ForegroundColor Green
Write-Host " Both servers are launching in separate windows!  " -ForegroundColor Green
Write-Host " - Backend API: http://127.0.0.1:8000           " -ForegroundColor Green
Write-Host " - Backend Docs: http://127.0.0.1:8000/docs     " -ForegroundColor Green
Write-Host " - Frontend Mobile: Follow instructions in Expo  " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
