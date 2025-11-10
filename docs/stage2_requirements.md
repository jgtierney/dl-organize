# Stage 2: Folder Structure Optimization - Requirements

## Overview

Stage 2 focuses on optimizing the directory hierarchy after filenames have been cleaned in Stage 1. This stage removes clutter, flattens unnecessary folder chains, and streamlines the overall folder structure.

**Status**: Requirements Complete

---

## Functional Requirements

### 1. Empty Folder Removal

#### 1.1 Scope
- Recursively identify and remove all empty folders
- A folder is considered empty if it contains:
  - No files
  - No subfolders
  - Only hidden files (which will be deleted in Stage 1)

#### 1.2 Processing Order
- Process bottom-up (deepest folders first)
- After removing files, parent folders may become empty
- Continue until no empty folders remain

#### 1.3 Example
```
BEFORE:
project/
├── src/
├── empty_folder/
├── another_empty/
│   └── nested_empty/
└── has_files/
    └── file.txt

AFTER:
project/
├── src/
└── has_files/
    └── file.txt
```

### 2. Folder Chain Flattening

#### 2.1 Flattening Rule
- Flatten folders that contain fewer than 5 total items (files + subfolders combined)
- Apply iteratively until no more flattening is possible

#### 2.2 Single-Child Folder Chains
- If folder A contains only folder B, and folder B contains files/folders:
  - Move B's contents up to A
  - Remove B

#### 2.3 Small Folder Threshold (< 5 Items)
- If a folder contains fewer than 5 items total:
  - Move all contents up one level to parent folder
  - Remove the now-empty folder
  - Continue process iteratively

#### 2.4 Processing Example
```
BEFORE:
downloads/
└── archive/
    └── old_files/
        ├── file1.txt
        └── file2.txt

STEP 1: archive/ has only 1 item (old_files/) - flatten
downloads/
└── old_files/
    ├── file1.txt
    └── file2.txt

STEP 2: old_files/ has only 2 items - flatten
downloads/
├── file1.txt
└── file2.txt
```

#### 2.5 Complex Example
```
BEFORE:
A/
└── B/                    # B has 1 item (C)
    └── C/                # C has 3 items (2 files + D)
        ├── file1.txt
        ├── file2.txt
        └── D/
            └── file3.txt

ITERATION 1: B has only 1 item (C) - flatten B
A/
└── C/                    # C has 3 items (< 5) - flatten C
    ├── file1.txt
    ├── file2.txt
    └── D/
        └── file3.txt

ITERATION 2: C has 3 items (< 5) - flatten C
A/
├── file1.txt
├── file2.txt
└── D/
    └── file3.txt

ITERATION 3: D has 1 item (< 5) - flatten D
A/
├── file1.txt
├── file2.txt
└── file3.txt
```

### 3. Folder Name Sanitization

#### 3.1 Apply Stage 1 Rules
- All Stage 1 filename sanitization rules apply to folder names
- Lowercase conversion
- Space to underscore replacement
- Non-ASCII transliteration
- Special character removal
- Collision handling

#### 3.2 Folder Collision Resolution
- Same strategy as files: `foldername_YYYYMMDD_N`
- Example:
  - `Documents/` (original)
  - `documents_20231108_1/` (collision)

### 4. Safety and Logging

#### 4.1 Dry-Run Mode
- Preview all folder operations before executing
- Show:
  - Folders to be removed (empty)
  - Folders to be flattened (with destination)
  - Folders to be renamed
  - Total counts

#### 4.2 Logging Requirements
- Log all folder removals
- Log all folder flatten operations
- Log all folder renames
- Summary statistics:
  - Folders removed (empty)
  - Folders flattened
  - Folders renamed
  - Total folders processed

---

## Configuration File Support

### 5.1 Optional Configuration File
- Support optional YAML configuration file: `~/.file_organizer.yaml`
- If file exists, load defaults from it
- CLI flags override config file settings
- If file doesn't exist, use built-in defaults

### 5.2 Configuration File Format
```yaml
# ~/.file_organizer.yaml (optional)
default_mode: dry-run          # or 'execute'
flatten_threshold: 5           # number of items for folder flattening
preserve_timestamps: true      # preserve original file timestamps
log_location: cwd              # 'cwd' or absolute path

# Large scale performance tuning
progress_update_interval: auto  # auto-adapt based on file count, or specify number
max_errors_logged: 1000        # prevent log explosion with detailed errors
scan_progress_interval: 10000  # files between scan progress updates

# Future Phase 4 options (not yet implemented):
# parallel_processing: false   # enable multi-threaded processing (16 cores available)
# worker_threads: 8             # number of parallel workers
```

### 5.3 Configuration Precedence
1. CLI flags (highest priority)
2. Config file settings
3. Built-in defaults (lowest priority)

---

## Safety and Validation

### 6.1 Target Directory Validation

#### 6.1.1 Blocked System Directories
The following directories are **strictly forbidden** and will cause immediate abort:
- `/` (root)
- `/usr`, `/usr/*`
- `/bin`, `/sbin`
- `/etc`
- `/boot`
- `/sys`, `/proc`, `/dev`
- `/lib`, `/lib64`

#### 6.1.2 Allowed Directories
- User home directories: `/home/username/...`
- `/tmp` and subdirectories
- `/opt` and subdirectories
- `/var` (with caution warning)
- `/mnt` and `/media` (mounted filesystems)
- Any directory under user home

#### 6.1.3 Path Validation Process
```python
# Pseudocode for validation
1. Verify path exists
2. Verify path is a directory
3. Convert to absolute path
4. Check against blocked directories list
5. If blocked: abort with error message
6. If allowed: proceed to size estimation
```

### 6.2 Processing Time Estimation and Confirmation

#### 6.2.1 Estimation Logic
Before processing, estimate time based on file/folder count:
- Scan directory tree (quick count)
- Estimate: ~100-200 files per second (conservative)
- Calculate estimated time

#### 6.2.2 Confirmation Threshold
If estimated processing time > 60 seconds (1 minute):
- Display warning with details:
  - Total files found
  - Total folders found
  - Estimated processing time
  - Target directory path
- Prompt for confirmation: `Continue with processing? (yes/no)`
- Require explicit "yes" to proceed
- Any other input: abort gracefully

#### 6.2.3 Example Confirmation Messages

**Medium Scale Example**:
```
WARNING: Large directory detected
  Path: /home/user/Downloads
  Files: 45,230
  Folders: 3,421
  Estimated time: ~4 minutes

This operation will modify file and folder names in place.
Continue with processing? (yes/no):
```

**Large Scale Example**:
```
WARNING: Very large directory detected
  Path: /mnt/downloads
  Files: 347,892
  Folders: 12,483
  Estimated time: ~29 minutes
  
  System resources: 32GB RAM, 16 cores available
  Expected memory usage: ~200-300MB

This operation will modify file and folder names in place.
Continue with processing? (yes/no):
```

### 6.3 Dry-Run Safety
- Dry-run is the **default mode**
- Must use `--execute` flag to actually perform operations
- Dry-run shows preview of all changes
- No confirmation prompts in dry-run (always safe)

---

## Edge Cases and Additional Requirements

### 7.1 File Timestamps

#### 7.1.1 Preservation Strategy
- **Preserve original timestamps** by default
- Use `shutil.move()` which preserves timestamps automatically
- Maintain:
  - Last modified time (mtime)
  - Last access time (atime)
  - Creation time (ctime) where supported

#### 7.1.2 Implementation Note
```python
# shutil.move() preserves timestamps by default
shutil.move(src, dst)  # Timestamps preserved
```

### 7.2 Locked and In-Use Files

#### 7.2.1 Error Handling
- Catch `PermissionError` and `OSError` exceptions
- Log the error with full path
- Skip the problematic file
- Continue processing remaining files
- Include in final error summary

#### 7.2.2 Example Error Log
```
2023-11-08 14:32:15 - ERROR - Permission denied: /path/to/locked_file.txt
2023-11-08 14:32:15 - INFO - Skipping locked file, continuing...
```

### 7.3 Recursion and Directory Depth

#### 7.3.1 No Arbitrary Depth Limit
- No maximum recursion depth enforced
- Python's default recursion limit (~1000) is sufficient
- Real-world directory trees rarely exceed 20-30 levels

#### 7.3.2 Symlink Loop Prevention
- Symlinks are broken/removed in Stage 1
- No risk of infinite loops from symlinks
- Only process actual directories, never follow links

### 7.4 Filesystem Support

#### 7.4.1 Primary Target
- Local ext4 filesystems (Ubuntu standard)
- All operations tested on ext4

#### 7.4.2 FUSE Filesystem Support
- FUSE filesystems are supported
- Examples: sshfs, encfs, s3fs, etc.
- May have slower performance than native filesystems
- Same validation and safety rules apply

#### 7.4.3 Network Filesystems
- NFS and SMB mounts should work
- Performance may be slower
- Network errors handled same as permission errors (skip and log)

### 7.5 Case Sensitivity

#### 7.5.1 Filesystem Handling
- All filenames converted to lowercase in Stage 1
- Case collisions resolved before Stage 2
- Case-insensitive filesystems (rare on Linux) won't cause issues
- Ubuntu default (ext4) is case-sensitive

### 7.6 Disk Space Validation

#### 7.6.1 Stages 1-2 (In-Place Operations)
- **No disk space check required**
- Operations are renames/moves within same filesystem
- Renames don't consume additional space
- No data duplication occurs

#### 7.6.2 Future Stages (Output Folder)
- **Stage 3 and beyond**: Disk space check required
- Before copying to output folder:
  - Calculate total size of input directory
  - Check available space on output filesystem
  - Require at least 110% of input size (10% safety margin)
  - Abort if insufficient space

### 7.7 Large Scale Operations

#### 7.7.1 Scale Specification
- **Target scale**: 100,000 - 500,000 files across 1,000 - 10,000 directories
- **System resources**: 32GB RAM, 16-core processor available
- Folders will be processed efficiently regardless of scale

#### 7.7.2 Iterative Flattening at Scale
When processing thousands of directories:
- Process bottom-up (deepest folders first)
- May require multiple passes for complete flattening
- Each pass processes newly-flattened folders
- Continue until no more flattening possible
- Progress tracking per pass

**Example with 10,000 directories**:
```
Pass 1: Flattened 3,245 folders
Pass 2: Flattened 1,832 folders  
Pass 3: Flattened 421 folders
Pass 4: Flattened 89 folders
Pass 5: No changes - flattening complete
Total: 5,587 folders flattened, 4,413 remaining
```

#### 7.7.3 Memory Efficiency
- With 32GB RAM: Can load full directory structure in memory
- 10k folders ≈ 10-50 MB in memory
- Collision tracking: Dict per directory (scales efficiently)
- No streaming required - full tree processing is optimal

#### 7.7.4 Progress Reporting at Scale
- Adaptive progress updates (consistent with Stage 1)
- For folder operations on large scale:
  - Report every 100 folders for 1,000-10,000 folders
  - Report every 500 folders for 10,000+ folders
- Clear indication of which pass is running (for iterative flattening)

---

## Stage Execution Order

### Option A: Sequential Automatic Execution
**Current Decision**: Run both stages automatically in sequence (from answer 11a)
**Status**: ✓ Confirmed

```bash
file-organizer -if /path/to/directory --execute

# This will:
# 1. Run Stage 1 (filename detoxification)
# 2. Automatically proceed to Stage 2 (folder optimization)
# 3. Generate single combined log
```

### Option B: Separate Stage Execution (Alternative)
Allow running stages independently:
```bash
file-organizer -if /path/to/directory --stage 1 --execute
file-organizer -if /path/to/directory --stage 2 --execute
```

**Status**: Not required for initial implementation

---

## Integration with Stage 1

### Execution Flow
1. **Stage 1**: Filename detoxification
   - Process all files
   - Delete hidden files
   - Handle symlinks
   - Rename files and folders

2. **Stage 2**: Folder optimization (runs automatically after Stage 1)
   - Remove empty folders
   - Flatten folder chains
   - Apply threshold-based flattening (< 5 items)
   - Rename any remaining folders if needed

3. **Report**: Combined summary
   - Stage 1 statistics
   - Stage 2 statistics
   - Total operation time
   - Final file/folder counts

### Shared Components
- Logging system
- Progress reporting
- Error handling
- Dry-run mode
- Path validation

---

## Test Requirements (Preliminary)

### Unit Tests
- Empty folder detection
- Folder chain identification
- Flattening logic (< 5 items threshold)
- Folder collision handling
- Iterative flattening until stable

### Integration Tests
```
test_stage2/
├── empty_folders_test/
│   ├── empty1/
│   ├── empty2/
│   └── has_file/
│       └── file.txt
├── chain_test/
│   └── level1/
│       └── level2/
│           └── level3/
│               └── file.txt
├── threshold_test/
│   └── folder_with_4_items/
│       ├── file1.txt
│       ├── file2.txt
│       ├── file3.txt
│       └── file4.txt
└── complex_test/
    └── mixed_structure/
        ├── small_folder/
        │   └── file.txt
        └── large_folder/
            ├── file1.txt
            ├── file2.txt
            ├── file3.txt
            ├── file4.txt
            └── file5.txt
```

---

## Success Criteria

Stage 2 will be considered complete when:

1. All empty folders are removed
2. All folder chains are flattened appropriately
3. Threshold-based flattening (< 5 items) is applied iteratively
4. Folder names are sanitized per Stage 1 rules
5. Collisions are handled safely
6. Progress is displayed during execution
7. Complete log file is generated
8. Dry-run mode shows accurate preview
9. Integration with Stage 1 is seamless
10. All tests pass
11. Configuration file support is implemented
12. Target directory validation prevents system directory modification
13. Processing time estimation and confirmation works correctly
14. File timestamps are preserved
15. Locked files are handled gracefully

---

## Implementation Priority

### Phase 1: Core Functionality
1. Empty folder removal
2. Folder chain flattening (< 5 items threshold)
3. Folder name sanitization
4. Collision handling

### Phase 2: Safety Features
1. Target directory validation
2. Processing time estimation
3. Confirmation prompts for large directories
4. Enhanced error handling for locked files

### Phase 3: Configuration
1. YAML configuration file support
2. Configuration precedence logic
3. Config file validation

### Phase 4: Large Scale & Performance Optimization
1. Large directory tree optimization (100k-500k files)
2. Memory usage validation and optimization
3. Adaptive progress reporting implementation
4. Log size management for large operations
5. Performance testing with realistic datasets (100k+ files)
6. FUSE filesystem testing
7. Network filesystem handling
8. Timestamp preservation verification
9. **Optional**: Multi-threaded processing (leverage 16 available cores)

---

## Dependencies

### Required Python Libraries
- `pyyaml`: For YAML configuration file parsing
- `pathlib`: For path operations (standard library)
- `shutil`: For file operations (standard library)
- `os`: For filesystem operations (standard library)

### Shared with Stage 1
- Logging system
- Progress reporting
- CLI argument parsing
- Path validation utilities

---

## Next Steps

1. ✅ **Requirements finalized** - All design decisions made
2. **Update design_decisions.md** - Document new decisions
3. **Update requirements.txt** - Add PyYAML dependency
4. **Begin Stage 1 implementation** - Start with core filename detoxification
5. **Implement Stage 2** - After Stage 1 is complete and tested
6. **Integration testing** - Test Stages 1-2 together
7. **Production deployment** - Create installation package

