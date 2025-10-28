#!/bin/bash
# Daily podcast generation script
# Usage: ./scripts/run_daily.sh [YYYY-MM-DD]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Synthetic Newsroom - Daily Runner"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -f "src/cli.py" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg not found. Please install it first.${NC}"
    exit 1
fi

if ! python -c "import src" 2>/dev/null; then
    echo -e "${RED}Error: Python dependencies not installed.${NC}"
    echo "Run: make setup"
    exit 1
fi

# Parse date argument
DATE_ARG=""
if [ -n "$1" ]; then
    DATE_ARG="--date $1"
    echo -e "${YELLOW}Running for date: $1${NC}"
else
    echo -e "${YELLOW}Running for today${NC}"
fi

# Run pipeline
echo ""
echo -e "${GREEN}Starting podcast generation pipeline...${NC}"
echo ""

python -m src.cli run-daily $DATE_ARG

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ Success! Podcast generated."
    echo -e "==========================================${NC}"
    echo ""
    echo "Output files:"
    ls -lh data/episodes/*.mp3 2>/dev/null | tail -1 || echo "No MP3 files found"
    echo ""
    echo "RSS feed: data/podcast.xml"
else
    echo ""
    echo -e "${RED}=========================================="
    echo "❌ Pipeline failed. Check logs above."
    echo -e "==========================================${NC}"
    exit 1
fi
