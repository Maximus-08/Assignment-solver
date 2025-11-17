#!/bin/bash
# MongoDB Atlas setup script

set -e

echo "🗄️  Setting up MongoDB Atlas..."

# Check if MongoDB CLI is installed
if ! command -v mongocli &> /dev/null; then
    echo "❌ MongoDB CLI not found. Please install it first:"
    echo "Visit: https://docs.mongodb.com/mongocli/stable/install/"
    exit 1
fi

# Configuration variables
PROJECT_NAME="assignment-solver"
CLUSTER_NAME="assignment-solver-cluster"
DB_NAME="assignment_solver_prod"

echo "📝 Creating MongoDB Atlas project..."
mongocli iam projects create "$PROJECT_NAME"

echo "🏗️  Creating MongoDB cluster..."
mongocli clusters create "$CLUSTER_NAME" \
    --provider AWS \
    --region US_EAST_1 \
    --tier M10 \
    --diskSizeGB 10 \
    --backup

echo "👤 Creating database user..."
read -p "Enter database username: " DB_USER
read -s -p "Enter database password: " DB_PASSWORD
echo

mongocli dbusers create \
    --username "$DB_USER" \
    --password "$DB_PASSWORD" \
    --role readWrite \
    --db "$DB_NAME"

echo "🔒 Setting up network access..."
mongocli accessLists create --ip 0.0.0.0/0 --comment "Allow all IPs (configure properly for production)"

echo "📋 Getting connection string..."
CONNECTION_STRING=$(mongocli clusters connectionStrings describe "$CLUSTER_NAME" --type standard)

echo "✅ MongoDB Atlas setup completed!"
echo "🔗 Connection string: $CONNECTION_STRING"
echo "⚠️  Remember to:"
echo "   1. Replace <username> and <password> in the connection string"
echo "   2. Configure proper IP whitelist for production"
echo "   3. Set up monitoring and alerts"