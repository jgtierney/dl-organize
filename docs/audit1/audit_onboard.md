# Repository Structure Analysis: jgtierney/dl-organize

**Analysis Date**: 2025-11-16
**Version**: 0.1.0-dev
**Status**: Production Ready (All 4 stages complete)
**Total LOC**: 5,853 lines (source code)

---

## 1. Project Overview

**File Organizer** is a Python-based CLI application designed to systematically organize and clean up large collections of downloaded files (100,000-500,000+ files). The project follows a **multi-stage pipeline architecture** with 4 distinct processing stages.

### Project Capabilities
- **Stage 1**: Filename detoxification (lowercase ASCII, 25,000-30,000 files/sec)
- **Stage 2**: Folder structure optimization (empty removal, flattening)
- **Stage 3A**: Internal duplicate detection (metadata-first, xxHash, SQLite cache)
- **Stage 3B**: Cross-folder deduplication (50% faster via cache reuse)
- **Stage 4**: File relocation with disk space validation

### Performance Benchmarks
- **Stage 1**: 110,000+ files tested at 25,000-30,000 files/second
- **Stage 3A**: First run ~60 min for 2TB/100k files, subsequent runs ~5 min (100% cache hits)
- **Stage 3B**: 50% performance improvement over scanning both folders
- **Stage 4**: Instant move on same filesystem (inode rename)

---

## 2. Directory Structure

```
dl-organize/
├── src/file_organizer/          # Main application package (5,853 LOC)
│   ├── __main__.py              # CLI entry point (28 LOC)
│   ├── cli.py                   # Command-line interface (458 LOC)
│   ├── config.py                # YAML configuration management (560 LOC)
│   ├── filename_cleaner.py      # ASCII transliteration engine (261 LOC)
│   ├── progress_bar.py          # Adaptive progress reporting (251 LOC)
│   ├── stage1.py                # Filename detoxification (393 LOC)
│   ├── stage2.py                # Folder structure optimization (556 LOC)
│   ├── stage3.py                # Duplicate detection orchestrator (960 LOC)
│   ├── stage4.py                # File relocation (663 LOC)
│   ├── hash_cache.py            # SQLite-based hash cache (684 LOC)
│   ├── duplicate_detector.py    # Metadata-first detection (563 LOC)
│   └── duplicate_resolver.py    # Resolution policy engine (459 LOC)
├── tests/                       # Test suite
│   ├── __init__.py
│   └── test_stage3_optimizations.py
├── docs/                        # Extensive documentation (247KB)
│   ├── requirements.md          # Project overview
│   ├── stage1_requirements.md   # Stage 1 specs (17KB)
│   ├── stage2_requirements.md   # Stage 2 specs (17KB)
│   ├── stage3_requirements.md   # Stage 3 specs (25KB)
│   ├── stage4_implementation_plan.md  # Stage 4 plan (20KB)
│   ├── design_decisions.md      # 29 documented design decisions (22KB)
│   ├── project-phases.md        # Roadmap and phases (13KB)
│   ├── onboarding.md           # Contributor guide (12KB)
│   └── agent-sessions.md       # Development history (16KB)
├── tools/                       # Utilities
│   └── generate_test_data.py   # Test data generator
├── appimage/                    # AppImage packaging
├── AppDir/                      # AppImage directory structure
├── requirements.txt             # Python dependencies
├── setup.py                     # Package configuration
└── .file_organizer.yaml.example # Configuration template (146 LOC)
```

---

## 3. Architecture and Design Patterns

### Multi-Stage Pipeline Architecture

```
┌──────────────────────────────────────────────┐
│  CLI Entry Point (__main__.py)              │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│  Argument Parsing (cli.py)                   │
│  - Parse CLI arguments                       │
│  - Load YAML config (.file_organizer.yaml)  │
│  - Validate paths and options                │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│  Configuration (Config class)                │
│  - Precedence: CLI > YAML > defaults        │
│  - Cache directory setup                     │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│  Stage Orchestration (cli.py:main)          │
│  - Safety checks (system dirs protection)   │
│  - Dry-run vs execute mode                  │
│  - Single stage or full pipeline            │
└───────────────┬──────────────────────────────┘
                │
      ┌─────────┴─────────┬──────────┬──────────┐
      ▼                   ▼          ▼          ▼
┌──────────┐    ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Stage 1  │ -> │ Stage 2  │->│ Stage 3  │->│ Stage 4  │
│ Filename │    │ Folders  │  │Duplicates│  │Relocation│
└──────────┘    └──────────┘  └────┬─────┘  └──────────┘
                                   │
                          ┌────────┴────────┐
                          ▼                 ▼
                    ┌──────────┐      ┌──────────┐
                    │ Stage 3A │      │ Stage 3B │
                    │ Internal │      │  Cross   │
                    └──────────┘      └──────────┘
```

### Key Design Patterns

1. **Processor Pattern**: Each stage is a self-contained processor class
2. **Configuration Precedence**: CLI args > YAML config > built-in defaults
3. **Dry-Run First**: Safe preview mode is default (requires `--execute` flag)
4. **Adaptive Progress**: Frequency scales with file count (prevents spam)
5. **Cache-First**: Persistent SQLite cache for performance optimization
6. **Metadata-First**: Only hash files with size collisions (10x speedup)

### Component Descriptions

#### Core Modules

**`cli.py` (458 LOC)**
- Entry point: `main()` function
- Argument parsing with `argparse`
- Stage orchestration and execution flow
- Safety validations (system directory protection)
- Timing and progress tracking

**`config.py` (560 LOC)**
- Class: `Config`
- YAML configuration loading from `.file_organizer.yaml`
- Precedence handling: CLI > YAML > defaults
- Default values for all stages
- Configuration validation

**`stage1.py` (393 LOC)**
- Class: `Stage1Processor`
- Filename sanitization (lowercase ASCII, underscore replacement)
- Hidden file removal (.DS_Store, etc.)
- Symlink handling (break links, process targets)
- Collision resolution with date stamps
- Statistics tracking

**`stage2.py` (556 LOC)**
- Class: `Stage2Processor`
- Empty folder removal (recursive)
- Folder flattening (threshold-based, default: 5 items)
- Folder name sanitization
- Iterative processing (multiple passes)

**`stage3.py` (960 LOC)**
- Class: `Stage3` (orchestrator)
- Manages Stage 3A (internal duplicates) and 3B (cross-folder)
- Cache initialization and management
- Progress reporting integration
- File verification optional (--verify-files)

**`stage4.py` (663 LOC)**
- Class: `Stage4Processor`
- File relocation from input to output
- Disk space validation (10% safety margin)
- Top-level file handling (auto-move to misc/)
- Input folder cleanup (optional --preserve-input)

**`filename_cleaner.py` (261 LOC)**
- Class: `FilenameCleaner`
- ASCII transliteration (café → cafe)
- Special character replacement
- Lowercase conversion
- Collision detection

**`hash_cache.py` (684 LOC)**
- Class: `HashCache`
- SQLite-based persistent cache
- Batch query optimization (chunks for >999 paths)
- Methods: `save_to_cache()`, `get_files_by_paths()`, `load_files_from_cache()`
- Cache location: `.file_organizer_cache/` in execution directory

**`duplicate_detector.py` (563 LOC)**
- Class: `DuplicateDetector`
- Metadata-first optimization (only hash size collisions)
- xxHash integration (10-20 GB/s hashing speed)
- Image file skipping (optional, default: enabled)
- Minimum file size filtering (default: 10KB)

**`duplicate_resolver.py` (459 LOC)**
- Class: `DuplicateResolver`
- Three-tier resolution policy:
  1. Priority 1: "keep" keyword in path (with ancestor priority)
  2. Priority 2: Path depth (deeper = better organized)
  3. Priority 3: Newest mtime (most recent wins)
- Safe deletion logic
- Statistics tracking

**`progress_bar.py` (251 LOC)**
- Class: `ProgressBar`, `SimpleProgress`
- Adaptive progress reporting
- Scales frequency based on total count
- Console-friendly output

---

## 4. Dependencies and Requirements

### Production Dependencies

```python
# requirements.txt
unidecode>=1.3.6   # ASCII transliteration for international characters (Stage 1)
pyyaml>=6.0        # YAML configuration file parsing (Stage 2+)
xxhash>=3.0.0      # Ultra-fast hashing algorithm (Stage 3, 10-20 GB/s)
```

### Development Dependencies (Optional)

```python
pytest>=7.4.0      # Testing framework
pytest-cov>=4.1.0  # Test coverage reporting
```

### Python Version Support

- **Minimum**: Python 3.8
- **Tested**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Recommended**: Python 3.10+

### System Requirements

**Recommended:**
- OS: Ubuntu Linux 22.04+
- RAM: 32GB (in-memory processing for performance)
- CPU: 16+ cores (single-threaded initially, multi-core planned)
- Storage: Fast SSD

**Minimum:**
- OS: Any Linux distribution
- RAM: 8GB
- CPU: Dual-core
- Storage: Any (performance varies)

---

## 5. Entry Points and Usage

### Installation

```bash
# Clone repository
git clone https://github.com/jgtierney/dl-organize.git
cd dl-organize

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Entry Points

**Primary Entry Point (Module):**
```bash
python -m src.file_organizer -if /path/to/directory [options]
```

**Console Script Entry Point (via setup.py):**
```bash
file-organizer -if /path/to/directory [options]
```

**Code Entry:**
- `src/file_organizer/__main__.py:main()` → calls `cli.main()`
- `src/file_organizer/cli.py:main()` → orchestration function

### CLI Usage Patterns

**Dry-Run Mode (Default):**
```bash
# Preview changes without executing
python -m src.file_organizer -if /path/to/directory
```

**Execute Mode:**
```bash
# Execute all stages (1-2-3A only)
python -m src.file_organizer -if /path/to/directory --execute

# Full pipeline with output folder (1-2-3A-3B-4)
python -m src.file_organizer -if /input -of /output --execute
```

**Stage-Specific Execution:**
```bash
# Stage 1 only (filename cleaning)
python -m src.file_organizer -if /path --stage 1 --execute

# Stage 2 only (folder optimization)
python -m src.file_organizer -if /path --stage 2 --execute

# Stage 3A only (duplicate detection)
python -m src.file_organizer -if /path --stage 3a --execute

# Stage 3B (cross-folder - requires output folder)
python -m src.file_organizer -if /input -of /output --stage 3b --execute

# Stage 4 only (file relocation - requires output folder)
python -m src.file_organizer -if /input -of /output --stage 4 --execute
```

**Stage 3 Options:**
```bash
# Include images in duplicate detection (default: skipped)
python -m src.file_organizer -if /path --stage 3a --no-skip-images --execute

# Custom minimum file size (default: 10KB)
python -m src.file_organizer -if /path --stage 3a --min-file-size 1024 --execute

# Verify files exist before resolving duplicates (slower)
python -m src.file_organizer -if /input -of /output --stage 3b --verify-files --execute
```

**Stage 4 Options:**
```bash
# Preserve input folder after relocation (default: clean input)
python -m src.file_organizer -if /input -of /output --stage 4 --execute --preserve-input
```

### CLI Arguments Reference

**Required:**
- `-if, --input-folder PATH`: Input directory to process

**Optional:**
- `-of, --output-folder PATH`: Output directory (required for Stage 3B/4)
- `--execute`: Execute operations (default is dry-run)
- `--verbose`: Enable verbose logging
- `--stage {1,2,3a,3b,4}`: Run specific stage only
- `--skip-images`: Skip image files in duplicate detection
- `--no-skip-images`: Include image files in duplicate detection
- `--min-file-size BYTES`: Minimum file size for duplicates (default: 10240)
- `--cache-dir PATH`: Cache directory (default: .file_organizer_cache)
- `--verify-files`: Verify file existence before resolution
- `--flatten-threshold N`: Folder flattening threshold (default: 5)
- `--preserve-input`: Keep input files after relocation

---

## 6. Configuration System

### Configuration File Location

**Path**: `.file_organizer.yaml` in execution directory (CWD)

**Precedence**: CLI flags > Config file > Built-in defaults

### Configuration Example

```yaml
# Execution mode
default_mode: dry-run  # Options: 'dry-run' | 'execute'

# Stage 2: Folder optimization
flatten_threshold: 5   # Range: 0-1000

# Stage 3: Duplicate detection
duplicate_detection:
  skip_images: true
  min_file_size: 10240  # 10KB in bytes
  # cache_directory: /path/to/cache  # Optional custom cache location

# File operations
preserve_timestamps: true

# Logging & output
verbose: false
log_location: cwd
max_errors_logged: 1000

# Performance tuning
progress_update_interval: auto  # Options: 'auto' | integer
scan_progress_interval: 10000
```

### Configuration Defaults (from `config.py`)

```python
DEFAULTS = {
    'default_mode': 'dry-run',
    'flatten_threshold': 5,
    'preserve_timestamps': True,
    'log_location': 'cwd',
    'progress_update_interval': 'auto',
    'max_errors_logged': 1000,
    'scan_progress_interval': 10000,
    'duplicate_detection': {
        'skip_images': True,
        'min_file_size': 10240  # 10KB
    },
    'verbose': True
}
```

---

## 7. Testing Infrastructure

### Test Framework
- **Framework**: pytest (commented in requirements.txt)
- **Coverage Tool**: pytest-cov (optional)

### Test Files

**Location**: `/home/user/dl-organize/tests/`

**Files:**
- `__init__.py`: Package initialization
- `test_stage3_optimizations.py`: Stage 3 optimization tests

### Test Coverage

**`test_stage3_optimizations.py` Tests:**

1. **Batch Query Optimization**:
   - `test_get_files_by_paths_empty_list()`: Empty list handling
   - `test_get_files_by_paths_small_list()`: Small list queries (< 999 paths)
   - `test_get_files_by_paths_large_list()`: Large list queries (> 999 paths, SQLite chunking)
   - `test_get_files_by_paths_nonexistent_paths()`: Non-existent path handling

2. **Cache Load Optimization**:
   - Incremental cache loading tests
   - Duplicate load prevention tests
   - Cache reuse validation tests

### Test Utilities

**Test Data Generator**: `tools/generate_test_data.py`
- Generates realistic test datasets
- Creates Stage 3 duplicate scenarios
- Various naming patterns and file structures

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src/file_organizer tests/

# Run specific test file
pytest tests/test_stage3_optimizations.py -v

# Run specific test class
pytest tests/test_stage3_optimizations.py::TestBatchQueryOptimization -v
```

### Additional Test Documentation

- `STAGE2_TEST_RESULTS.md`: Comprehensive Stage 2 test results
- `BUG_FIXES_STAGE2.md`: Stage 2 bug fixes and edge cases
- `test_progress.py`: Standalone progress reporting test script

### Testing Status by Stage

- **Stage 1**: ✅ Production-ready, tested on 110,000+ files
- **Stage 2**: ✅ Production-ready, comprehensive scenarios tested
- **Stage 3A**: ✅ Production-ready, optimizations verified
- **Stage 3B**: ✅ Production-ready, cache reuse validated
- **Stage 4**: ✅ Production-ready, full pipeline integrated

---

## 8. Documentation

### Documentation Size
**Total**: 247KB across 19+ files, 1,639+ lines of detailed requirements

### Key Documentation Files

**Overview & Onboarding:**
- `README.md`: Project overview, quick start, usage guide (380 LOC)
- `docs/onboarding.md`: New contributor guide (12KB)
- `docs/requirements.md`: Project requirements overview

**Stage-Specific Requirements:**
- `docs/stage1_requirements.md`: Stage 1 detailed specs (17KB)
- `docs/stage2_requirements.md`: Stage 2 detailed specs (17KB)
- `docs/stage3_requirements.md`: Stage 3 detailed specs (25KB)
- `docs/stage4_implementation_plan.md`: Stage 4 implementation plan (20KB)

**Implementation Plans:**
- `docs/stage3b_implementation_plan.md`: Stage 3B cross-folder deduplication (9KB)
- `docs/stage3b_resolution_optimization_plan.md`: Resolution optimization (11KB)
- `docs/progress_reporting_implementation_plan.md`: Progress reporting (22KB)

**Analysis & Decisions:**
- `docs/design_decisions.md`: 29 documented design decisions (22KB)
- `docs/stage3_performance_analysis.md`: Performance analysis (18KB)
- `docs/stage3b_bottleneck_analysis.md`: Bottleneck identification (7KB)
- `docs/implemented_optimizations.md`: Optimization summary (6KB)

**Project Management:**
- `docs/project-phases.md`: Roadmap and development phases (13KB)
- `docs/agent-sessions.md`: AI agent development history (16KB)

**Status Documentation:**
- `STATUS.md`: Quick status reference
- `SESSION_SUMMARY.md`: Recent session summaries
- `ONBOARDING_COMPLETE.md`: Onboarding completion status
- `STAGE2_TEST_RESULTS.md`: Stage 2 test results
- `BUG_FIXES_STAGE2.md`: Bug fixes documentation

---

## 9. Key Implementation Details

### Stage 1: Filename Detoxification

**File**: `src/file_organizer/stage1.py`

**Key Features:**
- Lowercase conversion
- ASCII transliteration (via `unidecode`)
- Special character → underscore replacement
- Hidden file deletion (dotfiles)
- Symlink breaking
- Collision resolution with date stamps (`file_YYYYMMDD_N.txt`)

**Algorithm Flow:**
1. Scan directory tree (depth-first)
2. Collect all files and folders
3. Process bottom-up (files first, then folders)
4. Track used names per directory
5. Generate unique names with collision resolution
6. Execute renames or preview (dry-run)

### Stage 2: Folder Optimization

**File**: `src/file_organizer/stage2.py`

**Key Features:**
- Empty folder removal (recursive)
- Folder flattening (threshold-based, default: 5 items)
- Iterative processing (multiple passes until no changes)
- Folder name sanitization

**Algorithm Flow:**
1. Remove all empty folders
2. Identify folders with ≤ threshold items
3. Flatten eligible folders (move contents to parent)
4. Handle collisions with unique naming
5. Repeat until no more flattening occurs

### Stage 3A: Internal Duplicate Detection

**Files**: `src/file_organizer/stage3.py`, `duplicate_detector.py`, `hash_cache.py`

**Key Features:**
- **Metadata-first optimization**: Only hash files with size collisions
- xxHash for ultra-fast hashing (10-20 GB/s)
- SQLite persistent cache (`.file_organizer_cache/`)
- Image skipping (optional, default: enabled)
- Minimum file size filtering (default: 10KB)

**Algorithm Flow:**
1. Load cache from previous runs
2. Scan directory for file metadata (path, size, mtime)
3. Group files by size
4. Only hash files in size collision groups
5. Identify duplicates by hash
6. Apply resolution policy (keep/depth/mtime)
7. Delete duplicates or preview

**Optimization**: First run hashes all files, subsequent runs use cache (~5 min for 100k files)

### Stage 3B: Cross-Folder Deduplication

**Files**: `src/file_organizer/stage3.py`

**Key Features:**
- Compares input folder vs output folder
- **Reuses input cache from Stage 3A** (50% faster)
- Only scans output folder (incremental)
- Same resolution policy as Stage 3A

**Algorithm Flow:**
1. Load input cache (from Stage 3A, instant)
2. Scan output folder and build cache
3. Compare hashes between input and output
4. Apply resolution policy (can delete from either folder)
5. Execute deletions or preview

### Stage 4: File Relocation

**File**: `src/file_organizer/stage4.py`

**Key Features:**
- Move files from input to output
- Top-level files → `output/misc/`
- Top-level folders → `output/folder_name/`
- Disk space validation (10% safety margin)
- Input cleanup (optional --preserve-input)

**Algorithm Flow:**
1. Validate disk space (size + 10% < available)
2. Identify top-level files and folders
3. Move top-level files to `output/misc/`
4. Move top-level folders to `output/`
5. Clean input folder (unless --preserve-input)
6. Preserve empty input root

### Three-Tier Resolution Policy

**Implementation**: `src/file_organizer/duplicate_resolver.py`

**Priority Order:**

1. **Priority 1: "keep" keyword in path**
   - Searches for "keep" in path components
   - Ancestor priority: `/keep/a/b/file.txt` beats `/a/keep/b/file.txt`
   - Example: `/important/keep/file.txt` wins over `/backup/file.txt`

2. **Priority 2: Path depth (deeper = better)**
   - Assumes deeper paths are more organized
   - Example: `/photos/2024/vacation/img.jpg` beats `/downloads/img.jpg`

3. **Priority 3: Newest mtime (most recent)**
   - Preserves the most recently modified file
   - Example: file modified 2024-01-15 beats file modified 2023-06-01

**Tie-breaking**: If all criteria equal, preserves first file encountered (deterministic)

---

## 10. Safety Features

1. **Dry-Run Default**: All operations preview by default, require `--execute` flag
2. **System Directory Protection**: Blocks operations on /, /usr, /etc, /bin, etc.
3. **Time Estimation**: Shows expected duration for large operations
4. **Comprehensive Logging**: All operations logged with timestamps
5. **Graceful Error Handling**: Skips problem files, continues processing
6. **Collision Prevention**: Unique naming with date stamps
7. **Disk Space Validation**: Requires available space + 10% safety margin (Stage 4)
8. **File Verification**: Optional --verify-files flag to detect moved/deleted files

---

## 11. Performance Characteristics

### Stage-Specific Performance

**Stage 1: Filename Detoxification**
- Small dataset (139 files): < 0.1s
- Medium dataset (10k files): 0.34s (~29,500 files/sec)
- Large dataset (95k files): 3.8s (~24,900 files/sec)
- **Bottleneck**: Filesystem I/O for renames

**Stage 2: Folder Optimization**
- Empty folder removal: Instant (filesystem speed)
- Folder flattening: ~1-2 passes for typical datasets
- Collision resolution: < 0.1ms per collision
- **Bottleneck**: Filesystem metadata operations

**Stage 3A: Duplicate Detection**
- Metadata-first optimization: 10x faster than traditional
- First run (2TB, 100k files): ~60 minutes (with disk I/O)
- Second run: ~5 minutes (100% cache hits)
- Cache hit rate: 90-98% on subsequent runs
- **Bottleneck**: Disk I/O for hashing (mitigated by xxHash 10-20 GB/s)

**Stage 3B: Cross-Folder Deduplication**
- 50% faster than scanning both folders (reuses input cache)
- Only scans output folder
- Cache hit rate: 100% for input folder
- **Bottleneck**: Output folder scanning

**Stage 4: File Relocation**
- Same filesystem: Instant (inode rename, no data copy)
- Cross-filesystem: Copy speed dependent on storage
- Disk space check: < 0.1s
- **Bottleneck**: Cross-filesystem moves (requires data copy)

### Expected Total Time (Full Pipeline)

| Files   | Stage 1   | Stage 2   | Stage 3A (first) | Total      |
|---------|-----------|-----------|------------------|------------|
| 10,000  | < 1 min   | < 1 min   | ~5 min           | ~7 min     |
| 100,000 | 5-10 min  | 2-5 min   | ~60 min          | ~70 min    |
| 500,000 | 25-50 min | 5-10 min  | ~5 hours         | ~6 hours   |

*Note: Actual performance depends on filesystem type (FUSE slower), storage speed, and duplicate ratio.*

---

## 12. Development Status

### Completed Stages

- ✅ **Stage 1**: Filename Detoxification - Production Ready
- ✅ **Stage 2**: Folder Structure Optimization - Production Ready
- ✅ **Stage 3A**: Internal Duplicate Detection - Production Ready
- ✅ **Stage 3B**: Cross-Folder Deduplication - Production Ready
- ✅ **Stage 4**: File Relocation - Production Ready

### Recent Achievements

- ✅ Stage 1: Tested on 110,000+ files at 25,000-30,000 files/sec
- ✅ Stage 2: Empty folder removal, iterative flattening, full CLI integration
- ✅ Stage 3A: Metadata-first optimization (10x speedup), xxHash integration, SQLite cache
- ✅ Stage 3B: Cross-folder deduplication, 50% performance improvement
- ✅ Stage 4: File relocation, disk space validation, input cleanup

### Package Information

**Name**: file-organizer
**Version**: 0.1.0-dev
**Author**: John Tierney (jgtierney@gmail.com)
**Repository**: https://github.com/jgtierney/dl-organize
**License**: MIT License (declared in setup.py)

---

## 13. Critical File Paths (Quick Reference)

### Source Code
- Entry point: `/home/user/dl-organize/src/file_organizer/__main__.py`
- CLI orchestration: `/home/user/dl-organize/src/file_organizer/cli.py`
- Configuration: `/home/user/dl-organize/src/file_organizer/config.py`
- Stage 1: `/home/user/dl-organize/src/file_organizer/stage1.py`
- Stage 2: `/home/user/dl-organize/src/file_organizer/stage2.py`
- Stage 3: `/home/user/dl-organize/src/file_organizer/stage3.py`
- Stage 4: `/home/user/dl-organize/src/file_organizer/stage4.py`
- Hash cache: `/home/user/dl-organize/src/file_organizer/hash_cache.py`
- Duplicate detection: `/home/user/dl-organize/src/file_organizer/duplicate_detector.py`
- Resolution policy: `/home/user/dl-organize/src/file_organizer/duplicate_resolver.py`

### Configuration & Setup
- Dependencies: `/home/user/dl-organize/requirements.txt`
- Setup script: `/home/user/dl-organize/setup.py`
- Config example: `/home/user/dl-organize/.file_organizer.yaml.example`
- Active config: `/home/user/dl-organize/.file_organizer.yaml`

### Documentation
- Main README: `/home/user/dl-organize/README.md`
- Onboarding: `/home/user/dl-organize/docs/onboarding.md`
- Stage 1 specs: `/home/user/dl-organize/docs/stage1_requirements.md`
- Stage 2 specs: `/home/user/dl-organize/docs/stage2_requirements.md`
- Stage 3 specs: `/home/user/dl-organize/docs/stage3_requirements.md`
- Stage 4 plan: `/home/user/dl-organize/docs/stage4_implementation_plan.md`
- Design decisions: `/home/user/dl-organize/docs/design_decisions.md`

### Tests
- Test directory: `/home/user/dl-organize/tests/`
- Stage 3 tests: `/home/user/dl-organize/tests/test_stage3_optimizations.py`
- Test data generator: `/home/user/dl-organize/tools/generate_test_data.py`

---

## 14. Common Development Tasks

### Running the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Dry-run preview
python -m src.file_organizer -if /path/to/directory

# Execute full pipeline
python -m src.file_organizer -if /input -of /output --execute
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=src/file_organizer tests/
```

### Building AppImage

```bash
# Build AppImage (Linux)
./build-appimage.sh

# Build and deploy
./build-and-deploy-appimage.sh
```

### Code Analysis

```bash
# Count lines of code
wc -l src/file_organizer/*.py

# Find specific functionality
grep -r "class.*Processor" src/

# Search for configuration keys
grep -r "get_flatten_threshold" src/
```

---

## 15. Known Limitations and Future Work

### Current Limitations
- Single-threaded processing (multi-core optimization planned)
- Linux-focused (Windows support untested)
- No GUI (CLI only)
- No automatic backup before operations

### Planned Features (from docs)
- Parallel processing (multi-core utilization)
- File classification/grouping
- Automatic backup option
- Windows support testing
- File logging (currently console-only)
- Configuration validation

### Performance Opportunities
- Multi-threaded hashing in Stage 3
- Parallel file operations in Stage 1/2
- Optimized SQLite cache queries
- Memory-mapped file reading for large files

---

**End of Audit Document**
