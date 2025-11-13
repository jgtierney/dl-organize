# File Organizer

A powerful Python application for systematically organizing and cleaning up large collections of downloaded files. Designed to handle 100,000-500,000 files across thousands of directories with comprehensive filename sanitization, folder structure optimization, and duplicate detection.

## 🎯 Project Status

**Current Phase**: Stages 1-2-3 Complete (3A & 3B), Stage 4 Planning
**Last Updated**: November 13, 2025

| Stage | Name | Status | Documentation |
|-------|------|--------|---------------|
| 1 | Filename Detoxification | ✅ **COMPLETE** - Production Ready | [Details](docs/stage1_requirements.md) |
| 2 | Folder Structure Optimization | ✅ **COMPLETE** - Production Ready | [Details](docs/stage2_requirements.md) |
| 3A | Internal Duplicate Detection | ✅ **COMPLETE** - Production Ready | [Details](docs/requirements/stage3_requirements.md) |
| 3B | Cross-Folder Deduplication | ✅ **COMPLETE** - Production Ready | [Plan](docs/stage3b_implementation_plan.md) |
| 4 | File Relocation | 📋 Planning Phase | [Roadmap](docs/project-phases.md) |

### 🎉 Recent Achievements
- ✅ **Stage 1**: Tested on **110,000+ files** with 100% success rate at **25,000-30,000 files/second**
- ✅ **Stage 2**: Empty folder removal, iterative flattening, full CLI integration
- ✅ **Stage 3A**: Metadata-first optimization (10x speedup), xxHash integration, SQLite cache with 100% hit rate on second run
- ✅ **Stage 3B**: Cross-folder deduplication with full resolution policy, 50% performance improvement via cache reuse, comprehensive testing

## 🚀 What It Does

The File Organizer processes directories through multiple stages:

### Stage 1: Filename Detoxification
- Converts all filenames to **lowercase ASCII**
- Replaces spaces and special characters with **underscores**
- Transliterates international characters (café → cafe)
- Removes hidden files (.DS_Store, etc.)
- Handles naming collisions with date stamps
- **Performance**: 100k files in 5-10 minutes

### Stage 2: Folder Structure Optimization
- Removes empty folders recursively
- Flattens unnecessary folder nesting
- Applies threshold-based optimization (< 5 items)
- Sanitizes folder names
- **Performance**: 10k folders in ~5 minutes

### Stage 3A: Internal Duplicate Detection
- **Metadata-first optimization**: Only hashes files with size collisions (10x speedup)
- **xxHash integration**: Ultra-fast hashing at 10-20 GB/s
- **SQLite cache**: Persistent cache with 100% hit rate on subsequent runs
- **Three-tier resolution policy**:
  - Priority 1: "keep" keyword (with ancestor priority)
  - Priority 2: Path depth (deeper = better organized)
  - Priority 3: Newest mtime (most recent wins)
- **Performance**: First run ~60 min for 2TB/100k files, subsequent runs ~5 min (cache hits)

### Stage 3B: Cross-Folder Deduplication
- Compares input folder against output folder for duplicates
- Reuses input cache from Stage 3A (no re-scanning required)
- Applies same three-tier resolution policy (keep/depth/mtime)
- Can delete from either folder based on resolution policy
- **50% performance improvement** over scanning both folders
- **Performance**: Instant cache load + output scan only

### Stage 4: File Relocation (Planned)
- Moves organized files from input to output folder
- Validates disk space availability
- Optional file classification/grouping

## 💻 System Requirements

### Recommended
- **OS**: Ubuntu Linux (22.04+) or similar
- **RAM**: 32GB
- **CPU**: 16+ cores (single-threaded initially, multi-core optimization planned)
- **Storage**: Fast SSD recommended

### Minimum
- **OS**: Any Linux distribution
- **RAM**: 8GB
- **CPU**: Dual-core
- **Storage**: Any (performance will vary)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/jgtierney/dl-organize.git
cd dl-organize
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Required dependencies:**
- `unidecode>=1.3.6` - ASCII transliteration (Stage 1)
- `pyyaml>=6.0` - YAML configuration (Stage 2)
- `xxhash>=3.0.0` - Ultra-fast hashing (Stage 3)

## 🎮 Usage

### Basic Usage (Dry-Run)
Preview changes without modifying files:
```bash
python -m src.file_organizer -if /path/to/messy/downloads
```

### Execute All Stages
Run the complete pipeline (Stages 1-2-3A):
```bash
python -m src.file_organizer -if /path/to/messy/downloads --execute
```

With output folder (runs Stages 1-2-3A-3B):
```bash
python -m src.file_organizer -if /path/to/input -of /path/to/output --execute
```

### Run Specific Stages
```bash
# Stage 1 only (filename cleaning)
python -m src.file_organizer -if /path/to/directory --stage 1 --execute

# Stage 2 only (folder optimization)
python -m src.file_organizer -if /path/to/directory --stage 2 --execute

# Stage 3A only (duplicate detection)
python -m src.file_organizer -if /path/to/directory --stage 3a --execute

# Stage 3B (cross-folder - requires output folder)
python -m src.file_organizer -if /input -of /output --stage 3b --execute
```

### Stage 3 Options
```bash
# Include images in duplicate detection (default: skipped)
python -m src.file_organizer -if /path --stage 3a --no-skip-images --execute

# Custom minimum file size (default: 10KB)
python -m src.file_organizer -if /path --stage 3a --min-file-size 1024 --execute
```

## ⚙️ Configuration

Optional configuration file in the **execution directory** at `.file_organizer.yaml`:

```yaml
# Stage 2: Folder Structure Optimization
flatten_threshold: 5  # folders with <= 5 items will be flattened

# Stage 3: Duplicate Detection
duplicate_detection:
  skip_images: true      # skip image files (.jpg, .png, etc.)
  min_file_size: 10240   # minimum file size in bytes (10KB)
```

**Note**: Configuration files are now stored in the execution directory (where you run the command), not in your home directory. This supports per-project configurations.

**Cache location**: `.file_organizer_cache/` in the execution directory (SQLite database for file hashes)

## 📊 Performance

### Stage-Specific Benchmarks

**Stage 1: Filename Detoxification**
- Small dataset (139 files): < 0.1s
- Medium dataset (10k files): 0.34s (~29,500 files/sec)
- Large dataset (95k files): 3.8s (~24,900 files/sec)

**Stage 2: Folder Optimization**
- Empty folder removal: Instant (filesystem speed)
- Folder flattening: ~1-2 passes for typical datasets
- Collision resolution: < 0.1ms per collision

**Stage 3A: Duplicate Detection**
- Metadata-first optimization: 10x faster than traditional
- First run (2TB, 100k files): ~60 minutes (with disk I/O)
- Second run: ~5 minutes (100% cache hits)
- Cache hit rate: 90-98% on subsequent runs
- Space saved: Typically 10-30% of total size

**Stage 3B: Cross-Folder Deduplication**
- 50% faster than scanning both folders (reuses input cache)
- Only scans output folder
- Cache hit rate: 100% for input folder

### Expected Total Time (All Stages)

| Files | Stage 1 | Stage 2 | Stage 3A (first) | Total |
|-------|---------|---------|------------------|-------|
| 10,000 | < 1 min | < 1 min | ~5 min | ~7 min |
| 100,000 | 5-10 min | 2-5 min | ~60 min | ~70 min |
| 500,000 | 25-50 min | 5-10 min | ~5 hours | ~6 hours |

*Actual performance depends on filesystem type (FUSE slower), storage speed, and duplicate ratio.*

## 🏗️ Project Structure

```
dl-organize/
├── src/
│   └── file_organizer/              # Main application package
│       ├── __init__.py              # Package initialization
│       ├── __main__.py              # CLI entry point
│       ├── cli.py                   # Command-line interface
│       ├── config.py                # Configuration management
│       ├── stage1.py                # Stage 1: Filename detoxification
│       ├── filename_cleaner.py      # Sanitization engine
│       ├── stage2.py                # Stage 2: Folder optimization
│       ├── stage3.py                # Stage 3: Orchestrator (3A & 3B)
│       ├── hash_cache.py            # SQLite-based hash cache (526 lines)
│       ├── duplicate_detector.py    # Metadata-first detection (494 lines)
│       └── duplicate_resolver.py    # Resolution policy (350 lines)
├── tools/
│   └── generate_test_data.py        # Test data generator (with Stage 3 scenarios)
├── docs/
│   ├── requirements/
│   │   └── stage3_requirements.md   # Stage 3 specifications
│   ├── stage1_requirements.md       # Stage 1 detailed specs (505 lines)
│   ├── stage2_requirements.md       # Stage 2 detailed specs (580 lines)
│   ├── stage3b_implementation_plan.md  # Stage 3B plan (304 lines)
│   ├── design_decisions.md          # All 29 design decisions
│   ├── project-phases.md            # Roadmap and phase details
│   ├── agent-sessions.md            # AI agent work log
│   └── onboarding.md                # New contributor guide
├── requirements.txt                 # Python dependencies
├── STATUS.md                        # Quick status reference
└── README.md                        # This file
```

## 📚 Documentation

### For New Contributors
- **Start here**: [Onboarding Guide](docs/onboarding.md)
- **Project overview**: [Requirements](docs/requirements.md)
- **Why decisions were made**: [Design Decisions](docs/design_decisions.md)
- **What's next**: [Project Phases](docs/project-phases.md)

### For Developers
- **Stage 1 specs**: [stage1_requirements.md](docs/stage1_requirements.md) - 505 lines
- **Stage 2 specs**: [stage2_requirements.md](docs/stage2_requirements.md) - 580 lines
- **Design rationale**: [design_decisions.md](docs/design_decisions.md) - 29 decisions
- **Agent sessions**: [agent-sessions.md](docs/agent-sessions.md) - Development history

### Total Documentation
- **1,639+ lines** of detailed requirements
- **29 design decisions** with rationale
- **4 agent work sessions** documented
- **100% coverage** of Stages 1-2

## 🔒 Safety Features

- **Dry-run default**: Preview changes before executing
- **System directory protection**: Blocks operations on /, /usr, /etc, etc.
- **Time estimation**: Shows expected duration, prompts for confirmation on large ops
- **Comprehensive logging**: All operations logged with timestamps
- **Graceful error handling**: Skips problem files, continues processing
- **Collision prevention**: Unique naming for conflicting files

## 🤝 Contributing

### Current Focus
**Stage 4 Planning** - File relocation from input to output with disk space validation and optional classification.

### How to Contribute
1. Read the [Onboarding Guide](docs/onboarding.md)
2. Review the [Project Phases](docs/project-phases.md) for roadmap
3. Pick a component to work on
4. Follow Python best practices (PEP 8)
5. Write tests for your code
6. Submit a pull request

### Development Priorities
1. **Stage 4 Planning & Design** (Current Priority)
   - File relocation strategy (input → output)
   - Disk space validation before operations
   - Optional file classification/grouping
   - Integration with completed Stages 1-3

2. **Testing & Optimization** (Ongoing)
   - Full pipeline integration tests (Stages 1-2-3A-3B)
   - Performance testing with large datasets (500k+ files)
   - Edge case coverage and error handling

3. **Production Hardening** (Nice to Have)
   - Logging to file (currently console-only)
   - Configuration validation
   - User documentation and tutorials

## 📋 Design Decisions

Key design decisions (see [design_decisions.md](docs/design_decisions.md) for complete list):

- **Adaptive Progress Reporting**: Frequency scales with file count (prevents spam)
- **In-Memory Processing**: Leverages 32GB RAM for performance
- **ASCII Transliteration**: International characters converted to ASCII equivalents
- **Date Stamp Collisions**: `file_YYYYMMDD_1.txt` format
- **Hidden File Deletion**: All dotfiles removed automatically
- **Symlink Breaking**: Links removed, targets processed if in tree
- **Configuration Optional**: Works out of box, YAML config for customization

## 🐛 Known Issues

None - project is in requirements phase.

## 📄 License

[To be determined]

## 👥 Authors

- Initial requirements and design: John Tierney (jgtierney@gmail.com)
- Requirements documentation: AI-assisted (Claude Sonnet 4.5)

## 🔗 Links

- **GitHub**: https://github.com/jgtierney/dl-organize
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/jgtierney/dl-organize/issues)

---

## Quick Start for Developers

```bash
# 1. Clone and setup
git clone https://github.com/jgtierney/dl-organize.git
cd dl-organize
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Read the documentation
cat docs/onboarding.md

# 3. Review Stage 1 requirements
less docs/stage1_requirements.md

# 4. Start implementing!
# Create your feature branch and begin coding
```

---

**Note**: This project is in active development. Stages 1, 2, and 3 (3A & 3B) are complete and production-ready. Stage 4 (file relocation) is in planning phase. Contributions welcome!
