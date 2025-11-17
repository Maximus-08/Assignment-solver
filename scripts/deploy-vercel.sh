#!/bin/bash
# Deployment script for Vercel (Frontend)

set -e

echo "🚀 Deploying frontend to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Navigate to frontend directory
cd frontend

# Set production environment variables
echo "📝 Setting up environment variables..."
vercel env add NEXTAUTH_URL production
vercel env add NEXTAUTH_SECRET production
vercel env add GOOGLE_CLIENT_ID production
vercel env add GOOGLE_CLIENT_SECRET production
vercel env add BACKEND_API_URL production
vercel env add NEXT_PUBLIC_BACKEND_API_URL production

# Deploy to production
echo "🔨 Building and deploying..."
vercel --prod

echo "✅ Frontend deployed successfully to Vercel!"
echo "🌐 Your application is now live!"