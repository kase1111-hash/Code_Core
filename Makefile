# Ollama Automation Harness - Makefile
# Run 'make help' to see available commands

.PHONY: help install install-dev venv clean lint format typecheck test coverage run docker-build docker-run

# Default Python
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Ollama Automation Harness$(NC)"
	@echo "$(YELLOW)Usage:$(NC) make [target]"
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Environment Setup
# =============================================================================

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Virtual environment created at $(VENV)$(NC)"
	@echo "Activate with: source $(VENV)/bin/activate"

install: ## Install runtime dependencies
	@echo "$(BLUE)Installing runtime dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed$(NC)"

install-dev: ## Install all dependencies (runtime + dev)
	@echo "$(BLUE)Installing all dependencies...$(NC)"
	pip install -r requirements-dev.txt
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Development environment ready$(NC)"

clean: ## Remove build artifacts and cache
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf .coverage htmlcov coverage.xml
	rm -rf dist build *.egg-info
	rm -rf $(VENV)
	@echo "$(GREEN)Cleanup complete$(NC)"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linter (ruff)
	@echo "$(BLUE)Running linter...$(NC)"
	ruff check .
	@echo "$(GREEN)Linting complete$(NC)"

format: ## Format code (ruff)
	@echo "$(BLUE)Formatting code...$(NC)"
	ruff format .
	ruff check --fix .
	@echo "$(GREEN)Formatting complete$(NC)"

typecheck: ## Run type checker (mypy)
	@echo "$(BLUE)Running type checker...$(NC)"
	mypy core utils main.py
	@echo "$(GREEN)Type checking complete$(NC)"

security: ## Run security analysis (bandit)
	@echo "$(BLUE)Running security analysis...$(NC)"
	bandit -r core utils cli.py -f txt || true
	@echo "$(GREEN)Security analysis complete$(NC)"

check: lint typecheck security ## Run all code quality checks

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)Tests complete$(NC)"

test-fast: ## Run tests (fail fast)
	@echo "$(BLUE)Running tests (fail fast)...$(NC)"
	pytest tests/ -v -x
	@echo "$(GREEN)Tests complete$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/test_validation.py tests/test_config.py tests/test_errors.py tests/test_executor.py tests/test_safety.py tests/test_secrets.py tests/test_error_tracking.py tests/test_logger.py -v
	@echo "$(GREEN)Unit tests complete$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/ -v -m "integration"
	@echo "$(GREEN)Integration tests complete$(NC)"

test-security: ## Run security tests
	@echo "$(BLUE)Running security tests...$(NC)"
	pytest tests/ -v -m "security or exploit or backdoor"
	@echo "$(GREEN)Security tests complete$(NC)"

test-performance: ## Run performance tests
	@echo "$(BLUE)Running performance tests...$(NC)"
	pytest tests/ -v -m "performance"
	@echo "$(GREEN)Performance tests complete$(NC)"

test-dynamic: ## Run dynamic/fuzzing tests
	@echo "$(BLUE)Running dynamic analysis tests...$(NC)"
	pytest tests/ -v -m "dynamic"
	@echo "$(GREEN)Dynamic tests complete$(NC)"

test-regression: ## Run regression tests
	@echo "$(BLUE)Running regression tests...$(NC)"
	pytest tests/ -v -m "regression"
	@echo "$(GREEN)Regression tests complete$(NC)"

coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ --cov=core --cov=utils --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# =============================================================================
# Running
# =============================================================================

run: ## Run the application
	@echo "$(BLUE)Starting Ollama Automation Harness...$(NC)"
	$(PYTHON) main.py

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t ollama-harness .
	@echo "$(GREEN)Docker image built$(NC)"

docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -it --env-file .env --network host ollama-harness

docker-dev: ## Run development Docker container
	@echo "$(BLUE)Starting development container...$(NC)"
	docker-compose --profile dev up -d dev
	docker-compose exec dev bash

# =============================================================================
# Setup
# =============================================================================

setup: venv ## Complete development setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements-dev.txt
	$(BIN)/pre-commit install
	mkdir -p logs sandbox
	@echo ""
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Activate venv: source $(VENV)/bin/activate"
	@echo "  2. Copy .env.example to .env and add your API key"
	@echo "  3. Run: make run"

# =============================================================================
# CI/CD
# =============================================================================

ci-lint: ## Run linting for CI (with output format)
	@echo "$(BLUE)CI: Running linter...$(NC)"
	ruff check . --output-format=github || ruff check .
	@echo "$(GREEN)CI: Linting complete$(NC)"

ci-test: ## Run tests for CI (with JUnit output)
	@echo "$(BLUE)CI: Running tests...$(NC)"
	pytest tests/ -v --tb=short --junitxml=test-results.xml
	@echo "$(GREEN)CI: Tests complete$(NC)"

ci-security: ## Run security scan for CI
	@echo "$(BLUE)CI: Running security scan...$(NC)"
	bandit -r core utils cli.py -f json -o bandit-results.json || true
	@echo "$(GREEN)CI: Security scan complete$(NC)"

ci: ci-lint ci-test ci-security ## Run all CI checks
	@echo "$(GREEN)All CI checks complete$(NC)"

# =============================================================================
# Build & Package
# =============================================================================

build: ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build
	@echo "$(GREEN)Build complete - packages in dist/$(NC)"

dist-clean: ## Clean distribution artifacts
	rm -rf dist/ build/ *.egg-info/
