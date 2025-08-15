# 🚀 RENDER.COM DEPLOYMENT - COMPLETE GUIDE

## 📋 STEP-BY-STEP INSTRUCTIONS

### Step 1: Create GitHub Repository
1. Go to https://github.com/new
2. Repository name: `stock-rating-checker`
3. Make it **Public**
4. **DON'T** initialize with README
5. Click **Create repository**

### Step 2: Connect Your Code to GitHub
After creating the repo, GitHub will show you commands. Run these in your terminal:

```bash
git remote add origin https://github.com/YOUR_USERNAME/stock-rating-checker.git
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username**

### Step 3: Deploy to Render.com
1. Go to https://render.com
2. Click **Sign Up** and choose **GitHub**
3. Authorize Render to access your repositories
4. Click **New +** → **Web Service**
5. Find and select your `stock-rating-checker` repository
6. Configure the deployment:

#### ⚙️ Render Configuration:
- **Name**: `stock-rating-checker` (or your preferred name)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn stock_rating_app:app`
- **Instance Type**: `Free`

#### 🔐 Environment Variables (Add these in Render):
- `FLASK_ENV` = `production`
- `SECRET_KEY` = `any-random-secret-key-here`

### Step 4: Deploy!
7. Click **Create Web Service**
8. Render will automatically build and deploy your app
9. Your app will be live at: `https://stock-rating-checker.onrender.com`

---

## 🎉 WHAT HAPPENS NEXT:
- ✅ Automatic builds from GitHub pushes
- ✅ Free SSL certificate
- ✅ Custom domain support
- ✅ 750 hours/month free
- ⚠️ App sleeps after 15 minutes (wakes up on first request)

---

## 🛠️ TROUBLESHOOTING:
If you have issues, check the **Logs** tab in Render dashboard.

Your app is 100% ready to deploy! 🚀
