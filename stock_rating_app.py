from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import concurrent.futures
import threading
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

def get_stock_price(ticker):
    """Fetch current stock price and daily change using Zacks"""
    try:
        ticker = normalize_ticker(ticker)
        url = f"https://www.zacks.com/stock/quote/{ticker}"
        
        response, error = make_request(url, headers=HEADERS_STANDARD, timeout=10)
        if error:
            return build_error_response('current_price', error['status'], 
                                      additional_fields={'change': 'N/A', 'change_percent': 'N/A', 
                                                       'currency': 'USD', 'stock_name': ticker})
        
        if response.status_code != 200:
            status_error = handle_http_status(response.status_code)
            if status_error:
                return {**status_error, 'current_price': 'N/A', 'change': 'N/A', 
                       'change_percent': 'N/A', 'currency': 'USD', 'stock_name': ticker}
        
        soup = get_page_soup(response)
        
        # Extract stock name from H1 title
        stock_name = ticker  # Default fallback
        h1_elements = soup.find_all('h1')
        for h1 in h1_elements:
            text = h1.get_text(strip=True)
            if ticker in text and '(' in text and ')' in text:
                # Extract company name before ticker in parentheses
                stock_name = text.split('(')[0].strip()
                break
        
        # Extract current price from .last_price
        price_element = soup.find(class_='last_price')
        current_price = None
        currency = 'USD'
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            # Extract price from format like "$272.41USD"
            import re
            price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if price_match:
                current_price = float(price_match.group(1).replace(',', ''))
            
            # Extract currency if present
            if 'USD' in price_text:
                currency = 'USD'
            elif 'EUR' in price_text:
                currency = 'EUR'
            elif 'GBP' in price_text:
                currency = 'GBP'
        
        # Extract change from .change element
        change_element = soup.find(class_='change')
        change = None
        change_percent = None
        
        if change_element:
            change_text = change_element.get_text(strip=True)
            # Parse format like "-0.54 (-0.20%)"
            import re
            change_match = re.search(r'([+-]?[\d.]+)\s*\(([+-]?[\d.]+)%\)', change_text)
            if change_match:
                change = float(change_match.group(1))
                change_percent = float(change_match.group(2))
        
        if current_price is not None:
            previous_close = round(current_price - (change if change else 0), 2)
            
            return {
                'current_price': round(current_price, 2),
                'previous_close': previous_close,
                'change': round(change, 2) if change is not None else 'N/A',
                'change_percent': round(change_percent, 2) if change_percent is not None else 'N/A',
                'currency': currency,
                'stock_name': stock_name,
                'success': True,
                'status': 'Found'
            }
        else:
            # Check if it's a valid stock page
            if ticker in str(soup):
                return {
                    'current_price': 'N/A',
                    'change': 'N/A',
                    'change_percent': 'N/A',
                    'currency': 'USD',
                    'stock_name': stock_name,
                    'success': False,
                    'status': 'Price data not available'
                }
            else:
                return build_error_response('current_price', 'Stock not found',
                                          additional_fields={'change': 'N/A', 'change_percent': 'N/A',
                                                           'currency': 'USD', 'stock_name': ticker})
            
    except Exception as e:
        return {
            'current_price': 'N/A',
            'change': 'N/A',
            'change_percent': 'N/A', 
            'currency': 'USD',
            'stock_name': ticker,  # Fallback to ticker if error
            'success': False,
            'status': f'Error: {str(e)[:50]}'
        }

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
    """Fetch Barchart opinion/signal rating with percentage score"""
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
        
        # Look for Barchart Opinion/Signal rating and percentage
        rating = None
        percentage_score = None
        full_opinion_text = None
        
        # Get the full page text first for percentage extraction
        page_text = soup.get_text().lower()
        
        # Method 1: Technical Opinion Widget
        technical_opinion = soup.find('div', class_='technical-opinion-widget')
        if technical_opinion:
            rating_link = technical_opinion.find('a', href=re.compile(r'/opinion'))
            if rating_link:
                rating_text = rating_link.get_text(strip=True)
                full_opinion_text = rating_text
                rating_text_lower = rating_text.lower()
                rating_text_lower = re.sub(r'\s+', ' ', rating_text_lower)
                rating = find_keywords_in_text(rating_text_lower, BARCHART_RATING_KEYWORDS)
        
        # Always search for percentage in the full page text regardless of where we found the rating
        percentage_patterns = [
            r'(?:technical\s+opinion\s+rating\s+is\s+a?\s*)?(\d+)%\s*(buy|sell|hold|strong\s+buy|strong\s+sell)',
            r'(\d+)\s*%\s*(buy|sell|hold)',
            r'technical.*?(\d+)\s*%.*?(buy|sell|hold)',
            r'opinion.*?(\d+)\s*%.*?(buy|sell|hold)'
        ]
        
        for pattern in percentage_patterns:
            percentage_match = re.search(pattern, page_text)
            if percentage_match:
                potential_percentage = percentage_match.group(1)
                rating_from_percentage = percentage_match.group(2)
                
                # Map the percentage rating to our standard format
                mapped_percentage_rating = find_keywords_in_text(rating_from_percentage, BARCHART_RATING_KEYWORDS)
                
                # Use this percentage if it's compatible with our found rating or if we don't have a rating yet
                # Consider "Buy" and "Strong Buy" as compatible, "Sell" and "Strong Sell" as compatible
                is_compatible = False
                if not rating:
                    is_compatible = True  # Use any percentage if we don't have a rating
                elif rating and mapped_percentage_rating:
                    # Check for compatible ratings
                    if ('buy' in rating.lower() and 'buy' in mapped_percentage_rating.lower()) or \
                       ('sell' in rating.lower() and 'sell' in mapped_percentage_rating.lower()) or \
                       ('hold' in rating.lower() and 'hold' in mapped_percentage_rating.lower()) or \
                       (rating == mapped_percentage_rating):
                        is_compatible = True
                
                if is_compatible:
                    percentage_score = potential_percentage
                    if not rating:
                        rating = mapped_percentage_rating
                    break
        
        # Method 2: Main rating element (if not found in technical opinion widget)
        if not rating:
            rating_element = soup.find('div', class_=['rating', 'buy']) or \
                            soup.find('div', class_=['rating', 'sell']) or \
                            soup.find('div', class_=['rating', 'hold'])
            if rating_element:
                rating_text = rating_element.get_text(strip=True)
                full_opinion_text = rating_text
                rating_text_lower = rating_text.lower()
                rating = find_keywords_in_text(rating_text_lower, BARCHART_RATING_KEYWORDS)
        
        # Method 3: Selector-based search (if still not found)
        if not rating:
            rating_selectors = [
                '[class*="opinion"]', '[class*="signal"]', '[class*="rating"]',
                '[class*="recommendation"]', '[data-ng-bind*="opinion"]',
                '.bc-opinion', '.opinion-text', '[class*="analyst"]'
            ]
            for selector in rating_selectors:
                rating_elements = soup.select(selector)
                for element in rating_elements:
                    text = element.get_text(strip=True)
                    full_opinion_text = text
                    text_lower = text.lower()
                    rating = find_keywords_in_text(text_lower, BARCHART_RATING_KEYWORDS)
                    if rating:
                        break
                if rating:
                    break
        
        # Method 4: Page text search with context (final fallback)
        if not rating:
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
                result = {'rating': rating}
                if percentage_score:
                    result['score'] = f"{percentage_score}%"
                if full_opinion_text and len(full_opinion_text) > len(rating):
                    # Store full opinion text for debugging/reference
                    result['opinion_text'] = full_opinion_text
                return build_success_response(result)
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
        'price': {'status': 'Fetching...'},
        'zacks': {'status': 'Fetching...'},
        'tipranks': {'status': 'Fetching...'},
        'barchart': {'status': 'Fetching...'},
        'stockopedia': {'status': 'Fetching...'},
        'stockanalysis': {'status': 'Fetching...'}
    }
    
    try:
        print(f"Fetching ratings for {ticker} using parallel execution...")
        start_time = datetime.now()
        
        # Define all functions to run in parallel
        fetch_functions = {
            'price': lambda: get_stock_price(ticker),
            'zacks': lambda: get_zacks_rating(ticker),
            'tipranks': lambda: get_tipranks_rating(ticker),
            'barchart': lambda: get_barchart_rating(ticker),
            'stockopedia': lambda: get_stockopedia_rating(ticker),
            'stockanalysis': lambda: get_stockanalysis_rating(ticker)
        }
        
        # Execute all functions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all tasks
            future_to_platform = {
                executor.submit(func): platform 
                for platform, func in fetch_functions.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    result = future.result(timeout=15)  # 15 second timeout per request
                    results[platform] = result
                    print(f"✓ {platform.title()} completed")
                except Exception as e:
                    print(f"✗ {platform.title()} failed: {str(e)[:50]}")
                    results[platform] = {
                        'status': f'Error: {str(e)[:50]}',
                        'success': False,
                        'rating': 'Error' if platform != 'price' else 'N/A'
                    }
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        print(f"Parallel execution completed in {execution_time:.2f}s")
        
        # Update timestamp to reflect actual completion time
        results['timestamp'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)
