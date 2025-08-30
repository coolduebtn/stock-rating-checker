from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import random
from datetime import datetime

app = Flask(__name__)

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

def get_stockopedia_rating(ticker):
    """Fetch Stockopedia StockRank - reliable data source without blocking"""
    try:
        ticker = ticker.upper().strip()
        
        # Stockopedia URL format - using NSQ for NASDAQ stocks (most common US exchange)
        url = f"https://www.stockopedia.com/share-prices/{ticker.lower()}-NSQ:{ticker}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Add random delay to appear more human-like
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Handle different response codes
        if response.status_code == 404:
            return {'stockrank': 'N/A', 'style': 'N/A', 'status': 'Stock not found', 'success': False}
        elif response.status_code != 200:
            return {'stockrank': 'N/A', 'style': 'N/A', 'status': f'HTTP {response.status_code}', 'success': False}
        
        # Extract StockRank from JSON data embedded in the page
        stockrank_match = re.search(r'"stockRank":(\d+)', response.text)
        if stockrank_match:
            stockrank = int(stockrank_match.group(1))
            
            # Extract style (company classification)
            style_match = re.search(r'"style":"([^"]+)"', response.text)
            
            # Map StockRank to categories for better understanding
            if stockrank >= 80:
                category = 'Excellent'
            elif stockrank >= 60:
                category = 'Good'
            elif stockrank >= 40:
                category = 'Average'
            elif stockrank >= 20:
                category = 'Poor'
            else:
                category = 'Very Poor'
            
            return {
                'stockrank': str(stockrank),
                'category': category,
                'style': style_match.group(1) if style_match else 'Unknown',
                'status': 'Found',
                'success': True
            }
        else:
            # Check if the page loaded but just doesn't have StockRank data
            if ticker.upper() in response.text:
                return {'stockrank': 'NR', 'style': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
            else:
                return {'stockrank': 'N/A', 'style': 'N/A', 'status': 'Stock not found', 'success': False}
        
    except requests.exceptions.Timeout:
        return {'stockrank': 'TIMEOUT', 'style': 'Timeout', 'status': 'Request timeout', 'success': False}
    except requests.exceptions.ConnectionError:
        return {'stockrank': 'CONN_ERROR', 'style': 'Connection Error', 'status': 'Connection failed', 'success': False}
    except Exception as e:
        return {'stockrank': 'Error', 'style': 'Error', 'status': str(e)[:50], 'success': False}

def get_stockstory_rating(ticker):
    """Fetch StockStory rating with multi-exchange support"""
    try:
        import json
        
        ticker = ticker.upper().strip()
        
        # Try multiple exchanges - NASDAQ first, then NYSE
        exchanges = ['nasdaq', 'nyse']
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = None
        successful_url = None
        
        # Try each exchange until we find the stock
        for exchange in exchanges:
            url = f"https://stockstory.org/us/stocks/{exchange}/{ticker.lower()}"
            
            # Add random delay
            time.sleep(random.uniform(0.5, 1.5))
            
            try:
                test_response = requests.get(url, headers=headers, timeout=15)
                
                if test_response.status_code == 200:
                    response = test_response
                    successful_url = url
                    break
                elif test_response.status_code == 404:
                    continue  # Try next exchange
                else:
                    continue
                    
            except requests.exceptions.RequestException:
                continue  # Try next exchange
        
        # If no successful response from any exchange
        if response is None:
            return {'rating': 'N/A', 'sentiment': 'N/A', 'status': 'Stock not found', 'success': False}
        
        # Extract StockStory company tags and ratings
        tag_matches = re.findall(r'aria-label="Company tag: ([^"]+)"', response.text)
        rating_matches = re.findall(r'aria-label="Company rating: ([^"]+)"', response.text)
        
        unique_tags = list(set(tag_matches))
        unique_ratings = list(set(rating_matches))
        
        sentiment = 'Unknown'
        rating_text = 'N/A'
        
        # Prioritize company ratings first
        if unique_ratings:
            rating_sentiment_map = {
                'Underperform': 'Negative',
                'Outperform': 'Positive', 
                'Investable': 'Neutral',
                'Speculative': 'Risky',
                'Avoid': 'Negative'
            }
            
            primary_rating = unique_ratings[0]
            rating_text = primary_rating
            sentiment = rating_sentiment_map.get(primary_rating, 'Neutral')
            
            # If we have both rating and positive tags, combine them
            if sentiment in ['Neutral', 'Positive'] and unique_tags:
                positive_tags = [tag for tag in unique_tags if tag in ['High Quality', 'Timely Buy', 'Good Value', 'Strong Growth']]
                if positive_tags:
                    rating_text = f"{primary_rating} + {', '.join(positive_tags)}"
                    if sentiment == 'Neutral':
                        sentiment = 'Positive'
        
        elif unique_tags:
            # If no explicit company ratings, use tags
            if 'High Quality' in unique_tags and 'Timely Buy' in unique_tags:
                rating_text = 'High Quality & Timely Buy'
                sentiment = 'Very Positive'
            elif 'Timely Buy' in unique_tags:
                rating_text = 'Timely Buy'
                sentiment = 'Positive'
            elif 'High Quality' in unique_tags:
                rating_text = 'High Quality'
                sentiment = 'Positive'
            elif 'Good Value' in unique_tags:
                rating_text = 'Good Value'
                sentiment = 'Positive'
            elif 'Strong Growth' in unique_tags:
                rating_text = 'Strong Growth'
                sentiment = 'Positive'
            else:
                rating_text = ', '.join(unique_tags[:2])
                sentiment = 'Neutral'
        
        # If no ratings or tags found, check JSON-LD structured data
        if sentiment == 'Unknown':
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_matches = re.findall(json_ld_pattern, response.text, re.DOTALL)
            
            for json_text in json_matches:
                try:
                    data = json.loads(json_text)
                    if isinstance(data, dict) and 'description' in data:
                        desc = data['description']
                        
                        if 'We like' in desc:
                            sentiment = 'Positive'
                            rating_text = 'Like'
                        elif 'We love' in desc:
                            sentiment = 'Very Positive'
                            rating_text = 'Love'
                        elif "We're not sold" in desc or 'not sold' in desc:
                            sentiment = 'Negative'
                            rating_text = 'Not Sold'
                        elif 'outstanding' in desc.lower():
                            sentiment = 'Positive'
                            rating_text = 'Outstanding'
                        
                        if sentiment != 'Unknown':
                            break
                            
                except json.JSONDecodeError:
                    continue
        
        return {
            'rating': rating_text,
            'sentiment': sentiment,
            'exchange': successful_url.split('/')[-2].upper() if successful_url else 'Unknown',
            'status': 'Found' if sentiment != 'Unknown' else 'No clear rating found',
            'success': sentiment != 'Unknown'
        }
        
    except Exception as e:
        return {'rating': 'Error', 'sentiment': 'Error', 'status': str(e)[:50], 'success': False}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_ratings', methods=['POST'])
def get_ratings():
    ticker = request.json.get('ticker', '').strip().upper()
    
    if not ticker:
        return jsonify({'error': 'Please enter a ticker symbol'})
    
    # Initialize results
    results = {
        'ticker': ticker,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'zacks': {'status': 'Fetching...'},
        'tipranks': {'status': 'Fetching...'},
        'barchart': {'status': 'Fetching...'},
        'stockopedia': {'status': 'Fetching...'},
        'stockstory': {'status': 'Fetching...'}
    }
    
    try:
        # Fetch Zacks rating
        print(f"Fetching Zacks rating for {ticker}...")
        zacks_result = get_zacks_rating(ticker)
        results['zacks'] = zacks_result
        
        # Fetch TipRanks rating
        print(f"Fetching TipRanks rating for {ticker}...")
        tipranks_result = get_tipranks_rating(ticker)
        results['tipranks'] = tipranks_result
        
        # Fetch Barchart rating
        print(f"Fetching Barchart rating for {ticker}...")
        barchart_result = get_barchart_rating(ticker)
        results['barchart'] = barchart_result
        
        # Fetch Stockopedia rating
        print(f"Fetching Stockopedia rating for {ticker}...")
        stockopedia_result = get_stockopedia_rating(ticker)
        results['stockopedia'] = stockopedia_result
        
        # Fetch StockStory rating
        print(f"Fetching StockStory rating for {ticker}...")
        stockstory_result = get_stockstory_rating(ticker)
        results['stockstory'] = stockstory_result
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)
