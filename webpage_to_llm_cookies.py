#!/usr/bin/env python3
"""
Convert webpage to LLM-friendly format using browser cookies for authentication.
"""

import sys
import argparse
import json
import sqlite3
import tempfile
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura
import requests


def get_chrome_cookies(domain=None):
    """Extract cookies from Chrome browser."""
    import platform
    system = platform.system()
    
    if system == "Darwin":  # macOS
        cookie_path = Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies"
    elif system == "Linux":
        cookie_path = Path.home() / ".config/google-chrome/Default/Cookies"
    elif system == "Windows":
        cookie_path = Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cookies"
    else:
        raise OSError(f"Unsupported OS: {system}")
    
    if not cookie_path.exists():
        return []
    
    # Copy cookie database to temp file (Chrome locks the original)
    temp_cookie_file = tempfile.NamedTemporaryFile(delete=False)
    shutil.copy2(cookie_path, temp_cookie_file.name)
    
    cookies = []
    try:
        conn = sqlite3.connect(temp_cookie_file.name)
        cursor = conn.cursor()
        
        if domain:
            query = "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key LIKE ?"
            cursor.execute(query, (f"%{domain}%",))
        else:
            query = "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies"
            cursor.execute(query)
        
        for row in cursor.fetchall():
            cookies.append({
                'name': row[0],
                'value': row[1],
                'domain': row[2],
                'path': row[3],
                'expiry': row[4],
                'secure': bool(row[5]),
                'httpOnly': bool(row[6])
            })
        
        conn.close()
    finally:
        Path(temp_cookie_file.name).unlink()
    
    return cookies


def fetch_with_cookies_selenium(url, cookies=None, wait_time=10, headless=True):
    """Fetch webpage using Selenium with browser cookies."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to domain first (required for setting cookies)
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        driver.get(base_url)
        
        # Add cookies
        if cookies:
            for cookie in cookies:
                try:
                    # Selenium expects different format
                    selenium_cookie = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie['domain'],
                        'path': cookie.get('path', '/'),
                    }
                    if cookie.get('expiry'):
                        selenium_cookie['expiry'] = cookie['expiry']
                    driver.add_cookie(selenium_cookie)
                except Exception as e:
                    print(f"Warning: Could not add cookie {cookie.get('name')}: {e}", file=sys.stderr)
        
        # Now navigate to actual URL
        driver.get(url)
        
        # Wait for content
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        import time
        time.sleep(3)
        
        html = driver.page_source
        title = driver.title
        
        return html, title
        
    finally:
        driver.quit()


def fetch_with_cookies_requests(url, cookies=None):
    """Fetch webpage using requests library with cookies."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    cookie_dict = {}
    if cookies:
        for cookie in cookies:
            cookie_dict[cookie['name']] = cookie['value']
    
    response = requests.get(url, headers=headers, cookies=cookie_dict, verify=False)
    response.raise_for_status()
    return response.text, None


def extract_content(html, url, method='auto'):
    """Extract main content from HTML."""
    
    # Try trafilatura first
    if method in ['trafilatura', 'auto']:
        content = trafilatura.extract(
            html,
            output_format='markdown',
            include_links=True,
            include_images=False,
            include_tables=True,
            deduplicate=True,
            url=url
        )
        if content:
            return content
    
    # Fallback to BeautifulSoup
    if method in ['beautifulsoup', 'auto']:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Find main content
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', class_='content') or 
            soup.find('div', id='content') or
            soup.find('div', class_='docs-content') or
            soup.find('div', class_='markdown-body') or
            soup.body
        )
        
        if main_content:
            markdown = md(str(main_content), heading_style="ATX", bullets="-")
            lines = [line.strip() for line in markdown.split('\n')]
            return '\n'.join(line for line in lines if line)
    
    return None


def process_with_cookies(url, method='auto', use_selenium=True, browser='chrome'):
    """Process webpage with browser cookies."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        print(f"Extracting cookies for domain: {domain}...", file=sys.stderr)
        cookies = get_chrome_cookies(domain)
        print(f"Found {len(cookies)} cookies", file=sys.stderr)
        
        if use_selenium:
            print(f"Fetching with Selenium and cookies...", file=sys.stderr)
            html, title = fetch_with_cookies_selenium(url, cookies)
        else:
            print(f"Fetching with requests and cookies...", file=sys.stderr)
            html, title = fetch_with_cookies_requests(url, cookies)
        
        print(f"Extracting content...", file=sys.stderr)
        content = extract_content(html, url, method)
        
        if not content:
            raise ValueError("Failed to extract content")
        
        # Format output
        output = []
        output.append(f"# {title or 'Untitled'}")
        output.append(f"Source: {url}")
        output.append("\n---\n")
        output.append(content)
        
        return '\n'.join(output)
        
    except Exception as e:
        return f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(
        description='Convert webpage to LLM format using browser cookies'
    )
    parser.add_argument('url', help='URL to convert')
    parser.add_argument(
        '-m', '--method',
        choices=['trafilatura', 'beautifulsoup', 'auto'],
        default='auto',
        help='Extraction method (default: auto)'
    )
    parser.add_argument(
        '--no-selenium',
        action='store_true',
        help='Use requests instead of Selenium'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    
    args = parser.parse_args()
    
    result = process_with_cookies(
        args.url,
        args.method,
        use_selenium=not args.no_selenium
    )
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()