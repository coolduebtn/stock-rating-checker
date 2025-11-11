# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
A Flask-based web scraping application that fetches stock ratings from multiple financial platforms (Zacks, TipRanks, and Barchart). The app provides real-time stock rating analysis with a responsive web interface.

## Architecture
- **Core Application**: Two main Flask apps:
  - `stock_rating_app.py` - Development version with basic functionality
  - `stock_rating_app_production.py` - Production version with security features, rate limiting, and enhanced error handling
- **Web Scraping**: Individual functions for each platform with different scraping strategies:
  - Zacks: HTML parsing with rank_view class selectors
  - TipRanks: Multiple fallback methods for Smart Score extraction
  - Barchart: Opinion rating extraction with retry logic
- **Frontend**: Single-page application using templates/index.html with async JavaScript for parallel API calls

## Common Development Commands

### Local Development
```bash
# Development server (uses myenv virtual environment)
./run_stock_rating_app.sh

# Production server (uses system Python/venv)
./run_production.sh

# Install dependencies
pip install -r requirements.txt

# Build for deployment
./build.sh
```

### Virtual Environment Management
- Development uses `myenv/` virtual environment (legacy)
- Production uses `.venv/` virtual environment
- Both environments are gitignored

## Key Files
- `stock_rating_app.py` - Main development application
- `stock_rating_app_production.py` - Production application with security features
- `requirements.txt` - Python dependencies (Flask, requests, BeautifulSoup4, pandas)
- `templates/index.html` - Single HTML template for the web interface
- `.env.example` - Environment variable template for production configuration

## Environment Configuration
Production configuration is managed via environment variables:
- `FLASK_ENV=production` - Enables production mode
- `SECRET_KEY` - Flask secret key for sessions
- `RATE_LIMIT_ENABLED=True` - Enables API rate limiting
- `SECURE_HEADERS=True` - Enables security headers
- `DEBUG=False` - Disables debug mode

## Development Notes
- The app runs on port 5001 by default
- Web scraping includes anti-blocking measures with random delays and user agents
- Each platform has fallback methods due to frequent DOM structure changes
- Rate limiting is implemented in production version using flask-limiter
- Progressive loading: results appear as each platform completes (parallel fetching)