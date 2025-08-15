#!/bin/bash

# Stock Rating Checker - Startup Script
# This script activates the virtual environment and starts the Flask app

echo "🚀 Starting Stock Rating Checker..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "myenv" ]; then
    echo "❌ Virtual environment 'myenv' not found!"
    echo "Please create it first with: python3 -m venv myenv"
    exit 1
fi

# Check if Flask is installed
if ! ./myenv/bin/python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found in virtual environment. Installing..."
    ./myenv/bin/pip install flask
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
if ! ./myenv/bin/python -c "import requests, bs4, pandas" 2>/dev/null; then
    echo "⚠️  Some packages missing. Installing dependencies..."
    ./myenv/bin/pip install requests beautifulsoup4 pandas lxml
fi

# Kill any existing Flask processes on port 5001
echo "🔍 Checking for existing processes on port 5001..."
if lsof -ti:5001 >/dev/null 2>&1; then
    echo "⚠️  Port 5001 is in use. Killing existing processes..."
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the Flask app
echo "🌐 Starting Flask app on http://localhost:5001..."
echo "📱 Access the app at: http://localhost:5001"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

# Run the app
./myenv/bin/python stock_rating_app.py

echo ""
echo "👋 Stock Rating Checker stopped."
