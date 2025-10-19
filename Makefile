.PHONY: help install test lint format clean run setup-db

help: ## Show this help message
	@echo "Email Transaction Parser - Development Commands"
	@echo "=============================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	./venv/bin/pip install -r requirements.txt

install-dev: ## Install development dependencies
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -e .[dev]

setup-db: ## Initialize database
	./venv/bin/python scripts/setup_db.py

run: ## Run the application
	./venv/bin/uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint: ## Run linting
	flake8 src/ tests/
	mypy src/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting
	black --check src/ tests/

clean: ## Clean up generated files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf build/ dist/ .eggs/

build: ## Build package
	python setup.py sdist bdist_wheel

install-local: ## Install package locally
	pip install -e .

uninstall: ## Uninstall package
	pip uninstall email-transaction-parser -y

docker-build: ## Build Docker image
	docker build -t email-transaction-parser .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env email-transaction-parser

docker-stop: ## Stop Docker container
	docker stop $$(docker ps -q --filter ancestor=email-transaction-parser)

logs: ## Show application logs
	tail -f logs/app.log

check: format-check lint test ## Run all checks

pre-commit: format lint test ## Run pre-commit checks

setup: install setup-db ## Complete setup (install + setup database)

dev-setup: install-dev setup-db ## Complete development setup
