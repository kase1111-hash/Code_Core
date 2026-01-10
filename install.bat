@echo off
REM =============================================================================
REM Ollama Automation Harness - Windows Installation Script
REM =============================================================================
REM This script installs the Ollama Automation Harness on Windows
REM
REM Usage:
REM   install.bat              - Interactive installation
REM   install.bat /quiet       - Non-interactive with defaults
REM   install.bat /dev         - Install with development dependencies
REM   install.bat /uninstall   - Remove installation
REM
REM Requirements:
REM   - Python 3.10 or higher
REM   - pip (Python package manager)
REM   - Ollama (optional, for local LLM)
REM =============================================================================

setlocal enabledelayedexpansion

REM Configuration
set "INSTALL_DIR=%USERPROFILE%\.ollama-harness"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "APP_NAME=ollama-harness"
set "MIN_PYTHON_VERSION=3.10"

REM Flags
set "QUIET=false"
set "DEV_MODE=false"
set "UNINSTALL=false"

REM Parse arguments
:parse_args
if "%1"=="" goto main
if /i "%1"=="/quiet" set "QUIET=true" & shift & goto parse_args
if /i "%1"=="/q" set "QUIET=true" & shift & goto parse_args
if /i "%1"=="/dev" set "DEV_MODE=true" & shift & goto parse_args
if /i "%1"=="/d" set "DEV_MODE=true" & shift & goto parse_args
if /i "%1"=="/uninstall" set "UNINSTALL=true" & shift & goto parse_args
if /i "%1"=="/u" set "UNINSTALL=true" & shift & goto parse_args
if /i "%1"=="/help" goto show_help
if /i "%1"=="/h" goto show_help
if /i "%1"=="/?" goto show_help
echo Unknown option: %1
goto show_help

:show_help
echo Ollama Automation Harness Installer
echo.
echo Usage: install.bat [options]
echo.
echo Options:
echo   /quiet, /q       Non-interactive installation
echo   /dev, /d         Install development dependencies
echo   /uninstall, /u   Remove installation
echo   /help, /h, /?    Show this help
goto end

:main
if "%UNINSTALL%"=="true" goto uninstall
goto install

REM =============================================================================
REM Installation
REM =============================================================================

:install
call :print_banner
echo.
echo Installation Settings:
echo   Install directory: %INSTALL_DIR%
echo   Development mode:  %DEV_MODE%
echo.

if "%QUIET%"=="false" (
    set /p "CONTINUE=Continue with installation? [Y/n] "
    if /i "!CONTINUE!"=="n" (
        echo Installation cancelled.
        goto end
    )
)

REM Check Python
call :check_python
if errorlevel 1 goto error

REM Check pip
call :check_pip
if errorlevel 1 goto error

REM Check Ollama (optional)
call :check_ollama

REM Create directories
call :create_directories

REM Create virtual environment
call :create_virtualenv
if errorlevel 1 goto error

REM Install dependencies
call :install_dependencies
if errorlevel 1 goto error

REM Copy application files
call :copy_files

REM Create launcher
call :create_launcher

REM Done
call :print_success
goto end

:check_python
echo [INFO] Checking Python installation...
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python %MIN_PYTHON_VERSION% or higher.
    echo   Visit: https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=*" %%i in ('python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"') do set "PYTHON_VERSION=%%i"
echo [SUCCESS] Python %PYTHON_VERSION% found
exit /b 0

:check_pip
echo [INFO] Checking pip installation...
python -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] pip not found. Please install pip.
    echo   Run: python -m ensurepip --upgrade
    exit /b 1
)
echo [SUCCESS] pip is available
exit /b 0

:check_ollama
echo [INFO] Checking Ollama installation...
where ollama >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Ollama not found. Install it for local LLM support.
    echo   Visit: https://ollama.ai/download
) else (
    echo [SUCCESS] Ollama found
)
exit /b 0

:create_directories
echo [INFO] Creating installation directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\logs" mkdir "%INSTALL_DIR%\logs"
if not exist "%INSTALL_DIR%\sandbox" mkdir "%INSTALL_DIR%\sandbox"
if not exist "%INSTALL_DIR%\config" mkdir "%INSTALL_DIR%\config"
echo [SUCCESS] Directories created
exit /b 0

:create_virtualenv
echo [INFO] Creating virtual environment...
if exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment exists, recreating...
    rmdir /s /q "%VENV_DIR%"
)
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    exit /b 1
)
echo [SUCCESS] Virtual environment created
exit /b 0

:install_dependencies
echo [INFO] Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
python -m pip install --upgrade pip

REM Install requirements
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    pip install python-dotenv pyyaml anthropic sentry-sdk
)

REM Install dev dependencies if requested
if "%DEV_MODE%"=="true" (
    echo [INFO] Installing development dependencies...
    if exist "requirements-dev.txt" (
        pip install -r requirements-dev.txt
    ) else (
        pip install pytest pytest-cov ruff mypy bandit
    )
)

call "%VENV_DIR%\Scripts\deactivate.bat"
echo [SUCCESS] Dependencies installed
exit /b 0

:copy_files
echo [INFO] Copying application files...
xcopy /E /I /Y "core" "%INSTALL_DIR%\core" >nul
xcopy /E /I /Y "utils" "%INSTALL_DIR%\utils" >nul
xcopy /E /I /Y "config" "%INSTALL_DIR%\config" >nul
copy /Y "cli.py" "%INSTALL_DIR%\" >nul
copy /Y "main.py" "%INSTALL_DIR%\" >nul

if exist ".env.example" (
    copy /Y ".env.example" "%INSTALL_DIR%\" >nul
    if not exist "%INSTALL_DIR%\.env" (
        copy /Y ".env.example" "%INSTALL_DIR%\.env" >nul
    )
)
echo [SUCCESS] Application files copied
exit /b 0

:create_launcher
echo [INFO] Creating launcher script...

REM Create batch launcher
(
echo @echo off
echo setlocal
echo set "INSTALL_DIR=%INSTALL_DIR%"
echo call "%%INSTALL_DIR%%\venv\Scripts\activate.bat"
echo cd /d "%%INSTALL_DIR%%"
echo python main.py %%*
echo endlocal
) > "%INSTALL_DIR%\%APP_NAME%.bat"

REM Create PowerShell launcher
(
echo # Ollama Automation Harness Launcher
echo $InstallDir = "%INSTALL_DIR%"
echo ^& "$InstallDir\venv\Scripts\Activate.ps1"
echo Set-Location $InstallDir
echo python main.py @args
echo deactivate
) > "%INSTALL_DIR%\%APP_NAME%.ps1"

echo [SUCCESS] Launcher scripts created
echo.
echo To run from anywhere, add %INSTALL_DIR% to your PATH:
echo   1. Open System Properties ^> Advanced ^> Environment Variables
echo   2. Edit PATH and add: %INSTALL_DIR%
echo.
echo Or run directly: %INSTALL_DIR%\%APP_NAME%.bat
exit /b 0

:print_banner
echo.
echo =====================================================================
echo              Ollama Automation Harness Installer
echo =====================================================================
exit /b 0

:print_success
echo.
echo =====================================================================
echo                    Installation Complete!
echo =====================================================================
echo.
echo Next steps:
echo   1. Configure your settings: notepad %INSTALL_DIR%\.env
echo   2. Run the application: %INSTALL_DIR%\%APP_NAME%.bat --help
echo.
echo For more information, see the README.md
exit /b 0

REM =============================================================================
REM Uninstallation
REM =============================================================================

:uninstall
call :print_banner
echo.
echo [WARNING] Uninstalling Ollama Automation Harness...
echo.

if "%QUIET%"=="false" (
    set /p "CONFIRM=Are you sure you want to uninstall? [y/N] "
    if /i not "!CONFIRM!"=="y" (
        echo Uninstall cancelled.
        goto end
    )
)

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo [SUCCESS] Removed %INSTALL_DIR%
) else (
    echo [INFO] Installation directory not found
)

echo.
echo [SUCCESS] Uninstallation complete
goto end

:error
echo.
echo [ERROR] Installation failed
exit /b 1

:end
endlocal
