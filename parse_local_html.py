#!/usr/bin/env python3
"""
Parse a locally saved HTML file and convert to LLM-friendly format.
"""

import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura


def parse_html_file(file_path, method='auto'):
    """Parse a locally saved HTML file."""
    
    # Read the HTML file
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Get the original URL from the HTML if available
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try to extract URL from saved comment
    url = None
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and 'saved from url' in text):
        if 'saved from url' in comment:
            # Extract URL from comment like: <!-- saved from url=(0076)https://... -->
            import re
            match = re.search(r'saved from url=\(\d+\)(https?://[^\s]+)', comment)
            if match:
                url = match.group(1).strip()
                break
    
    # Get title
    title = soup.title.string if soup.title else "Untitled"
    
    # Try different extraction methods
    content = None
    
    # Method 1: Try trafilatura
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
    
    # Method 2: Look for specific content areas
    if not content and method in ['beautifulsoup', 'auto']:
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button']):
            element.decompose()
        
        # Try to find main content areas
        content_selectors = [
            # Generic content areas
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '#main-content',
            '.content',
            '#content',
            
            # Documentation specific
            '.docs-content',
            '.documentation-content',
            '.markdown-body',
            '.doc-content',
            '.page-content',
            '.post-content',
            
            # TechDocs/Backstage specific (for UKG portal)
            '.jss4-511',  # Common TechDocs content class
            '[class*="makeStyles-content"]',
            '[class*="TechDocsContent"]',
            '[class*="MarkdownContent"]',
            '.MuiContainer-root article',
            'div[class*="jss"][class*="511"]',
            
            # Material-UI containers
            '.MuiContainer-root',
            '.MuiPaper-root',
            
            # Look for divs with markdown content
            'div:has(> h1, > h2, > h3, > p, > ul, > ol, > pre)',
        ]
        
        main_content = None
        for selector in content_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    # Find the element with the most text content
                    for elem in elements:
                        text_length = len(elem.get_text(strip=True))
                        if text_length > 100:  # Minimum content threshold
                            if not main_content or text_length > len(main_content.get_text(strip=True)):
                                main_content = elem
            except:
                continue
        
        # If still no content, try to find the largest div with substantial text
        if not main_content:
            all_divs = soup.find_all('div')
            text_divs = []
            for div in all_divs:
                text = div.get_text(strip=True)
                # Skip navigation and UI elements
                if len(text) > 200 and not any(skip in text[:100] for skip in ['Cookie', 'Accept', 'Login', 'Sign in']):
                    text_divs.append((div, len(text)))
            
            if text_divs:
                text_divs.sort(key=lambda x: x[1], reverse=True)
                main_content = text_divs[0][0]
        
        if main_content:
            # Convert to markdown
            content = md(str(main_content), heading_style="ATX", bullets="-")
            
            # Clean up
            lines = [line.strip() for line in content.split('\n')]
            content = '\n'.join(line for line in lines if line)
    
    # Method 3: Extract all text as fallback
    if not content:
        # Get all text from body
        body = soup.find('body')
        if body:
            # Remove obvious non-content elements
            for elem in body.find_all(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            
            text = body.get_text(separator='\n', strip=True)
            
            # Clean up text
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # Skip empty lines and obvious UI elements
                if line and len(line) > 2 and not line.startswith('MuiTypography'):
                    cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines)
    
    # Format output
    output = []
    output.append(f"# {title}")
    if url:
        output.append(f"Source: {url}")
    output.append("\n---\n")
    output.append(content if content else "No content extracted")
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Parse local HTML file to LLM-friendly format'
    )
    parser.add_argument('file', help='Path to HTML file')
    parser.add_argument(
        '-m', '--method',
        choices=['trafilatura', 'beautifulsoup', 'auto'],
        default='auto',
        help='Extraction method (default: auto)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '-c', '--clipboard',
        action='store_true',
        help='Copy output to clipboard'
    )
    
    args = parser.parse_args()
    
    # Parse the file
    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    result = parse_html_file(file_path, args.method)
    
    # Handle output
    if args.clipboard:
        import subprocess
        subprocess.run(['pbcopy'], input=result, text=True)
        print("✓ Content copied to clipboard", file=sys.stderr)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Content saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()