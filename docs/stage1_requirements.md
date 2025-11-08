# Stage 1: Filename Detoxification - Detailed Requirements

## Overview

Stage 1 focuses on systematically cleaning and standardizing all file and folder names within a target directory tree. The goal is to create consistent, ASCII-only, lowercase filenames that are compatible across all systems and avoid common issues with special characters.

---

## Technical Specifications

### Environment
- **Language**: Python 3.8 or higher
- **Platform**: Linux (kernel 6.8+)
- **Required Libraries**:
  - `unidecode`: For non-ASCII character transliteration
  - `pathlib`: For path operations (standard library)
  - `argparse`: For CLI parsing (standard library)
  - `logging`: For operation logging (standard library)
  - `os`, `shutil`: For file operations (standard library)

### Module Structure
```
src/file_organizer/
├── __init__.py
├── __main__.py           # CLI entry point
├── stage1.py             # Stage 1 logic
├── filename_cleaner.py   # Filename sanitization
├── utils.py              # Shared utilities
└── logger.py             # Logging configuration
```

---

## Command-Line Interface

### Basic Syntax
```bash
file-organizer -if /path/to/directory [OPTIONS]
```

### Arguments
- `-if, --input-folder`: **Required**. Path to the directory to process
- `-of, --output-folder`: Optional. Reserved for future stages (not used in Stage 1)

### Flags
- `--execute`: Execute the operations. Without this flag, runs in dry-run mode (preview only)
- `--verbose`: Enable verbose logging (future enhancement - not required for initial implementation)

### Examples
```bash
# Preview changes (dry-run mode - default)
file-organizer -if /home/user/Downloads

# Actually execute the changes
file-organizer -if /home/user/Downloads --execute
```

### Exit Codes
- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Permission denied
- `4`: Target directory not found

---

## Functional Requirements

### 1. Filename Sanitization Rules

Apply the following transformations to all file and folder names:

#### 1.1 Case Conversion
- Convert all characters to lowercase
- Example: `MyFile.TXT` → `myfile.txt`

#### 1.2 Space Replacement
- Replace all spaces with underscores
- Example: `my document.pdf` → `my_document.pdf`

#### 1.3 Non-ASCII Character Transliteration
- Use the `unidecode` library to transliterate non-ASCII characters to ASCII equivalents
- Examples:
  - `café.txt` → `cafe.txt`
  - `über_file.pdf` → `uber_file.pdf`
  - `naïve_approach.doc` → `naive_approach.doc`
  - `resumé.pdf` → `resume.pdf`

#### 1.4 Special Character Removal
- Keep only: alphanumeric characters (a-z, 0-9), underscores (`_`), and periods (`.`)
- Remove all other characters: `@#$%^&*()[]{}|\\;:"'<>,?/!-+=~` etc.
- Examples:
  - `file@name#2023.txt` → `filename2023.txt`
  - `report-(final).docx` → `reportfinal.docx`
  - `data[2023].csv` → `data2023.csv`

#### 1.5 Multiple File Extension Handling
- Replace internal periods (not the final extension separator) with underscores
- Examples:
  - `archive.tar.gz` → `archive_tar.gz`
  - `data.backup.json` → `data_backup.json`
  - `report.v2.final.pdf` → `report_v2_final.pdf`

#### 1.6 Consecutive Special Character Collapsing
- Multiple consecutive underscores should be collapsed to a single underscore
- Example: `file___name.txt` → `file_name.txt`

#### 1.7 Leading and Trailing Character Stripping
- Strip leading and trailing underscores and periods from the base filename
- Do NOT strip the leading period from hidden files (they will be deleted - see section 3.1)
- Examples:
  - `_important_.txt` → `important.txt`
  - `___file.pdf` → `file.pdf`
  - `.trailing.txt.` → `.trailing.txt` (leading dot preserved for now, but file will be deleted)

### 2. Filename Length Constraints

#### 2.1 Maximum Length
- Linux filesystem limit: 255 bytes per filename component
- Application limit: 200 characters for safety margin

#### 2.2 Truncation Strategy
- If sanitized filename exceeds 200 characters:
  1. Truncate the base filename (preserve the extension)
  2. If the full path still exceeds filesystem limits after truncation:
     - Skip the file
     - Log an error with the full path
     - Continue processing other files

#### 2.3 Truncation Example
```
Original: very_long_filename_that_exceeds_the_character_limit_and_needs_truncation.txt (85 chars)
If > 200: very_long_filename_that_exceeds_the_character_limit_and_needs_truncation_more_text_here[...continues...].txt
After:    very_long_filename_that_exceeds_the_character_limit_and_needs_truncation_more_text_here_truncated_at_200_characters_preserving_only_the_last_extension_which_is_txt.txt
```

### 3. Edge Cases and Special Handling

#### 3.1 Hidden Files (Starting with `.`)
- **Delete all hidden files entirely**
- This includes: `.DS_Store`, `.gitignore`, `.cache`, etc.
- Log each deletion
- Hidden folders should also be deleted

#### 3.2 Symbolic Links
- **Break the symbolic link** (delete the link itself)
- **If the link target exists within the directory tree being processed**: process the target file normally
- If the target is outside the tree: log and skip
- Do not follow symlinks to prevent infinite loops
- Log all symlink operations

#### 3.3 Files Without Extensions
- Process normally (no extension added)
- Examples:
  - `README` → `readme`
  - `Makefile` → `makefile`
  - `LICENSE` → `license`

#### 3.4 Empty Filenames
- If sanitization results in an empty filename: skip the file and log an error
- Example: `@#$.txt` would become `.txt` (invalid)

### 4. Collision Resolution

When two or more files would have the same name after sanitization:

#### 4.1 Collision Detection
- Track all target filenames in the current directory
- Detect collisions before applying changes

#### 4.2 Collision Naming Strategy
- Append date stamp and counter: `filename_YYYYMMDD_N.ext`
- Date format: `YYYYMMDD` (e.g., `20231108`)
- Counter: `1`, `2`, `3`, etc.
- Examples:
  - `file.txt` (original)
  - `file_20231108_1.txt` (first collision)
  - `file_20231108_2.txt` (second collision)

#### 4.3 Processing Order
- Process files in alphabetical order by original name
- First file to claim a name keeps it
- Subsequent files get the collision suffix

---

## Non-Functional Requirements

### 1. Performance

#### 1.1 Progress Feedback
- Display a progress bar during processing
- Print status every 10 files: `50/1754 processed`
- Update progress bar continuously

#### 1.2 Expected Performance
- Should handle 10,000+ files efficiently
- No specific speed requirement, but operations should be file I/O bound, not CPU bound

### 2. Error Handling

#### 2.1 File-Level Errors
- If an individual file operation fails:
  - Log the error with full path and reason
  - Continue processing remaining files
  - Include failed files in final summary

#### 2.2 Permission Errors
- If permission denied:
  - Log the error
  - Skip the file
  - Continue processing

#### 2.3 Unexpected Errors
- Catch and log all exceptions
- Provide meaningful error messages
- Include full traceback in log file (but not console output)

### 3. Logging

#### 3.1 Log File Location
- Create log in the **current working directory** (where the command is run)
- Log filename format: `file_organizer_YYYYMMDD_HHMMSS.log`

#### 3.2 Log Content (Minimal Detail Level)
- Operation start time and parameters
- Errors encountered (with file paths)
- Files that were skipped and why
- Summary statistics:
  - Total files scanned
  - Files renamed
  - Files deleted (hidden files)
  - Symlinks processed
  - Files skipped (errors)
  - Collisions resolved
- Operation end time and duration

#### 3.3 Log Format
```
2023-11-08 14:30:22 - INFO - File Organizer Stage 1 started
2023-11-08 14:30:22 - INFO - Input directory: /home/user/Downloads
2023-11-08 14:30:22 - INFO - Mode: DRY-RUN (preview only)
2023-11-08 14:30:23 - INFO - Scanning directory tree...
2023-11-08 14:30:25 - INFO - Found 1754 files and 42 folders
2023-11-08 14:30:25 - INFO - Processing files...
2023-11-08 14:30:26 - ERROR - Permission denied: /path/to/file.txt
2023-11-08 14:30:27 - INFO - Deleted hidden file: /path/.DS_Store
2023-11-08 14:32:15 - INFO - Processing complete
2023-11-08 14:32:15 - INFO - Summary: 1754 scanned, 1203 renamed, 15 deleted, 3 skipped, 8 collisions
```

### 4. Safety Features

#### 4.1 Dry-Run Mode (Default)
- Default behavior: preview changes without executing
- Show summary of planned changes:
  - Files to be renamed (show 10 examples)
  - Files to be deleted (hidden files)
  - Collisions detected
  - Total counts
- Require `--execute` flag to actually perform operations

#### 4.2 Permissions and Ownership
- Set file permissions to `644` (rw-r--r--)
- Set directory permissions to `755` (rwxr-xr-x)
- **Attempt** to set owner to `nobody` and group to `users`
- If ownership change fails (requires root):
  - Log the failure
  - Continue processing (do not abort)
  - Permissions should still be changed

#### 4.3 Path Validation
- Verify input directory exists
- Verify input directory is actually a directory (not a file)
- Convert to absolute path for safety

---

## Test Requirements

### Unit Tests
- Filename sanitization functions
- Collision detection and resolution
- Special character handling
- Non-ASCII transliteration
- Path truncation logic

### Integration Tests
- Full directory processing
- Dry-run vs. execute modes
- Error handling and recovery
- Progress reporting
- Log file generation

### Test Data Structure
```
test_data/
├── spaces in folder/
│   ├── File With Spaces.txt
│   └── UPPERCASE.TXT
├── special@chars#here/
│   ├── file@2023.pdf
│   └── .hidden_file
├── unicode_test/
│   ├── café.txt
│   ├── über.pdf
│   └── naïve.doc
├── collisions/
│   ├── file.txt
│   ├── FILE.TXT
│   └── File (1).txt
└── edge_cases/
    ├── archive.tar.gz
    ├── .DS_Store
    ├── symlink -> ../target.txt
    └── verylongfilename[...].txt
```

---

## Implementation Notes

### Recursive Processing
- Process files depth-first
- Process files before renaming parent directories
- Keep track of renamed directories to update child paths

### Atomic Operations
- Rename operations should use `os.rename()` or `shutil.move()`
- Handle cross-filesystem boundaries if necessary

### State Management
- No persistent state between runs
- Each execution is independent
- Logs provide the only record of changes

---

## Concrete Examples

### Example 1: Basic Sanitization
```
BEFORE: "My Document (Final Version).PDF"
AFTER:  "my_document_final_version.pdf"
```

### Example 2: Non-ASCII Characters
```
BEFORE: "Café Menu — Entrées & Desserts.docx"
AFTER:  "cafe_menu_entrees_desserts.docx"
```

### Example 3: Multiple Extensions
```
BEFORE: "backup.2023.11.08.tar.gz"
AFTER:  "backup_2023_11_08_tar.gz"
```

### Example 4: Collision Resolution
```
Directory contains:
  - "Report 2023.pdf"
  - "REPORT 2023.pdf"
  - "report (2023).pdf"

AFTER processing:
  - "report_2023.pdf" (first file processed alphabetically)
  - "report_2023_20231108_1.pdf"
  - "report_2023_20231108_2.pdf"
```

### Example 5: Special Characters
```
BEFORE: "___file@#$name___.txt"
AFTER:  "filename.txt"
```

### Example 6: Hidden Files (Deleted)
```
BEFORE: ".DS_Store"
AFTER:  [deleted]

BEFORE: ".gitignore"
AFTER:  [deleted]
```

### Example 7: Symbolic Link
```
BEFORE: "link.txt" -> "/home/user/target.txt"
AFTER:  [symlink deleted, target processed if in tree]
```

### Example 8: Path Too Long
```
BEFORE: "very_long_filename_that_is_over_200_characters_[...]_and_continues.txt"
STEP 1: Truncate to 200 chars: "very_long_filename_[...truncated...].txt"
STEP 2: Check full path length
IF still too long: Skip and log error
```

---

## Success Criteria

Stage 1 is considered complete when:

1. All files and folders are renamed according to the rules
2. All collisions are resolved safely
3. All hidden files are deleted
4. All symlinks are handled appropriately
5. Progress is displayed clearly during execution
6. Errors are handled gracefully
7. Complete log file is generated
8. Dry-run mode shows accurate preview
9. All unit and integration tests pass
10. Permissions are set correctly (644/755)

---

## Future Enhancements (Not Required for Stage 1)

- `--verbose` flag for detailed logging
- Configuration file support for custom rules
- Exclude patterns (e.g., don't process certain file types)
- Parallel processing for large directories
- More sophisticated collision resolution strategies
- Undo/rollback capability

