# Project Overview

## What the application does

File Organizer is a powerful Python application for systematically organizing and cleaning up large collections of downloaded files. It's designed to handle 100,000-500,000 files across thousands of directories with comprehensive filename sanitization, folder structure optimization, duplicate detection, and file relocation.

The application processes files through a four-stage pipeline:

- **Stage 1: Filename Detoxification** - Converts filenames to lowercase ASCII, replaces spaces/special characters with underscores, transliterates international characters, removes hidden files, and handles naming collisions
- **Stage 2: Folder Structure Optimization** - Removes empty folders, flattens unnecessary nesting (configurable threshold), and sanitizes folder names
- **Stage 3A: Internal Duplicate Detection** - Uses metadata-first optimization (10x speedup), xxHash for ultra-fast hashing, SQLite cache for persistence, and applies a three-tier resolution policy (keep keyword → path depth → newest mtime)
- **Stage 3B: Cross-Folder Deduplication** - Compares input folder against output folder, reuses input cache from Stage 3A, applies same resolution policy
- **Stage 4: File Relocation** - Moves organized files from input to output folder, automatically classifies top-level files into `misc/` subfolder, preserves directory structure for folders, validates disk space, and optionally cleans input folder

## Tech stack

- **Language**: Python 3.8+ (supports Python 3.8 through 3.12)
- **Core Dependencies**:
  - `unidecode>=1.3.6` - ASCII transliteration for international characters (Stage 1)
  - `pyyaml>=6.0` - YAML configuration file support (Stage 2)
  - `xxhash>=3.0.0` - Ultra-fast file hashing at 10-20 GB/s (Stage 3)
- **Database**: SQLite (for persistent hash cache with 5 indexes)
- **Architecture**: CLI-based command-line tool
- **Package Management**: setuptools with entry points

## Architecture overview

The application follows a modular, stage-based pipeline architecture:

- **CLI Layer** (`cli.py`): Command-line interface with argument parsing, validation, and orchestration
- **Stage Processors**: 
  - `Stage1Processor` (`stage1.py`) - Filename sanitization engine
  - `Stage2Processor` (`stage2.py`) - Folder structure optimization
  - `Stage3` (`stage3.py`) - Duplicate detection orchestrator (handles both 3A and 3B)
  - `Stage4Processor` (`stage4.py`) - File relocation and cleanup
- **Core Modules**:
  - `filename_cleaner.py` - Filename sanitization logic with collision handling
  - `duplicate_detector.py` - Metadata-first duplicate detection engine (494 lines)
  - `duplicate_resolver.py` - Three-tier resolution policy implementation (350 lines)
  - `hash_cache.py` - SQLite-based persistent hash cache with batch operations (526 lines)
  - `config.py` - YAML configuration management with CLI override support
  - `progress_bar.py` - Adaptive progress reporting (scales with file count)
- **Entry Point**: `__main__.py` provides `python -m src.file_organizer` interface
- **Configuration**: Optional `.file_organizer.yaml` in execution directory (not home directory, supports per-project configs)
- **Cache Location**: `.file_organizer_cache/` SQLite database in execution directory

The architecture is designed for:
- Sequential stage execution (1 → 2 → 3A → 3B → 4)
- In-place modification for Stages 1-2
- Cross-folder operations for Stages 3B-4
- Dry-run default mode (preview before execute)
- Large-scale processing (100k-500k files, leverages 32GB RAM systems)

## Build/test commands

### Installation
```bash
# Clone repository
git clone https://github.com/jgtierney/dl-organize.git
cd dl-organize

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package (optional, for entry point)
pip install -e .
```

### Running the Application
```bash
# Dry-run (preview changes without executing)
python -m src.file_organizer -if /path/to/messy/downloads

# Execute all stages (Stages 1-2-3A only, no output folder)
python -m src.file_organizer -if /path/to/messy/downloads --execute

# Full pipeline with output folder (Stages 1-2-3A-3B-4)
python -m src.file_organizer -if /path/to/input -of /path/to/output --execute

# Run specific stage
python -m src.file_organizer -if /path --stage 1 --execute
python -m src.file_organizer -if /path --stage 2 --execute
python -m src.file_organizer -if /path --stage 3a --execute
python -m src.file_organizer -if /input -of /output --stage 3b --execute
python -m src.file_organizer -if /input -of /output --stage 4 --execute
```

### Testing
```bash
# Run tests (pytest)
pytest tests/

# Generate test data
python tools/generate_test_data.py /tmp/test --size small
python tools/generate_test_data.py /tmp/test --stage3 --size small
```

# Code Review Focus Areas

## Security

### Input Validation
- **System Directory Protection**: Blocks operations on dangerous system directories (`/`, `/usr`, `/bin`, `/sbin`, `/etc`, `/boot`, `/sys`, `/proc`, `/dev`, `/lib`, `/lib64`) - implemented in `cli.py:validate_arguments()` (lines 167-191)
- **Path Validation**: Verifies input/output directories exist and are actually directories before processing
- **Absolute Path Resolution**: Converts all paths to absolute paths for safety checks
- **CLI Argument Validation**: Comprehensive validation in `validate_arguments()` function

### Authentication & Authorization
- **File Permissions**: Attempts to set file permissions to `644` and directory permissions to `755` (Stage 1)
- **Ownership Changes**: Attempts to set owner to `nobody` and group to `users`, but gracefully handles failures (requires root)
- **Permission Errors**: Gracefully skips files with permission errors, logs them, and continues processing

### Data Exposure
- **Dry-Run Default**: Default mode is preview-only, preventing accidental modifications
- **Comprehensive Logging**: All operations logged with timestamps (though currently console-only, file logging not yet implemented)
- **Error Handling**: Skips problem files rather than aborting entire operation
- **Collision Prevention**: Unique naming for conflicting files prevents data loss

## Performance

### Database Queries
- **SQLite Cache Optimization**: Uses 5 indexes for fast lookups (file_path, folder, file_size, file_hash, file_mtime)
- **Batch Operations**: `get_files_by_paths()` method for batch queries instead of individual lookups
- **Cache Hit Rate**: Achieves 90-98% cache hit rate on subsequent runs, 100% hit rate for input folder in Stage 3B
- **WAL Mode**: SQLite uses Write-Ahead Logging for thread-safety (prepared for future parallelization)

### Algorithms
- **Metadata-First Optimization**: Only hashes files with size collisions (10x speedup over traditional approach)
- **Size-Based Filtering**: Skips files smaller than configurable threshold (default 10KB) before hashing
- **Image Skipping**: Optionally skips image files (.jpg, .png, etc.) which are often intentionally duplicated
- **Incremental Cache Reload**: After hashing, only reloads files that were hashed (not entire cache)

### Memory Usage
- **In-Memory Processing**: Designed to leverage 32GB RAM systems for performance
- **Large Dataset Handling**: Successfully tested on 110,000+ files
- **Cache Management**: SQLite cache persists to disk, reducing memory footprint for large datasets

### Known Performance Bottlenecks
- **Sequential Hashing**: Stage 3B hashing is sequential (one file at a time) - documented opportunity for 8-16x speedup with parallel hashing (see `docs/stage3b_bottleneck_analysis.md`)
- **Progress Reporting Gaps**: Some operations have "dead air" periods:
  - Stage 1: Initial directory scan (5-30 seconds for 100k+ files) - see `docs/progress_reporting_audit.md`
  - Stage 4: Folder size calculation (10-20 seconds for 100k+ files)
  - Stage 3B: Cross-folder duplicate finding (30-60 seconds depending on size)

## Code Quality

### Naming Conventions
- Follows PEP 8 style guide (mentioned in contributing guide)
- Class names use PascalCase (e.g., `Stage1Processor`, `FilenameCleaner`)
- Function/method names use snake_case (e.g., `process_files()`, `validate_arguments()`)
- Module names use snake_case (e.g., `filename_cleaner.py`, `duplicate_detector.py`)

### Structure
- **Modular Design**: Each stage is a separate processor class
- **Separation of Concerns**: Core logic separated from CLI, config, and utilities
- **Single Responsibility**: Each module has a clear, focused purpose
- **Type Hints**: Code uses type hints (e.g., `from typing import List, Dict, Tuple, Optional`)

### Maintainability
- **Comprehensive Documentation**: 1,639+ lines of detailed requirements documentation
- **Design Decisions Documented**: 29 design decisions documented in `docs/design_decisions.md`
- **Clear Error Messages**: Descriptive error messages for validation failures
- **Graceful Degradation**: Continues processing when individual files fail

## Testing

### Coverage
- **Test Files Exist**: `tests/test_stage3_optimizations.py` contains 11 test functions
- **Test Focus**: Currently focused on Stage 3 optimizations (batch queries, cache reuse, incremental reload)
- **Integration Testing**: Mentioned as priority in README but not yet fully implemented
- **Test Data Generator**: `tools/generate_test_data.py` available for generating test scenarios

### Test Quality
- **Unit Tests**: Tests for batch operations, cache management, duplicate detection
- **Performance Tests**: `test_batch_query_vs_get_all_files_performance()` measures performance improvements
- **Edge Cases**: Tests for empty lists, nonexistent paths, different folders

### Edge Cases
- **Known Gaps**: Full pipeline integration tests (Stages 1-2-3A-3B-4) mentioned as priority
- **Large Dataset Testing**: Performance testing with 500k+ files mentioned as ongoing priority
- **Error Handling**: Edge case coverage mentioned as priority

## Best Practices

### Framework-Specific Patterns
- **Pathlib Usage**: Consistent use of `pathlib.Path` instead of string paths
- **Python 3.8+ Features**: Uses modern Python features (type hints, f-strings, pathlib)
- **CLI Patterns**: Uses `argparse` with clear help text and validation
- **Configuration Patterns**: YAML configuration with CLI override precedence (CLI > Config > Defaults)

### Python Best Practices
- **Virtual Environment**: Project includes venv setup instructions
- **Package Structure**: Proper package structure with `src/` layout
- **Entry Points**: Uses setuptools entry points for CLI command (`file-organizer`)
- **Version Management**: Version tracked in `__init__.py` (`__version__ = "0.1.0-dev"`)

# Project-Specific Context

## Known issues or technical debt

### Performance Issues
1. **Sequential Hashing Bottleneck** (Stage 3B)
   - **Location**: `stage3.py:462-494` in `_find_cross_folder_duplicates()`
   - **Impact**: 114,189 files hashed sequentially, taking ~22 minutes (could be 1.5-3 minutes with parallel hashing)
   - **Opportunity**: 8-16x speedup with `ThreadPoolExecutor` parallelization (16 cores available)
   - **Documentation**: `docs/stage3b_bottleneck_analysis.md`, `docs/stage3_performance_analysis.md`

2. **Progress Reporting Gaps**
   - **Stage 1**: Initial directory scan has 5-30 seconds of "dead air" for 100k+ files
   - **Stage 4**: Folder size calculation has 10-20 seconds of "dead air"
   - **Stage 3B**: Cross-folder duplicate finding has 30-60 seconds of "dead air"
   - **Documentation**: `docs/progress_reporting_audit.md`, `docs/progress_reporting_implementation_plan.md`

3. **Cache Reload Optimization**
   - After hashing, currently reloads ALL files from cache (237k+ entries)
   - Only needs to reload files that were hashed (114k entries)
   - **Status**: Partially addressed with incremental reload, but could be further optimized

### Missing Features
1. **File Logging**: Currently console-only logging, file logging mentioned as "Nice to Have" in README
2. **Parallel Hashing**: Not yet implemented despite documented 8-16x speedup opportunity
3. **Configuration Validation**: Configuration validation mentioned as "Nice to Have" priority

### Technical Debt
- **Test Coverage**: Integration tests for full pipeline (Stages 1-2-3A-3B-4) mentioned as priority but not yet complete
- **Large Dataset Testing**: Performance testing with 500k+ files mentioned as ongoing priority

## Recent changes or areas of concern

### Recent Completions (November 2025)
- **Stage 3B**: Cross-folder deduplication completed with cache reuse optimization (50% performance improvement)
- **Stage 4**: File relocation completed with automatic classification and input cleanup
- **Cache Optimizations**: Incremental cache reload and batch query optimizations implemented
- **All Stages Complete**: Stages 1, 2, 3A, 3B, and 4 are all production-ready

### Areas of Concern
1. **Performance Optimization Opportunities**: Sequential hashing is the biggest remaining bottleneck
2. **Progress Reporting**: User experience could be improved with better progress feedback during long operations
3. **Testing**: Full integration test coverage would increase confidence in production readiness

## Coding standards your team follows

- **PEP 8**: Python style guide compliance mentioned in contributing guide (`docs/onboarding.md`)
- **Python Version**: Python 3.8+ required (supports 3.8 through 3.12)
- **Type Hints**: Code uses type hints for better IDE support and documentation
- **Modular Architecture**: Stage-based modular design with clear separation of concerns
- **Documentation**: Comprehensive documentation expected (1,639+ lines of requirements docs)
- **Error Handling**: Graceful error handling pattern (skip problem files, log, continue)

## Any third-party integrations

### Direct Dependencies
- **unidecode** (`>=1.3.6`): ASCII transliteration for international characters (Stage 1)
- **pyyaml** (`>=6.0`): YAML configuration file parsing (Stage 2)
- **xxhash** (`>=3.0.0`): Ultra-fast non-cryptographic hashing at 10-20 GB/s (Stage 3)

### Standard Library Usage
- **sqlite3**: SQLite database for persistent hash cache
- **pathlib**: Modern path handling (Python 3.4+)
- **argparse**: Command-line argument parsing
- **shutil**: File operations (move, copy)
- **os**: System operations (permissions, symlinks)

### Development Dependencies (Optional)
- **pytest** (`>=7.4.0`): Testing framework (commented in requirements.txt)
- **pytest-cov** (`>=4.1.0`): Test coverage reports (commented in requirements.txt)

### Integration Points
- **Filesystem**: Direct filesystem operations (no FUSE-specific code, but handles FUSE errors gracefully)
- **SQLite Database**: Persistent cache stored in `.file_organizer_cache/` directory
- **YAML Configuration**: Optional `.file_organizer.yaml` file in execution directory

# Non-Goals for This Review

- **Don't reformat code unless there are real issues**: Code formatting is acceptable as-is, focus on functional issues
- **Don't rename symbols unnecessarily**: Variable/function/class names are clear and follow conventions
- **Avoid bikeshedding on style preferences**: Don't debate minor style choices, focus on substantive code quality, security, and performance issues




