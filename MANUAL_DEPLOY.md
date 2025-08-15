# 🚀 Manual Heroku Deployment Guide

## Step 1: Login to Heroku (already done)
```bash
heroku login
```

## Step 2: Create Heroku App
```bash
heroku create YOUR-APP-NAME-HERE
```
**Replace `YOUR-APP-NAME-HERE` with your preferred app name (must be unique)**

## Step 3: Ensure you have the required files
✅ `Procfile` - already created  
✅ `requirements.txt` - already created  
✅ `stock_rating_app.py` - already created  
✅ `templates/index.html` - already created  

## Step 4: Initialize Git (if not done)
```bash
git init
git add .
git commit -m "Initial commit"
```

## Step 5: Add Heroku remote
```bash
heroku git:remote -a YOUR-APP-NAME-HERE
```

## Step 6: Set environment variables
```bash
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
```

## Step 7: Deploy to Heroku
```bash
git push heroku main
```

## Step 8: Open your app
```bash
heroku open
```

---

## 🔧 If you get errors:

### View logs:
```bash
heroku logs --tail
```

### Restart app:
```bash
heroku restart
```

### Check config:
```bash
heroku config
```

---

## 🎉 Your app will be live at:
**https://YOUR-APP-NAME-HERE.herokuapp.com**

---

## 💡 Quick Commands Summary:
```bash
# 1. Create app
heroku create my-stock-rating-app

# 2. Set up git
git add .
git commit -m "Deploy to production"

# 3. Deploy
git push heroku main

# 4. Open
heroku open
```
