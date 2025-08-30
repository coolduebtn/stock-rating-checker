#!/bin/bash

# Stock Rating Checker - Production Startup Script
# This script starts the Flask app in production mode

echo "🚀 Starting Stock Rating Checker (Production Mode)..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set production environment variables
export FLASK_ENV=production
export DEBUG=False
export RATE_LIMIT_ENABLED=True
export SECURE_HEADERS=True

# Kill any existing Flask processes on port 5001
echo "🔍 Checking for existing processes on port 5001..."
if lsof -ti:5001 >/dev/null 2>&1; then
    echo "⚠️  Port 5001 is in use. Killing existing processes..."
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the production Flask app
echo "🌐 Starting Flask app in production mode on http://localhost:5001..."
echo "📱 Access the app at: http://localhost:5001"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

# Run the production app
python3 stock_rating_app_production.py

echo ""
echo "👋 Stock Rating Checker stopped."
