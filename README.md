# Stock Rating Checker

A web application that fetches stock ratings from Zacks, TipRanks, and Barchart for individual ticker symbols.

## Features
- Real-time stock rating fetching from 3 major platforms
- Beautiful responsive web interface
- Individual ticker symbol lookup
- Consensus rating analysis
- Production-ready with error handling

## Platforms Supported
- **Zacks**: Rating scale 1-5 (Strong Buy to Strong Sell)
- **TipRanks**: Smart Score 1-10 with rating
- **Barchart**: Opinion ratings (Buy, Hold, Sell, etc.)

## Live Demo
Deploy this app to see it in action!

## Local Development
```bash
pip install -r requirements.txt
python stock_rating_app.py
```

## Deployment
This app is ready to deploy to:
- Render.com (recommended)
- Railway.app
- Fly.io
- Any Python hosting platform

## Environment Variables
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key`
- `RATE_LIMIT_ENABLED=True` (optional)
- `SECURE_HEADERS=True` (optional)
