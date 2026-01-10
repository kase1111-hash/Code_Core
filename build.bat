@echo off
REM Ollama Automation Harness - Windows Build Script
REM Usage: build.bat [command]
REM
REM Commands:
REM   install      - Install dependencies
REM   install-dev  - Install development dependencies
REM   test         - Run all tests
REM   test-quick   - Run quick tests
REM   lint         - Run linting
REM   format       - Format code
REM   check        - Run all checks
REM   clean        - Clean build artifacts
REM   run          - Run the application
REM   help         - Show this help

setlocal enabledelayedexpansion

REM Set Python command (use python or python3)
set PYTHON=python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    set PYTHON=python3
)

REM Parse command
if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="test" goto test
if "%1"=="test-quick" goto test-quick
if "%1"=="test-unit" goto test-unit
if "%1"=="test-security" goto test-security
if "%1"=="test-performance" goto test-performance
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="typecheck" goto typecheck
if "%1"=="security" goto security
if "%1"=="check" goto check
if "%1"=="clean" goto clean
if "%1"=="run" goto run
if "%1"=="version" goto version
if "%1"=="build" goto build
if "%1"=="package-zip" goto package-zip
if "%1"=="package-exe" goto package-exe
if "%1"=="package-docker" goto package-docker
if "%1"=="package-all" goto package-all
if "%1"=="ci" goto ci

echo Unknown command: %1
goto help

:help
echo.
echo Ollama Automation Harness - Build Script
echo.
echo Usage: build.bat [command]
echo.
echo Commands:
echo   install       Install runtime dependencies
echo   install-dev   Install development dependencies
echo   test          Run all tests
echo   test-quick    Run tests (fail fast)
echo   test-unit     Run unit tests only
echo   test-security Run security tests
echo   test-performance Run performance tests
echo   lint          Run linting (ruff)
echo   format        Format code (ruff)
echo   typecheck     Run type checking (mypy)
echo   security      Run security scan (bandit)
echo   check         Run all code quality checks
echo   clean         Clean build artifacts
echo   run           Run the application
echo   version       Show version
echo   build         Build distribution packages
echo   package-zip   Create zip distribution
echo   package-exe   Create standalone executable
echo   package-docker Build production Docker image
echo   package-all   Create all distribution packages
echo   ci            Run all CI checks
echo   help          Show this help
echo.
goto end

:install
echo Installing runtime dependencies...
%PYTHON% -m pip install -r requirements.txt
if %ERRORLEVEL% equ 0 (
    echo Dependencies installed successfully.
) else (
    echo Failed to install dependencies.
    exit /b 1
)
goto end

:install-dev
echo Installing development dependencies...
%PYTHON% -m pip install -r requirements.txt
%PYTHON% -m pip install pytest pytest-cov ruff mypy bandit
if %ERRORLEVEL% equ 0 (
    echo Development dependencies installed successfully.
) else (
    echo Failed to install dependencies.
    exit /b 1
)
goto end

:test
echo Running all tests...
%PYTHON% -m pytest tests/ -v
if %ERRORLEVEL% equ 0 (
    echo All tests passed.
) else (
    echo Some tests failed.
    exit /b 1
)
goto end

:test-quick
echo Running tests (fail fast)...
%PYTHON% -m pytest tests/ -v -x --tb=short
goto end

:test-unit
echo Running unit tests...
%PYTHON% -m pytest tests/test_validation.py tests/test_config.py tests/test_errors.py tests/test_executor.py tests/test_safety.py -v
goto end

:test-security
echo Running security tests...
%PYTHON% -m pytest tests/ -v -m "security or exploit or backdoor"
goto end

:test-performance
echo Running performance tests...
%PYTHON% -m pytest tests/ -v -m "performance"
goto end

:lint
echo Running linter...
%PYTHON% -m ruff check core utils cli.py
if %ERRORLEVEL% equ 0 (
    echo Linting passed.
) else (
    echo Linting found issues.
)
goto end

:format
echo Formatting code...
%PYTHON% -m ruff format core utils cli.py tests
%PYTHON% -m ruff check core utils cli.py --fix
echo Code formatted.
goto end

:typecheck
echo Running type checker...
%PYTHON% -m mypy core utils cli.py --ignore-missing-imports
goto end

:security
echo Running security scan...
%PYTHON% -m bandit -r core utils cli.py -f txt
goto end

:check
echo Running all checks...
call :lint
call :typecheck
call :security
echo All checks complete.
goto end

:clean
echo Cleaning build artifacts...
if exist __pycache__ rmdir /s /q __pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .mypy_cache rmdir /s /q .mypy_cache
if exist .ruff_cache rmdir /s /q .ruff_cache
if exist htmlcov rmdir /s /q htmlcov
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist .coverage del .coverage
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul
echo Cleanup complete.
goto end

:run
echo Starting Ollama Automation Harness...
%PYTHON% cli.py run
goto end

:version
%PYTHON% cli.py version
goto end

:build
echo Building distribution packages...
%PYTHON% -m pip install --upgrade build
%PYTHON% -m build
echo Build complete - packages in dist/
goto end

:package-zip
echo Creating zip distribution...
%PYTHON% scripts/package.py zip
echo Zip package created in dist/
goto end

:package-exe
echo Creating standalone executable...
%PYTHON% -m pip install pyinstaller
%PYTHON% scripts/package.py exe
echo Executable created in dist/
goto end

:package-docker
echo Building production Docker image...
docker build -f Dockerfile.prod -t ollama-harness:latest .
echo Docker image built.
goto end

:package-all
echo Creating all distribution packages...
%PYTHON% scripts/package.py all
echo All packages created in dist/
goto end

:ci
echo Running CI checks...
call :lint
call :test
call :security
echo CI checks complete.
goto end

:end
endlocal
