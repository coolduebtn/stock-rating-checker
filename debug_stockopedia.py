#!/usr/bin/env python3
"""
Debug script to test Stockopedia function directly
"""

import requests
import re
import time
import random

def get_stockopedia_rating_debug(ticker):
    """Debug version of the Stockopedia function"""
    try:
        ticker = ticker.upper().strip()
        
        # Stockopedia URL format - using NSQ for NASDAQ stocks (most common US exchange)
        url = f"https://www.stockopedia.com/share-prices/{ticker.lower()}-NSQ:{ticker}/"
        
        print(f"Testing URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Add random delay to appear more human-like
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Response status code: {response.status_code}")
        
        # Handle different response codes
        if response.status_code == 404:
            return {'stockrank': 'N/A', 'style': 'N/A', 'status': 'Stock not found', 'success': False}
        elif response.status_code != 200:
            return {'stockrank': 'N/A', 'style': 'N/A', 'status': f'HTTP {response.status_code}', 'success': False}
        
        # Extract StockRank from JSON data embedded in the page
        stockrank_match = re.search(r'"stockRank":(\d+)', response.text)
        print(f"StockRank regex match: {stockrank_match}")
        
        if stockrank_match:
            stockrank = int(stockrank_match.group(1))
            print(f"Found StockRank: {stockrank}")
            
            # Extract additional useful info
            name_match = re.search(r'"name":"([^"]+)"', response.text)
            style_match = re.search(r'"style":"([^"]+)"', response.text)
            
            print(f"Name match: {name_match}")
            print(f"Style match: {style_match}")
            
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
            
            result = {
                'stockrank': str(stockrank),
                'category': category,
                'style': style_match.group(1) if style_match else 'Unknown',
                'name': name_match.group(1) if name_match else ticker,
                'status': 'Found',
                'success': True
            }
            print(f"Returning result: {result}")
            return result
        else:
            print("No StockRank found in response")
            # Check if the page loaded but just doesn't have StockRank data
            if ticker.upper() in response.text:
                print("Ticker found in response text")
                return {'stockrank': 'NR', 'style': 'Not Rated', 'status': 'Stock found but not rated', 'success': True}
            else:
                print("Ticker not found in response text")
                return {'stockrank': 'N/A', 'style': 'N/A', 'status': 'Stock not found', 'success': False}
        
    except Exception as e:
        print(f"Exception occurred: {e}")
        return {'stockrank': 'Error', 'style': 'Error', 'status': str(e)[:50], 'success': False}

if __name__ == "__main__":
    result = get_stockopedia_rating_debug('AAPL')
    print(f"\nFinal result: {result}")
