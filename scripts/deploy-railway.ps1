# PowerShell deployment script for Railway (Backend and Agent)

Write-Host "🚀 Deploying backend and agent to Railway..." -ForegroundColor Green

# Check if Railway CLI is installed
if (!(Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Railway CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "npm install -g @railway/cli" -ForegroundColor Yellow
    exit 1
}

# Login to Railway (if not already logged in)
railway login

# Deploy Backend
Write-Host "📦 Deploying backend service..." -ForegroundColor Yellow
Set-Location backend
railway up --service backend

# Deploy Agent
Write-Host "🤖 Deploying automation agent..." -ForegroundColor Yellow
Set-Location ../agent
railway up --service agent

Write-Host "✅ Backend and agent deployed successfully to Railway!" -ForegroundColor Green
Write-Host "🔧 Don't forget to set up environment variables in Railway dashboard" -ForegroundColor Cyan