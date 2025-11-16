#!/usr/bin/env python3
"""
Quick test script to verify Barchart percentage extraction
"""

import sys
import os

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_rating_app import get_barchart_rating
import json

def test_barchart_rating(ticker):
    """Test the Barchart rating function with percentage extraction"""
    print(f"Testing Barchart rating for {ticker}...")
    result = get_barchart_rating(ticker)
    
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print(f"✅ Successfully got rating: {result.get('rating')}")
        if 'score' in result:
            print(f"✅ Successfully got percentage score: {result.get('score')}")
        else:
            print("⚠️ No percentage score found")
        if 'opinion_text' in result:
            print(f"📝 Full opinion text: {result.get('opinion_text')}")
    else:
        print(f"❌ Failed: {result.get('status')}")
    
    return result

if __name__ == "__main__":
    # Test with a few common tickers
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    
    for ticker in test_tickers:
        print("\n" + "="*50)
        test_barchart_rating(ticker)
        print("="*50)