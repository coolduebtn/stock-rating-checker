#!/bin/bash

# Stock Rating Checker - Heroku Deployment Script
# This script prepares and deploys your app to Heroku

echo "🚀 Starting Stock Rating Checker deployment to Heroku..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found!"
    echo "Please install it: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if already logged in to Heroku
echo "🔐 Checking Heroku authentication..."
if ! heroku auth:whoami &> /dev/null; then
    echo "Please log in to Heroku:"
    heroku login
fi

echo "✅ Heroku authentication confirmed"

# Initialize git repository if not exists
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << EOF
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
myenv/
.env
.venv
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.DS_Store
*.sqlite3
instance/
EOF
fi

# Ensure we have the main app file (not production version)
if [ ! -f "stock_rating_app.py" ]; then
    echo "📁 Creating main app file for Heroku..."
    cp stock_rating_app_production.py stock_rating_app.py
fi

# Add and commit files
echo "📦 Preparing files for deployment..."
git add .
git commit -m "Prepare for Heroku deployment" || echo "No changes to commit"

# Generate a unique app name
TIMESTAMP=$(date +"%m%d")
DEFAULT_APP_NAME="stock-rating-app-$TIMESTAMP"

# Read app name from user with default
echo ""
echo "Enter your Heroku app name (or press Enter for default: $DEFAULT_APP_NAME):"
read -r APP_NAME

if [ -z "$APP_NAME" ]; then
    APP_NAME=$DEFAULT_APP_NAME
fi

echo "📱 Using app name: $APP_NAME"

# Create Heroku app
echo "🌐 Creating Heroku app: $APP_NAME..."
if heroku create $APP_NAME 2>/dev/null; then
    echo "✅ Heroku app created successfully!"
else
    echo "⚠️  App creation failed (might already exist). Trying to connect to existing app..."
    # Try to add the remote if it doesn't exist
    if ! git remote get-url heroku &> /dev/null; then
        heroku git:remote -a $APP_NAME 2>/dev/null || {
            echo "❌ Could not connect to app $APP_NAME"
            echo "Please try a different app name or check if you own this app"
            exit 1
        }
    fi
fi

# Set environment variables
echo "⚙️  Setting environment variables..."
heroku config:set FLASK_ENV=production -a $APP_NAME
heroku config:set SECRET_KEY=$(openssl rand -base64 32) -a $APP_NAME
heroku config:set RATE_LIMIT_ENABLED=True -a $APP_NAME
heroku config:set SECURE_HEADERS=True -a $APP_NAME

# Deploy to Heroku
echo "� Deploying to Heroku..."
if git push heroku main 2>/dev/null || git push heroku master 2>/dev/null; then
    echo "✅ Deployment successful!"
    
    # Wait a moment for the app to start
    echo "⏳ Waiting for app to start..."
    sleep 10
    
    # Open the app
    echo "🌐 Opening your app..."
    heroku open -a $APP_NAME
    
    echo ""
    echo "🎉 Your Stock Rating Checker is now live!"
    echo "📱 App URL: https://$APP_NAME.herokuapp.com"
    echo "📊 Heroku Dashboard: https://dashboard.heroku.com/apps/$APP_NAME"
    echo ""
    echo "Useful commands:"
    echo "  heroku logs --tail -a $APP_NAME    # View live logs"
    echo "  heroku restart -a $APP_NAME        # Restart the app"
    echo "  heroku config -a $APP_NAME         # View environment variables"
    
else
    echo "❌ Deployment failed! Checking logs..."
    heroku logs --tail -a $APP_NAME
    exit 1
fi
