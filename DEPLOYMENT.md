# Stock Rating Checker - Production Deployment Guide

## 🚀 Production Deployment Options

### Option 1: Heroku (Easiest)
### Option 2: Digital Ocean/AWS/GCP with Gunicorn
### Option 3: Docker Container
### Option 4: VPS with Nginx + Gunicorn

---

## 📋 Prerequisites

1. **Domain name** (optional but recommended)
2. **SSL certificate** (Let's Encrypt is free)
3. **Production server** (cloud provider or VPS)
4. **Environment variables** for sensitive data

---

## 🔧 Option 1: Heroku Deployment (Recommended for beginners)

### Step 1: Install Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Login to Heroku
heroku login
```

### Step 2: Prepare your app
```bash
# Create Procfile (tells Heroku how to run your app)
echo "web: gunicorn stock_rating_app:app" > Procfile

# Create requirements.txt
pip freeze > requirements.txt

# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit"
```

### Step 3: Create Heroku app
```bash
# Create new Heroku app
heroku create your-stock-rating-app

# Deploy
git push heroku main
```

### Step 4: Configure environment
```bash
# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key-here

# Open your app
heroku open
```

---

## 🐳 Option 2: Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "stock_rating_app:app"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "80:5000"
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

---

## 🌐 Option 3: VPS with Nginx + Gunicorn

### System Requirements
- Ubuntu 20.04+ or CentOS 8+
- Python 3.8+
- Nginx
- Systemd

### Installation Commands
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv nginx supervisor -y

# Create app directory
sudo mkdir -p /var/www/stock-rating-app
sudo chown $USER:$USER /var/www/stock-rating-app
```

---

## ⚙️ Security & Performance Considerations

### Environment Variables
```bash
# .env file (never commit to git)
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production
DEBUG=False
RATE_LIMIT_ENABLED=True
MAX_REQUESTS_PER_MINUTE=60
```

### Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

### HTTPS/SSL
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📊 Monitoring & Logging

### Application Monitoring
- **Sentry** for error tracking
- **New Relic** for performance monitoring
- **DataDog** for infrastructure monitoring

### Health Check Endpoint
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-app-name"
        heroku_email: "your-email@example.com"
```

---

## 💰 Cost Estimates

### Heroku
- **Free tier**: $0/month (limited hours)
- **Hobby tier**: $7/month (24/7 uptime)
- **Production tier**: $25+/month (better performance)

### Digital Ocean
- **Basic Droplet**: $5-10/month
- **Load Balancer**: $10/month (optional)
- **Managed Database**: $15+/month (if needed)

### AWS
- **EC2 t3.micro**: ~$8-10/month
- **Application Load Balancer**: ~$16/month
- **CloudFront CDN**: ~$1-5/month

---

## 🛡️ Production Checklist

- [ ] Environment variables configured
- [ ] Debug mode disabled
- [ ] HTTPS/SSL enabled
- [ ] Rate limiting implemented
- [ ] Error monitoring setup
- [ ] Database backups (if applicable)
- [ ] Health checks configured
- [ ] Logging configured
- [ ] Security headers added
- [ ] Domain configured
- [ ] CDN setup (optional)

---

## 🚨 Important Notes

1. **Never commit secrets** to version control
2. **Use environment variables** for configuration
3. **Implement rate limiting** to prevent abuse
4. **Monitor your app** for errors and performance
5. **Keep dependencies updated** for security
6. **Use HTTPS** in production
7. **Implement caching** for better performance

---

## 📞 Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test locally first
4. Monitor resource usage
5. Check network connectivity
