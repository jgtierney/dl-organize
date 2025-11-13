# Stage 4 Implementation Plan: File Relocation

## Overview

Stage 4 relocates organized and deduplicated files from the input folder to the output folder, completing the full organization pipeline. This stage uses fast move operations and removes the input folder by default.

## Design Decisions

### 1. Move Operation (Not Copy)
- **Operation**: Move files (rename/move inodes) - fast and efficient
- **Rationale**: User is organizing downloads into final destination
- **Performance**: Much faster than copy (no data transfer needed)
- **Default Behavior**: Remove input folder after successful move
- **Safety**: `--preserve-input` flag available if user wants to keep input

### 2. Directory Structure
- **Preserve relative paths** from input to output
- Input: `/input/documents/work/report.pdf`
- Output: `/output/documents/work/report.pdf`
- Maintains organization from Stages 1-2
- Preserves "keep" folder semantics

### 3. Cleanup Behavior
- **Default**: Remove input folder after successful move
- **Optional**: `--preserve-input` flag to keep input folder
- Input folder only removed if ALL files moved successfully

### 4. Automatic Execution
- **Auto-runs** as part of full pipeline when output folder provided
- Can also run standalone: `--stage 4`

### 5. Future: Classification Support
- **Phase 1** (Current): Move files preserving structure
- **Phase 2** (Future): Optional classification
  - Move top-level files to `miscellaneous/` subfolder
  - Optional grouping by type/date
  - Configurable via `.file_organizer.yaml`

### 6. Performance Priority
- Optimize for speed over redundancy
- Move operations (not copy)
- Minimal verification (existence check)
- Parallel operations where possible

## Workflow

### Five-Phase Process

```
Phase 1: Validation
  ✓ Verify output folder exists/is writable
  ✓ Calculate input folder size
  ✓ Check sufficient disk space (10% margin)
  ✓ Verify no locked/in-use files

Phase 2: Directory Structure Creation
  → Create output directory tree (preserve structure)
  → Handle mkdir errors gracefully
  → Set proper permissions (755)

Phase 3: File Relocation
  → Move files from input to output
  → Preserve relative paths
  → Handle collisions (shouldn't happen after Stage 3B)
  → Update progress display
  → Log all operations

Phase 4: Verification
  → Verify all files exist in output
  → Check file counts match
  → Validate critical files moved

Phase 5: Cleanup (unless --preserve-input)
  → Remove empty directories in input
  → Remove input root folder
  → Report final status
```

## Implementation Details

### Core Module: `stage4.py`

```python
class Stage4Processor:
    """
    Stage 4: File Relocation

    Moves organized and deduplicated files from input to output folder.
    Preserves directory structure and removes input by default.
    """

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        preserve_input: bool = False,
        dry_run: bool = True,
        verbose: bool = False
    ):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.preserve_input = preserve_input
        self.dry_run = dry_run
        self.verbose = verbose

    def process(self) -> Stage4Results:
        """
        Execute Stage 4: File relocation.

        Returns:
            Stage4Results with operation statistics
        """
        # Phase 1: Validation
        self._validate_folders()
        self._check_disk_space()

        # Phase 2: Create directory structure
        self._create_output_structure()

        # Phase 3: Move files
        moved_files = self._relocate_files()

        # Phase 4: Verification
        self._verify_relocation(moved_files)

        # Phase 5: Cleanup (unless --preserve-input)
        if not self.preserve_input and not self.dry_run:
            self._cleanup_input_folder()

        return self._generate_results(moved_files)
```

### Key Methods

#### 1. Validation
```python
def _validate_folders(self) -> None:
    """Validate input and output folders."""
    # Check input folder exists and is readable
    if not self.input_folder.exists():
        raise ValueError(f"Input folder does not exist: {self.input_folder}")

    # Check output folder exists or can be created
    if not self.output_folder.exists():
        self.output_folder.mkdir(parents=True, exist_ok=True)

    # Check write permissions
    if not os.access(self.output_folder, os.W_OK):
        raise PermissionError(f"Output folder not writable: {self.output_folder}")

def _check_disk_space(self) -> None:
    """Verify sufficient disk space in output location."""
    input_size = self._calculate_folder_size(self.input_folder)
    output_free = shutil.disk_usage(self.output_folder).free

    required = int(input_size * 1.1)  # 10% safety margin

    if output_free < required:
        raise DiskSpaceError(
            f"Insufficient disk space. "
            f"Required: {self._format_size(required)}, "
            f"Available: {self._format_size(output_free)}"
        )
```

#### 2. Directory Structure Creation
```python
def _create_output_structure(self) -> None:
    """Create output directory tree mirroring input structure."""
    for dirpath, dirnames, _ in os.walk(self.input_folder):
        # Calculate relative path
        rel_path = Path(dirpath).relative_to(self.input_folder)
        output_dir = self.output_folder / rel_path

        # Create directory in output
        if not self.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(output_dir, 0o755)
```

#### 3. File Relocation
```python
def _relocate_files(self) -> List[MovedFile]:
    """Move all files from input to output preserving structure."""
    moved_files = []
    file_list = list(self._walk_files(self.input_folder))
    total_files = len(file_list)

    for idx, file_path in enumerate(file_list, 1):
        # Calculate destination
        rel_path = file_path.relative_to(self.input_folder)
        dest_path = self.output_folder / rel_path

        # Move file (or simulate in dry-run)
        if not self.dry_run:
            self._move_file(file_path, dest_path)

        moved_files.append(MovedFile(
            source=file_path,
            destination=dest_path,
            size=file_path.stat().st_size
        ))

        # Update progress
        if idx % 100 == 0 or idx == total_files:
            self._report_progress(idx, total_files, moved_files)

    return moved_files

def _move_file(self, source: Path, dest: Path) -> None:
    """
    Move a single file from source to destination.

    Uses shutil.move() which:
    - Uses os.rename() if same filesystem (fast)
    - Falls back to copy + delete if different filesystems
    """
    try:
        # Handle collision (shouldn't happen after Stage 3B)
        if dest.exists():
            # Log warning and skip
            logger.warning(f"Destination exists, skipping: {dest}")
            return

        # Ensure parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(source), str(dest))

        # Preserve timestamps
        shutil.copystat(str(source), str(dest))

    except Exception as e:
        logger.error(f"Failed to move {source} to {dest}: {e}")
        raise
```

#### 4. Verification
```python
def _verify_relocation(self, moved_files: List[MovedFile]) -> None:
    """Verify all files were moved successfully."""
    if self.dry_run:
        return  # Skip verification in dry-run

    missing = []
    for moved in moved_files:
        if not moved.destination.exists():
            missing.append(moved.destination)

    if missing:
        raise VerificationError(
            f"Verification failed: {len(missing)} files missing in output"
        )
```

#### 5. Cleanup
```python
def _cleanup_input_folder(self) -> None:
    """Remove input folder after successful move."""
    try:
        # Remove input folder recursively
        shutil.rmtree(self.input_folder)
        logger.info(f"Removed input folder: {self.input_folder}")
    except Exception as e:
        logger.warning(
            f"Could not remove input folder: {e}. "
            f"Files have been moved successfully, but input folder remains."
        )
```

## CLI Integration

### New Arguments

```python
# Add to argparse in cli.py
parser.add_argument(
    "--preserve-input",
    action="store_true",
    help="Keep input folder after moving files (default: remove input)"
)

parser.add_argument(
    "--stage",
    type=str,
    choices=["1", "2", "3a", "3b", "4"],  # Add "4"
    help="Run specific stage only"
)
```

### Execution Logic

```python
# Stage 4: File Relocation
# Run if explicitly requested OR if run_all and output folder provided
should_run_4 = args.stage == "4" or (run_all and args.output_folder)

if should_run_4:
    # Validate output folder is provided
    if not args.output_folder:
        print("\n❌ ERROR: Stage 4 requires --output-folder (-of)")
        return 1

    print("\nStarting Stage 4: File Relocation...")

    stage4 = Stage4Processor(
        input_folder=Path(args.input_folder),
        output_folder=Path(args.output_folder),
        preserve_input=args.preserve_input,
        dry_run=not args.execute,
        verbose=args.verbose
    )

    results = stage4.process()

    if not args.execute:
        print("\n💡 TIP: Run with --execute to actually move files")
```

## Progress Reporting

### Phase 1: Validation
```
============================================================
  Stage 4: File Relocation
============================================================
Input folder:  /path/to/input
Output folder: /path/to/output
Mode: EXECUTE (will move files)
Cleanup: Input folder will be removed after move

[Phase 1/5] Validation
  ✓ Input folder: 12,453 files, 50.2 GB
  ✓ Output folder writable
  ✓ Disk space: 250.0 GB available (50.2 GB required)
  ✓ Sufficient space with 10% margin
```

### Phase 2: Directory Structure
```
[Phase 2/5] Creating Directory Structure
  ✓ Created 345 directories in output folder
```

### Phase 3: File Relocation
```
[Phase 3/5] Moving Files
  Progress: [████████░░] 8,234 / 12,453 files (66.1%)
  Moved: 33.2 GB / 50.2 GB
  Speed: ~1,250 files/sec
  Time remaining: ~3 seconds
```

### Phase 4: Verification
```
[Phase 4/5] Verification
  ✓ Verified: 12,453 / 12,453 files exist in output
  ✓ All files moved successfully
```

### Phase 5: Cleanup
```
[Phase 5/5] Cleanup
  ✓ Removed input folder: /path/to/input
  ✓ Operation complete
```

### Final Summary
```
============================================================
  Stage 4 Complete
============================================================
Files moved: 12,453
Data transferred: 50.2 GB
Directories created: 345
Input folder: Removed
Time taken: 8.3 seconds

✓ All files relocated successfully
```

## Error Handling

### Common Errors

**Insufficient Disk Space**:
```
❌ ERROR: Insufficient disk space in output location
Required: 50.2 GB (with 10% margin)
Available: 30.1 GB
Please free up space or use different output location
```

**Output Folder Not Writable**:
```
❌ ERROR: Cannot write to output folder
Folder: /path/to/output
Reason: Permission denied
Solution: Check folder permissions or use sudo
```

**File Collision** (shouldn't happen):
```
⚠️  WARNING: Destination file exists, skipping
File: documents/report.pdf
This should not happen after Stage 3B
Consider re-running Stage 3B if seeing multiple collisions
```

**Partial Failure**:
```
❌ ERROR: Verification failed
Missing files: 3 / 12,453
Files may have been moved but could not be verified
Input folder preserved for safety
Please investigate before retrying
```

## Testing Strategy

### Test Scenarios

**Test 1: Basic Relocation (Small Dataset)**
- Input: 50 files in 10 directories
- Expected: All files moved, structure preserved
- Verify: File counts match, input folder removed

**Test 2: Large Dataset**
- Input: 10,000 files in 500 directories
- Expected: Fast move operation (< 30 seconds)
- Verify: Progress reporting works

**Test 3: Preserve Input Flag**
- Run with `--preserve-input`
- Expected: Files moved, input folder still exists
- Verify: Files exist in both locations

**Test 4: Dry-Run Mode**
- Run without `--execute`
- Expected: Preview only, no actual moves
- Verify: Input folder unchanged

**Test 5: Insufficient Space**
- Mock disk space check to fail
- Expected: Error before moving files
- Verify: No files moved

**Test 6: Cross-Filesystem Move**
- Input and output on different filesystems
- Expected: shutil.move falls back to copy+delete
- Verify: Files moved successfully (slower)

**Test 7: Deep Directory Tree**
- Input: 20 levels deep
- Expected: Output structure matches
- Verify: Relative paths preserved

## Implementation Todo List

### Core Implementation (Tasks 1-7)
- [ ] Create `stage4.py` module with Stage4Processor class
- [ ] Implement folder validation (_validate_folders)
- [ ] Implement disk space check (_check_disk_space)
- [ ] Implement directory structure creation (_create_output_structure)
- [ ] Implement file relocation (_relocate_files, _move_file)
- [ ] Implement verification (_verify_relocation)
- [ ] Implement cleanup (_cleanup_input_folder)

### Progress & Reporting (Tasks 8-10)
- [ ] Implement progress reporting for all phases
- [ ] Add dry-run preview mode
- [ ] Add verbose logging option

### CLI Integration (Tasks 11-13)
- [ ] Add `--stage 4` to argparse choices
- [ ] Add `--preserve-input` flag to argparse
- [ ] Wire up Stage 4 in main() execution flow
- [ ] Add Stage 4 to auto-run pipeline

### Testing (Tasks 14-17)
- [ ] Add Stage 4 test cases to stage4.py __main__
- [ ] Test basic relocation with small dataset
- [ ] Test large dataset performance
- [ ] Test --preserve-input flag
- [ ] Test dry-run mode
- [ ] Test error conditions (space, permissions)
- [ ] Test cross-filesystem moves

### Error Handling (Tasks 18-19)
- [ ] Add comprehensive error handling
- [ ] Add recovery logic for partial failures
- [ ] Add helpful error messages

### Documentation (Tasks 20-21)
- [ ] Update README.md with Stage 4 examples
- [ ] Update STATUS.md when complete
- [ ] Create user guide for Stage 4

### Finalization (Task 22)
- [ ] Commit and push Stage 4 implementation

## Configuration Support

### Config File Options (Future)

```yaml
# Stage 4: File Relocation
relocation:
  preserve_input: false          # Default: remove input after move
  verify_moves: true            # Verify all files after move
  classification:
    enabled: false              # Future: Optional classification
    top_level_to_misc: true    # Move top-level files to miscellaneous/
```

## Future Enhancements

### Phase 2: Classification Support

**Top-Level File Organization**:
```
Before:
/input/
  ├── documents/work/report.pdf
  ├── photos/vacation/img.jpg
  ├── random_file.txt            ← Top-level file
  └── another.pdf                 ← Top-level file

After:
/output/
  ├── documents/work/report.pdf
  ├── photos/vacation/img.jpg
  └── miscellaneous/              ← New folder
      ├── random_file.txt
      └── another.pdf
```

**Optional Grouping**:
- By file type: `documents/`, `images/`, `videos/`, `audio/`, `archives/`
- By date: `2025/01/`, `2025/02/`
- By size category: `large/`, `medium/`, `small/`
- Custom rules via config file

## Performance Expectations

### Move Operations

**Same Filesystem** (most common):
- Uses `os.rename()` - instant (just updates inode)
- 10,000 files: < 10 seconds
- 100,000 files: < 60 seconds

**Different Filesystems**:
- Falls back to copy + delete
- Speed depends on disk I/O
- 10,000 files (50 GB): ~5-10 minutes

### Optimization Strategy

1. **Batch Operations**: Move files in batches for better performance
2. **Minimal Verification**: Check existence, not hashes (speed priority)
3. **Parallel Processing** (future): Use multiprocessing for cross-filesystem moves
4. **Progress Updates**: Only update every N files to avoid slowdown

## Usage Examples

### Full Pipeline with Relocation
```bash
# Organize and move files (removes input by default)
file-organizer -if /downloads -of /organized --execute

# Stages run: 1 → 2 → 3A → 3B → 4
```

### Full Pipeline Preserving Input
```bash
# Keep input folder after move
file-organizer -if /downloads -of /organized --execute --preserve-input
```

### Stage 4 Only
```bash
# Run only Stage 4 (assumes Stages 1-3 already done)
file-organizer -if /downloads -of /organized --stage 4 --execute
```

### Dry-Run Preview
```bash
# Preview what would happen
file-organizer -if /downloads -of /organized --stage 4
```

## Benefits

1. **Fast**: Move operations are instant on same filesystem
2. **Clean**: Removes input folder by default (organized files in output)
3. **Safe**: Verification ensures all files moved successfully
4. **Flexible**: `--preserve-input` available if needed
5. **Automatic**: Runs as part of full pipeline when output folder specified
6. **Future-Ready**: Architecture supports classification features

## Related Files

- `src/file_organizer/stage4.py` - Stage 4 processor (to be created)
- `src/file_organizer/cli.py` - CLI integration (to be updated)
- `src/file_organizer/config.py` - Configuration support (to be extended)
- `docs/requirements/stage4_requirements.md` - Full Stage 4 specification (to be created)
- `docs/project-phases.md` - Project roadmap (to be updated)
