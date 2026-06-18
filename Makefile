.PHONY: run test lint clean coverage mypy format ingest help

help:  ## Show this help message
	@echo Available targets:
	@echo   run       - Launch Streamlit dashboard
	@echo   test      - Run all unit tests
	@echo   coverage  - Run tests with coverage report
	@echo   lint      - Run flake8 linter
	@echo   format    - Auto-format code with black
	@echo   mypy      - Run static type checking
	@echo   ingest    - Fetch and store market data
	@echo   clean     - Remove build artifacts and caches

run:  ## Launch Streamlit dashboard
	streamlit run app/streamlit_app.py

test:  ## Run all unit tests
	pytest tests/ -v --tb=short

coverage:  ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml -v

lint:  ## Run flake8 linter
	flake8 src/ app/ tests/ --max-line-length=120 --ignore=E501,W503

format:  ## Auto-format with black
	black src/ app/ tests/ --line-length 120

mypy:  ## Run static type checking
	mypy src/ --ignore-missing-imports --no-strict-optional

ingest:  ## Fetch market data and store in SQLite
	python run.py

clean:  ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache htmlcov .mypy_cache
	rm -rf src/__pycache__ tests/__pycache__
	rm -rf *.egg-info src/*.egg-info
	rm -f coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
