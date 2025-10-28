.PHONY: help setup install clean run test lint format validate

# Default target
help:
	@echo "Synthetic Newsroom - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup      - Initial setup (create venv, install deps, copy configs)"
	@echo "  make install    - Install Python dependencies"
	@echo "  make run        - Run daily podcast generation"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters (flake8, mypy)"
	@echo "  make format     - Format code (black, isort)"
	@echo "  make validate   - Validate configuration"
	@echo "  make clean      - Clean temporary files"

# Setup environment
setup:
	@echo "Setting up Synthetic Newsroom..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Installing dependencies..."
	@.venv/bin/pip install --upgrade pip
	@.venv/bin/pip install -r requirements.txt
	@if [ ! -f ".env" ]; then \
		echo "Copying .env.example to .env..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env and add your API keys!"; \
	fi
	@if [ ! -f "configs/settings.yaml" ]; then \
		echo "Copying settings.example.yaml to settings.yaml..."; \
		cp configs/settings.example.yaml configs/settings.yaml; \
	fi
	@echo "Creating data directories..."
	@mkdir -p data/{news_raw,news_clean,transcripts,audio_stems,episodes,metadata}
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and add your API keys"
	@echo "  2. Edit configs/settings.yaml if needed"
	@echo "  3. Run: make validate"
	@echo "  4. Run: make run"

# Install dependencies only
install:
	pip install -r requirements.txt

# Run daily pipeline
run:
	python -m src.cli run-daily

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=term-missing

# Lint code
lint:
	@echo "Running flake8..."
	@flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503 || true
	@echo "Running mypy..."
	@mypy src/ --ignore-missing-imports || true

# Format code
format:
	@echo "Running black..."
	@black src/ tests/ --line-length=100
	@echo "Running isort..."
	@isort src/ tests/ --profile black

# Validate configuration
validate:
	python -m src.cli validate-config

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pkl" -delete
	@find . -type f -name "*.tmp" -delete
	@rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
	@echo "✅ Clean complete!"

# Development server (for serving podcast RSS)
serve:
	@echo "Starting local HTTP server on http://localhost:8080"
	@echo "Serving data/ directory for podcast RSS access"
	@cd data && python -m http.server 8080
