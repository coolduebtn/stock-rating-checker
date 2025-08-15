import requests
from bs4 import BeautifulSoup
import sys

def debug_zacks_page(ticker):
    """Debug what we're getting from Zacks page"""
    url = f"https://www.zacks.com/stock/quote/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for rank in different ways
    print("\n1. Looking for rank_view class:")
    rank_views = soup.find_all('p', class_='rank_view')
    print(f"   Found {len(rank_views)} elements with class 'rank_view'")
    for rv in rank_views[:2]:  # Show first 2
        print(f"   Content: {rv.get_text(strip=True)[:100]}")
    
    print("\n2. Looking for rank_chip span:")
    rank_chips = soup.find_all('span', class_='rank_chip')
    print(f"   Found {len(rank_chips)} elements with class 'rank_chip'")
    for rc in rank_chips[:2]:
        print(f"   Content: {rc.get_text(strip=True)}")
    
    print("\n3. Looking for text containing 'Zacks Rank':")
    zacks_texts = soup.find_all(string=lambda text: 'Zacks Rank' in text if text else False)
    print(f"   Found {len(zacks_texts)} text nodes containing 'Zacks Rank'")
    for zt in zacks_texts[:3]:
        print(f"   Text: {zt.strip()[:100]}")
    
    print("\n4. Looking for any element containing rank number:")
    import re
    rank_pattern = re.compile(r'Rank #?(\d)')
    rank_elements = soup.find_all(string=rank_pattern)
    print(f"   Found {len(rank_elements)} elements matching rank pattern")
    for re_elem in rank_elements[:3]:
        print(f"   Text: {re_elem.strip()[:100]}")
    
    # Save HTML for manual inspection
    with open(f'{ticker}_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print(f"\nSaved HTML to {ticker}_page.html for inspection")

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "CCL"
    debug_zacks_page(ticker)