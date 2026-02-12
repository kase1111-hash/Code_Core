# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Ollama Automation Harness.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Runtime Errors](#runtime-errors)
4. [Ollama Issues](#ollama-issues)
5. [Claude API Issues](#claude-api-issues)
6. [Permission & Security Issues](#permission--security-issues)
7. [Performance Issues](#performance-issues)
8. [Docker Issues](#docker-issues)
9. [Logging & Debugging](#logging--debugging)
10. [Getting Help](#getting-help)

---

## Quick Diagnostics

Run the built-in health check to identify issues:

```bash
# Run system health check
python cli.py check --verbose

# Or run code quality checks (lint + typecheck + security)
make check
```

This checks:
- Python version
- Ollama availability
- Required directories
- Configuration files
- Required packages

### Common Output

```
System Health Check
==================================================
[OK] Python 3.10.12
[OK] Ollama found: /usr/local/bin/ollama
[OK] Directory exists: sandbox/
[OK] Directory exists: logs/
[OK] Directory exists: config/
[OK] .env file exists
[OK] Permissions file exists
[OK] Package installed: anthropic
[OK] Package installed: PyYAML
[OK] Package installed: python-dotenv
--------------------------------------------------
Passed: 10, Failed: 0
```

---

## Installation Issues

### Python Version Too Old

**Error:**
```
SyntaxError: invalid syntax
# or
ModuleNotFoundError: No module named 'typing'
```

**Solution:**
```bash
# Check version
python --version

# Use Python 3.10+
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'anthropic'
```

**Solution:**
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### pip Install Fails

**Error:**
```
ERROR: Could not build wheels for PyYAML
```

**Solution:**
```bash
# Install build dependencies
# Ubuntu/Debian
sudo apt-get install python3-dev libyaml-dev

# macOS
brew install libyaml

# Then retry
pip install -r requirements.txt
```

### Permission Denied During Install

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or use --user flag (not recommended)
pip install --user -r requirements.txt
```

---

## Runtime Errors

### "No module named 'core'"

**Error:**
```
ModuleNotFoundError: No module named 'core'
```

**Solution:**
```bash
# Ensure you're in the project directory
cd /path/to/ollama-automation-harness

# Ensure virtual environment is active
source .venv/bin/activate

# Run from project root
python main.py
```

### "Config file not found"

**Error:**
```
FileNotFoundError: config/permissions.yaml not found
```

**Solution:**
```bash
# Initialize configuration
python -m cli config init

# Or initialize via CLI
python -m cli config init --force
```

### "Sandbox directory does not exist"

**Error:**
```
FileNotFoundError: ./sandbox does not exist
```

**Solution:**
```bash
# Create directories
mkdir -p sandbox logs

# Or run health check with fix
python -m cli check --fix
```

### YAML Parse Error

**Error:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution:**
```yaml
# Check permissions.yaml for syntax errors
# Ensure proper indentation (2 spaces)

# Correct:
actions:
  read_file: auto
  write_file: ask

# Incorrect:
actions:
read_file: auto  # Missing indentation
```

---

## Ollama Issues

### Ollama Not Found

**Error:**
```
OllamaError: Ollama not found. Please install Ollama
```

**Solution:**

1. **Install Ollama:**
   ```bash
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # macOS
   brew install ollama

   # Or download from https://ollama.com
   ```

2. **Verify installation:**
   ```bash
   which ollama
   ollama --version
   ```

3. **Start Ollama service:**
   ```bash
   ollama serve
   ```

4. **Pull required model:**
   ```bash
   ollama pull llama3
   ```

### Ollama Timeout

**Error:**
```
OllamaError: Ollama timed out after 60 seconds
```

**Solution:**

1. **Increase timeout:**
   ```bash
   # In .env
   OLLAMA_TIMEOUT=120
   ```

2. **Use a smaller model:**
   ```bash
   ollama pull phi
   # Then in .env
   OLLAMA_MODEL=phi
   ```

3. **Check system resources:**
   ```bash
   # Memory
   free -h

   # CPU
   top
   ```

4. **Restart Ollama:**
   ```bash
   # Kill existing
   pkill ollama

   # Restart
   ollama serve
   ```

### Model Not Found

**Error:**
```
Error: model 'llama3' not found
```

**Solution:**
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3

# Verify
ollama run llama3 "Hello"
```

### Ollama Crashes or Freezes

**Symptoms:**
- No response from Ollama
- High memory usage
- System becomes unresponsive

**Solution:**

1. **Kill and restart:**
   ```bash
   pkill -9 ollama
   ollama serve
   ```

2. **Use smaller model:**
   ```bash
   # phi is smaller and faster
   ollama pull phi
   ```

3. **Increase swap (Linux):**
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## Claude API Issues

### API Key Not Set

**Warning:**
```
Warning: ANTHROPIC_API_KEY not set, using Ollama fallback
```

**Solution:**
```bash
# Add to .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env

# Or export directly
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Authentication Error

**Error:**
```
ClaudeError: Authentication failed (401)
```

**Solution:**

1. **Verify API key:**
   ```bash
   # Check key is set
   echo $ANTHROPIC_API_KEY

   # Should start with sk-ant-
   ```

2. **Check key validity at console.anthropic.com**

3. **Regenerate key if necessary**

### Rate Limit Exceeded

**Error:**
```
ClaudeError: Rate limit exceeded (429)
```

**Solution:**

1. **Wait and retry** - Rate limits reset over time

2. **Reduce request frequency:**
   ```bash
   # In .env
   LOOP_DELAY=5.0
   ```

3. **Use Ollama for some operations:**
   ```python
   # Force Ollama for classification
   response = get_response(prompt, use_api=False)
   ```

### API Error (500/503)

**Error:**
```
ClaudeError: API server error (500)
```

**Solution:**

1. **Check Anthropic status:** [status.anthropic.com](https://status.anthropic.com)

2. **Retry with backoff** - Automatic retry is built in

3. **Fall back to Ollama:**
   ```bash
   # Temporarily unset API key
   unset ANTHROPIC_API_KEY
   python main.py
   ```

---

## Permission & Security Issues

### Path Traversal Blocked

**Error:**
```
ExecutionResult: Path validation failed: ../sensitive/file.txt
```

**This is expected behavior.** The harness prevents access outside the sandbox.

**If you need to access files outside sandbox:**
1. Copy files into sandbox
2. Adjust `SANDBOX_DIR` in `.env`
3. Use absolute paths within allowed directories

### Permission Denied by Policy

**Error:**
```
Decision: user (Action denied by policy)
```

**Solution:**
```yaml
# In config/permissions.yaml
# Change from:
actions:
  your_action: deny

# To:
actions:
  your_action: ask  # or auto
```

### Extension Not Allowed

**Error:**
```
ExecutionResult: Extension not allowed: .exe
```

**Solution:**
```yaml
# In config/permissions.yaml
sandbox:
  allowed_extensions:
    - .py
    - .txt
    - .json
    - .exe  # Add if needed (use caution!)
```

### Dangerous Keyword False Positive

**Symptom:** Safe commands trigger user approval

**Solution:**
```yaml
# Review dangerous_keywords in config/permissions.yaml
dangerous_keywords:
  - deploy
  - production
  # Remove false positives
  # - keyword_causing_issues
```

---

## Performance Issues

### Slow Response Times

**Diagnosis:**
```bash
# Enable verbose mode
python main.py -v

# Check timing in logs
grep "duration" logs/automation.log
```

**Solutions:**

1. **Use faster Ollama model:**
   ```bash
   OLLAMA_MODEL=phi
   ```

2. **Increase API tokens (fewer round-trips):**
   ```bash
   CLAUDE_MAX_TOKENS=8192
   ```

3. **Check network latency:**
   ```bash
   ping api.anthropic.com
   ```

### High Memory Usage

**Diagnosis:**
```bash
# Check process memory
ps aux | grep -E "python|ollama"

# Monitor in real-time
htop
```

**Solutions:**

1. **Use smaller Ollama model**
2. **Restart Ollama periodically**
3. **Limit concurrent operations**

### Log Files Too Large

**Solution:**
```bash
# Enable log rotation (already default)
# In .env
LOG_ROTATION=true
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5

# Manual cleanup
rm logs/automation.log.*
```

---

## Docker Issues

### Container Won't Start

**Error:**
```
docker: Error response from daemon: Conflict
```

**Solution:**
```bash
# Remove existing container
docker rm ollama-harness

# Rebuild and run
docker-compose up --build
```

### Volume Mount Errors

**Error:**
```
Error: path /app/sandbox is not shared from the host
```

**Solution:**
```bash
# Create directories first
mkdir -p sandbox logs config

# Use absolute paths in docker-compose.yml
volumes:
  - /full/path/to/sandbox:/app/sandbox
```

### Ollama Not Available in Container

**Solution:**

1. **Use host network:**
   ```yaml
   # docker-compose.yml
   network_mode: host
   ```

2. **Or use Ollama container:**
   ```yaml
   services:
     ollama:
       image: ollama/ollama
     harness:
       depends_on:
         - ollama
       environment:
         - OLLAMA_HOST=ollama:11434
   ```

### Permission Issues in Container

**Solution:**
```dockerfile
# In Dockerfile
RUN chown -R 1000:1000 /app
USER 1000
```

---

## Logging & Debugging

### Enable Debug Mode

```bash
# In .env
DEBUG=true

# Or at runtime
DEBUG=true python main.py
```

### View Detailed Logs

```bash
# Follow logs in real-time
tail -f logs/automation.log

# Search for errors
grep -i error logs/automation.log

# View with context
grep -B5 -A5 "ClaudeError" logs/automation.log
```

### Enable JSON Logging

```bash
# In .env
LOG_JSON=true

# View with jq
tail -f logs/automation.json | jq
```

### Debug Classification

```bash
# See classification details
python main.py -v 2>&1 | grep -i "decision\|classify"
```

### Capture Full Debug Output

```bash
# Save all output
python main.py -v 2>&1 | tee debug.log

# With timestamps
python main.py -v 2>&1 | ts '[%Y-%m-%d %H:%M:%S]' | tee debug.log
```

---

## Getting Help

### Before Asking for Help

1. **Run diagnostics:**
   ```bash
   python -m cli check --verbose
   ```

2. **Check logs:**
   ```bash
   tail -50 logs/automation.log
   ```

3. **Search existing issues:**
   - [GitHub Issues](https://github.com/kase1111-hash/Code_Core/issues)

### Information to Include

When reporting issues, include:

```markdown
**Environment:**
- OS: (e.g., Ubuntu 22.04, macOS 14.0, Windows 11)
- Python: (output of `python --version`)
- Ollama: (output of `ollama --version`)

**Steps to Reproduce:**
1. ...
2. ...

**Expected Behavior:**
...

**Actual Behavior:**
...

**Error Output:**
```
(paste error here)
```

**Relevant Config:**
```yaml
(paste relevant config, redact secrets)
```

**Log Output:**
```
(paste relevant logs)
```
```

### Where to Get Help

1. **GitHub Issues:** For bugs and feature requests
2. **Discussions:** For questions and community help
3. **Documentation:** Check all docs in `docs/` directory

---

## Error Reference

### Error Codes

| Code | Name | Description |
|------|------|-------------|
| 1000 | UNKNOWN | Unknown error |
| 1001 | CONFIGURATION | Configuration error |
| 1002 | VALIDATION | Input validation failed |
| 2001 | OLLAMA_ERROR | General Ollama error |
| 2002 | OLLAMA_TIMEOUT | Ollama operation timed out |
| 2003 | OLLAMA_NOT_FOUND | Ollama not installed |
| 2011 | CLAUDE_ERROR | General Claude error |
| 2012 | CLAUDE_API_ERROR | Claude API returned error |
| 2013 | CLAUDE_AUTH_ERROR | Claude authentication failed |
| 3001 | EXECUTION_ERROR | Command execution failed |
| 3002 | SANDBOX_VIOLATION | Path outside sandbox |
| 3003 | PERMISSION_DENIED | Action not permitted |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Dependency missing |
| 130 | Interrupted (Ctrl+C) |

---

*Last updated: 2025-02-12*
