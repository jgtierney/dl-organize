# Stage 2: Folder Structure Optimization - Requirements

## Overview

Stage 2 focuses on optimizing the directory hierarchy after filenames have been cleaned in Stage 1. This stage removes clutter, flattens unnecessary folder chains, and streamlines the overall folder structure.

**Status**: Requirements In Progress (Open Questions Remain)

---

## Known Requirements

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

## Open Questions and Design Decisions

The following questions need to be answered before Stage 2 can be fully specified:

### Question 22: Input/Output Folder Structure
**Context**: User mentioned a future stage that will relocate files from input to output folder.

**Options**:
- a) For Stages 1-2, operate in-place on a single directory (no `-of` flag yet)
- b) Implement `-if` and `-of` now, making `-of` optional (defaults to in-place if not specified)
- c) Other approach?

**Impact**: Affects CLI interface design and how file operations are handled.

---

### Question 23: Execute Confirmation Flow
**Context**: Default is dry-run mode, but execution flow needs clarification.

**Options**:
- a) After dry-run, show summary and prompt "Execute these changes? (yes/no)"
- b) Require explicit `--execute` flag, no prompts (fully non-interactive)
- c) Dry-run by default, but `--execute` also shows preview and prompts for confirmation

**Current Decision**: Option b (from earlier answer 8b) - require `--execute` flag, no prompts
**Status**: ✓ Confirmed

---

### Question 24: Dependency on External Libraries
**Context**: Stage 1 uses `unidecode` for transliteration. What's the policy for dependencies?

**Options**:
- a) Acceptable - include in requirements.txt
- b) Prefer standard library only where possible
- c) No preference

**Impact**: Affects maintainability, installation complexity, and feature availability.

---

### Question 25: Configuration File Support
**Context**: Should the application support persistent configuration?

**Options**:
- a) Not needed - CLI flags are sufficient
- b) Support optional config file (e.g., `~/.file_organizer.yaml`)
- c) Required config file for safety

**Impact**: Affects user experience and complexity of default settings.

---

### Question 26: Target Directory Validation
**Context**: Safety measures to prevent running on system directories.

**Options**:
- a) Basic validation: path must exist and be a directory
- b) Strict validation: prevent running on system directories (/, /usr, /etc, /home)
- c) Require explicit confirmation for directories containing > X files (what threshold?)

**Impact**: Prevents accidental destruction of critical system files.

---

### Question 27: Filename Truncation Details
**Context**: When filename exceeds 200 characters, how exactly to truncate?

**Options**:
- a) Truncate from the middle of basename: `very_long_name_here.txt` → `very_long_..._here.txt`
- b) Truncate from the end of basename: `very_long_name_here.txt` → `very_long_na.txt`
- c) Smart truncate preserving extension: ensure `.txt` stays intact

**Current Decision**: Option c appears to be the intent (preserve extension)
**Status**: ✓ Clarified in Stage 1 requirements

---

### Question 28: Additional Requirements
**Context**: Are there other requirements, constraints, or edge cases for Stages 1-2?

**Areas to consider**:
- Handling of special Linux directories (e.g., `/proc`, `/sys`)
- Maximum recursion depth limits
- Handling of files currently in use / locked
- Behavior when disk space is low
- Network filesystem considerations
- Case-sensitive vs case-insensitive filesystem handling
- Handling of file timestamps (preserve or update?)
- Support for parallel/concurrent processing
- Memory usage constraints for large directory trees

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

## Success Criteria (Preliminary)

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

---

## Notes for Future Discussion

- Should Stage 2 run automatically after Stage 1, or require a separate invocation?
  - **Current decision**: Run automatically (answer 11a) ✓

- Should there be a maximum recursion depth to prevent issues with deeply nested structures?

- How should the application handle very large directory trees (millions of files)?

- Should folder timestamps be preserved or updated?

- Should there be an option to reverse/undo Stage 2 operations?

---

## Next Steps

1. **Answer remaining open questions** (Questions 22, 24-28)
2. **Finalize Stage 2 requirements** based on answers
3. **Define detailed test scenarios**
4. **Create implementation plan**
5. **Begin development** of Stage 1 (Stage 2 will follow)

