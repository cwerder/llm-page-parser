#!/usr/bin/env python3
"""
Convert webpage content to LLM-friendly format with JavaScript support.
Uses Selenium for JavaScript-rendered pages.
"""

import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura


def fetch_with_selenium(url, wait_time=10, headless=True):
    """Fetch webpage content using Selenium for JavaScript support."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Accept self-signed certificates
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-insecure-localhost")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(url)
        
        # Wait for content to load
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(2)
        
        # Get page source after JavaScript execution
        html = driver.page_source
        title = driver.title
        
        return html, title
        
    finally:
        driver.quit()


def extract_content(html, url, method='auto'):
    """Extract main content from HTML."""
    
    # Try trafilatura first if requested
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
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content areas
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
            # Convert to markdown
            markdown = md(str(main_content), heading_style="ATX", bullets="-")
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in markdown.split('\n')]
            markdown = '\n'.join(line for line in lines if line)
            
            return markdown
    
    return None


def process_js_webpage(url, method='auto', wait_time=10, headless=True):
    """Process a JavaScript-rendered webpage."""
    try:
        print(f"Fetching {url} with Selenium...", file=sys.stderr)
        html, title = fetch_with_selenium(url, wait_time, headless)
        
        print(f"Extracting content...", file=sys.stderr)
        content = extract_content(html, url, method)
        
        if not content:
            raise ValueError("Failed to extract content from webpage")
        
        # Format output
        output = []
        output.append(f"# {title or 'Untitled'}")
        output.append(f"Source: {url}")
        output.append("\n---\n")
        output.append(content)
        
        return '\n'.join(output)
        
    except Exception as e:
        return f"Error processing webpage: {e}"


def main():
    parser = argparse.ArgumentParser(
        description='Convert JavaScript-rendered webpage to LLM-friendly format'
    )
    parser.add_argument('url', help='URL of the webpage to convert')
    parser.add_argument(
        '-m', '--method',
        choices=['trafilatura', 'beautifulsoup', 'auto'],
        default='auto',
        help='Extraction method to use (default: auto)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--max-length',
        type=int,
        help='Maximum output length in characters'
    )
    parser.add_argument(
        '--wait-time',
        type=int,
        default=10,
        help='Time to wait for page to load (default: 10 seconds)'
    )
    parser.add_argument(
        '--show-browser',
        action='store_true',
        help='Show browser window (default: headless mode)'
    )
    
    args = parser.parse_args()
    
    # Process the webpage
    result = process_js_webpage(
        args.url, 
        args.method, 
        args.wait_time,
        headless=not args.show_browser
    )
    
    # Apply length limit if specified
    if args.max_length and len(result) > args.max_length:
        result = result[:args.max_length] + "\n\n[Content truncated...]"
    
    # Output result
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Content saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()