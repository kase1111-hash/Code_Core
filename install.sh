#!/bin/bash
# =============================================================================
# Ollama Automation Harness - Installation Script
# =============================================================================
# This script installs the Ollama Automation Harness on Unix/Linux/macOS
#
# Usage:
#   ./install.sh              # Interactive installation
#   ./install.sh --quiet      # Non-interactive with defaults
#   ./install.sh --dev        # Install with development dependencies
#   ./install.sh --uninstall  # Remove installation
#
# Requirements:
#   - Python 3.10 or higher
#   - pip (Python package manager)
#   - Ollama (optional, for local LLM)
# =============================================================================

set -e

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/.ollama-harness}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
APP_NAME="ollama-harness"
MIN_PYTHON_VERSION="3.10"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Flags
QUIET=false
DEV_MODE=false
UNINSTALL=false

# =============================================================================
# Helper Functions
# =============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║              Ollama Automation Harness Installer                  ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    command -v "$1" &> /dev/null
}

version_gte() {
    # Compare versions: returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# =============================================================================
# Prerequisite Checks
# =============================================================================

check_python() {
    log_info "Checking Python installation..."

    local python_cmd=""

    # Try python3 first, then python
    if check_command python3; then
        python_cmd="python3"
    elif check_command python; then
        python_cmd="python"
    else
        log_error "Python not found. Please install Python $MIN_PYTHON_VERSION or higher."
        echo "  Visit: https://www.python.org/downloads/"
        exit 1
    fi

    # Check version
    local version=$($python_cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

    if version_gte "$version" "$MIN_PYTHON_VERSION"; then
        log_success "Python $version found ($python_cmd)"
        PYTHON_CMD="$python_cmd"
    else
        log_error "Python $version is too old. Please install Python $MIN_PYTHON_VERSION or higher."
        exit 1
    fi
}

check_pip() {
    log_info "Checking pip installation..."

    if $PYTHON_CMD -m pip --version &> /dev/null; then
        log_success "pip is available"
    else
        log_error "pip not found. Please install pip."
        echo "  Run: $PYTHON_CMD -m ensurepip --upgrade"
        exit 1
    fi
}

check_ollama() {
    log_info "Checking Ollama installation..."

    if check_command ollama; then
        local ollama_version=$(ollama --version 2>/dev/null | head -1)
        log_success "Ollama found: $ollama_version"
        return 0
    else
        log_warning "Ollama not found. Install it for local LLM support."
        echo "  Visit: https://ollama.ai/download"
        return 1
    fi
}

# =============================================================================
# Installation Functions
# =============================================================================

create_directories() {
    log_info "Creating installation directories..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/sandbox"
    mkdir -p "$INSTALL_DIR/config"
    mkdir -p "$BIN_DIR"

    log_success "Directories created"
}

create_virtualenv() {
    log_info "Creating virtual environment..."

    if [ -d "$VENV_DIR" ]; then
        log_warning "Virtual environment already exists, recreating..."
        rm -rf "$VENV_DIR"
    fi

    $PYTHON_CMD -m venv "$VENV_DIR"
    log_success "Virtual environment created at $VENV_DIR"
}

install_dependencies() {
    log_info "Installing dependencies..."

    # Activate virtual environment
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install from requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        # Install core dependencies directly
        pip install python-dotenv pyyaml anthropic sentry-sdk
    fi

    # Install dev dependencies if requested
    if [ "$DEV_MODE" = true ]; then
        log_info "Installing development dependencies..."
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
        else
            pip install pytest pytest-cov ruff mypy bandit
        fi
    fi

    deactivate
    log_success "Dependencies installed"
}

copy_application_files() {
    log_info "Copying application files..."

    # Copy source files
    cp -r core "$INSTALL_DIR/"
    cp -r utils "$INSTALL_DIR/"
    cp -r config "$INSTALL_DIR/"
    cp cli.py "$INSTALL_DIR/"
    cp main.py "$INSTALL_DIR/"

    # Copy configuration templates
    if [ -f ".env.example" ]; then
        cp .env.example "$INSTALL_DIR/"
        if [ ! -f "$INSTALL_DIR/.env" ]; then
            cp .env.example "$INSTALL_DIR/.env"
        fi
    fi

    log_success "Application files copied"
}

create_launcher_script() {
    log_info "Creating launcher script..."

    cat > "$BIN_DIR/$APP_NAME" << 'LAUNCHER'
#!/bin/bash
# Ollama Automation Harness Launcher

INSTALL_DIR="${OLLAMA_HARNESS_HOME:-$HOME/.ollama-harness}"
VENV_DIR="$INSTALL_DIR/venv"

# Activate virtual environment and run
source "$VENV_DIR/bin/activate"
cd "$INSTALL_DIR"
python main.py "$@"
deactivate
LAUNCHER

    chmod +x "$BIN_DIR/$APP_NAME"
    log_success "Launcher script created at $BIN_DIR/$APP_NAME"
}

configure_environment() {
    log_info "Configuring environment..."

    # Check if BIN_DIR is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        log_warning "$BIN_DIR is not in your PATH"

        local shell_rc=""
        if [ -f "$HOME/.bashrc" ]; then
            shell_rc="$HOME/.bashrc"
        elif [ -f "$HOME/.zshrc" ]; then
            shell_rc="$HOME/.zshrc"
        fi

        if [ -n "$shell_rc" ] && [ "$QUIET" = false ]; then
            echo ""
            read -p "Add $BIN_DIR to PATH in $shell_rc? [y/N] " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "" >> "$shell_rc"
                echo "# Ollama Automation Harness" >> "$shell_rc"
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$shell_rc"
                log_success "PATH updated in $shell_rc"
                echo "  Please restart your shell or run: source $shell_rc"
            fi
        else
            echo ""
            echo "Add this to your shell config:"
            echo "  export PATH=\"\$PATH:$BIN_DIR\""
        fi
    fi
}

# =============================================================================
# Uninstallation
# =============================================================================

uninstall() {
    print_banner
    log_warning "Uninstalling Ollama Automation Harness..."

    if [ "$QUIET" = false ]; then
        read -p "Are you sure you want to uninstall? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Uninstall cancelled"
            exit 0
        fi
    fi

    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed $INSTALL_DIR"
    fi

    # Remove launcher script
    if [ -f "$BIN_DIR/$APP_NAME" ]; then
        rm -f "$BIN_DIR/$APP_NAME"
        log_success "Removed $BIN_DIR/$APP_NAME"
    fi

    log_success "Uninstallation complete"
}

# =============================================================================
# Main Installation
# =============================================================================

install() {
    print_banner

    echo -e "${BOLD}Installation Settings:${NC}"
    echo "  Install directory: $INSTALL_DIR"
    echo "  Binary directory:  $BIN_DIR"
    echo "  Development mode:  $DEV_MODE"
    echo ""

    if [ "$QUIET" = false ]; then
        read -p "Continue with installation? [Y/n] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Installation cancelled"
            exit 0
        fi
    fi

    # Run installation steps
    check_python
    check_pip
    check_ollama || true  # Optional
    create_directories
    create_virtualenv
    install_dependencies
    copy_application_files
    create_launcher_script
    configure_environment

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   Installation Complete!                          ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Configure your settings: nano $INSTALL_DIR/.env"
    echo "  2. Run the application: $APP_NAME --help"
    echo ""
    echo "For more information, see the README.md"
}

# =============================================================================
# Parse Arguments
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet|-q)
            QUIET=true
            shift
            ;;
        --dev|-d)
            DEV_MODE=true
            shift
            ;;
        --uninstall|-u)
            UNINSTALL=true
            shift
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            VENV_DIR="$INSTALL_DIR/venv"
            shift 2
            ;;
        --bin-dir)
            BIN_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Ollama Automation Harness Installer"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --quiet, -q       Non-interactive installation"
            echo "  --dev, -d         Install development dependencies"
            echo "  --uninstall, -u   Remove installation"
            echo "  --install-dir     Set installation directory"
            echo "  --bin-dir         Set binary directory"
            echo "  --help, -h        Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run appropriate action
if [ "$UNINSTALL" = true ]; then
    uninstall
else
    install
fi
