from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from common import (
    normalize_ticker, is_foreign_ticker, add_human_delay, make_request,
    handle_http_status, get_page_soup, validate_stock_page, ticker_in_page,
    find_element_by_selectors, extract_text_by_selectors, extract_number_from_text,
    find_keywords_in_text, search_text_with_context, validate_score_range,
    map_score_to_rating, find_json_value, find_all_regex_matches,
    build_error_response, build_success_response, extract_stock_analysis_data,
    HEADERS_STANDARD, HEADERS_COMPREHENSIVE, RATING_KEYWORDS, BARCHART_RATING_KEYWORDS,
    STOCKANALYSIS_RATING_KEYWORDS
)

app = Flask(__name__)

def get_zacks_rating(ticker):
    """Fetch Zacks rating - confirmed working method"""
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
        
        # Method 1: Look for rank_view with rank_chip (confirmed working)
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
            
            # Map to rating
            rank_mapping = {
                '1': 'Strong Buy', '2': 'Buy', '3': 'Hold',
                '4': 'Sell', '5': 'Strong Sell'
            }
            
            if rank and rank in rank_mapping:
                return build_success_response({
                    'rank': rank,
                    'rating': rank_mapping[rank]
                })
        
        # If no rank found, check if it's a valid stock page
        if soup.find('h1') and ticker in str(soup.find('h1')):
            return {'rank': 'NR', 'rating': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
        else:
            return build_error_response('rank', 'Stock not found')
        
    except Exception as e:
        return build_error_response('rank', str(e)[:50])

def get_tipranks_rating(ticker):
    """Fetch TipRanks Smart Score and rating with improved rate limiting and error handling"""
    try:
        ticker = normalize_ticker(ticker)
        
        if is_foreign_ticker(ticker):
            return build_error_response('score', 'Foreign ticker', additional_fields={'rating': 'Foreign/OTC'})
        
        url = f"https://www.tipranks.com/stocks/{ticker.lower()}"
        
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('score', error['status'], additional_fields={'rating': 'Error'})
        
        # Handle different error codes
        status_error = handle_http_status(response.status_code, {
            471: build_error_response('score', 'Site blocking requests', additional_fields={'rating': 'Access Blocked'}),
            403: build_error_response('score', 'Access forbidden', additional_fields={'rating': 'Forbidden'}),
            429: build_error_response('score', 'Too many requests', additional_fields={'rating': 'Rate Limited'}),
            404: build_error_response('score', 'Stock not found'),
        })
        if status_error:
            return status_error
        
        soup = get_page_soup(response)
        
        # Validate page
        is_valid, title_text = validate_stock_page(soup, ticker)
        if not is_valid:
            return build_error_response('score', 'Stock not found')
        
        if not ticker_in_page(ticker, title_text):
            return build_error_response('score', 'Stock not found')
        
        # Look for Smart Score
        score = None
        score_selectors = [
            'span[data-testid="smart-score-text"]', '.smart-score-text',
            '[class*="smart-score"]', '[class*="smartScore"]',
            '[data-testid*="score"]', '.score-text', '[class*="score-value"]'
        ]
        
        for selector in score_selectors:
            score_element = find_element_by_selectors(soup, [selector])
            if score_element:
                score_text = score_element.get_text(strip=True)
                score_num = extract_number_from_text(score_text)
                if score_num and validate_score_range(score_num):
                    score = str(score_num)
                    break
        
        # Fallback: search in page text
        if not score:
            page_text = soup.get_text()
            score_patterns = [r'Smart Score[:\s]*(\d+)', r'(\d+)/10', r'Score[:\s]*(\d+)']
            for pattern in score_patterns:
                matches = find_all_regex_matches(page_text, pattern)
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
        
        # Look for rating
        rating_selectors = [
            '[data-testid*="rating"]', '[class*="rating"]', '[class*="sentiment"]',
            '[class*="recommendation"]', '[class*="consensus"]'
        ]
        
        rating = find_keywords_in_text(
            extract_text_by_selectors(soup, rating_selectors) or '',
            RATING_KEYWORDS
        )
        
        # Map score to rating if needed
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
    """Fetch Barchart opinion/signal rating"""
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.barchart.com/stocks/quotes/{ticker.lower()}/overview"
        
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('rating', error['status'])
        
        # Handle error codes
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
        
        # Look for Barchart Opinion/Signal rating
        rating = None
        
        # Method 1: Technical Opinion Widget
        technical_opinion = soup.find('div', class_='technical-opinion-widget')
        if technical_opinion:
            rating_link = technical_opinion.find('a', href=re.compile(r'/opinion'))
            if rating_link:
                rating_text = rating_link.get_text(strip=True).lower()
                rating_text = re.sub(r'\s+', ' ', rating_text)
                rating = find_keywords_in_text(rating_text, BARCHART_RATING_KEYWORDS)
        
        # Method 2: Main rating element
        if not rating:
            rating_element = soup.find('div', class_=['rating', 'buy']) or \
                            soup.find('div', class_=['rating', 'sell']) or \
                            soup.find('div', class_=['rating', 'hold'])
            if rating_element:
                rating_text = rating_element.get_text(strip=True).lower()
                rating = find_keywords_in_text(rating_text, BARCHART_RATING_KEYWORDS)
        
        # Method 3: Selector-based search
        if not rating:
            rating_selectors = [
                '[class*="opinion"]', '[class*="signal"]', '[class*="rating"]',
                '[class*="recommendation"]', '[data-ng-bind*="opinion"]',
                '.bc-opinion', '.opinion-text', '[class*="analyst"]'
            ]
            for selector in rating_selectors:
                rating_elements = soup.select(selector)
                for element in rating_elements:
                    text = element.get_text(strip=True).lower()
                    rating = find_keywords_in_text(text, BARCHART_RATING_KEYWORDS)
                    if rating:
                        break
                if rating:
                    break
        
        # Method 4: Page text search with context
        if not rating:
            page_text = soup.get_text().lower()
            context_patterns = [
                r'(opinion|signal|rating|recommendation|consensus|analyst).*?{keyword}',
                r'{keyword}.*?(opinion|signal|rating|recommendation)',
                r'barchart.*?{keyword}',
                r'{keyword}.*?barchart'
            ]
            rating = search_text_with_context(page_text, BARCHART_RATING_KEYWORDS, context_patterns)
        
        # Check if valid stock page and return appropriate response
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
    """Fetch Stockopedia StockRank - reliable data source without blocking"""
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.stockopedia.com/share-prices/{ticker.lower()}-NSQ:{ticker}/"
        
        response, error = make_request(url, headers=HEADERS_STANDARD, timeout=10)
        if error:
            return build_error_response('stockrank', error['status'], additional_fields={'style': 'N/A'})
        
        # Handle error codes
        status_error = handle_http_status(response.status_code, {
            404: build_error_response('stockrank', 'Stock not found', additional_fields={'style': 'N/A'}),
        })
        if status_error:
            return status_error
        
        # Extract StockRank from JSON data
        stockrank_str = find_json_value(response.text, r'"stockRank":(\d+)')
        if stockrank_str:
            try:
                stockrank = int(stockrank_str)
                
                # Map StockRank to category
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
                
                style = find_json_value(response.text, r'"style":"([^"]+)"')
                
                return build_success_response({
                    'stockrank': str(stockrank),
                    'category': category,
                    'style': style or 'Unknown'
                })
            except (ValueError, TypeError):
                pass
        
        # Check if valid stock page
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
    """Fetch Stock Analysis Analyst Consensus and Price Target"""
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://stockanalysis.com/stocks/{ticker.lower()}/forecast/"
        
        response, error = make_request(url, headers=HEADERS_COMPREHENSIVE, timeout=15)
        if error:
            return build_error_response('consensus', error['status'], additional_fields={'price_target': 'N/A'})
        
        # Handle error codes
        status_error = handle_http_status(response.status_code, {
            403: build_error_response('consensus', 'Access forbidden', additional_fields={'price_target': 'N/A'}),
            429: build_error_response('consensus', 'Too many requests', additional_fields={'price_target': 'N/A'}),
            404: build_error_response('consensus', 'Stock not found', additional_fields={'price_target': 'N/A'}),
        })
        if status_error:
            return status_error
        
        soup = get_page_soup(response)
        
        is_valid, title_text = validate_stock_page(soup, ticker)
        if not is_valid:
            return build_error_response('consensus', 'Stock not found', additional_fields={'price_target': 'N/A'})
        
        if not ticker_in_page(ticker, title_text):
            return build_error_response('consensus', 'Stock not found', additional_fields={'price_target': 'N/A'})
        
        # Extract Stock Analysis data
        analysis_data = extract_stock_analysis_data(soup, ticker)
        
        if not analysis_data:
            return build_error_response('consensus', 'Unable to extract data', additional_fields={'price_target': 'N/A'})
        
        # Build response
        result = {
            'consensus': analysis_data.get('consensus', 'N/A'),
            'price_target': analysis_data.get('price_target', 'N/A'),
            'status': 'Found',
            'success': True
        }
        
        # Add optional fields if available
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
        'stockanalysis': {'status': 'Fetching...'}
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
        
        # Fetch Stock Analysis consensus and price target
        print(f"Fetching Stock Analysis data for {ticker}...")
        stockanalysis_result = get_stockanalysis_rating(ticker)
        results['stockanalysis'] = stockanalysis_result
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)
