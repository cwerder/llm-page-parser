#!/usr/bin/env python3
"""
Convert webpage using Safari cookies (easier access on macOS).
"""

import sys
import argparse
import subprocess
import json
from selenium import webdriver
from selenium.webdriver.safari.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura
import time


def fetch_with_safari(url, wait_time=10, headless=False):
    """Fetch webpage using Safari WebDriver (uses existing Safari session/cookies)."""
    
    # Safari options
    options = Options()
    
    # Note: Safari doesn't support headless mode
    # It will use your existing Safari session with cookies
    
    print("Opening Safari (will use your existing session)...", file=sys.stderr)
    driver = webdriver.Safari(options=options)
    
    try:
        driver.get(url)
        
        # Wait for content to load
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(3)
        
        # Try to find main content or wait for specific elements
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main, article, .content, .docs-content, .markdown-body"))
            )
        except:
            pass  # Continue even if specific elements not found
        
        html = driver.page_source
        title = driver.title
        
        return html, title
        
    finally:
        driver.quit()


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
        
        # Find main content - expanded selectors for docs sites
        main_content = None
        
        # Try various content selectors
        selectors = [
            'main',
            'article', 
            '[role="main"]',
            '.docs-content',
            '.documentation-content',
            '.markdown-body',
            '.content-body',
            '#content',
            '.content',
            'div.content',
            '.doc-content',
            '.page-content',
            '.post-content'
        ]
        
        for selector in selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            # Try to find the largest div with text
            divs = soup.find_all('div')
            if divs:
                main_content = max(divs, key=lambda d: len(d.get_text(strip=True)))
        
        if not main_content:
            main_content = soup.body
        
        if main_content:
            markdown = md(str(main_content), heading_style="ATX", bullets="-")
            lines = [line.strip() for line in markdown.split('\n')]
            return '\n'.join(line for line in lines if line)
    
    return None


def process_with_safari(url, method='auto', wait_time=10):
    """Process webpage using Safari with existing cookies."""
    try:
        print(f"Fetching {url} with Safari...", file=sys.stderr)
        html, title = fetch_with_safari(url, wait_time)
        
        print(f"Extracting content...", file=sys.stderr)
        content = extract_content(html, url, method)
        
        if not content:
            # If no content extracted, try to get all text
            soup = BeautifulSoup(html, 'html.parser')
            content = soup.get_text(separator='\n', strip=True)
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
        description='Convert webpage using Safari (with existing cookies)'
    )
    parser.add_argument('url', help='URL to convert')
    parser.add_argument(
        '-m', '--method',
        choices=['trafilatura', 'beautifulsoup', 'auto'],
        default='auto',
        help='Extraction method (default: auto)'
    )
    parser.add_argument(
        '--wait-time',
        type=int,
        default=10,
        help='Time to wait for page load (default: 10 seconds)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    
    args = parser.parse_args()
    
    # Enable Safari automation if needed
    try:
        subprocess.run(['safaridriver', '--enable'], capture_output=True, check=False)
    except:
        pass
    
    result = process_with_safari(
        args.url,
        args.method,
        args.wait_time
    )
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()