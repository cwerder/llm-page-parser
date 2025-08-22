#!/usr/bin/env python3
"""
Script to save current Arc browser page and parse it.
Uses AppleScript to get the page source from the active Arc tab.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura


def get_arc_page_source():
    """Get HTML source from the current Arc tab using AppleScript."""
    
    # AppleScript to get page source from Arc
    applescript = '''
    tell application "Arc"
        if (count of windows) > 0 then
            tell front window
                tell active tab
                    set pageURL to URL
                    set pageTitle to title
                    set pageSource to execute javascript "document.documentElement.outerHTML"
                    return pageURL & "|||" & pageTitle & "|||" & pageSource
                end tell
            end tell
        else
            return "ERROR: No Arc window open"
        end if
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout.strip()
        if output.startswith("ERROR:"):
            raise RuntimeError(output)
        
        parts = output.split("|||")
        if len(parts) != 3:
            raise ValueError("Unexpected AppleScript output format")
        
        url, title, html = parts
        return url, title, html
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get Arc page: {e.stderr}")


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
        for script in soup(["script", "style", "nav", "header", "footer", "aside", "button"]):
            script.decompose()
        
        # Find main content
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
            '.post-content',
            # UKG specific
            '.MuiContainer-root',
            '[class*="makeStyles-content"]',
            # Generic documentation patterns
            '[class*="docs"]',
            '[class*="documentation"]',
            '.main-content',
            '#main-content'
        ]
        
        main_content = None
        for selector in selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            # Try to find the largest text-containing div
            divs = soup.find_all('div')
            if divs:
                # Filter divs with substantial text
                text_divs = [(d, len(d.get_text(strip=True))) for d in divs]
                text_divs = [d for d in text_divs if d[1] > 100]
                if text_divs:
                    main_content = max(text_divs, key=lambda x: x[1])[0]
        
        if not main_content:
            main_content = soup.body
        
        if main_content:
            markdown = md(str(main_content), heading_style="ATX", bullets="-")
            lines = [line.strip() for line in markdown.split('\n')]
            return '\n'.join(line for line in lines if line)
    
    return None


def main():
    try:
        print("Getting page from Arc browser...", file=sys.stderr)
        url, title, html = get_arc_page_source()
        
        print(f"Processing: {title}", file=sys.stderr)
        print(f"URL: {url}", file=sys.stderr)
        
        content = extract_content(html, url)
        
        if not content:
            # If extraction failed, get all text
            soup = BeautifulSoup(html, 'html.parser')
            content = soup.get_text(separator='\n', strip=True)
        
        # Format output
        output = []
        output.append(f"# {title}")
        output.append(f"Source: {url}")
        output.append("\n---\n")
        output.append(content)
        
        result = '\n'.join(output)
        
        # Copy to clipboard
        subprocess.run(['pbcopy'], input=result, text=True)
        print("✓ Content copied to clipboard", file=sys.stderr)
        
        # Also print to stdout
        print(result)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()