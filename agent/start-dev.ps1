# Agent Development Startup Script

Write-Host "🟡 Starting Assignment Solver Agent..." -ForegroundColor Yellow
Write-Host ""

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Start the agent
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host "✓ Starting agent (will fetch assignments and generate solutions)" -ForegroundColor Green
Write-Host ""

python main.py
