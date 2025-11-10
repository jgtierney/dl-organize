# File Organizer

A powerful Python application for systematically organizing and cleaning up large collections of downloaded files. Designed to handle 100,000-500,000 files across thousands of directories with comprehensive filename sanitization, folder structure optimization, and duplicate detection.

## 🎯 Project Status

**Current Phase**: Stage 1 Complete, Stage 2 Development Starting  
**Last Updated**: November 10, 2025

| Stage | Name | Status | Documentation |
|-------|------|--------|---------------|
| 1 | Filename Detoxification | ✅ **COMPLETE** - Production Ready | [Details](docs/stage1_requirements.md) |
| 2 | Folder Structure Optimization | ✅ **COMPLETE** - Production Ready | [Details](docs/stage2_requirements.md) |
| 3 | Duplicate Detection & Resolution | 📋 Requirements Complete - Ready for Dev | [Details](docs/stage3_requirements.md) |
| 4 | File Relocation | 📋 Planning Phase | [Roadmap](docs/project-phases.md) |

### 🎉 Stage 1 Achievement
- ✅ Tested on **110,000+ files** with 100% success rate
- ✅ Performance: **25,000-30,000 files/second** (50-150x faster than target!)
- ✅ Zero errors across all test datasets
- ✅ Ready for real-world deployment

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

### Stage 3: Duplicate Detection & Resolution
- **Hash-based duplicate identification** (SHA-256, SHA-1, MD5, BLAKE2b)
- **Configurable resolution policies** (keep newest, largest, oldest, first, or manual)
- **Persistent hash caching** for fast subsequent runs
- **Parallel hashing** support (leverage multi-core CPUs)
- **Size-based pre-filtering** (massive performance boost)
- **Memory efficient**: < 500MB for 500k files
- **Performance**: 100GB in < 5 minutes (SSD)

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

## 🎮 Usage

### Basic Usage (Dry-Run)
Preview changes without modifying files:
```bash
file-organizer -if /path/to/messy/downloads
```

### Execute Changes
Actually perform the operations:
```bash
file-organizer -if /path/to/messy/downloads --execute
```

### With Output Folder (Future - Stage 3+)
```bash
file-organizer -if /path/to/input -of /path/to/output --execute
```

## ⚙️ Configuration

Optional configuration file at `~/.file_organizer.yaml`:

```yaml
# Operation mode
default_mode: dry-run  # or 'execute'

# Folder optimization
flatten_threshold: 5  # folders with < 5 items will be flattened

# File handling
preserve_timestamps: true

# Performance tuning (for large operations)
progress_update_interval: auto  # adaptive based on file count
max_errors_logged: 1000
scan_progress_interval: 10000
```

## 📊 Performance

Expected performance on recommended hardware (32GB RAM, 16 cores):

| Files | Stage 1 | Stage 2 | Total |
|-------|---------|---------|-------|
| 10,000 | < 1 min | < 1 min | ~2 min |
| 100,000 | 5-10 min | 2-5 min | 10-15 min |
| 500,000 | 25-50 min | 5-10 min | 30-60 min |

*Actual performance depends on filesystem type (FUSE slower), storage speed, and operation complexity.*

## 🏗️ Project Structure

```
file-organizer/
├── src/
│   └── file_organizer/        # Main application code (to be implemented)
│       ├── __init__.py
│       ├── __main__.py        # CLI entry point
│       ├── stage1.py          # Filename detoxification
│       ├── stage2.py          # Folder optimization
│       ├── filename_cleaner.py
│       ├── utils.py
│       └── logger.py
├── tests/                      # Test files (to be implemented)
├── docs/                       # Comprehensive documentation
│   ├── requirements.md         # Project overview
│   ├── stage1_requirements.md  # Stage 1 detailed specs (505 lines)
│   ├── stage2_requirements.md  # Stage 2 detailed specs (580 lines)
│   ├── design_decisions.md     # All 29 design decisions
│   ├── project-phases.md       # Roadmap and phase details
│   ├── agent-sessions.md       # AI agent work log
│   └── onboarding.md           # New contributor guide
├── config/                     # Configuration files
├── requirements.txt            # Python dependencies
└── README.md                   # This file
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
- **Stage 3 specs**: [stage3_requirements.md](docs/stage3_requirements.md) - 861 lines
- **Design rationale**: [design_decisions.md](docs/design_decisions.md) - 29 decisions
- **Agent sessions**: [agent-sessions.md](docs/agent-sessions.md) - Development history

### Total Documentation
- **2,500+ lines** of detailed requirements
- **29 design decisions** with rationale
- **Multiple agent work sessions** documented
- **100% coverage** of Stages 1-3

## 🔒 Safety Features

- **Dry-run default**: Preview changes before executing
- **System directory protection**: Blocks operations on /, /usr, /etc, etc.
- **Time estimation**: Shows expected duration, prompts for confirmation on large ops
- **Comprehensive logging**: All operations logged with timestamps
- **Graceful error handling**: Skips problem files, continues processing
- **Collision prevention**: Unique naming for conflicting files

## 🤝 Contributing

### Current Focus
The project is currently in the **requirements phase** with complete specifications for Stages 1-2. Implementation is ready to begin.

### How to Contribute
1. Read the [Onboarding Guide](docs/onboarding.md)
2. Review [Stage 1 Requirements](docs/stage1_requirements.md)
3. Pick a component to implement
4. Follow Python best practices (PEP 8)
5. Write tests for your code
6. Submit a pull request

### Development Priorities
1. **Stage 1 Implementation** (High Priority)
   - Filename sanitization module
   - Collision detection and resolution
   - Progress tracking
   - Logging system

2. **Stage 2 Implementation** (High Priority)
   - Folder structure analysis
   - Iterative flattening
   - Configuration file parsing

3. **Testing** (High Priority)
   - Unit tests for all functions
   - Integration tests for full stages
   - Performance testing with 100k+ files

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

**Note**: This project is currently in the requirements and design phase. All specifications for Stages 1-2 are complete and ready for implementation. Contributions welcome!
