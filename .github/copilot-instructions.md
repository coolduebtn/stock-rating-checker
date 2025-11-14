# Stock Rating Checker - AI Agent Instructions

## Project Overview
A Flask web scraper that aggregates stock ratings from 5 financial platforms (Zacks, TipRanks, Barchart, Stockopedia, Stock Analysis) plus price data from Zacks with parallel execution for 3-4 second response times.

## Architecture & Key Components

### Dual Application Pattern
- **Development**: `stock_rating_app.py` + `./run_stock_rating_app.sh` (uses `myenv/` venv, port 5001, debug=True)
- **Production**: `stock_rating_app_production.py` + `./run_production.sh` (uses system Python/`.venv`, rate limiting, security headers)

### Core Modules
- `common.py`: Centralized utilities for HTTP requests, parsing, error handling, and anti-blocking measures
- `templates/index.html`: Single-page app with async JavaScript for progressive result loading
- Platform-specific scrapers with multiple fallback methods due to frequent DOM changes

### Critical Patterns
1. **Parallel Execution**: All 5 rating platforms + price data fetch concurrently using `concurrent.futures.ThreadPoolExecutor` 
2. **Anti-Blocking**: Random delays, rotating user agents, timeout handling in `common.py`
3. **Graceful Degradation**: Each platform fails independently; partial results still display
4. **Progressive Loading**: Frontend shows "Loading..." states, updates as each platform completes

## Development Commands

```bash
# Development server (preferred for coding)
./run_stock_rating_app.sh

# Production testing
./run_production.sh

# Manual dependency install
pip install -r requirements.txt
```

## Web Scraping Implementation Notes

### Pattern: Multi-Method Fallbacks
Each platform implements 3-4 extraction methods due to frequent site changes:
```python
# Example from get_tipranks_rating()
# Method 1: CSS selectors
# Method 2: Regex patterns  
# Method 3: Page text search with context
# Method 4: JSON value extraction
```

### Pattern: Standardized Error Responses
Use `build_error_response()` and `build_success_response()` from `common.py`:
```python
return build_error_response('rating', 'Stock not found')
return build_success_response({'rating': 'Buy', 'score': '8'})
```

### Pattern: Request Flow
1. `normalize_ticker()` - uppercase, strip whitespace
2. `make_request()` - standardized HTTP with error handling
3. `validate_stock_page()` - confirm valid ticker page
4. Multiple parsing attempts with fallbacks
5. Standardized response format

## Frontend Integration

### Progressive Loading Implementation
- Initialize results display immediately with loading states
- Single parallel `/get_ratings` POST request (not individual platform calls)  
- JavaScript updates each platform card as data arrives
- Consensus calculation from all successful platforms

### Styling Pattern
Rating-specific CSS classes: `.rating-strong-buy`, `.rating-hold`, `.rating-sell`, etc.
Platform logos: `.zacks-logo`, `.tipranks-logo` with gradient backgrounds

## Environment Configuration

### Production Variables
```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key  
RATE_LIMIT_ENABLED=True
SECURE_HEADERS=True
DEBUG=False
```

## Common Debugging Approaches

1. **Platform Scraping Issues**: Check `common.py` utilities first, then platform-specific fallback methods
2. **Timeout Problems**: Adjust timeout values in `make_request()` calls (default 10-15s)
3. **Rate Limiting**: Modify `add_human_delay()` parameters or user agents in `HEADERS_*`
4. **Frontend Loading**: Check browser console for failed `/get_ratings` requests

## File Organization Logic
- Shell scripts handle environment setup and process management
- `common.py` contains all reusable scraping utilities to reduce duplication
- Platform functions follow consistent naming: `get_{platform}_rating(ticker)`
- Single HTML template with embedded CSS/JS for simplicity