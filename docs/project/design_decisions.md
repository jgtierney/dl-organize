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
| **21** | **Progress Feedback** | How to show progress for large operations? | **Adaptive**: Scale frequency with file count (10/100/500/1000 files) | Prevents console spam for large ops, maintains useful feedback |
| **22** | **Input/Output Structure** | Should Stages 1-2 support output folder? | **A**: In-place operations only (no `-of` flag for Stages 1-2) | Simpler implementation, `-of` reserved for Stage 3 file relocation |
| **23** | **Execute Confirmation** | How to confirm execution? | **B**: Require explicit `--execute` flag, no prompts (non-interactive) | Already decided - fully automated, no interactive prompts |
| **24** | **Dependencies Policy** | Policy for external libraries? | **C**: Case-by-case decisions, no strict policy | Flexibility to add useful libraries when needed, practical approach |
| **25** | **Configuration File** | Support persistent configuration? | **B**: Optional YAML config file (`~/.file_organizer.yaml`) | Convenience for repeated use, CLI flags override, graceful if missing |
| **26** | **Directory Validation** | How strict should path validation be? | **D**: Strict validation + confirmation for large dirs (>1min estimate) | Block system directories, warn on large operations, maximum safety |
| **27** | **Filename Truncation** | How to truncate long filenames? | **C**: Smart truncate preserving extension | Already decided in Stage 1 - preserve extension integrity |
| **28.1** | **File Timestamps** | Preserve or update timestamps? | Preserve original timestamps using `shutil.move()` | Easiest implementation, maintains file history |
| **28.2** | **Locked Files** | Handle files in use? | Skip with error log, continue processing | Robust operation, don't abort on single file failure |
| **28.3** | **Recursion Depth** | Set maximum depth limit? | No limit, symlinks already handled | Python default sufficient, symlink loops prevented in Stage 1 |
| **28.4** | **Network/FUSE** | Special handling for network filesystems? | Support FUSE, handle errors like permission errors | User mentioned FUSE usage, treat network errors gracefully |
| **28.5** | **Case Sensitivity** | Handle case-insensitive filesystems? | No special handling needed | All lowercase in Stage 1, ext4 is case-sensitive |
| **28.6** | **Disk Space** | Check available disk space? | Not for Stages 1-2 (in-place), yes for Stage 3 (output folder) | In-place renames don't consume space, copying does |
| **29** | **Large Scale Optimization** | How to handle 100k-500k files efficiently? | Load full tree in memory, adaptive progress, limited logging, single-threaded (Phase 4: optional multi-core) | System has 32GB RAM & 16 cores - leverage resources for performance |

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

### Decision 21: Adaptive Progress Reporting
**Problem**: Users need feedback during long operations, but at scale (100k+ files), printing every 10 files creates 10,000+ console updates.

**Considered Options**:
- Silent (no progress)
- Progress bar only
- Print every 10 files (too verbose at scale)
- **Progress bar + adaptive frequency** ✓

**Chosen**: Progress bar (continuous) with adaptive status updates:
- **< 1,000 files**: Every 10 files (`50/754 processed`)
- **1,000 - 10,000 files**: Every 100 files (`2,300/8,421 processed`)
- **10,000 - 100,000 files**: Every 500 files (`45,500/87,234 processed`)
- **100,000+ files**: Every 1,000 files (`234,000/456,789 processed`)

**Reasoning**:
- Progress bar shows visual completion
- Adaptive frequency scales with operation size
- Prevents console spam (100k files = 100 updates, not 10,000)
- Still provides concrete numbers at useful intervals
- Format `XX/YY processed` remains clear and informative
- Balances feedback with performance at all scales

---

### Decision 22: In-Place Operations Only (Stages 1-2)
**Problem**: Should Stages 1-2 support an output folder, or operate in-place?

**Considered Options**:
- In-place only (modify source directory) ✓
- Support optional output folder now
- Other approach

**Chosen**: In-place operations only for Stages 1-2.

**Reasoning**:
- Simpler implementation (no copying logic)
- Faster execution (rename vs copy)
- No additional disk space required
- `-of` flag reserved for Stage 3 (file relocation/organization)
- User can make backup before running if desired
- Dry-run mode provides safety

---

### Decision 25: Optional YAML Configuration File
**Problem**: Should the application support persistent configuration?

**Considered Options**:
- No config file (CLI only)
- Optional config file ✓
- Required config file

**Chosen**: Support optional YAML configuration file at `~/.file_organizer.yaml`.

**Reasoning**:
- Convenience for users who run frequently
- CLI flags can override config settings
- Graceful fallback if config missing
- YAML is human-readable and widely used
- Not required (low barrier to entry)
- Supports sensible defaults without configuration

**Example Config**:
```yaml
default_mode: dry-run
flatten_threshold: 5
preserve_timestamps: true
log_location: cwd
```

---

### Decision 26: Strict Validation + Confirmation
**Problem**: How to prevent accidental damage to system files or large directories?

**Considered Options**:
- Basic validation only
- Strict system directory blocking
- Confirmation prompts
- Combination (strict + confirmation) ✓

**Chosen**: Strict validation blocking system directories, plus confirmation for operations > 1 minute estimated.

**Reasoning**:
- **System directory blocking**: Prevents catastrophic mistakes
  - Block: `/`, `/usr`, `/bin`, `/sbin`, `/etc`, `/boot`, `/sys`, `/proc`, `/dev`, `/lib`
  - Allow: `/home/username/...`, `/tmp`, `/opt`, `/mnt`, `/media`
- **Time-based confirmation**: User explicitly confirms large operations
  - Estimate: ~100-200 files/second
  - Prompt if > 60 seconds estimated
  - Shows file count, folder count, estimated time
- **Layered safety**: Multiple safeguards better than one
- **User-friendly**: Doesn't block legitimate use cases

---

### Decision 28: Edge Case Specifications
**Problem**: Multiple edge cases need clear handling rules.

#### 28.1: Preserve File Timestamps
**Chosen**: Preserve original timestamps automatically.
**Reasoning**:
- Easiest implementation (`shutil.move()` preserves by default)
- Maintains file history and provenance
- Expected behavior for file organization tools
- No additional code required

#### 28.2: Skip Locked Files
**Chosen**: Catch errors, log, skip, continue.
**Reasoning**:
- Robust operation (one failure doesn't abort everything)
- Clear error reporting in logs
- User can manually handle problem files later
- Matches overall error handling philosophy

#### 28.3: No Recursion Depth Limit
**Chosen**: No arbitrary depth limit enforced.
**Reasoning**:
- Python's default recursion limit (~1000 levels) is sufficient
- Real-world directories rarely exceed 20-30 levels
- Symlink loops already prevented (symlinks broken in Stage 1)
- Unnecessary complexity to add artificial limit

#### 28.4: FUSE Filesystem Support
**Chosen**: Support FUSE, handle errors gracefully.
**Reasoning**:
- User specifically mentioned using FUSE filesystems
- Treat network/FUSE errors same as permission errors (skip and log)
- No special code needed, just error handling
- Examples: sshfs, encfs, s3fs

#### 28.5: Case Sensitivity Handling
**Chosen**: No special handling needed.
**Reasoning**:
- All filenames lowercase after Stage 1
- Case collisions resolved in Stage 1
- Ubuntu default (ext4) is case-sensitive
- Case-insensitive filesystems rare on Linux

#### 28.6: Disk Space Validation
**Chosen**: No check for Stages 1-2; add for Stage 3+.
**Reasoning**:
- **Stages 1-2**: In-place renames/moves don't consume disk space
- **Stage 3+**: Copying to output folder requires space check
  - Calculate total input size
  - Verify output filesystem has 110% of input size (safety margin)
  - Abort if insufficient space

---

### Decision 29: Large Scale Optimization Strategy
**Problem**: How to efficiently handle 100,000-500,000 files across thousands of directories?

**Context**: User has 32GB RAM and 16-core processor available for operations.

**Considered Options**:
- Streaming/generator approach (memory-efficient but slower)
- Load full tree in memory (leverages available RAM) ✓
- Parallel processing from the start
- Single-threaded with optional parallelization ✓

**Chosen**: Multi-faceted approach leveraging available hardware:

1. **Load Full Directory Tree in Memory**
   - With 32GB RAM, 500k files ≈ 50-200MB (< 1% of RAM)
   - Enables faster processing, accurate progress tracking
   - Better collision detection with full tree view

2. **Adaptive Progress Reporting**
   - Scale update frequency with file count
   - Prevents console spam (100k files = 100 updates, not 10,000)
   - See Decision 21 for details

3. **Limited Error Logging**
   - Log first 1,000 detailed errors, then summarize
   - Prevents GB-sized log files
   - Target: 1-10MB logs for 500k files

4. **Single-Threaded Initially**
   - File I/O is typically the bottleneck, not CPU
   - Simpler implementation and debugging
   - Likely sufficient for performance targets

5. **Optional Multi-Core Processing (Phase 4)**
   - 16 cores available if performance testing shows benefit
   - Can parallelize file processing operations
   - Requires thread-safe collision tracking

**Reasoning**:
- **Hardware-appropriate**: Use available resources (32GB RAM)
- **Performance targets achievable**:
  - 100k files: 5-10 minutes
  - 500k files: 25-50 minutes
- **Scalability**: Approaches scale linearly with file count
- **Maintainability**: Start simple (single-threaded), optimize if needed
- **User experience**: Fast scanning, clear progress, manageable logs

**Memory Footprint**:
- 500k files × 100 bytes/file ≈ 50MB
- Collision tracking + state ≈ 50-100MB
- Total: < 500MB (< 2% of available 32GB RAM)

**Performance Comparison**:
- Streaming approach: Lower memory, but must re-scan for each stage
- In-memory approach: Higher memory (but trivial at 32GB), single scan, faster overall

---

## Principles Derived from Decisions

### Safety First
- Dry-run default mode
- System directory blocking
- Confirmation for large operations
- Continue on errors (don't abort entire operation)
- Clear logging and error reporting
- Graceful degradation (permissions, ownership)
- Preserve file timestamps

### Clarity and Consistency
- All lowercase filenames
- Underscores as separators
- Single extension per file
- Predictable collision naming (date + counter)
- ASCII-only characters

### Simplification
- Remove hidden files and clutter
- Break symlinks to avoid complexity
- Flatten unnecessary nesting (< 5 items threshold)
- Collapse redundant characters
- In-place operations (no copying)

### User-Friendly
- Progress feedback (bar + periodic counts)
- Minimal but sufficient logging
- Clear error messages
- Predictable behavior
- Optional configuration file
- Flexible dependency policy

### Robustness
- Skip locked files, continue processing
- Support FUSE and network filesystems
- Handle edge cases gracefully
- No arbitrary limits (recursion depth)
- Cross-platform ASCII compatibility

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2023-11-08 | Initial design decisions documented (Decisions 1-21) |
| 2.0 | 2023-11-10 | Stage 2 finalized: Added decisions 22-28, all specifications complete |
| 2.1 | 2023-11-10 | Large scale optimization: Updated Decision 21 (adaptive progress), added Decision 29 (scale strategy for 100k-500k files with 32GB RAM/16 cores) |

---

## References

- [Stage 1 Requirements](./stage1_requirements.md)
- [Stage 2 Requirements](./stage2_requirements.md)
- [Requirements Overview](./requirements.md)

