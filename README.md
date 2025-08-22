# LLM Page Parser

Convert webpage content into clean, LLM-friendly markdown format. Automatically extracts main content, removes ads/navigation, and copies to clipboard for easy pasting into ChatGPT, Claude, or other LLMs.

## Quick Start

```bash
# Install (one-time setup)
./install.sh

# Use from anywhere
webpage2llm https://example.com
```

Content is **automatically copied to your clipboard** and displayed in terminal.

## Installation

### Automatic Installation (Recommended)
```bash
git clone <this-repo>
cd llm_page_parser
./install.sh
```

This installs the `webpage2llm` command globally in `~/bin/`.

### Manual Installation
```bash
uv venv
source .venv/bin/activate
uv pip install requests beautifulsoup4 markdownify trafilatura lxml selenium
```

## Usage

### Basic Usage
```bash
# Parse any public webpage (auto-copies to clipboard)
webpage2llm https://example.com

# Parse without clipboard
webpage2llm https://example.com -n
```

### For Authenticated/Dynamic Sites

#### Current Browser Tab (Arc/Chrome)
```bash
# Get content from currently open tab in Arc or Chrome
webpage2llm --current
```
**Note**: For Chrome, you must enable: View → Developer → Allow JavaScript from Apple Events

#### JavaScript-Heavy Sites
```bash
# Use Selenium for single-page apps
webpage2llm --js https://spa-website.com
```

#### Sites with Authentication
```bash
# For internal sites with self-signed certificates
webpage2llm --no-verify-ssl https://internal.company.com

# Use browser cookies (experimental)
webpage2llm --cookies https://authenticated-site.com

# Use Safari (uses your logged-in session)
webpage2llm --safari https://authenticated-site.com
```

#### Parse Saved HTML Files
```bash
# First save page in browser: Cmd+S → "Web Page, Complete"
python parse_local_html.py ~/Downloads/saved_page.html
```

### Advanced Options

```bash
# Save to file
webpage2llm https://example.com -o output.md

# Limit output length
webpage2llm https://example.com --max-length 5000

# Choose extraction method
webpage2llm https://example.com -m trafilatura  # or beautifulsoup

# Show help
webpage2llm --help
```

## Options

| Flag | Description |
|------|-------------|
| `-n, --no-clipboard` | Don't copy to clipboard (just print) |
| `--current` | Get from current browser tab (Arc/Chrome) |
| `--js` | Use Selenium for JavaScript sites |
| `--no-verify-ssl` | Disable SSL verification |
| `--cookies` | Use Chrome browser cookies |
| `--safari` | Use Safari WebDriver |
| `-o FILE` | Save output to file |
| `--max-length N` | Limit output to N characters |
| `-m METHOD` | Extraction method (auto/trafilatura/beautifulsoup) |

## Features

- 🎯 **Smart Extraction**: Automatically identifies and extracts main content
- 📋 **Auto-Clipboard**: Output automatically copied to clipboard (macOS)
- 🌐 **Universal Support**: Works with static and dynamic websites
- 🔐 **Authentication**: Multiple methods for authenticated sites
- 🧹 **Clean Output**: Removes ads, navigation, and clutter
- 📝 **Markdown Format**: Perfect for LLM consumption
- 🏃 **Fast**: Lightweight and efficient

## Examples

### Parse documentation
```bash
webpage2llm https://docs.python.org/3/tutorial/
```

### Get content from current Arc browser tab
```bash
webpage2llm --current
```

### Parse internal company wiki
```bash
webpage2llm --no-verify-ssl https://internal.wiki.company.com/page
```

### Parse React/Vue/Angular apps
```bash
webpage2llm --js https://app.example.com
```

## Troubleshooting

### "No module named 'bs4'" error
You're not using the virtual environment. The `webpage2llm` command handles this automatically.

### JavaScript sites showing "Please enable JavaScript"
Use the `--js` flag or `--current` flag with the page open in your browser.

### SSL Certificate errors
Use `--no-verify-ssl` for internal sites with self-signed certificates.

### Authentication required
1. Best option: Open page in Arc/Chrome, then use `--current`
2. Alternative: Save page as HTML, parse with `parse_local_html.py`

### Chrome "JavaScript from Apple Events" error
Enable in Chrome: View → Developer → Allow JavaScript from Apple Events

## How It Works

1. **Fetches** webpage content (with various authentication methods)
2. **Extracts** main content using:
   - Trafilatura (high-quality extraction)
   - BeautifulSoup (fallback)
3. **Cleans** removing ads, navigation, scripts
4. **Converts** to clean markdown
5. **Copies** to clipboard automatically

## Requirements

- Python 3.8+
- macOS (for clipboard support)
- Chrome or Arc browser (for `--current` option)
- uv package manager (for installation)

## License

MIT