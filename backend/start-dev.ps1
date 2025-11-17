# Backend Development Server Startup Script

Write-Host "🔴 Starting Backend Server..." -ForegroundColor Red
Write-Host ""

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Start the server
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host "✓ Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host "✓ API docs available at http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
