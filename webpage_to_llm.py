#!/usr/bin/env python3
"""
Convert webpage content to LLM-friendly format.
Extracts main content, removes ads/navigation, and outputs clean text or markdown.
"""

import sys
import argparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura
from urllib.parse import urljoin, urlparse


def fetch_webpage(url, timeout=10, verify_ssl=True):
    """Fetch webpage content with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=timeout, verify=verify_ssl)
    response.raise_for_status()
    return response.text


def extract_with_trafilatura(html, url):
    """Use trafilatura for high-quality content extraction."""
    content = trafilatura.extract(
        html,
        output_format='markdown',
        include_links=True,
        include_images=False,
        include_tables=True,
        deduplicate=True,
        url=url
    )
    return content


def extract_with_beautifulsoup(html, url):
    """Fallback extraction using BeautifulSoup."""
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
        soup.body
    )
    
    if not main_content:
        return None
    
    # Convert to markdown
    markdown = md(str(main_content), heading_style="ATX", bullets="-")
    
    # Clean up excessive whitespace
    lines = [line.strip() for line in markdown.split('\n')]
    markdown = '\n'.join(line for line in lines if line)
    
    return markdown


def extract_metadata(soup, url):
    """Extract useful metadata from the page."""
    metadata = {
        'url': url,
        'title': None,
        'description': None,
    }
    
    # Get title
    if soup.title:
        metadata['title'] = soup.title.string
    
    # Get meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        metadata['description'] = meta_desc.get('content', '')
    
    return metadata


def process_webpage(url, method='auto', verify_ssl=True):
    """
    Process a webpage and convert to LLM-friendly format.
    
    Args:
        url: The webpage URL
        method: 'trafilatura', 'beautifulsoup', or 'auto'
        verify_ssl: Whether to verify SSL certificates
    """
    try:
        # Fetch the webpage
        html = fetch_webpage(url, verify_ssl=verify_ssl)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract metadata
        metadata = extract_metadata(soup, url)
        
        # Extract content
        content = None
        
        if method in ['trafilatura', 'auto']:
            content = extract_with_trafilatura(html, url)
            
        if not content and method in ['beautifulsoup', 'auto']:
            content = extract_with_beautifulsoup(html, url)
        
        if not content:
            raise ValueError("Failed to extract content from webpage")
        
        # Format output
        output = []
        
        # Add metadata header
        output.append(f"# {metadata['title'] or 'Untitled'}")
        output.append(f"Source: {url}")
        if metadata['description']:
            output.append(f"Description: {metadata['description']}")
        output.append("\n---\n")
        
        # Add content
        output.append(content)
        
        return '\n'.join(output)
        
    except requests.RequestException as e:
        return f"Error fetching webpage: {e}"
    except Exception as e:
        return f"Error processing webpage: {e}"


def main():
    parser = argparse.ArgumentParser(
        description='Convert webpage to LLM-friendly format'
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
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification (use for internal/self-signed certs)'
    )
    
    args = parser.parse_args()
    
    # Process the webpage
    result = process_webpage(args.url, args.method, verify_ssl=not args.no_verify_ssl)
    
    # Apply length limit if specified
    if args.max_length and len(result) > args.max_length:
        result = result[:args.max_length] + "\n\n[Content truncated...]"
    
    # Output result
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Content saved to {args.output}")
    else:
        print(result)


if __name__ == '__main__':
    main()