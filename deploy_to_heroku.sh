#!/bin/bash

# Heroku Deployment Script for Stock Rating Checker
# This script prepares and deploys your app to Heroku

echo "🚀 Preparing Stock Rating Checker for Heroku deployment..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found!"
    echo "Please install it: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Login to Heroku (if not already logged in)
echo "🔐 Checking Heroku authentication..."
if ! heroku auth:whoami &> /dev/null; then
    echo "Please log in to Heroku:"
    heroku login
fi

# Initialize git repository if not exists
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for Heroku deployment"
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

# Read app name from user
read -p "Enter your Heroku app name (e.g., my-stock-rating-app): " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name cannot be empty!"
    exit 1
fi

# Create Heroku app
echo "🌐 Creating Heroku app: $APP_NAME..."
if heroku create $APP_NAME; then
    echo "✅ Heroku app created successfully!"
else
    echo "⚠️  App might already exist. Continuing..."
    # Try to add the remote if it doesn't exist
    if ! git remote get-url heroku &> /dev/null; then
        heroku git:remote -a $APP_NAME
    fi
fi

# Set environment variables
echo "⚙️  Setting environment variables..."
heroku config:set FLASK_ENV=production -a $APP_NAME
heroku config:set SECRET_KEY=$(openssl rand -base64 32) -a $APP_NAME
heroku config:set RATE_LIMIT_ENABLED=True -a $APP_NAME
heroku config:set SECURE_HEADERS=True -a $APP_NAME

# Ensure we're using the production app file
if [ ! -f "stock_rating_app.py" ]; then
    echo "📁 Using production app file..."
    cp stock_rating_app_production.py stock_rating_app.py
fi

# Commit any changes
echo "📦 Committing changes for deployment..."
git add .
git commit -m "Prepare for Heroku deployment" || echo "No changes to commit"

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
if git push heroku main; then
    echo "✅ Deployment successful!"
    
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
    echo "❌ Deployment failed! Check the logs:"
    heroku logs --tail -a $APP_NAME
fi
