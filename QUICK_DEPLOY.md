# 🚀 Quick Production Deployment Guide

## Option 1: Heroku (Easiest - 5 minutes)

### Step 1: Install Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Or download from: https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Deploy with our script
```bash
./deploy_to_heroku.sh
```

**That's it!** The script will:
- Create your Heroku app
- Set environment variables
- Deploy your code
- Open your live app

---

## Option 2: Digital Ocean App Platform (Also Easy)

### Step 1: Create account at DigitalOcean.com

### Step 2: Create new App
1. Choose "GitHub" as source
2. Select your repository
3. Choose these settings:
   - **Name**: stock-rating-checker
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `gunicorn stock_rating_app:app`
   - **HTTP Port**: 8080

### Step 3: Set Environment Variables
```
FLASK_ENV=production
SECRET_KEY=your-secret-key
RATE_LIMIT_ENABLED=True
```

**Cost**: ~$5/month

---

## Option 3: Docker Deployment

### Step 1: Build and run locally
```bash
docker build -t stock-rating-app .
docker run -p 80:5000 stock-rating-app
```

### Step 2: Deploy to any cloud provider
- **AWS ECS**: ~$10-20/month
- **Google Cloud Run**: ~$5-15/month
- **Azure Container Instances**: ~$5-15/month

---

## 💰 Cost Comparison

| Platform | Free Tier | Paid Plans | Pros | Cons |
|----------|-----------|------------|------|------|
| **Heroku** | Yes (limited) | $7-25/month | Easiest deployment | More expensive |
| **DigitalOcean** | No | $5-12/month | Good value | Requires more setup |
| **Railway** | Yes | $5/month | Simple, fast | Newer platform |
| **Render** | Yes | $7/month | Auto-deploy | Limited free tier |

---

## 🛡️ Production Checklist

Before going live:

- [ ] Set strong `SECRET_KEY` environment variable
- [ ] Enable `FLASK_ENV=production`
- [ ] Set up domain name (optional)
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Test all three rating sources
- [ ] Enable rate limiting
- [ ] Set up error logging

---

## 📊 Monitoring & Maintenance

### Health Check
Your app includes `/health` endpoint for monitoring:
```
GET https://your-app.herokuapp.com/health
```

### Error Tracking
Add Sentry for error monitoring:
```bash
heroku addons:create sentry:f1 -a your-app-name
```

### Performance Monitoring
- **New Relic**: Application performance
- **Heroku Metrics**: Built-in monitoring
- **UptimeRobot**: Uptime monitoring

---

## 🚨 Troubleshooting

### Common Issues:

1. **App won't start**
   - Check `heroku logs --tail`
   - Verify `requirements.txt` is correct
   - Ensure `Procfile` exists

2. **Rate limiting errors**
   - Reduce request frequency
   - Add delays between requests
   - Use VPN if blocked

3. **Timeout errors**
   - Increase timeout settings
   - Check network connectivity
   - Verify target websites are accessible

### Quick Fixes:
```bash
# View logs
heroku logs --tail -a your-app-name

# Restart app
heroku restart -a your-app-name

# Check configuration
heroku config -a your-app-name
```

---

## 🎯 Recommended: Start with Heroku

**Why Heroku?**
- ✅ Free tier available
- ✅ Automatic deployment script included
- ✅ Built-in monitoring
- ✅ Easy scaling
- ✅ Automatic SSL

**Quick Start:**
```bash
./deploy_to_heroku.sh
```

Your app will be live at: `https://your-app-name.herokuapp.com`
