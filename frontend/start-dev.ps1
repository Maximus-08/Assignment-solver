# Start Frontend Development Server
Write-Host "Starting Assignment Solver Frontend..." -ForegroundColor Green

# Set execution policy for this session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    Write-Host "Note: Using Tailwind CSS v4" -ForegroundColor Cyan
    npm install
}

# Check for correct Tailwind version
Write-Host "Verifying Tailwind CSS v4 installation..." -ForegroundColor Yellow
$tailwindVersion = npm list tailwindcss --depth=0 2>$null | Select-String "tailwindcss@"
if ($tailwindVersion -match "4\.") {
    Write-Host "✓ Tailwind CSS v4 detected" -ForegroundColor Green
} else {
    Write-Host "⚠ Reinstalling dependencies for Tailwind v4..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
    Remove-Item package-lock.json -ErrorAction SilentlyContinue
    npm install
}

# Start the development server
Write-Host "`nStarting Next.js development server on http://localhost:3000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Gray
npm run dev
