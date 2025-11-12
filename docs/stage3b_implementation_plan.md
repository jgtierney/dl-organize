# Stage 3B Implementation Plan: Cross-Folder Deduplication

## Overview

Stage 3B identifies and resolves duplicate files between the input and output folders, using the same three-tier resolution policy as Stage 3A.

## Optimized Workflow

### Key Optimization: Reuse Input Cache from Stage 3A

**Stage 3B does NOT re-scan the input folder!**
- Input folder cache already exists from Stage 3A (100% cache hits)
- Only scan/hash the output folder
- Massive performance improvement (~50% faster than scanning both)

### Five-Phase Process

```
Phase 1: Load Input Cache (instant)
  ✓ Read from .file_organizer_cache/hashes.db
  ✓ WHERE folder = 'input'
  ✓ No re-scanning or re-hashing needed

Phase 2: Scan Output Folder
  → Scan all files in output directory
  → Apply same filtering (skip images, min size)
  → Hash files using metadata-first optimization
  → Save to cache WHERE folder = 'output'

Phase 3: Find Cross-Folder Duplicates
  → Match hashes between input and output caches
  → GROUP BY file_hash
  → Identify files that exist in BOTH folders

Phase 4: Apply Resolution Policy (Same as Stage 3A)
  Priority 1: "keep" keyword (ancestor priority rule)
  Priority 2: Path depth (deeper = better organized)
  Priority 3: Newest mtime (most recent)

Phase 5: Execute Deletions
  → Delete file that loses resolution (either folder)
  → Report deletions in dry-run mode
  → Update cache after deletions
```

## Resolution Policy (Full Three-Tier)

### Priority 1: "keep" Keyword
- Files with "keep" anywhere in path beat files without
- **Ancestor priority rule** applies:
  - Higher ancestor "keep" folders beat lower ones
  - "keep" in folder name beats "keep" in filename only
- **Can delete from either folder** based on policy

**Example:**
```
Input:  /input/keep/important/video.mp4 (2024-01-01)
Output: /output/video.mp4 (2025-11-01, newer but no "keep")
→ DELETE from output (input has "keep" keyword)
```

### Priority 2: Path Depth
- Deeper paths preferred (better organized after Stage 2)
- Count number of directory components

**Example:**
```
Input:  /input/video.mp4 (depth=2)
Output: /output/movies/action/thriller/video.mp4 (depth=5)
→ DELETE from input (output is deeper/better organized)
```

### Priority 3: Newest mtime
- Most recent modification time wins
- Rationale: Newest version likely has latest edits

**Example:**
```
Input:  /input/downloads/video.mp4 (2025-11-01, depth=3)
Output: /output/archive/video.mp4 (2024-06-15, depth=3, same depth)
→ DELETE from output (input is newer)
```

## Implementation Todo List

### Core Implementation (Tasks 2-7)
- [x] Review Stage 3B requirements and design
- [ ] Add `run_stage3b()` method to Stage3 class
- [ ] Load input folder cache (from Stage 3A - no re-scanning)
- [ ] Scan and hash output folder (build output cache)
- [ ] Find cross-folder duplicates (match hashes between input/output)
- [ ] Apply full resolution policy (keep/depth/mtime) for cross-folder dupes
- [ ] Support deleting from either folder based on resolution policy

### Progress & Reporting (Tasks 8-10)
- [ ] Update progress reporting for two-folder workflow
- [ ] Implement dry-run report for Stage 3B
- [ ] Implement execute mode for Stage 3B (delete per policy)

### Testing (Tasks 11-14)
- [ ] Add Stage 3B test cases
- [ ] Test Stage 3B with real data (input vs output folders)
- [ ] Update CLI to wire up Stage 3B execution
- [ ] Verify output folder requirement validation works
- [ ] Test full pipeline: Stage 3A → Stage 3B workflow

### Finalization (Tasks 15-16)
- [ ] Document Stage 3B usage and examples
- [ ] Commit and push Stage 3B implementation

## Key Implementation Details

### Database Queries

**Load input cache:**
```sql
SELECT file_path, file_hash, file_size, file_mtime
FROM file_cache
WHERE folder = 'input' AND file_hash IS NOT NULL
```

**Load output cache:**
```sql
SELECT file_path, file_hash, file_size, file_mtime
FROM file_cache
WHERE folder = 'output' AND file_hash IS NOT NULL
```

**Find cross-folder duplicates:**
```sql
SELECT file_hash, COUNT(*) as count
FROM file_cache
WHERE file_hash IS NOT NULL
GROUP BY file_hash
HAVING COUNT(DISTINCT folder) = 2
```

### Code Structure

```python
def run_stage3b(self) -> Stage3Results:
    """
    Run Stage 3B: Cross-folder deduplication.

    Compares input folder (from 3A cache) against output folder.
    Uses full resolution policy to determine which file to keep.

    Returns:
        Stage3Results with execution summary
    """
    # Phase 1: Load input cache (instant)
    input_files = self.cache.get_all_files('input')

    # Phase 2: Scan output folder
    detector = DuplicateDetector(...)
    output_groups = detector.detect_duplicates(self.output_folder, folder='output')

    # Phase 3: Find cross-folder duplicates
    cross_dupes = self._find_cross_folder_duplicates(input_files)

    # Phase 4: Apply resolution policy
    for dupe_group in cross_dupes:
        file_to_keep, files_to_delete = self.resolver.resolve_duplicates(
            dupe_group.files
        )
        # files_to_delete can be from either input or output!

    # Phase 5: Execute deletions
    if not self.dry_run:
        self._execute_deletions(files_to_delete)
```

## Example Scenarios

### Scenario 1: "keep" in Input Beats Newer Output
```
Input:  /input/keep/important/video.mp4
        - mtime: 2024-01-01
        - depth: 4
        - has "keep": Yes (folder)

Output: /output/video.mp4
        - mtime: 2025-11-01 (newer!)
        - depth: 2
        - has "keep": No

Resolution: DELETE from output
Reason: Priority 1 - Input has "keep" keyword
```

### Scenario 2: Deeper Output Beats Input
```
Input:  /input/video.mp4
        - mtime: 2025-01-01
        - depth: 2
        - has "keep": No

Output: /output/movies/action/thriller/video.mp4
        - mtime: 2024-06-15 (older!)
        - depth: 5
        - has "keep": No

Resolution: DELETE from input
Reason: Priority 2 - Output has deeper path (better organized)
```

### Scenario 3: Newer Input Beats Older Output
```
Input:  /input/downloads/video.mp4
        - mtime: 2025-11-01
        - depth: 3
        - has "keep": No

Output: /output/archive/video.mp4
        - mtime: 2024-06-15
        - depth: 3 (same depth)
        - has "keep": No

Resolution: DELETE from output
Reason: Priority 3 - Input has newer mtime
```

### Scenario 4: Output "keep" Beats Everything
```
Input:  /input/new_downloads/video.mp4
        - mtime: 2025-11-01 (newest!)
        - depth: 3
        - has "keep": No

Output: /output/keep/archive/video.mp4
        - mtime: 2024-01-01 (oldest!)
        - depth: 4
        - has "keep": Yes (folder)

Resolution: DELETE from input
Reason: Priority 1 - Output has "keep" keyword (beats newer mtime)
```

## Usage Examples

```bash
# Dry-run: Preview what would be deleted
file-organizer -if /input -of /output --stage 3b

# Execute: Actually delete duplicates based on resolution policy
file-organizer -if /input -of /output --stage 3b --execute

# Full pipeline: Stage 3A then 3B
file-organizer -if /input -of /output --stage 3a --execute
file-organizer -if /input -of /output --stage 3b --execute

# Or run all stages together (when all implemented)
file-organizer -if /input -of /output --execute
```

## Benefits

1. **Performance**: Reuses input cache from 3A (no re-scanning)
2. **Consistency**: Same resolution policy across all of Stage 3
3. **Flexibility**: Can delete from either folder based on policy
4. **Intelligent**: Respects "keep" keyword, organization, and recency
5. **Cache efficiency**: Output cache persists for future runs

## Design Rationale

### Why Not Always Delete from Input?

**Original approach** (simpler):
- Always keep output, always delete from input
- Assumes output is "canonical" destination

**Current approach** (flexible):
- Apply full resolution policy
- Output folder might have old/poorly organized files
- Input folder might have important "keep" files
- Resolution policy ensures best file is kept regardless of location

### Why Reuse Input Cache?

**Performance impact:**
- Stage 3A: Hash 10,000 input files = ~5 minutes
- Stage 3B without optimization: Re-hash 10,000 input files = ~5 minutes (wasted!)
- Stage 3B with optimization: Load cache = instant

**Cache hit rate:**
- First run 3A: 0% cache hits (must hash everything)
- Run 3B after 3A: 100% cache hits for input folder!

## Next Steps

1. Implement `run_stage3b()` method in `src/file_organizer/stage3.py`
2. Add cross-folder duplicate detection logic
3. Wire up CLI integration in `src/file_organizer/cli.py`
4. Test with real data
5. Document and commit

## Related Files

- `src/file_organizer/stage3.py` - Stage 3 orchestrator
- `src/file_organizer/duplicate_detector.py` - Duplicate detection engine
- `src/file_organizer/duplicate_resolver.py` - Resolution policy
- `src/file_organizer/hash_cache.py` - SQLite cache management
- `src/file_organizer/cli.py` - CLI integration
- `docs/requirements/stage3_requirements.md` - Full Stage 3 specification
