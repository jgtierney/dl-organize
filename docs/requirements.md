# File Organization Application - Requirements Overview

## Introduction

This document provides a high-level overview of the File Organization Application, a Linux-based tool designed to systematically organize and clean up large collections of downloaded files and folders. The application focuses on filename sanitization, folder structure optimization, and robust handling of edge cases.

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
**Status**: Requirements In Progress  
**Document**: [`stage2_requirements.md`](./stage2_requirements.md)

Optimizes directory hierarchy:
- Empty folder removal
- Folder chain flattening (< 5 items threshold)
- Folder deduplication
- Structure simplification

### Stage 3: File Relocation
**Status**: Planning Phase  
**Document**: To be created

Will handle moving organized files from input to output directory with classification and grouping logic.

## Design Philosophy

1. **Safety First**: Dry-run default mode, comprehensive logging, graceful error handling
2. **Transparency**: Clear progress feedback, detailed operation logs
3. **Robustness**: Handle edge cases (symlinks, hidden files, long names, collisions)
4. **Performance**: Efficient processing of large file collections
5. **Unix Philosophy**: Do one thing well, composable stages

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
