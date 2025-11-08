# Design Decisions Reference

This document provides a quick reference table of all design decisions made during the requirements gathering process.

---

## Decision Summary Table

| # | Category | Question | Decision | Rationale |
|---|----------|----------|----------|-----------|
| **1** | **File Extensions** | How to handle multiple file extensions (e.g., `archive.tar.gz`)? | **B**: Replace internal periods with underscores → `archive_tar.gz` | Simplifies parsing, ensures single extension, avoids confusion |
| **2** | **Non-ASCII Characters** | How to handle non-ASCII/Unicode characters? | **A**: Transliterate to ASCII equivalents using `unidecode` library | Preserves meaning, improves compatibility, handles international names gracefully |
| **3** | **Collision Resolution** | How to resolve file naming collisions? | **Date stamp + counter**: `file_YYYYMMDD_N.txt` | Provides temporal context and handles multiple collisions per day |
| **4** | **Periods in Filenames** | How to handle periods within base filenames? | **A**: Replace internal periods with underscores | Consistent with extension handling, avoids ambiguity |
| **5** | **Folder Flattening** | How aggressively to flatten folder chains? | **A**: Flatten single-child chains **+** iteratively flatten folders with < 5 items | Balances organization with simplification, removes unnecessary nesting |
| **6** | **Hidden Files** | How to handle hidden files (starting with `.`)? | **B**: Delete entirely | Cleanup purpose, removes system metadata clutter |
| **7** | **Symbolic Links** | How to handle symbolic links? | **B**: Break/remove symlinks, process target if in tree | Simplifies structure, avoids link complexity and potential loops |
| **8** | **Dry-Run Mode** | Should the application support previewing changes? | **B**: Default is dry-run (require `--execute` to run) | Safety first, prevents accidental changes |
| **9** | **Logging Level** | What level of logging detail? | **A**: Minimal - errors + summary only | Cleaner output, sufficient for troubleshooting, can enhance later |
| **10** | **Log Location** | Where to store log files? | **A**: Current working directory (where command is run) | User knows location, easy to find, no permission issues |
| **11** | **Stage Execution** | Run stages separately or together? | **A**: Run both stages automatically in sequence | Streamlined workflow, simpler for users |
| **12** | **Empty Folders with Hidden Files** | Are folders with only hidden files considered empty? | **A**: Yes, consider empty and remove | Hidden files deleted in Stage 1, so folder becomes empty |
| **13** | **Backup/Rollback** | Should the application create backups? | **A**: No backup - operations are final | Simpler implementation, users should backup beforehand |
| **14** | **File Permissions** | What permissions and ownership to apply? | **C**: Set 644/755, attempt `nobody:users` ownership, continue if fails | Standard permissions, enhanced security if possible, graceful degradation |
| **15** | **Error Handling** | What to do when processing fails mid-operation? | **B**: Skip failed file, log error, continue with remaining files | Robust operation, maximizes processed files, clear error reporting |
| **16** | **Files Without Extensions** | How to handle extensionless files (e.g., `README`, `Makefile`)? | **A**: Process normally, no extension added | Respect common conventions, many valid files have no extension |
| **17** | **Long Filenames** | How to handle filenames exceeding limits? | **B** then **C**: Truncate to 200 chars; if path still too long, skip and log | Reasonable limit with safety margin, clear failure handling |
| **18** | **Multiple Consecutive Special Chars** | How to handle `file___name.txt`? | **A**: Collapse to single underscore → `file_name.txt` | Cleaner output, removes redundant separators |
| **19** | **Leading/Trailing Special Chars** | How to handle `_file_` or `..name..`? | **A**: Strip leading and trailing underscores/periods | Cleaner names, removes edge artifacts |
| **20** | **CLI Format** | What should the command syntax be? | `file-organizer -if /path/to/directory [-of /path/to/output]` | Explicit input/output flags, extensible for future stages |
| **21** | **Progress Feedback** | How to show progress for large operations? | **B**: Progress bar + print every 10th file with `50/1754 processed` format | Balanced feedback, not overwhelming, shows real progress |

---

## Detailed Decision Explanations

### Decision 1: Replace Internal Periods with Underscores
**Problem**: Files like `archive.tar.gz` or `data.backup.json` have multiple periods.

**Considered Options**:
- Keep as-is: `archive.tar.gz`
- Replace internal: `archive_tar.gz` ✓
- Keep only final: `archive.gz`

**Chosen**: Replace internal periods with underscores.

**Reasoning**:
- Simplifies extension detection (only need to check final period)
- Avoids confusion about what the "real" extension is
- Maintains file information (user can still see it was a tar.gz)
- Consistent with overall strategy of using underscores as separators

---

### Decision 2: Transliterate Non-ASCII Characters
**Problem**: How to handle international characters like `café.txt`, `über.pdf`, `文档.doc`?

**Considered Options**:
- Transliterate to ASCII: `café.txt` → `cafe.txt` ✓
- Replace with underscores: `café.txt` → `caf_.txt`
- Strip entirely: `café.txt` → `caf.txt`
- Skip files with non-ASCII: (not considered)

**Chosen**: Transliterate using `unidecode` library.

**Reasoning**:
- Preserves meaning and readability
- Handles European languages gracefully (é→e, ñ→n, ü→u)
- Better than losing characters entirely
- Industry-standard approach
- `unidecode` is well-maintained and reliable

---

### Decision 3: Date Stamp + Counter for Collisions
**Problem**: When `file.txt` already exists, what should the duplicate be named?

**Considered Options**:
- Append counter: `file_1.txt`, `file_2.txt`
- Append timestamp: `file_20231108_143022.txt`
- Append date + counter: `file_20231108_1.txt` ✓
- Append hash: `file_a3f2.txt`

**Chosen**: Date stamp (YYYYMMDD) + counter format.

**Reasoning**:
- Provides temporal context (when was this collision resolved?)
- Handles multiple collisions on same day (counter)
- More readable than full timestamp
- More meaningful than just a counter
- Shorter than full timestamp
- Sortable by date

---

### Decision 5: Aggressive Folder Flattening (< 5 Items)
**Problem**: How much to flatten folder hierarchies?

**Considered Options**:
- Flatten only single-child chains ✓ (base requirement)
- **PLUS** flatten any folder with < 5 items ✓ (additional rule)
- Flatten completely (too aggressive)
- Don't flatten (defeats purpose)

**Chosen**: Iteratively flatten single-child chains AND folders with fewer than 5 total items.

**Reasoning**:
- Single-child chains are always unnecessary nesting
- Folders with < 5 items add little organizational value
- Threshold of 5 balances simplification with maintaining logical structure
- Iterative application ensures maximum flattening
- User explicitly requested this behavior

**Example**:
```
BEFORE: A/B/C/file.txt (B has 1 item, C has 1 item)
AFTER:  A/file.txt (both flattened)
```

---

### Decision 6: Delete Hidden Files
**Problem**: What to do with `.DS_Store`, `.gitignore`, `.cache`, etc.?

**Considered Options**:
- Process normally (rename them)
- Skip entirely (leave as-is)
- Delete completely ✓

**Chosen**: Delete all hidden files.

**Reasoning**:
- Application purpose is cleanup
- Hidden files are usually system metadata/cache
- `.DS_Store` (macOS), `.Thumbs.db` (Windows) are clutter
- User confirmed intent to remove hidden files
- Reduces confusion in target directory

**Warning**: This is destructive. Users should be informed that version control files (`.git`, `.svn`) will be affected if present.

---

### Decision 7: Break Symlinks, Process Target
**Problem**: Symbolic links can create loops and complexity.

**Considered Options**:
- Follow links and process target
- Skip symlinks entirely
- Break links, process target if in tree ✓

**Chosen**: Delete the symlink itself, process the target file if it exists within the directory tree.

**Reasoning**:
- Simplifies the directory structure
- Eliminates potential for broken links after renaming
- Prevents infinite loops
- If target is in tree, it will be processed normally
- If target is external, link would be broken anyway after cleanup

---

### Decision 8: Dry-Run as Default
**Problem**: How to prevent accidental file destruction?

**Considered Options**:
- No dry-run (just run)
- Optional dry-run with `--dry-run` flag
- **Default dry-run, require `--execute` to run** ✓

**Chosen**: Dry-run is the default behavior; require `--execute` flag to actually perform operations.

**Reasoning**:
- Safety first: prevents accidental mass renaming
- Forces users to review changes before applying
- Common pattern in destructive tools (e.g., `git clean -n`)
- Low cost to add `--execute` flag
- Reduces support burden from user mistakes

---

### Decision 14: Standard Permissions, Attempt Ownership Change
**Problem**: What permissions should files have after processing?

**Considered Options**:
- Preserve existing permissions
- Apply standard permissions: 644/755 ✓
- Apply restrictive permissions: 600/700

**Additional**: Attempt to set owner to `nobody` and group to `users`; continue if it fails.

**Chosen**: Set 644 for files, 755 for directories, attempt `nobody:users` ownership, continue if fails.

**Reasoning**:
- **644 (rw-r--r--)**: Owner can read/write, others can read
- **755 (rwxr-xr-x)**: Owner can read/write/execute, others can read/execute
- Standard Unix permissions for shared files
- **nobody:users**: Security practice (minimal privileges)
- **Continue on failure**: Doesn't break if user lacks root/sudo
- Graceful degradation: permissions still improved even if ownership fails

---

### Decision 17: Truncate to 200 Chars, Then Skip
**Problem**: Linux filename limit is 255 bytes, but some filenames might exceed this.

**Considered Options**:
- Truncate to 255 (risky, no margin)
- Truncate to 200 (safe margin) ✓
- If path still too long after truncation: skip file ✓

**Chosen**: Two-phase approach:
1. Truncate basename to 200 characters (preserving extension)
2. If full path still exceeds filesystem limits, skip the file and log error

**Reasoning**:
- 200-char limit provides safety margin
- Full path includes directory structure, which can be long
- Better to skip than to risk filesystem errors
- Logs make it clear which files were skipped
- User can manually handle edge cases

---

### Decision 21: Progress Bar + Periodic Updates
**Problem**: Users need feedback during long operations.

**Considered Options**:
- Silent (no progress)
- Progress bar only
- Print every file (too verbose)
- **Progress bar + print every Nth file** ✓

**Chosen**: Progress bar with status updates every 10 files: `50/1754 processed`

**Reasoning**:
- Progress bar shows visual completion
- Periodic counts provide concrete numbers
- Every 10 files balances feedback with noise
- Format `XX/YY processed` is clear and informative
- Doesn't overwhelm terminal output

---

## Open Questions

See [`stage2_requirements.md`](./stage2_requirements.md) for questions that still need answers:

- **Question 22**: Input/output folder structure for Stages 1-2
- **Question 24**: Dependency policy (external libraries)
- **Question 25**: Configuration file support
- **Question 26**: Target directory validation strictness
- **Question 28**: Additional edge cases and requirements

---

## Principles Derived from Decisions

### Safety First
- Dry-run default
- Continue on errors (don't abort entire operation)
- Clear logging
- Graceful degradation (permissions)

### Clarity and Consistency
- All lowercase
- Underscores as separators
- Single extension per file
- Predictable collision naming

### Simplification
- Remove hidden files
- Break symlinks
- Flatten unnecessary nesting
- Collapse redundant characters

### User-Friendly
- Progress feedback
- Minimal but sufficient logging
- Clear error messages
- Predictable behavior

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2023-11-08 | Initial design decisions documented |

---

## References

- [Stage 1 Requirements](./stage1_requirements.md)
- [Stage 2 Requirements](./stage2_requirements.md)
- [Requirements Overview](./requirements.md)

