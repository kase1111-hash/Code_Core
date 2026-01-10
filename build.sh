#!/bin/bash
# Ollama Automation Harness - Shell Build Script
# Usage: ./build.sh [command]
#
# Commands:
#   install      - Install dependencies
#   install-dev  - Install development dependencies
#   test         - Run all tests
#   test-quick   - Run quick tests
#   lint         - Run linting
#   format       - Format code
#   check        - Run all checks
#   clean        - Clean build artifacts
#   run          - Run the application
#   help         - Show this help

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

# Functions
show_help() {
    echo -e "${BLUE}Ollama Automation Harness - Build Script${NC}"
    echo ""
    echo "Usage: ./build.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install       Install runtime dependencies"
    echo "  install-dev   Install development dependencies"
    echo "  setup         Complete development setup"
    echo "  test          Run all tests"
    echo "  test-quick    Run tests (fail fast)"
    echo "  test-unit     Run unit tests only"
    echo "  test-security Run security tests"
    echo "  test-perf     Run performance tests"
    echo "  test-dynamic  Run dynamic/fuzzing tests"
    echo "  lint          Run linting (ruff)"
    echo "  format        Format code (ruff)"
    echo "  typecheck     Run type checking (mypy)"
    echo "  security      Run security scan (bandit)"
    echo "  check         Run all code quality checks"
    echo "  clean         Clean build artifacts"
    echo "  run           Run the application"
    echo "  version       Show version"
    echo "  build         Build distribution packages"
    echo "  package-zip   Create zip distribution"
    echo "  package-exe   Create standalone executable"
    echo "  package-docker Build production Docker image"
    echo "  package-all   Create all distribution packages"
    echo "  ci            Run all CI checks"
    echo "  help          Show this help"
    echo ""
}

cmd_install() {
    echo -e "${BLUE}Installing runtime dependencies...${NC}"
    $PYTHON -m pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

cmd_install_dev() {
    echo -e "${BLUE}Installing development dependencies...${NC}"
    $PYTHON -m pip install -r requirements.txt
    $PYTHON -m pip install pytest pytest-cov ruff mypy bandit safety
    echo -e "${GREEN}✓ Development dependencies installed${NC}"
}

cmd_setup() {
    echo -e "${BLUE}Setting up development environment...${NC}"
    cmd_install_dev
    mkdir -p logs sandbox
    echo -e "${GREEN}✓ Development environment ready${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Copy .env.example to .env and add your configuration"
    echo "  2. Run: ./build.sh run"
}

cmd_test() {
    echo -e "${BLUE}Running all tests...${NC}"
    $PYTHON -m pytest tests/ -v
    echo -e "${GREEN}✓ All tests passed${NC}"
}

cmd_test_quick() {
    echo -e "${BLUE}Running tests (fail fast)...${NC}"
    $PYTHON -m pytest tests/ -v -x --tb=short
}

cmd_test_unit() {
    echo -e "${BLUE}Running unit tests...${NC}"
    $PYTHON -m pytest tests/test_validation.py tests/test_config.py tests/test_errors.py tests/test_executor.py tests/test_safety.py tests/test_secrets.py tests/test_error_tracking.py tests/test_logger.py -v
}

cmd_test_security() {
    echo -e "${BLUE}Running security tests...${NC}"
    $PYTHON -m pytest tests/ -v -m "security or exploit or backdoor"
}

cmd_test_perf() {
    echo -e "${BLUE}Running performance tests...${NC}"
    $PYTHON -m pytest tests/ -v -m "performance"
}

cmd_test_dynamic() {
    echo -e "${BLUE}Running dynamic analysis tests...${NC}"
    $PYTHON -m pytest tests/ -v -m "dynamic"
}

cmd_lint() {
    echo -e "${BLUE}Running linter...${NC}"
    $PYTHON -m ruff check core utils cli.py
    echo -e "${GREEN}✓ Linting complete${NC}"
}

cmd_format() {
    echo -e "${BLUE}Formatting code...${NC}"
    $PYTHON -m ruff format core utils cli.py tests
    $PYTHON -m ruff check core utils cli.py --fix
    echo -e "${GREEN}✓ Code formatted${NC}"
}

cmd_typecheck() {
    echo -e "${BLUE}Running type checker...${NC}"
    $PYTHON -m mypy core utils cli.py --ignore-missing-imports || true
    echo -e "${GREEN}✓ Type checking complete${NC}"
}

cmd_security() {
    echo -e "${BLUE}Running security scan...${NC}"
    $PYTHON -m bandit -r core utils cli.py -f txt || true
    echo -e "${GREEN}✓ Security scan complete${NC}"
}

cmd_check() {
    echo -e "${BLUE}Running all checks...${NC}"
    cmd_lint
    cmd_typecheck
    cmd_security
    echo -e "${GREEN}✓ All checks complete${NC}"
}

cmd_clean() {
    echo -e "${BLUE}Cleaning build artifacts...${NC}"
    rm -rf __pycache__ */__pycache__ */*/__pycache__
    rm -rf .pytest_cache .mypy_cache .ruff_cache
    rm -rf .coverage htmlcov coverage.xml
    rm -rf dist build *.egg-info
    rm -rf test-results.xml bandit-results.json
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

cmd_run() {
    echo -e "${BLUE}Starting Ollama Automation Harness...${NC}"
    $PYTHON cli.py run
}

cmd_version() {
    $PYTHON cli.py version
}

cmd_build() {
    echo -e "${BLUE}Building distribution packages...${NC}"
    $PYTHON -m pip install --upgrade build
    $PYTHON -m build
    echo -e "${GREEN}✓ Build complete - packages in dist/${NC}"
}

cmd_package_zip() {
    echo -e "${BLUE}Creating zip distribution...${NC}"
    $PYTHON scripts/package.py zip
    echo -e "${GREEN}✓ Zip package created in dist/${NC}"
}

cmd_package_exe() {
    echo -e "${BLUE}Creating standalone executable...${NC}"
    $PYTHON -m pip install pyinstaller
    $PYTHON scripts/package.py exe
    echo -e "${GREEN}✓ Executable created in dist/${NC}"
}

cmd_package_docker() {
    echo -e "${BLUE}Building production Docker image...${NC}"
    docker build -f Dockerfile.prod -t ollama-harness:latest .
    echo -e "${GREEN}✓ Docker image built${NC}"
}

cmd_package_all() {
    echo -e "${BLUE}Creating all distribution packages...${NC}"
    $PYTHON scripts/package.py all
    echo -e "${GREEN}✓ All packages created in dist/${NC}"
}

cmd_ci() {
    echo -e "${BLUE}Running CI checks...${NC}"
    echo -e "${BLUE}[1/3] Linting...${NC}"
    $PYTHON -m ruff check core utils cli.py --output-format=github || $PYTHON -m ruff check core utils cli.py
    echo -e "${BLUE}[2/3] Testing...${NC}"
    $PYTHON -m pytest tests/ -v --tb=short --junitxml=test-results.xml
    echo -e "${BLUE}[3/3] Security scan...${NC}"
    $PYTHON -m bandit -r core utils cli.py -f json -o bandit-results.json || true
    echo -e "${GREEN}✓ CI checks complete${NC}"
}

# Main
case "${1:-help}" in
    install)        cmd_install ;;
    install-dev)    cmd_install_dev ;;
    setup)          cmd_setup ;;
    test)           cmd_test ;;
    test-quick)     cmd_test_quick ;;
    test-unit)      cmd_test_unit ;;
    test-security)  cmd_test_security ;;
    test-perf)      cmd_test_perf ;;
    test-dynamic)   cmd_test_dynamic ;;
    lint)           cmd_lint ;;
    format)         cmd_format ;;
    typecheck)      cmd_typecheck ;;
    security)       cmd_security ;;
    check)          cmd_check ;;
    clean)          cmd_clean ;;
    run)            cmd_run ;;
    version)        cmd_version ;;
    build)          cmd_build ;;
    package-zip)    cmd_package_zip ;;
    package-exe)    cmd_package_exe ;;
    package-docker) cmd_package_docker ;;
    package-all)    cmd_package_all ;;
    ci)             cmd_ci ;;
    help|--help|-h) show_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
