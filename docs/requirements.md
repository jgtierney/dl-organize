# File Organization Application - Requirements Overview

## Introduction

This document provides a high-level overview of the File Organization Application, a Linux-based tool designed to systematically organize and clean up large collections of downloaded files and folders. The application focuses on filename sanitization, folder structure optimization, and robust handling of edge cases.

### Scale & System Requirements

- **Target Scale**: 100,000 - 500,000 files across 1,000 - 10,000 directories
- **Recommended System**: 32GB RAM, multi-core processor (optimized for 16+ cores)
- **Minimum System**: 8GB RAM, dual-core processor
- **Expected Processing Time**: 
  - 100k files: 5-10 minutes
  - 500k files: 25-50 minutes (on recommended hardware)

## Purpose

The File Organizer addresses common problems with downloaded file collections:
- Inconsistent naming conventions (spaces, special characters, mixed case)
- Non-ASCII characters that cause compatibility issues
- Cluttered folder hierarchies with unnecessary nesting
- Empty folders and single-child folder chains

## Application Architecture

### Technical Specifications

- **Language**: Python 3.8+
- **Platform**: Linux
- **Dependencies**: See `requirements.txt`
- **Interface**: Command-line interface (CLI)
- **Project Structure**:
  ```
  file-organizer/
  ├── src/file_organizer/    # Main application code
  ├── tests/                  # Test files
  ├── docs/                   # Documentation (this directory)
  ├── config/                 # Configuration files
  ├── requirements.txt        # Python dependencies
  └── README.md              # Project overview
  ```

### Command-Line Interface

```bash
file-organizer -if /path/to/directory [-of /path/to/output]
  --execute    # Actually perform operations (default is dry-run preview)
  --verbose    # Detailed logging (future enhancement)
```

**Default Behavior**: Dry-run mode (preview only) unless `--execute` flag is provided.

## Development Stages

The application is being developed in multiple stages, each with specific goals and requirements:

### Stage 1: Filename Detoxification
**Status**: Requirements Complete  
**Document**: [`stage1_requirements.md`](./stage1_requirements.md)

Focuses on cleaning and standardizing individual file and folder names:
- ASCII-only filenames with transliteration
- Lowercase conversion
- Special character removal/replacement
- Collision handling
- Extension normalization

### Stage 2: Folder Structure Optimization
**Status**: Requirements Complete  
**Document**: [`stage2_requirements.md`](./stage2_requirements.md)

Optimizes directory hierarchy:
- Empty folder removal
- Folder chain flattening (< 5 items threshold)
- Folder deduplication
- Structure simplification
- Configuration file support
- Target directory validation
- Processing time estimation

### Stage 3: File Relocation
**Status**: Planning Phase  
**Document**: To be created

Will handle moving organized files from input to output directory with classification and grouping logic.

## Design Philosophy

1. **Safety First**: Dry-run default mode, system directory blocking, comprehensive logging, graceful error handling
2. **Transparency**: Clear progress feedback, processing time estimates, detailed operation logs
3. **Robustness**: Handle edge cases (symlinks, hidden files, long names, collisions, FUSE filesystems)
4. **Performance**: Efficient in-place operations, optimized for large file collections (100k-500k files)
5. **Scalability**: Adaptive progress reporting, memory-efficient with available resources (32GB RAM), optional multi-core processing
6. **Unix Philosophy**: Do one thing well, composable stages
7. **User-Friendly**: Optional configuration file, sensible defaults, clear confirmations

## Configuration

The application supports an optional YAML configuration file at `~/.file_organizer.yaml`:

```yaml
# Optional configuration file
default_mode: dry-run          # or 'execute'
flatten_threshold: 5           # number of items for folder flattening
preserve_timestamps: true      # preserve original file timestamps
log_location: cwd              # 'cwd' or absolute path

# Large scale performance tuning
progress_update_interval: auto  # auto-adapt based on file count
max_errors_logged: 1000        # prevent log explosion
scan_progress_interval: 10000  # files between scan updates
```

Configuration precedence: CLI flags > Config file > Built-in defaults

**Note**: For operations on 100k+ files, adaptive settings ensure manageable console output and log file sizes while maintaining useful progress feedback.

## Documentation Index

This project has comprehensive documentation organized for different audiences and purposes.

### 📖 For New Contributors
**Start here** → [Onboarding Guide](./onboarding.md) - Complete navigation and reading guide

### 📋 Core Documentation

#### Overview & Planning
- **[README.md](../README.md)** - Project overview, quick start, current status
- **[requirements.md](./requirements.md)** - This file (high-level requirements)
- **[project-phases.md](./project-phases.md)** - Complete roadmap, all stages, timeline

#### Detailed Specifications (Implementation-Ready)
- **[stage1_requirements.md](./stage1_requirements.md)** - Filename Detoxification (505 lines)
  - Sanitization rules, performance targets, examples
  - **Status**: ✅ Complete, ready for implementation
  
- **[stage2_requirements.md](./stage2_requirements.md)** - Folder Optimization (580 lines)
  - Flattening logic, configuration, validation
  - **Status**: ✅ Complete, ready for implementation

#### Context & Rationale
- **[design_decisions.md](./design_decisions.md)** - All 29 design decisions with full rationale
  - Why each decision was made
  - Alternatives considered
  - Performance implications

- **[agent-sessions.md](./agent-sessions.md)** - Development history
  - Chronological work sessions
  - Q&A that led to decisions
  - Git commit references

### 🎯 Quick Navigation

**"I want to understand..."**
- The project goals → [README.md](../README.md)
- What each stage does → [project-phases.md](./project-phases.md)
- Why decisions were made → [design_decisions.md](./design_decisions.md)
- Where to start → [onboarding.md](./onboarding.md)

**"I want to implement..."**
- Stage 1 (filenames) → [stage1_requirements.md](./stage1_requirements.md)
- Stage 2 (folders) → [stage2_requirements.md](./stage2_requirements.md)
- Tests → See "Test Requirements" sections in stage docs

**"I'm an AI agent continuing work..."**
- Previous sessions → [agent-sessions.md](./agent-sessions.md)
- Current status → [project-phases.md](./project-phases.md)
- All decisions → [design_decisions.md](./design_decisions.md)

### 📊 Documentation Statistics
- **Total pages**: 7 core documents
- **Total lines**: 2,500+ lines of specifications
- **Design decisions**: 29 documented with rationale
- **Agent sessions**: 4 recorded
- **Requirements coverage**: 100% for Stages 1-2

---

## Quick Reference

For detailed design decisions and rationale, see [`design_decisions.md`](./design_decisions.md).

For stage-specific requirements:
- **Stage 1**: [`stage1_requirements.md`](./stage1_requirements.md)
- **Stage 2**: [`stage2_requirements.md`](./stage2_requirements.md)

## Glossary

- **Detoxification**: Process of sanitizing filenames to remove problematic characters
- **Flattening**: Removing unnecessary intermediate folders in a directory chain
- **Collision**: When two different files would have the same name after sanitization
- **Dry-run**: Preview mode that shows what would change without modifying files
- **Transliteration**: Converting non-ASCII characters to ASCII equivalents (e.g., é → e)

## Notes

- Additional stages may be added iteratively as needs arise
- Each stage can be run independently or as part of a pipeline
- The application prioritizes data safety and provides clear feedback at every step
