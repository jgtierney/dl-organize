# Development Setup Guide

## System Requirements

Before setting up the development environment, ensure you have:

### Install System Packages
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev
```

## Setup Steps

### 1. Create Virtual Environment
```bash
cd /home/john/file-organizer
python3 -m venv venv
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python -c "import unidecode; import yaml; print('Dependencies OK')"
```

### 5. Run Tests
```bash
# Test filename cleaner
python src/file_organizer/filename_cleaner.py

# Run all tests (when available)
python -m pytest tests/
```

## Development Tools (Optional)

### Install Development Dependencies
```bash
pip install pytest pytest-cov black flake8 mypy
```

### Code Formatting
```bash
black src/
```

### Linting
```bash
flake8 src/
```

### Type Checking
```bash
mypy src/
```

## Current Status

- ✅ Project structure created
- ✅ Core filename_cleaner.py implemented
- ⏳ **Next**: Install dependencies and test
- ⏳ CLI interface
- ⏳ Directory scanner
- ⏳ Full Stage 1 implementation

## Quick Start for User

After setup is complete:

```bash
# Activate environment
source venv/bin/activate

# Test on a directory (dry-run)
python -m file_organizer -if /path/to/test/directory

# Execute changes
python -m file_organizer -if /path/to/test/directory --execute
```

