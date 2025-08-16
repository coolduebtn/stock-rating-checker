#!/usr/bin/env python3
"""
Test script to check Stockopedia StockRank data extraction
"""

import requests
import re
import json
from bs4 import BeautifulSoup

def get_stockopedia_stockrank(symbol):
    """
    Extract StockRank from Stockopedia for a given stock symbol
    
    Args:
        symbol (str): Stock symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        dict: Contains stockrank value and additional info, or error message
    """
    try:
        # Format the URL - Stockopedia uses NSQ:SYMBOL format for NASDAQ stocks
        url = f"https://www.stockopedia.com/share-prices/{symbol.lower()}-NSQ:{symbol.upper()}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"Fetching data for {symbol} from: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Method 1: Try to extract StockRank from JSON data
        stockrank_match = re.search(r'"stockRank":(\d+)', response.text)
        if stockrank_match:
            stockrank = int(stockrank_match.group(1))
            print(f"✅ Found StockRank: {stockrank}")
            
            # Try to extract additional useful info
            name_match = re.search(r'"name":"([^"]+)"', response.text)
            price_match = re.search(r'"lastClosePrice":"([^"]+)"', response.text)
            style_match = re.search(r'"style":"([^"]+)"', response.text)
            
            return {
                'symbol': symbol,
                'stockrank': stockrank,
                'name': name_match.group(1) if name_match else 'Unknown',
                'price': price_match.group(1) if price_match else 'Unknown',
                'style': style_match.group(1) if style_match else 'Unknown',
                'source': 'Stockopedia',
                'success': True
            }
        else:
            print(f"❌ Could not find StockRank in response")
            return {
                'symbol': symbol,
                'error': 'StockRank not found in response',
                'success': False
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {
            'symbol': symbol,
            'error': f'Request failed: {str(e)}',
            'success': False
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {
            'symbol': symbol,
            'error': f'Unexpected error: {str(e)}',
            'success': False
        }

def test_multiple_stocks():
    """Test StockRank extraction for multiple stocks"""
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    print("Testing Stockopedia StockRank extraction...")
    print("=" * 50)
    
    results = []
    for symbol in test_symbols:
        print(f"\nTesting {symbol}:")
        result = get_stockopedia_stockrank(symbol)
        results.append(result)
        
        if result['success']:
            print(f"✅ {result['name']} ({symbol}): StockRank {result['stockrank']} - {result['style']}")
        else:
            print(f"❌ {symbol}: {result['error']}")
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\nSuccessful extractions:")
        for result in successful:
            print(f"  {result['symbol']}: {result['stockrank']} ({result['style']})")
    
    if failed:
        print("\nFailed extractions:")
        for result in failed:
            print(f"  {result['symbol']}: {result['error']}")
    
    return results

if __name__ == "__main__":
    test_multiple_stocks()
