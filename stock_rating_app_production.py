from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
import json
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv
from common import (
    normalize_ticker, is_foreign_ticker, make_request,
    handle_http_status, get_page_soup, validate_stock_page, ticker_in_page,
    extract_number_from_text, find_keywords_in_text, search_text_with_context, 
    validate_score_range, map_score_to_rating, find_json_value, find_all_regex_matches,
    build_error_response, build_success_response, extract_stock_analysis_data,
    HEADERS_STANDARD, HEADERS_COMPREHENSIVE, RATING_KEYWORDS, BARCHART_RATING_KEYWORDS,
    STOCKANALYSIS_RATING_KEYWORDS
)

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

# Rate limiting setup (optional)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    rate_limits = ["200 per day", "50 per hour"] if os.getenv('RATE_LIMIT_ENABLED') == 'True' else None
    
    try:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=rate_limits
        )
    except TypeError:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=rate_limits
        )
except ImportError:
    limiter = None

# Import all 5 rating functions from common module
def get_zacks_rating(ticker):
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.zacks.com/stock/quote/{ticker}"
        response, error = make_request(url, headers=HEADERS_STANDARD, timeout=10)
        if error:
            return build_error_response('rank', error['status'])
        if response.status_code != 200:
            status_error = handle_http_status(response.status_code)
            if status_error:
                return {**status_error, 'rank': status_error.get('error', 'N/A')}
        soup = get_page_soup(response)
        rank_element = soup.find('p', class_='rank_view')
        if rank_element:
            rank_chip = rank_element.find('span', class_='rank_chip')
            rank = None
            if rank_chip and rank_chip.text.strip():
                rank = rank_chip.text.strip()
            else:
                rank_text = rank_element.get_text(strip=True)
                rank_match = re.match(r'^(\d)-', rank_text)
                if rank_match:
                    rank = rank_match.group(1)
            rank_mapping = {'1': 'Strong Buy', '2': 'Buy', '3': 'Hold', '4': 'Sell', '5': 'Strong Sell'}
            if rank and rank in rank_mapping:
                return build_success_response({'rank': rank, 'rating': rank_mapping[rank]})
        if soup.find('h1') and ticker in str(soup.find('h1')):
            return {'rank': 'NR', 'rating': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
        else:
            return build_error_response('rank', 'Stock not found')
    except Exception as e:
        return build_error_response('rank', str(e)[:50])

def get_tipranks_rating(ticker):
    try:
        ticker = normalize_ticker(ticker)
        if is_foreign_ticker(ticker):
            return build_error_response('score', 'Foreign ticker', additional_fields={'rating': 'Foreign/OTC'})
        url = f"https://www.tipranks.com/stocks/{ticker.lower()}"
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('score', error['status'], additional_fields={'rating': 'Error'})
        status_error = handle_http_status(response.status_code, {
            471: build_error_response('score', 'Site blocking requests', additional_fields={'rating': 'Access Blocked'}),
            403: build_error_response('score', 'Access forbidden', additional_fields={'rating': 'Forbidden'}),
            429: build_error_response('score', 'Too many requests', additional_fields={'rating': 'Rate Limited'}),
            404: build_error_response('score', 'Stock not found'),
        })
        if status_error:
            return status_error
        soup = get_page_soup(response)
        is_valid, title_text = validate_stock_page(soup, ticker)
        if not is_valid or not ticker_in_page(ticker, title_text):
            return build_error_response('score', 'Stock not found')
        score = None
        score_patterns = [r'Smart Score[:\s]*(\d+)', r'(\d+)/10', r'Score[:\s]*(\d+)']
        for pattern in score_patterns:
            matches = find_all_regex_matches(soup.get_text(), pattern)
            for match in matches:
                try:
                    score_num = int(match)
                    if validate_score_range(score_num):
                        score = str(score_num)
                        break
                except (ValueError, TypeError):
                    continue
            if score:
                break
        rating_text = soup.get_text().lower() if soup else ''
        rating = find_keywords_in_text(rating_text, RATING_KEYWORDS)
        if score and not rating:
            rating = map_score_to_rating(score)
        if score:
            return build_success_response({'score': score, 'rating': rating or 'N/A'})
        else:
            if ticker_in_page(ticker, title_text):
                return {'score': 'NR', 'rating': 'Not Rated', 'status': 'Stock found but no Smart Score', 'success': True}
            else:
                return build_error_response('score', 'Stock not found')
    except requests.exceptions.Timeout:
        return build_error_response('score', 'Request timeout', additional_fields={'rating': 'Timeout'})
    except requests.exceptions.ConnectionError:
        return build_error_response('score', 'Connection failed', additional_fields={'rating': 'Connection Error'})
    except Exception as e:
        return build_error_response('score', str(e)[:50], additional_fields={'rating': 'Error'})

def get_barchart_rating(ticker):
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.barchart.com/stocks/quotes/{ticker.lower()}/overview"
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('rating', error['status'])
        status_error = handle_http_status(response.status_code, {
            403: build_error_response('rating', 'Access forbidden'),
            429: build_error_response('rating', 'Too many requests'),
            404: build_error_response('rating', 'Stock not found'),
        })
        if status_error:
            return status_error
        soup = get_page_soup(response)
        is_valid, title_text = validate_stock_page(soup, ticker)
        if not is_valid:
            return build_error_response('rating', 'Stock not found')
        rating = None
        technical_opinion = soup.find('div', class_='technical-opinion-widget')
        if technical_opinion:
            rating_link = technical_opinion.find('a', href=re.compile(r'/opinion'))
            if rating_link:
                rating_text = rating_link.get_text(strip=True).lower()
                rating = find_keywords_in_text(rating_text, BARCHART_RATING_KEYWORDS)
        if not rating:
            page_text = soup.get_text().lower()
            context_patterns = [r'(opinion|signal|rating|recommendation|consensus|analyst).*?{keyword}',
                              r'{keyword}.*?(opinion|signal|rating|recommendation)', r'barchart.*?{keyword}', r'{keyword}.*?barchart']
            rating = search_text_with_context(page_text, BARCHART_RATING_KEYWORDS, context_patterns)
        if ticker.lower() in title_text.lower() or ticker.upper() in title_text:
            if rating:
                return build_success_response({'rating': rating})
            else:
                return {'rating': 'Not Rated', 'status': 'Stock found but no rating', 'success': True}
        else:
            return build_error_response('rating', 'Stock not found')
    except requests.exceptions.Timeout:
        return build_error_response('rating', 'Request timeout')
    except requests.exceptions.ConnectionError:
        return build_error_response('rating', 'Connection failed')
    except Exception as e:
        return build_error_response('rating', str(e)[:50])

def get_stockopedia_rating(ticker):
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.stockopedia.com/share-prices/{ticker.lower()}-NSQ:{ticker}/"
        response, error = make_request(url, headers=HEADERS_STANDARD, timeout=10)
        if error:
            return build_error_response('stockrank', error['status'], additional_fields={'style': 'N/A'})
        status_error = handle_http_status(response.status_code, {
            404: build_error_response('stockrank', 'Stock not found', additional_fields={'style': 'N/A'}),
        })
        if status_error:
            return status_error
        stockrank_str = find_json_value(response.text, r'"stockRank":(\d+)')
        if stockrank_str:
            try:
                stockrank = int(stockrank_str)
                category = 'Excellent' if stockrank >= 80 else 'Good' if stockrank >= 60 else 'Average' if stockrank >= 40 else 'Poor' if stockrank >= 20 else 'Very Poor'
                style = find_json_value(response.text, r'"style":"([^"]+)"')
                return build_success_response({'stockrank': str(stockrank), 'category': category, 'style': style or 'Unknown'})
            except (ValueError, TypeError):
                pass
        if ticker in response.text:
            return {'stockrank': 'NR', 'style': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
        else:
            return build_error_response('stockrank', 'Stock not found', additional_fields={'style': 'N/A'})
    except requests.exceptions.Timeout:
        return build_error_response('stockrank', 'Request timeout', additional_fields={'style': 'Timeout'})
    except requests.exceptions.ConnectionError:
        return build_error_response('stockrank', 'Connection failed', additional_fields={'style': 'Connection Error'})
    except Exception as e:
        return build_error_response('stockrank', str(e)[:50], additional_fields={'style': 'Error'})

def get_stockanalysis_rating(ticker):
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://stockanalysis.com/stocks/{ticker.lower()}/forecast/"
        
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('consensus', error['status'], additional_fields={'price_target': 'N/A'})
        
        status_error = handle_http_status(response.status_code, {
            403: build_error_response('consensus', 'Access forbidden', additional_fields={'price_target': 'N/A'}),
            429: build_error_response('consensus', 'Too many requests', additional_fields={'price_target': 'N/A'}),
            404: build_error_response('consensus', 'Stock not found', additional_fields={'price_target': 'N/A'}),
        })
        if status_error:
            return status_error
        
        soup = get_page_soup(response)
        is_valid, title_text = validate_stock_page(soup, ticker)
        if not is_valid or not ticker_in_page(ticker, title_text):
            return build_error_response('consensus', 'Stock not found', additional_fields={'price_target': 'N/A'})
        
        analysis_data = extract_stock_analysis_data(soup, ticker)
        if not analysis_data:
            return build_error_response('consensus', 'Unable to extract data', additional_fields={'price_target': 'N/A'})
        
        result = {
            'consensus': analysis_data.get('consensus', 'N/A'),
            'price_target': analysis_data.get('price_target', 'N/A'),
            'status': 'Found',
            'success': True
        }
        
        if 'analyst_count' in analysis_data:
            result['analyst_count'] = analysis_data['analyst_count']
        if 'upside_downside' in analysis_data:
            result['upside_downside'] = analysis_data['upside_downside']
        
        return result
    except requests.exceptions.Timeout:
        return build_error_response('consensus', 'Request timeout', additional_fields={'price_target': 'Timeout'})
    except requests.exceptions.ConnectionError:
        return build_error_response('consensus', 'Connection failed', additional_fields={'price_target': 'Connection Error'})
    except Exception as e:
        return build_error_response('consensus', str(e)[:50], additional_fields={'price_target': 'Error'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'version': os.getenv('APP_VERSION', '1.0.0')})

@app.route('/get_ratings_stream', methods=['POST'])
def get_ratings_stream():
    if limiter:
        limiter.limit("10 per minute")(lambda: None)()
    ticker = request.json.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify({'error': 'Please enter a ticker symbol'})
    if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', ticker):
        return jsonify({'error': 'Invalid ticker symbol format'})
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_platform = {
                executor.submit(get_zacks_rating, ticker): 'zacks',
                executor.submit(get_tipranks_rating, ticker): 'tipranks',
                executor.submit(get_barchart_rating, ticker): 'barchart',
                executor.submit(get_stockopedia_rating, ticker): 'stockopedia',
                executor.submit(get_stockanalysis_rating, ticker): 'stockanalysis'
            }
            results = {'ticker': ticker, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            for future in concurrent.futures.as_completed(future_to_platform, timeout=45):
                platform = future_to_platform[future]
                try:
                    results[platform] = future.result()
                    app.logger.info(f"Completed {platform} for {ticker}")
                except Exception as e:
                    app.logger.error(f"Error fetching {platform} for {ticker}: {str(e)}")
                    results[platform] = {'rating': 'Error', 'status': f'Error: {str(e)[:50]}', 'success': False}
        return jsonify(results)
    except concurrent.futures.TimeoutError:
        app.logger.error(f"Timeout fetching ratings for {ticker}")
        return jsonify({'error': 'Request timeout - some platforms may be slow'})
    except Exception as e:
        app.logger.error(f"Error fetching ratings for {ticker}: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

@app.route('/get_ratings', methods=['POST'])
def get_ratings():
    if limiter:
        limiter.limit("10 per minute")(lambda: None)()
    ticker = request.json.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify({'error': 'Please enter a ticker symbol'})
    if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', ticker):
        return jsonify({'error': 'Invalid ticker symbol format'})
    results = {'ticker': ticker, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
               'zacks': {'status': 'Fetching...'},  'tipranks': {'status': 'Fetching...'},
               'barchart': {'status': 'Fetching...'}, 'stockopedia': {'status': 'Fetching...'},
               'stockanalysis': {'status': 'Fetching...'}}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_platform = {
                executor.submit(get_zacks_rating, ticker): 'zacks',
                executor.submit(get_tipranks_rating, ticker): 'tipranks',
                executor.submit(get_barchart_rating, ticker): 'barchart',
                executor.submit(get_stockopedia_rating, ticker): 'stockopedia',
                executor.submit(get_stockanalysis_rating, ticker): 'stockanalysis'
            }
            for future in concurrent.futures.as_completed(future_to_platform, timeout=45):
                platform = future_to_platform[future]
                try:
                    results[platform] = future.result()
                    app.logger.info(f"Completed {platform} for {ticker}")
                except Exception as e:
                    app.logger.error(f"Error fetching {platform} for {ticker}: {str(e)}")
                    results[platform] = {'rating': 'Error', 'status': f'Error: {str(e)[:50]}', 'success': False}
        return jsonify(results)
    except concurrent.futures.TimeoutError:
        app.logger.error(f"Timeout fetching ratings for {ticker}")
        return jsonify({'error': 'Request timeout - some platforms may be slow'})
    except Exception as e:
        app.logger.error(f"Error fetching ratings for {ticker}: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

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
