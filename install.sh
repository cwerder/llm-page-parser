#!/bin/bash
# Install webpage2llm as a system command

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/bin"
COMMAND_NAME="webpage2llm"

echo "Installing webpage2llm..."

# Create bin directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Create the command script
cat > "$INSTALL_DIR/$COMMAND_NAME" << 'EOF'
#!/bin/bash
# webpage2llm - Convert webpages to LLM-friendly format

# Path to the actual script directory
SCRIPT_DIR="__SCRIPT_DIR__"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found. Please run install.sh from the llm_page_parser directory." >&2
    exit 1
fi

# Default to the regular script
SCRIPT="webpage_to_llm.py"

# Check for flags
SHOW_HELP=false
USE_JS=false
USE_COOKIES=false
USE_SAFARI=false
USE_CURRENT=false

for arg in "$@"; do
    case $arg in
        -h|--help)
            SHOW_HELP=true
            ;;
        --js)
            USE_JS=true
            ;;
        --cookies)
            USE_COOKIES=true
            ;;
        --safari)
            USE_SAFARI=true
            ;;
        --current|--chrome)
            USE_CURRENT=true
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    echo "webpage2llm - Convert webpages to LLM-friendly format"
    echo ""
    echo "Usage: webpage2llm [OPTIONS] URL"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -n, --no-clipboard  Disable automatic clipboard copy"
    echo "  --js                Use Selenium for JavaScript-rendered pages"
    echo "  --cookies           Use Chrome browser cookies for authentication"
    echo "  --safari            Use Safari WebDriver (uses logged-in session)"
    echo "  --current           Get content from current browser tab (Arc/Chrome)"
    echo "  --no-verify-ssl     Disable SSL verification (for internal sites)"
    echo "  -o, --output FILE   Save output to file"
    echo "  --max-length N      Limit output to N characters"
    echo "  -m, --method METHOD Use specific extraction method (auto/trafilatura/beautifulsoup)"
    echo ""
    echo "Examples:"
    echo "  webpage2llm https://example.com                  # Auto-copies to clipboard"
    echo "  webpage2llm https://example.com -n               # Without clipboard"
    echo "  webpage2llm https://example.com -o output.md"
    echo "  webpage2llm --js https://spa-website.com"
    echo "  webpage2llm --cookies https://authenticated-site.com  # Use browser cookies"
    echo "  webpage2llm --no-verify-ssl https://internal.company.com"
    exit 0
fi

# Select appropriate script and filter arguments
if [ "$USE_CURRENT" = true ]; then
    # Check if Arc is running, otherwise use Chrome
    if pgrep -x "Arc" > /dev/null; then
        "$VENV_PYTHON" "$SCRIPT_DIR/save_and_parse_arc.py"
    else
        "$VENV_PYTHON" "$SCRIPT_DIR/save_and_parse.py"
    fi
    exit 0
elif [ "$USE_SAFARI" = true ]; then
    SCRIPT="webpage_to_llm_safari.py"
    # Filter out --safari from arguments
    FILTERED_ARGS=()
    for arg in "$@"; do
        if [ "$arg" != "--safari" ]; then
            FILTERED_ARGS+=("$arg")
        fi
    done
    set -- "${FILTERED_ARGS[@]}"
elif [ "$USE_COOKIES" = true ]; then
    SCRIPT="webpage_to_llm_cookies.py"
    # Filter out --cookies from arguments
    FILTERED_ARGS=()
    for arg in "$@"; do
        if [ "$arg" != "--cookies" ]; then
            FILTERED_ARGS+=("$arg")
        fi
    done
    set -- "${FILTERED_ARGS[@]}"
elif [ "$USE_JS" = true ]; then
    SCRIPT="webpage_to_llm_js.py"
    # Filter out --js from arguments
    FILTERED_ARGS=()
    for arg in "$@"; do
        if [ "$arg" != "--js" ]; then
            FILTERED_ARGS+=("$arg")
        fi
    done
    set -- "${FILTERED_ARGS[@]}"
fi

# Check if --no-clipboard flag is present (to disable default clipboard behavior)
USE_CLIPBOARD=true  # Default to true
for arg in "$@"; do
    if [ "$arg" = "--no-clipboard" ] || [ "$arg" = "-n" ]; then
        USE_CLIPBOARD=false
        break
    fi
done

# Filter out clipboard flags from arguments
FILTERED_ARGS=()
for arg in "$@"; do
    if [ "$arg" != "--no-clipboard" ] && [ "$arg" != "-n" ] && [ "$arg" != "--clipboard" ] && [ "$arg" != "-c" ]; then
        FILTERED_ARGS+=("$arg")
    fi
done
set -- "${FILTERED_ARGS[@]}"

# Run the appropriate script and handle clipboard
if [ "$USE_CLIPBOARD" = true ]; then
    OUTPUT=$("$VENV_PYTHON" "$SCRIPT_DIR/$SCRIPT" "$@" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$OUTPUT" | pbcopy
        echo "✓ Content copied to clipboard" >&2
        echo "$OUTPUT"
    else
        echo "Error: Failed to fetch webpage" >&2
        exit 1
    fi
else
    "$VENV_PYTHON" "$SCRIPT_DIR/$SCRIPT" "$@"
fi
EOF

# Replace the placeholder with actual path
sed -i.bak "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" "$INSTALL_DIR/$COMMAND_NAME"
rm "$INSTALL_DIR/$COMMAND_NAME.bak"

# Make it executable
chmod +x "$INSTALL_DIR/$COMMAND_NAME"

# Setup virtual environment and install dependencies
echo "Setting up virtual environment..."
cd "$SCRIPT_DIR"
uv venv
uv pip install requests beautifulsoup4 markdownify trafilatura lxml selenium

echo ""
echo "Installation complete!"
echo ""

# Check if ~/bin is in PATH
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    echo "NOTE: $HOME/bin is not in your PATH."
    echo "Add the following line to your shell profile (~/.zshrc or ~/.bash_profile):"
    echo ""
    echo "  export PATH=\"\$HOME/bin:\$PATH\""
    echo ""
    echo "Then reload your shell or run: source ~/.zshrc"
else
    echo "You can now use: webpage2llm <url>"
fi

echo ""
echo "Examples:"
echo "  webpage2llm https://example.com"
echo "  webpage2llm --js https://spa-website.com"
echo "  webpage2llm --no-verify-ssl https://internal.site.com"