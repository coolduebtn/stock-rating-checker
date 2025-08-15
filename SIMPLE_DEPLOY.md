# Simple Heroku Deployment Guide

## Step 1: Verify Your Heroku Account
1. Go to https://heroku.com/verify
2. Add payment information (required for all apps, even free ones)
3. No charges will occur for free tier usage

## Step 2: Deploy Your App
Once verified, run these commands in your terminal:

```bash
# Create a unique app name
heroku create stock-rating-checker-$(whoami)-$(date +%m%d)

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set RATE_LIMIT_ENABLED=True
heroku config:set SECURE_HEADERS=True

# Deploy the app
git push heroku main

# Open your app
heroku open
```

## Step 3: Monitor Your App
```bash
# View logs
heroku logs --tail

# Check app status
heroku ps

# Restart if needed
heroku restart
```

## Alternative: Use Railway (No Payment Required)
If you prefer not to verify Heroku immediately, try Railway:

1. Sign up at https://railway.app
2. Connect your GitHub account
3. Deploy directly from your repository

## Alternative: Use Render (Free Tier)
1. Sign up at https://render.com
2. Connect your GitHub repository
3. Deploy as a web service

Your app is ready to deploy once your account is verified!
