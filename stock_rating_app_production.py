from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import random
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Production configuration
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
else:
    app.config['DEBUG'] = True

# Rate limiting setup (optional - requires flask-limiter)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"] if os.getenv('RATE_LIMIT_ENABLED') == 'True' else None
    )
except ImportError:
    limiter = None

def get_zacks_rating(ticker):
    """Fetch Zacks rating - confirmed working method"""
    try:
        ticker = ticker.upper().strip()
        url = f"https://www.zacks.com/stock/quote/{ticker}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {'rank': 'N/A', 'rating': 'N/A', 'status': f'HTTP {response.status_code}', 'success': False}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Look for rank_view with rank_chip (confirmed working)
        rank_element = soup.find('p', class_='rank_view')
        if rank_element:
            # First try rank_chip span
            rank_chip = rank_element.find('span', class_='rank_chip')
            if rank_chip and rank_chip.text.strip():
                rank = rank_chip.text.strip()
            else:
                # If rank_chip is empty, look for rank in the text content
                rank_text = rank_element.get_text(strip=True)
                # Extract rank from text like "3-Holdof 53" or "1-Strong Buyof 51"
                rank_match = re.match(r'^(\d)-', rank_text)
                if rank_match:
                    rank = rank_match.group(1)
                else:
                    rank = None
            
            # Map to rating
            rank_mapping = {
                '1': 'Strong Buy',
                '2': 'Buy',
                '3': 'Hold',
                '4': 'Sell',
                '5': 'Strong Sell'
            }
            
            if rank and rank in rank_mapping:
                return {
                    'rank': rank,
                    'rating': rank_mapping[rank],
                    'status': 'Found',
                    'success': True
                }
        
        # If no rank found, check if it's a valid stock page
        if soup.find('h1') and ticker.upper() in str(soup.find('h1')):
            return {'rank': 'NR', 'rating': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
        else:
            return {'rank': 'N/A', 'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
    except Exception as e:
        return {'rank': 'Error', 'rating': 'Error', 'status': str(e)[:50], 'success': False}

def get_tipranks_rating(ticker):
    """Fetch TipRanks Smart Score and rating with improved rate limiting and error handling"""
    try:
        ticker = ticker.upper().strip()
        
        # Skip obvious foreign/OTC tickers that won't be on TipRanks US site
        foreign_suffixes = ['F', 'Y', 'FF', 'ZY', 'GY', 'SY', 'UY', 'IY', 'LY']
        if any(ticker.endswith(suffix) for suffix in foreign_suffixes):
            return {'score': 'N/A', 'rating': 'Foreign/OTC', 'status': 'Foreign ticker', 'success': False}
        
        url = f"https://www.tipranks.com/stocks/{ticker.lower()}"
        
        # More comprehensive headers to appear more like a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        
        # Add random delay to appear more human-like
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, timeout=15)
        
        # Handle different error codes
        if response.status_code == 471:
            return {'score': 'BLOCKED', 'rating': 'Access Blocked', 'status': 'Site blocking requests', 'success': False}
        elif response.status_code == 403:
            return {'score': 'BLOCKED', 'rating': 'Forbidden', 'status': 'Access forbidden', 'success': False}
        elif response.status_code == 429:
            return {'score': 'RATE_LIMITED', 'rating': 'Rate Limited', 'status': 'Too many requests', 'success': False}
        elif response.status_code == 404:
            return {'score': 'N/A', 'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        elif response.status_code != 200:
            return {'score': 'N/A', 'rating': 'N/A', 'status': f'HTTP {response.status_code}', 'success': False}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we got a valid stock page first
        page_title = soup.find('title')
        if not page_title:
            return {'score': 'N/A', 'rating': 'N/A', 'status': 'Invalid page', 'success': False}
        
        title_text = page_title.get_text().upper()
        
        # Check for error pages or redirects
        if 'NOT FOUND' in title_text or 'ERROR' in title_text or '404' in title_text:
            return {'score': 'N/A', 'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
        # Check if ticker is in the title (basic validation)
        if ticker not in title_text and ticker.replace('.', '') not in title_text:
            return {'score': 'N/A', 'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
        # Look for Smart Score - try multiple methods
        score = None
        rating = None
        
        # Method 1: Look for Smart Score in various possible locations
        score_selectors = [
            'span[data-testid="smart-score-text"]',
            '.smart-score-text',
            '[class*="smart-score"]',
            '[class*="smartScore"]',
            '[data-testid*="score"]',
            '.score-text',
            '[class*="score-value"]'
        ]
        
        for selector in score_selectors:
            try:
                score_element = soup.select_one(selector)
                if score_element:
                    score_text = score_element.get_text(strip=True)
                    # Extract number from text like "8" or "8/10"
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        potential_score = int(score_match.group(1))
                        if 1 <= potential_score <= 10:
                            score = str(potential_score)
                            break
            except:
                continue
        
        # Method 2: Search in page text with better validation
        if not score:
            page_text = soup.get_text()
            # Look for patterns like "Smart Score: 8" or "8/10"
            score_patterns = [
                r'Smart Score[:\s]*(\d+)',
                r'(\d+)/10',
                r'Score[:\s]*(\d+)'
            ]
            for pattern in score_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    potential_score = int(match.group(1))
                    if 1 <= potential_score <= 10:  # Validate score range
                        score = str(potential_score)
                        break
                if score:
                    break
        
        # Method 3: Look for rating text with better keyword mapping
        rating_selectors = [
            '[data-testid*="rating"]',
            '[class*="rating"]',
            '[class*="sentiment"]',
            '[class*="recommendation"]',
            '[class*="consensus"]'
        ]
        
        rating_keywords = {
            'outperform': 'Outperform',
            'neutral': 'Neutral', 
            'underperform': 'Underperform',
            'bullish': 'Outperform',
            'bearish': 'Underperform',
            'buy': 'Outperform',
            'sell': 'Underperform',
            'hold': 'Neutral',
            'positive': 'Outperform',
            'negative': 'Underperform'
        }
        
        for selector in rating_selectors:
            try:
                rating_elements = soup.select(selector)
                for element in rating_elements:
                    text = element.get_text(strip=True).lower()
                    for keyword, mapped_rating in rating_keywords.items():
                        if keyword in text:
                            rating = mapped_rating
                            break
                    if rating:
                        break
                if rating:
                    break
            except:
                continue
        
        # Map score to rating if we have score but no explicit rating
        if score and not rating:
            score_num = int(score)
            if score_num >= 8:
                rating = 'Outperform'
            elif score_num >= 5:
                rating = 'Neutral'
            else:
                rating = 'Underperform'
        
        # Return results
        if score:
            return {
                'score': score,
                'rating': rating or 'N/A',
                'status': 'Found',
                'success': True
            }
        else:
            # Check if the stock page exists but just doesn't have a Smart Score
            if ticker in title_text:
                return {'score': 'NR', 'rating': 'Not Rated', 'status': 'Stock found but no Smart Score', 'success': True}
            else:
                return {'score': 'N/A', 'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
    except requests.exceptions.Timeout:
        return {'score': 'TIMEOUT', 'rating': 'Timeout', 'status': 'Request timeout', 'success': False}
    except requests.exceptions.ConnectionError:
        return {'score': 'CONN_ERROR', 'rating': 'Connection Error', 'status': 'Connection failed', 'success': False}
    except Exception as e:
        return {'score': 'Error', 'rating': 'Error', 'status': str(e)[:50], 'success': False}

def get_barchart_rating(ticker):
    """Fetch Barchart opinion/signal rating"""
    try:
        ticker = ticker.upper().strip()
        url = f"https://www.barchart.com/stocks/quotes/{ticker.lower()}/overview"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Add random delay to appear more human-like
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, timeout=15)
        
        # Handle different error codes
        if response.status_code == 403:
            return {'rating': 'Forbidden', 'status': 'Access forbidden', 'success': False}
        elif response.status_code == 429:
            return {'rating': 'Rate Limited', 'status': 'Too many requests', 'success': False}
        elif response.status_code == 404:
            return {'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        elif response.status_code != 200:
            return {'rating': 'N/A', 'status': f'HTTP {response.status_code}', 'success': False}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we got a valid stock page first
        page_title = soup.find('title')
        if not page_title:
            return {'rating': 'N/A', 'status': 'Invalid page', 'success': False}
        
        title_text = page_title.get_text().upper()
        
        # Check for error pages or redirects
        if 'NOT FOUND' in title_text or 'ERROR' in title_text or '404' in title_text:
            return {'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
        # Look for Barchart Opinion/Signal rating
        rating = None
        
        # Method 1: Look for opinion or signal in various selectors
        rating_selectors = [
            '[class*="opinion"]',
            '[class*="signal"]',
            '[class*="rating"]',
            '[class*="recommendation"]',
            '[data-ng-bind*="opinion"]',
            '.bc-opinion',
            '.opinion-text',
            '[class*="analyst"]'
        ]
        
        # Barchart rating keywords and their standardized forms
        rating_keywords = {
            'strong buy': 'Strong Buy',
            'strongbuy': 'Strong Buy',
            'buy': 'Buy',
            'strong sell': 'Strong Sell',
            'strongsell': 'Strong Sell', 
            'sell': 'Sell',
            'hold': 'Hold',
            'neutral': 'Hold',
            'bullish': 'Buy',
            'bearish': 'Sell',
            'overweight': 'Buy',
            'underweight': 'Sell',
            'outperform': 'Buy',
            'underperform': 'Sell',
            'positive': 'Buy',
            'negative': 'Sell'
        }
        
        # Search in specific elements first
        for selector in rating_selectors:
            try:
                rating_elements = soup.select(selector)
                for element in rating_elements:
                    text = element.get_text(strip=True).lower()
                    # Check for exact matches first
                    for keyword, mapped_rating in rating_keywords.items():
                        if keyword in text:
                            # Make sure it's not part of a larger word
                            if re.search(rf'\b{re.escape(keyword)}\b', text):
                                rating = mapped_rating
                                break
                    if rating:
                        break
                if rating:
                    break
            except:
                continue
        
        # Method 2: Search in page text with context validation
        if not rating:
            page_text = soup.get_text().lower()
            for keyword, mapped_rating in rating_keywords.items():
                if keyword in page_text:
                    # Try to find it in context to make sure it's a rating
                    context_patterns = [
                        f'(opinion|signal|rating|recommendation|consensus|analyst).*?{re.escape(keyword)}',
                        f'{re.escape(keyword)}.*?(opinion|signal|rating|recommendation)',
                        f'barchart.*?{re.escape(keyword)}',
                        f'{re.escape(keyword)}.*?barchart'
                    ]
                    for pattern in context_patterns:
                        if re.search(pattern, page_text):
                            rating = mapped_rating
                            break
                    if rating:
                        break
        
        # Check if it's a valid stock page by looking for the ticker
        if ticker.lower() in title_text.lower() or ticker.upper() in title_text:
            if rating:
                return {
                    'rating': rating,
                    'status': 'Found',
                    'success': True
                }
            else:
                return {'rating': 'Not Rated', 'status': 'Stock found but no rating', 'success': True}
        else:
            return {'rating': 'N/A', 'status': 'Stock not found', 'success': False}
        
    except requests.exceptions.Timeout:
        return {'rating': 'Timeout', 'status': 'Request timeout', 'success': False}
    except requests.exceptions.ConnectionError:
        return {'rating': 'Connection Error', 'status': 'Connection failed', 'success': False}
    except Exception as e:
        return {'rating': 'Error', 'status': str(e)[:50], 'success': False}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for production monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': os.getenv('APP_VERSION', '1.0.0')
    })

@app.route('/get_ratings', methods=['POST'])
def get_ratings():
    if limiter:
        # Apply rate limiting if available
        limiter.limit("10 per minute")(lambda: None)()
    
    ticker = request.json.get('ticker', '').strip().upper()
    
    if not ticker:
        return jsonify({'error': 'Please enter a ticker symbol'})
    
    # Validate ticker format (basic validation)
    if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', ticker):
        return jsonify({'error': 'Invalid ticker symbol format'})
    
    # Initialize results
    results = {
        'ticker': ticker,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'zacks': {'status': 'Fetching...'},
        'tipranks': {'status': 'Fetching...'},
        'barchart': {'status': 'Fetching...'}
    }
    
    try:
        # Fetch Zacks rating
        app.logger.info(f"Fetching Zacks rating for {ticker}")
        zacks_result = get_zacks_rating(ticker)
        results['zacks'] = zacks_result
        
        # Fetch TipRanks rating
        app.logger.info(f"Fetching TipRanks rating for {ticker}")
        tipranks_result = get_tipranks_rating(ticker)
        results['tipranks'] = tipranks_result
        
        # Fetch Barchart rating
        app.logger.info(f"Fetching Barchart rating for {ticker}")
        barchart_result = get_barchart_rating(ticker)
        results['barchart'] = barchart_result
        
        return jsonify(results)
    
    except Exception as e:
        app.logger.error(f"Error fetching ratings for {ticker}: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

# Security headers
@app.after_request
def add_security_headers(response):
    if os.getenv('SECURE_HEADERS') == 'True':
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    app.run(debug=app.config['DEBUG'], host=host, port=port)
