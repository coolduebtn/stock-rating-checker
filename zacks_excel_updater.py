import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sys

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
            return {'Zacks_Rank': 'N/A', 'Zacks_Rating': 'N/A', 'Note': f'HTTP {response.status_code}'}
        
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
                import re
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
                    'Zacks_Rank': rank,
                    'Zacks_Rating': rank_mapping[rank],
                    'Note': 'Found'
                }
        
        # If no rank found, check if it's a valid stock page
        if soup.find('h1') and ticker.upper() in str(soup.find('h1')):
            return {'Zacks_Rank': 'NR', 'Zacks_Rating': 'Not Rated', 'Note': 'Stock found but not rated'}
        else:
            return {'Zacks_Rank': 'N/A', 'Zacks_Rating': 'N/A', 'Note': 'Stock not found'}
        
    except Exception as e:
        return {'Zacks_Rank': 'Error', 'Zacks_Rating': 'Error', 'Note': str(e)[:30]}

def get_tipranks_rating(ticker):
    """Fetch TipRanks Smart Score and rating with improved rate limiting and error handling"""
    try:
        ticker = ticker.upper().strip()
        
        # Skip obvious foreign/OTC tickers that won't be on TipRanks US site
        foreign_suffixes = ['F', 'Y', 'FF', 'ZY', 'GY', 'SY', 'UY', 'IY', 'LY']
        if any(ticker.endswith(suffix) for suffix in foreign_suffixes):
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'Foreign/OTC', 'Note': 'Foreign ticker'}
        
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
        import random
        time.sleep(random.uniform(1.5, 3.5))
        
        response = requests.get(url, headers=headers, timeout=20)
        
        # Handle different error codes
        if response.status_code == 471:
            return {'TipRanks_Score': 'BLOCKED', 'TipRanks_Rating': 'Access Blocked', 'Note': 'Site blocking automated requests'}
        elif response.status_code == 403:
            return {'TipRanks_Score': 'BLOCKED', 'TipRanks_Rating': 'Forbidden', 'Note': 'Access forbidden'}
        elif response.status_code == 429:
            return {'TipRanks_Score': 'RATE_LIMITED', 'TipRanks_Rating': 'Rate Limited', 'Note': 'Too many requests'}
        elif response.status_code == 404:
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': 'Stock not found'}
        elif response.status_code != 200:
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': f'HTTP {response.status_code}'}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we got a valid stock page first
        page_title = soup.find('title')
        if not page_title:
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': 'Invalid page'}
        
        title_text = page_title.get_text().upper()
        
        # Check for error pages or redirects
        if 'NOT FOUND' in title_text or 'ERROR' in title_text or '404' in title_text:
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': 'Stock not found'}
        
        # Check if ticker is in the title (basic validation)
        if ticker not in title_text and ticker.replace('.', '') not in title_text:
            return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': 'Stock not found'}
        
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
                    import re
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
            import re
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
        
        # Method 4: Search in general text with context validation
        if not rating:
            page_text = soup.get_text().lower()
            for keyword, mapped_rating in rating_keywords.items():
                if keyword in page_text:
                    # Try to find it in context to make sure it's a rating
                    import re
                    context_patterns = [
                        f'(analyst|recommendation|rating|consensus|sentiment|outlook).*?{keyword}',
                        f'{keyword}.*?(rating|recommendation|outlook)',
                        f'tipranks.*?{keyword}'
                    ]
                    for pattern in context_patterns:
                        if re.search(pattern, page_text):
                            rating = mapped_rating
                            break
                    if rating:
                        break
        
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
                'TipRanks_Score': score,
                'TipRanks_Rating': rating or 'N/A',
                'Note': 'Found'
            }
        else:
            # Check if the stock page exists but just doesn't have a Smart Score
            if ticker in title_text:
                return {'TipRanks_Score': 'NR', 'TipRanks_Rating': 'Not Rated', 'Note': 'Stock found but no Smart Score'}
            else:
                return {'TipRanks_Score': 'N/A', 'TipRanks_Rating': 'N/A', 'Note': 'Stock not found'}
        
    except requests.exceptions.Timeout:
        return {'TipRanks_Score': 'TIMEOUT', 'TipRanks_Rating': 'Timeout', 'Note': 'Request timeout'}
    except requests.exceptions.ConnectionError:
        return {'TipRanks_Score': 'CONN_ERROR', 'TipRanks_Rating': 'Connection Error', 'Note': 'Connection failed'}
    except Exception as e:
        return {'TipRanks_Score': 'Error', 'TipRanks_Rating': 'Error', 'Note': str(e)[:30]}

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
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        
        # Add random delay to appear more human-like
        import random
        time.sleep(random.uniform(1.0, 2.5))
        
        response = requests.get(url, headers=headers, timeout=20)
        
        # Handle different error codes
        if response.status_code == 403:
            return {'Barchart_Rating': 'Forbidden', 'Note': 'Access forbidden'}
        elif response.status_code == 429:
            return {'Barchart_Rating': 'Rate Limited', 'Note': 'Too many requests'}
        elif response.status_code == 404:
            return {'Barchart_Rating': 'N/A', 'Note': 'Stock not found'}
        elif response.status_code != 200:
            return {'Barchart_Rating': 'N/A', 'Note': f'HTTP {response.status_code}'}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we got a valid stock page first
        page_title = soup.find('title')
        if not page_title:
            return {'Barchart_Rating': 'N/A', 'Note': 'Invalid page'}
        
        title_text = page_title.get_text().upper()
        
        # Check for error pages or redirects
        if 'NOT FOUND' in title_text or 'ERROR' in title_text or '404' in title_text:
            return {'Barchart_Rating': 'N/A', 'Note': 'Stock not found'}
        
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
                            import re
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
                    import re
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
        
        # Method 3: Look for specific Barchart opinion classes or IDs
        if not rating:
            try:
                # Look for common Barchart opinion elements
                opinion_elements = soup.find_all(['span', 'div', 'td'], 
                    text=re.compile(r'(strong\s+buy|strong\s+sell|buy|sell|hold|neutral)', re.IGNORECASE))
                
                for element in opinion_elements:
                    text = element.get_text(strip=True).lower()
                    for keyword, mapped_rating in rating_keywords.items():
                        if keyword in text:
                            rating = mapped_rating
                            break
                    if rating:
                        break
            except:
                pass
        
        # Check if it's a valid stock page by looking for the ticker
        if ticker.lower() in title_text.lower() or ticker.upper() in title_text:
            if rating:
                return {
                    'Barchart_Rating': rating,
                    'Note': 'Found'
                }
            else:
                return {'Barchart_Rating': 'Not Rated', 'Note': 'Stock found but no rating'}
        else:
            return {'Barchart_Rating': 'N/A', 'Note': 'Stock not found'}
        
    except requests.exceptions.Timeout:
        return {'Barchart_Rating': 'Timeout', 'Note': 'Request timeout'}
    except requests.exceptions.ConnectionError:
        return {'Barchart_Rating': 'Connection Error', 'Note': 'Connection failed'}
    except Exception as e:
        return {'Barchart_Rating': 'Error', 'Note': str(e)[:30]}

def process_csv_file(csv_file):
    """Process CSV file and add Zacks, TipRanks, and Barchart ratings"""
    print(f"\nProcessing: {csv_file}")
    
    # Detect delimiter
    with open(csv_file, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
    
    # Read CSV
    df = pd.read_csv(csv_file, delimiter=delimiter)
    print(f"Loaded {len(df)} rows")
    
    # Find ticker column
    ticker_column = None
    for col in df.columns:
        if 'symbol' in col.lower() or 'ticker' in col.lower():
            ticker_column = col
            break
    
    if not ticker_column:
        print("\nColumns:", list(df.columns))
        col_num = input("Which column number has tickers? (1-based): ")
        ticker_column = df.columns[int(col_num) - 1]
    
    print(f"Using ticker column: {ticker_column}")
    
    # Add new columns
    df['Zacks_Rank'] = ''
    df['Zacks_Rating'] = ''
    df['TipRanks_Score'] = ''
    df['TipRanks_Rating'] = ''
    df['Barchart_Rating'] = ''
    df['Last_Updated'] = ''
    
    # Track fetch notes internally but don't add to CSV
    fetch_notes = {}
    tipranks_notes = {}
    barchart_notes = {}
    
    # Statistics
    stats = {
        'Strong Buy': 0,
        'Buy': 0,
        'Hold': 0,
        'Sell': 0,
        'Strong Sell': 0,
        'Not Rated': 0,
        'Not Found': 0,
        'Error': 0
    }
    
    tipranks_stats = {
        'Outperform': 0,
        'Neutral': 0,
        'Underperform': 0,
        'Not Rated': 0,
        'Not Found': 0,
        'Error': 0,
        'Blocked': 0,
        'Foreign/OTC': 0,
        'Rate Limited': 0,
        'Timeout': 0
    }
    
    barchart_stats = {
        'Strong Buy': 0,
        'Buy': 0,
        'Hold': 0,
        'Sell': 0,
        'Strong Sell': 0,
        'Not Rated': 0,
        'Not Found': 0,
        'Error': 0,
        'Rate Limited': 0,
        'Timeout': 0
    }
    
    print(f"\nFetching Zacks, TipRanks, and Barchart ratings...")
    print(f"Estimated time: {len(df) * 8 / 60:.1f} minutes (with improved delays)\n")
    
    # Process each ticker
    for idx, row in df.iterrows():
        ticker = str(row[ticker_column]).strip()
        
        if not ticker or ticker == 'nan':
            continue
        
        print(f"[{idx+1}/{len(df)}] {ticker:<8}...", end='', flush=True)
        
        # Fetch Zacks rating
        zacks_result = get_zacks_rating(ticker)
        df.at[idx, 'Zacks_Rank'] = zacks_result['Zacks_Rank']
        df.at[idx, 'Zacks_Rating'] = zacks_result['Zacks_Rating']
        
        # Store fetch note internally for reporting
        fetch_notes[ticker] = zacks_result['Note']
        
        # Update Zacks stats
        if zacks_result['Note'] == 'Found':
            stats[zacks_result['Zacks_Rating']] += 1
            zacks_status = f"Z:{zacks_result['Zacks_Rank']}"
        elif zacks_result['Note'] == 'Stock found but not rated':
            stats['Not Rated'] += 1
            zacks_status = "Z:NR"
        elif 'Error' in zacks_result['Zacks_Rating']:
            stats['Error'] += 1
            zacks_status = "Z:Err"
        else:
            stats['Not Found'] += 1
            zacks_status = "Z:NF"
        
        # Short delay between requests
        time.sleep(1)
        
        # Fetch TipRanks rating (includes its own random delay)
        tipranks_result = get_tipranks_rating(ticker)
        df.at[idx, 'TipRanks_Score'] = tipranks_result['TipRanks_Score']
        df.at[idx, 'TipRanks_Rating'] = tipranks_result['TipRanks_Rating']
        
        # Store TipRanks fetch note internally for reporting
        tipranks_notes[ticker] = tipranks_result['Note']
        
        # Update TipRanks stats
        if tipranks_result['Note'] == 'Found':
            tipranks_stats[tipranks_result['TipRanks_Rating']] += 1
            tipranks_status = f"T:{tipranks_result['TipRanks_Score']}"
        elif tipranks_result['Note'] == 'Stock found but no Smart Score':
            tipranks_stats['Not Rated'] += 1
            tipranks_status = "T:NR"
        elif tipranks_result['Note'] == 'Foreign ticker':
            tipranks_stats['Foreign/OTC'] += 1
            tipranks_status = "T:Foreign"
        elif tipranks_result['Note'] == 'Site blocking automated requests':
            tipranks_stats['Blocked'] += 1
            tipranks_status = "T:Block"
        elif tipranks_result['Note'] == 'Too many requests':
            tipranks_stats['Rate Limited'] += 1
            tipranks_status = "T:RateLimit"
        elif tipranks_result['Note'] == 'Request timeout':
            tipranks_stats['Timeout'] += 1
            tipranks_status = "T:Timeout"
        elif 'Error' in tipranks_result['TipRanks_Rating']:
            tipranks_stats['Error'] += 1
            tipranks_status = "T:Err"
        else:
            tipranks_stats['Not Found'] += 1
            tipranks_status = "T:NF"
        
        # Short delay before Barchart
        time.sleep(1)
        
        # Fetch Barchart rating (includes its own random delay)
        barchart_result = get_barchart_rating(ticker)
        df.at[idx, 'Barchart_Rating'] = barchart_result['Barchart_Rating']
        df.at[idx, 'Last_Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Store Barchart fetch note internally for reporting
        barchart_notes[ticker] = barchart_result['Note']
        
        # Update Barchart stats
        if barchart_result['Note'] == 'Found':
            barchart_stats[barchart_result['Barchart_Rating']] += 1
            barchart_status = f"B:{barchart_result['Barchart_Rating'][:3]}"
        elif barchart_result['Note'] == 'Stock found but no rating':
            barchart_stats['Not Rated'] += 1
            barchart_status = "B:NR"
        elif barchart_result['Note'] == 'Too many requests':
            barchart_stats['Rate Limited'] += 1
            barchart_status = "B:RateLimit"
        elif barchart_result['Note'] == 'Request timeout':
            barchart_stats['Timeout'] += 1
            barchart_status = "B:Timeout"
        elif 'Error' in barchart_result['Barchart_Rating']:
            barchart_stats['Error'] += 1
            barchart_status = "B:Err"
        else:
            barchart_stats['Not Found'] += 1
            barchart_status = "B:NF"
        
        print(f" {zacks_status} | {tipranks_status} | {barchart_status}")
        
        # If we hit rate limiting, add extra delay
        rate_limited = any(result['Note'] in ['Too many requests', 'Site blocking automated requests'] 
                          for result in [tipranks_result, barchart_result])
        
        if rate_limited:
            print(f"  ⚠️  Rate limited - adding 10 second delay...")
            time.sleep(10)
        else:
            # Normal delay between requests (1-3 seconds)
            import random
            time.sleep(random.uniform(1, 3))
    
    # Save results
    output_file = csv_file.replace('.csv', '_zacks_tipranks_barchart_complete.csv')
    df.to_csv(output_file, index=False, sep=delimiter)
    print(f"\n✅ Saved to: {output_file}")
    
    # Display comprehensive results
    print("\n" + "="*120)
    print("COMPLETE ZACKS, TIPRANKS & BARCHART RATINGS RESULTS")
    print("="*120)
    
    # Show all stocks with ratings
    print("\n📊 STOCKS WITH ZACKS, TIPRANKS & BARCHART RATINGS:")
    print("-"*120)
    
    for rating in ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']:
        stocks = df[df['Zacks_Rating'] == rating]
        if len(stocks) > 0:
            print(f"\n{rating.upper()} (Zacks Rank {list('12345')['Strong Buy,Buy,Hold,Sell,Strong Sell'.split(',').index(rating)]}) - {len(stocks)} stocks:")
            for _, row in stocks.iterrows():
                company = str(row.get('Company Name', 'N/A'))[:30]
                price = str(row.get('Price', 'N/A'))[:8]
                tipranks_score = str(row['TipRanks_Score'])
                tipranks_rating = str(row['TipRanks_Rating'])[:12]
                barchart_rating = str(row['Barchart_Rating'])[:12]
                print(f"  {row[ticker_column]:<8} | {company:<30} | Price: {price:<8} | TipRanks: {tipranks_score}/10 ({tipranks_rating}) | Barchart: {barchart_rating}")
    
    # Show TipRanks specific ratings
    print("\n📈 TIPRANKS SMART SCORE DISTRIBUTION:")
    print("-"*120)
    
    for rating in ['Outperform', 'Neutral', 'Underperform']:
        stocks = df[df['TipRanks_Rating'] == rating]
        if len(stocks) > 0:
            scores = stocks['TipRanks_Score'].tolist()
            avg_score = sum([int(s) for s in scores if s.isdigit()]) / len([s for s in scores if s.isdigit()]) if any(s.isdigit() for s in scores) else 0
            print(f"\n{rating.upper()} - {len(stocks)} stocks (Avg Score: {avg_score:.1f}):")
            for _, row in stocks.iterrows():
                company = str(row.get('Company Name', 'N/A'))[:30]
                zacks_rank = str(row['Zacks_Rank'])
                zacks_rating = str(row['Zacks_Rating'])[:12]
                tipranks_score = str(row['TipRanks_Score'])
                barchart_rating = str(row['Barchart_Rating'])[:12]
                print(f"  {row[ticker_column]:<8} | {company:<30} | Score: {tipranks_score}/10 | Zacks: R{zacks_rank} ({zacks_rating}) | Barchart: {barchart_rating}")
    
    # Show Barchart specific ratings
    print("\n📊 BARCHART OPINION DISTRIBUTION:")
    print("-"*120)
    
    for rating in ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']:
        stocks = df[df['Barchart_Rating'] == rating]
        if len(stocks) > 0:
            print(f"\n{rating.upper()} - {len(stocks)} stocks:")
            for _, row in stocks.iterrows():
                company = str(row.get('Company Name', 'N/A'))[:30]
                zacks_rank = str(row['Zacks_Rank'])
                zacks_rating = str(row['Zacks_Rating'])[:12]
                tipranks_score = str(row['TipRanks_Score'])
                tipranks_rating = str(row['TipRanks_Rating'])[:12]
                print(f"  {row[ticker_column]:<8} | {company:<30} | Zacks: R{zacks_rank} ({zacks_rating}) | TipRanks: {tipranks_score}/10 ({tipranks_rating})")
    
    # Show unrated stocks
    print("\n⚠️  STOCKS WITHOUT RATINGS:")
    print("-"*120)
    
    # Zacks not rated but found
    zacks_not_rated = df[df['Zacks_Rating'] == 'Not Rated']
    if len(zacks_not_rated) > 0:
        print(f"\nZacks - Found but Not Rated ({len(zacks_not_rated)} stocks):")
        tickers = zacks_not_rated[ticker_column].tolist()
        print(", ".join(tickers))
    
    # TipRanks not rated but found
    tipranks_not_rated = df[df['TipRanks_Rating'] == 'Not Rated']
    if len(tipranks_not_rated) > 0:
        print(f"\nTipRanks - Found but No Smart Score ({len(tipranks_not_rated)} stocks):")
        tickers = tipranks_not_rated[ticker_column].tolist()
        print(", ".join(tickers))
    
    # Barchart not rated but found
    barchart_not_rated = df[df['Barchart_Rating'] == 'Not Rated']
    if len(barchart_not_rated) > 0:
        print(f"\nBarchart - Found but No Rating ({len(barchart_not_rated)} stocks):")
        tickers = barchart_not_rated[ticker_column].tolist()
        print(", ".join(tickers))
    
    # Not found on Zacks
    zacks_not_found = [ticker for ticker, note in fetch_notes.items() if note == 'Stock not found']
    if zacks_not_found:
        print(f"\nNot Found on Zacks ({len(zacks_not_found)} stocks):")
        print(", ".join(zacks_not_found))
    
    # Not found on TipRanks
    tipranks_not_found = [ticker for ticker, note in tipranks_notes.items() if note == 'Stock not found']
    if tipranks_not_found:
        print(f"\nNot Found on TipRanks ({len(tipranks_not_found)} stocks):")
        print(", ".join(tipranks_not_found))
    
    # Not found on Barchart
    barchart_not_found = [ticker for ticker, note in barchart_notes.items() if note == 'Stock not found']
    if barchart_not_found:
        print(f"\nNot Found on Barchart ({len(barchart_not_found)} stocks):")
        print(", ".join(barchart_not_found))
    
    # Summary statistics
    print("\n" + "="*120)
    print("SUMMARY STATISTICS")
    print("="*120)
    
    # Zacks stats
    zacks_total_rated = sum(stats[r] for r in ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'])
    print(f"Total Stocks Processed: {len(df)}")
    print(f"\n📊 ZACKS RATINGS:")
    print(f"  Stocks with Zacks Ratings: {zacks_total_rated}")
    print(f"  Stocks without Zacks Ratings: {len(df) - zacks_total_rated}")
    print("  Zacks Rating Distribution:")
    for rating, count in stats.items():
        if count > 0:
            print(f"    {rating}: {count}")
    
    # TipRanks stats
    tipranks_total_rated = sum(tipranks_stats[r] for r in ['Outperform', 'Neutral', 'Underperform'])
    print(f"\n📈 TIPRANKS SMART SCORES:")
    print(f"  Stocks with TipRanks Scores: {tipranks_total_rated}")
    print(f"  Stocks without TipRanks Scores: {len(df) - tipranks_total_rated}")
    print("  TipRanks Rating Distribution:")
    for rating, count in tipranks_stats.items():
        if count > 0:
            print(f"    {rating}: {count}")
    
    # Barchart stats
    barchart_total_rated = sum(barchart_stats[r] for r in ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'])
    print(f"\n📊 BARCHART OPINIONS:")
    print(f"  Stocks with Barchart Ratings: {barchart_total_rated}")
    print(f"  Stocks without Barchart Ratings: {len(df) - barchart_total_rated}")
    print("  Barchart Rating Distribution:")
    for rating, count in barchart_stats.items():
        if count > 0:
            print(f"    {rating}: {count}")
    
    # Combined investment signals
    print(f"\n💡 COMBINED INVESTMENT SIGNALS:")
    
    if zacks_total_rated > 0:
        zacks_buy_signals = stats['Strong Buy'] + stats['Buy']
        zacks_sell_signals = stats['Sell'] + stats['Strong Sell']
        print(f"  Zacks Buy Signals (Rank 1-2): {zacks_buy_signals} stocks")
        print(f"  Zacks Hold (Rank 3): {stats['Hold']} stocks")
        print(f"  Zacks Sell Signals (Rank 4-5): {zacks_sell_signals} stocks")
    
    if tipranks_total_rated > 0:
        print(f"  TipRanks Outperform (Score 8-10): {tipranks_stats['Outperform']} stocks")
        print(f"  TipRanks Neutral (Score 5-7): {tipranks_stats['Neutral']} stocks")
        print(f"  TipRanks Underperform (Score 1-4): {tipranks_stats['Underperform']} stocks")
    
    if barchart_total_rated > 0:
        barchart_buy_signals = barchart_stats['Strong Buy'] + barchart_stats['Buy']
        barchart_sell_signals = barchart_stats['Sell'] + barchart_stats['Strong Sell']
        print(f"  Barchart Buy Signals: {barchart_buy_signals} stocks")
        print(f"  Barchart Hold: {barchart_stats['Hold']} stocks")
        print(f"  Barchart Sell Signals: {barchart_sell_signals} stocks")
    
    # Strong consensus signals across all three platforms
    strong_buy_all = df[(df['Zacks_Rating'].isin(['Strong Buy', 'Buy'])) & 
                       (df['TipRanks_Rating'] == 'Outperform') &
                       (df['Barchart_Rating'].isin(['Strong Buy', 'Buy']))]
    
    strong_buy_two = df[((df['Zacks_Rating'].isin(['Strong Buy', 'Buy'])) & (df['TipRanks_Rating'] == 'Outperform')) |
                       ((df['Zacks_Rating'].isin(['Strong Buy', 'Buy'])) & (df['Barchart_Rating'].isin(['Strong Buy', 'Buy']))) |
                       ((df['TipRanks_Rating'] == 'Outperform') & (df['Barchart_Rating'].isin(['Strong Buy', 'Buy'])))]
    
    strong_sell_all = df[(df['Zacks_Rating'].isin(['Sell', 'Strong Sell'])) & 
                        (df['TipRanks_Rating'] == 'Underperform') &
                        (df['Barchart_Rating'].isin(['Sell', 'Strong Sell']))]
    
    if len(strong_buy_all) > 0:
        print(f"\n🔥 TRIPLE BUY CONSENSUS (All 3 Positive): {len(strong_buy_all)} stocks")
        for _, row in strong_buy_all.iterrows():
            print(f"    {row[ticker_column]} - Zacks: {row['Zacks_Rating']}, TipRanks: {row['TipRanks_Score']}/10, Barchart: {row['Barchart_Rating']}")
    
    # Remove the previous strong_buy_both section and replace with two-way consensus
    strong_buy_two_filtered = strong_buy_two[~strong_buy_two.index.isin(strong_buy_all.index)]
    if len(strong_buy_two_filtered) > 0:
        print(f"\n🔥 DUAL BUY CONSENSUS (2 of 3 Positive): {len(strong_buy_two_filtered)} stocks")
        for _, row in strong_buy_two_filtered.iterrows():
            print(f"    {row[ticker_column]} - Zacks: {row['Zacks_Rating']}, TipRanks: {row['TipRanks_Score']}/10, Barchart: {row['Barchart_Rating']}")
    
    if len(strong_sell_all) > 0:
        print(f"\n⚠️  TRIPLE SELL CONSENSUS (All 3 Negative): {len(strong_sell_all)} stocks")
        for _, row in strong_sell_all.iterrows():
            print(f"    {row[ticker_column]} - Zacks: {row['Zacks_Rating']}, TipRanks: {row['TipRanks_Score']}/10, Barchart: {row['Barchart_Rating']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python zacks_excel_updater.py <csv_file>")
        sys.exit(1)
    
    process_csv_file(sys.argv[1])

if __name__ == "__main__":
    main()