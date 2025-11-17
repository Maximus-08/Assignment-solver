# PowerShell deployment script for Vercel (Frontend)

Write-Host "🚀 Deploying frontend to Vercel..." -ForegroundColor Green

# Check if Vercel CLI is installed
if (!(Get-Command vercel -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Vercel CLI not found. Installing..." -ForegroundColor Red
    npm install -g vercel
}

# Navigate to frontend directory
Set-Location frontend

# Set production environment variables
Write-Host "📝 Setting up environment variables..." -ForegroundColor Yellow
vercel env add NEXTAUTH_URL production
vercel env add NEXTAUTH_SECRET production
vercel env add GOOGLE_CLIENT_ID production
vercel env add GOOGLE_CLIENT_SECRET production
vercel env add BACKEND_API_URL production
vercel env add NEXT_PUBLIC_BACKEND_API_URL production

# Deploy to production
Write-Host "🔨 Building and deploying..." -ForegroundColor Yellow
vercel --prod

Write-Host "✅ Frontend deployed successfully to Vercel!" -ForegroundColor Green
Write-Host "🌐 Your application is now live!" -ForegroundColor Cyan