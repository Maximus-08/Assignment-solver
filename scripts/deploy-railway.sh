#!/bin/bash
# Deployment script for Railway (Backend and Agent)

set -e

echo "🚀 Deploying backend and agent to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "npm install -g @railway/cli"
    exit 1
fi

# Login to Railway (if not already logged in)
railway login

# Deploy Backend
echo "📦 Deploying backend service..."
cd backend
railway up --service backend

# Deploy Agent
echo "🤖 Deploying automation agent..."
cd ../agent
railway up --service agent

echo "✅ Backend and agent deployed successfully to Railway!"
echo "🔧 Don't forget to set up environment variables in Railway dashboard"