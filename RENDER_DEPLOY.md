# Render.com Deployment Guide

## Step 1: Push to GitHub
1. Create a new repository on GitHub
2. Copy the repository URL
3. Run these commands:

```bash
git remote add origin YOUR_GITHUB_REPO_URL
git branch -M main
git push -u origin main
```

## Step 2: Deploy on Render
1. Go to https://render.com
2. Sign up with your GitHub account
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - **Name**: `stock-rating-checker`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn stock_rating_app:app`
   - **Instance Type**: `Free`

## Step 3: Set Environment Variables
In Render dashboard, add these environment variables:
- `FLASK_ENV` = `production`
- `SECRET_KEY` = `your-random-secret-key`

## Step 4: Deploy!
Click "Create Web Service" - Render will automatically deploy your app!

---

## 🎉 Your app will be live at:
`https://stock-rating-checker.onrender.com`

## 📊 Features of Render Free Tier:
- ✅ Automatic deployments from GitHub
- ✅ Custom domains
- ✅ SSL certificates
- ✅ 750 hours/month (enough for most apps)
- ⚠️ Apps sleep after 15 minutes of inactivity
- ⚠️ Cold start delay when waking up

---

## Alternative: Quick Railway Deployment
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "Deploy from GitHub repo"
4. Select your repository
5. Done! Railway auto-configures everything
