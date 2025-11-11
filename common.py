"""
Common utilities for stock rating fetchers
Reduces code duplication across multiple modules
"""

import requests
import time
import random
import re
from bs4 import BeautifulSoup
from functools import wraps


# ============================================================================
# CONSTANTS
# ============================================================================

# Standard browser headers to avoid blocking
HEADERS_STANDARD = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

HEADERS_COMPREHENSIVE = {
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

# Common rating keywords mapping
RATING_KEYWORDS = {
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

BARCHART_RATING_KEYWORDS = {
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

STOCKANALYSIS_RATING_KEYWORDS = {
    'strong buy': 'Strong Buy',
    'buy': 'Buy',
    'hold': 'Hold',
    'sell': 'Sell',
    'strong sell': 'Strong Sell',
    'bullish': 'Buy',
    'bearish': 'Sell',
    'neutral': 'Hold'
}


# ============================================================================
# STRING UTILITIES
# ============================================================================

def normalize_ticker(ticker):
    """Normalize ticker symbol to uppercase and strip whitespace"""
    return ticker.upper().strip()


def is_foreign_ticker(ticker):
    """Check if ticker appears to be a foreign/OTC listing"""
    foreign_suffixes = ['F', 'Y', 'FF', 'ZY', 'GY', 'SY', 'UY', 'IY', 'LY']
    return any(ticker.endswith(suffix) for suffix in foreign_suffixes)


# ============================================================================
# HTTP REQUEST UTILITIES
# ============================================================================

def add_human_delay(min_delay=0.5, max_delay=1.5):
    """Add random delay to appear more human-like"""
    time.sleep(random.uniform(min_delay, max_delay))


def make_request(url, headers=None, timeout=10, add_delay=True):
    """
    Make HTTP request with standardized error handling and optional human delay
    
    Args:
        url: The URL to request
        headers: HTTP headers dict (defaults to HEADERS_STANDARD)
        timeout: Request timeout in seconds
        add_delay: Whether to add random delay before request
    
    Returns:
        tuple: (response_object, error_dict_or_None)
        - If successful: (response, None)
        - If failed: (None, error_dict)
    """
    if headers is None:
        headers = HEADERS_STANDARD
    
    if add_delay:
        add_human_delay()
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return response, None
    except requests.exceptions.Timeout:
        return None, {'error': 'Timeout', 'status': 'Request timeout', 'success': False}
    except requests.exceptions.ConnectionError:
        return None, {'error': 'Connection Error', 'status': 'Connection failed', 'success': False}
    except Exception as e:
        return None, {'error': 'Error', 'status': str(e)[:50], 'success': False}


def handle_http_status(status_code, custom_checks=None):
    """
    Handle HTTP status codes and return error dict if applicable
    
    Args:
        status_code: HTTP status code
        custom_checks: Dict of {status_code: error_dict} for custom handling
    
    Returns:
        error_dict or None (None means status code is OK)
    """
    if custom_checks and status_code in custom_checks:
        return custom_checks[status_code]
    
    if status_code == 200:
        return None
    elif status_code == 404:
        return {'error': 'N/A', 'status': 'Stock not found', 'success': False}
    elif status_code == 403:
        return {'error': 'Forbidden', 'status': 'Access forbidden', 'success': False}
    elif status_code == 429:
        return {'error': 'Rate Limited', 'status': 'Too many requests', 'success': False}
    else:
        return {'error': 'N/A', 'status': f'HTTP {status_code}', 'success': False}


# ============================================================================
# PAGE PARSING UTILITIES
# ============================================================================

def get_page_soup(response):
    """Parse response content to BeautifulSoup object"""
    if not response:
        return None
    return BeautifulSoup(response.content, 'html.parser')


def validate_stock_page(soup, ticker):
    """
    Validate that we got a valid stock page
    
    Args:
        soup: BeautifulSoup object
        ticker: Stock ticker symbol
    
    Returns:
        tuple: (is_valid, page_title_text)
    """
    if not soup:
        return False, None
    
    page_title = soup.find('title')
    if not page_title:
        return False, None
    
    title_text = page_title.get_text().upper()
    
    # Check for error pages
    if 'NOT FOUND' in title_text or 'ERROR' in title_text or '404' in title_text:
        return False, title_text
    
    return True, title_text


def ticker_in_page(ticker, title_text):
    """Check if ticker appears in page title"""
    if not title_text:
        return False
    ticker_upper = ticker.upper()
    ticker_normalized = ticker_upper.replace('.', '')
    return ticker_upper in title_text or ticker_normalized in title_text


def find_element_by_selectors(soup, selectors):
    """
    Try to find element using multiple CSS selectors
    
    Args:
        soup: BeautifulSoup object
        selectors: List of CSS selectors to try
    
    Returns:
        First matching element or None
    """
    if not soup or not selectors:
        return None
    
    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element:
                return element
        except:
            continue
    
    return None


def extract_text_by_selectors(soup, selectors):
    """
    Extract text using multiple CSS selectors
    
    Args:
        soup: BeautifulSoup object
        selectors: List of CSS selectors to try
    
    Returns:
        First non-empty text content or None
    """
    if not soup or not selectors:
        return None
    
    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        except:
            continue
    
    return None


# ============================================================================
# REGEX & TEXT UTILITIES
# ============================================================================

def extract_number_from_text(text, pattern=None):
    """
    Extract first number from text
    
    Args:
        text: Text to search
        pattern: Regex pattern (defaults to any number)
    
    Returns:
        int or None
    """
    if not text:
        return None
    
    if pattern is None:
        pattern = r'(\d+)'
    
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            return None
    
    return None


def find_keywords_in_text(text, keyword_dict):
    """
    Find first matching keyword in text and return mapped value
    
    Args:
        text: Text to search
        keyword_dict: Dict of {keyword: mapped_value}
    
    Returns:
        mapped_value or None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for keyword, mapped_value in keyword_dict.items():
        if keyword in text_lower:
            return mapped_value
    
    return None


def search_text_with_context(page_text, keywords_dict, context_patterns):
    """
    Search for keywords in page text with context validation
    
    Args:
        page_text: Full page text to search
        keywords_dict: Dict of {keyword: mapped_value}
        context_patterns: List of regex patterns for context validation
    
    Returns:
        mapped_value or None
    """
    if not page_text or not keywords_dict:
        return None
    
    page_text_lower = page_text.lower()
    
    for keyword, mapped_value in keywords_dict.items():
        if keyword not in page_text_lower:
            continue
        
        # Try to find keyword in context
        for pattern_template in context_patterns:
            pattern = pattern_template.format(keyword=re.escape(keyword))
            if re.search(pattern, page_text_lower):
                return mapped_value
    
    return None


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_score_range(score, min_val=1, max_val=10):
    """Validate if score is within expected range"""
    try:
        score_int = int(score)
        return min_val <= score_int <= max_val
    except (ValueError, TypeError):
        return False


def map_score_to_rating(score, thresholds=None):
    """
    Map numeric score to text rating
    
    Args:
        score: Numeric score
        thresholds: Dict of {min_score: rating} (default: standard mapping for 1-10)
    
    Returns:
        Rating string
    """
    if thresholds is None:
        thresholds = {
            8: 'Outperform',
            5: 'Neutral',
            0: 'Underperform'
        }
    
    try:
        score_int = int(score)
        for threshold in sorted(thresholds.keys(), reverse=True):
            if score_int >= threshold:
                return thresholds[threshold]
    except (ValueError, TypeError):
        pass
    
    return 'N/A'


# ============================================================================
# PATTERN MATCHING UTILITIES
# ============================================================================

def find_json_value(text, key_pattern):
    """
    Extract value from JSON-like text
    
    Args:
        text: Text containing JSON
        key_pattern: Regex pattern like r'"key":(\d+)'
    
    Returns:
        Matched value or None
    """
    if not text:
        return None
    
    match = re.search(key_pattern, text)
    if match:
        try:
            return match.group(1)
        except IndexError:
            return None
    
    return None


def find_all_regex_matches(text, pattern):
    """Find all regex matches in text"""
    if not text:
        return []
    
    try:
        return re.findall(pattern, text)
    except:
        return []


# ============================================================================
# ERROR RESPONSE BUILDERS
# ============================================================================

def build_error_response(error_key, error_status, success=False, additional_fields=None):
    """
    Build standardized error response dict
    
    Args:
        error_key: Key for error field (e.g., 'rating', 'score', 'rank')
        error_status: Status message
        success: Success flag (default False)
        additional_fields: Extra fields to include
    
    Returns:
        Error response dict
    """
    response = {error_key: 'N/A', 'status': error_status, 'success': success}
    if additional_fields:
        response.update(additional_fields)
    return response


def build_success_response(data_dict, success=True):
    """
    Build standardized success response dict
    
    Args:
        data_dict: Dict with rating data
        success: Success flag (default True)
    
    Returns:
        Response dict with success flag added
    """
    response = dict(data_dict)
    response['status'] = response.get('status', 'Found')
    response['success'] = success
    return response


# ============================================================================
# STOCK ANALYSIS UTILITIES
# ============================================================================

def extract_stock_analysis_data(soup, ticker):
    """
    Extract Analyst Consensus and Price Target from Stock Analysis
    
    Args:
        soup: BeautifulSoup object of Stock Analysis forecast page
        ticker: Stock ticker symbol
    
    Returns:
        dict: {consensus, price_target, count, upside_downside} or error dict
    """
    if not soup:
        return None
    
    data = {}
    page_text = soup.get_text()
    
    # Look for the main consensus summary text:
    # "26 analysts that cover Apple stock have a consensus rating of "Buy" and an average price target of $275.87"
    
    # Pattern 1: Look for "X analysts ... consensus rating of "..."
    consensus_pattern = r'(\d+)\s*analysts?\s+(?:that\s+cover\s+)?(?:[^"]*?)consensus\s+(?:rating\s+)?of\s*["\']?(strong\s+buy|buy|hold|sell|strong\s+sell|bullish|bearish)["\']?'
    match = re.search(consensus_pattern, page_text, re.IGNORECASE)
    
    if match:
        analyst_count = int(match.group(1))
        consensus_text = match.group(2).strip().lower()
        
        data['analyst_count'] = analyst_count
        data['consensus'] = find_keywords_in_text(consensus_text, STOCKANALYSIS_RATING_KEYWORDS) or consensus_text.title()
    else:
        # Fallback: Look for just the rating keywords in common patterns
        consensus_match = re.search(r'consensus\s+(?:rating\s+)?of\s*["\']?(\w+(?:\s+\w+)?)["\']?', page_text, re.IGNORECASE)
        if consensus_match:
            consensus_text = consensus_match.group(1).lower()
            data['consensus'] = find_keywords_in_text(consensus_text, STOCKANALYSIS_RATING_KEYWORDS) or consensus_text.title()
    
    # Look for Price Target - pattern: "average price target of $275.87"
    price_patterns = [
        r'average\s+price\s+target\s+of\s*\$?([\d.]+)',
        r'price\s+target[:\s]*\$?([\d.]+)',
        r'target[:\s]*\$?([\d.]+)',
    ]
    
    price_target = None
    for pattern in price_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            try:
                price_target = float(match.group(1))
                data['price_target'] = price_target
                break
            except (ValueError, IndexError):
                continue
    
    # Look for upside/downside percentage
    upside_patterns = [
        r'(\d+(?:\.\d+)?)\s*%\s*(?:upside|upside\s+potential)',
        r'(?:upside|upside\s+potential)[:\s]*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%.*?upside',
    ]
    
    for pattern in upside_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            data['upside_downside'] = f"{match.group(1)}%"
            break
    
    return data if data else None
