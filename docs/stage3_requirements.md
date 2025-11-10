# Stage 3: Duplicate Detection & Resolution - Detailed Requirements

## 📋 Implementation Status

**Status**: 📋 **PLANNING PHASE**  
**Expected Start**: After Stage 2 completion  
**Complexity**: High (Hash computation, memory management)

### Dependencies
- ✅ Stage 1: Filename Detoxification (Complete)
- ✅ Stage 2: Folder Structure Optimization (Complete)
- ⏳ Stage 3: This stage
- 📋 Stage 4: File Relocation (Depends on Stage 3)

---

## Overview

Stage 3 focuses on identifying and resolving duplicate files within the organized directory tree. This stage ensures that only unique files exist before relocation to the output folder (Stage 4), preventing wasted storage space and reducing file clutter.

### Core Objectives

1. **Duplicate Detection**: Identify files with identical content using cryptographic hashing
2. **Duplicate Resolution**: Apply configurable policies to keep the "best" version
3. **Performance**: Process 100k-500k files efficiently
4. **Memory Efficiency**: Use streaming and caching for large-scale operations
5. **Transparency**: Provide clear reporting on duplicates found and actions taken

---

## Technical Specifications

### Environment
- **Language**: Python 3.8 or higher
- **Platform**: Linux (kernel 6.8+)
- **Required Libraries**:
  - `hashlib`: For file hashing (standard library)
  - `pathlib`: For path operations (standard library)
  - `json`: For hash cache storage (standard library)
  - `concurrent.futures`: For parallel hashing (standard library, optional)

### Module Structure
```
src/file_organizer/
├── stage3.py              # Stage 3 orchestration
├── duplicate_detector.py  # Hash computation and duplicate finding
├── duplicate_resolver.py  # Duplicate resolution policies
├── hash_cache.py          # Persistent hash caching
└── config.py             # Configuration (extended for Stage 3)
```

---

## Command-Line Interface

### Arguments (Extended)
```bash
file-organizer -if /path/to/directory [OPTIONS]

# Stage 3 runs automatically after Stage 2, or can be run independently:
file-organizer -if /path/to/directory --stage 3 --execute
```

### Configuration Options

New options in `~/.file_organizer.yaml`:

```yaml
# Stage 3: Duplicate Detection
duplicate_detection:
  enabled: true                    # Run Stage 3 automatically
  hash_algorithm: sha256           # sha256, sha1, md5, blake2b
  resolution_policy: keep_newest   # keep_newest, keep_largest, keep_oldest, manual
  hash_cache_enabled: true         # Cache hashes for performance
  hash_cache_location: ~/.file_organizer_cache/hashes.json
  parallel_hashing: true           # Use multiple CPU cores
  max_workers: 8                   # Number of parallel hash workers
  min_file_size_for_dedup: 1024    # Only check files >= 1KB (skip tiny files)
  max_file_size_for_hash: null     # null = no limit, or size in bytes
```

---

## Functional Requirements

### FR3.1: Duplicate Detection via Content Hashing

**Description**: Identify duplicate files by computing cryptographic hashes of file contents.

**Implementation**:
1. Scan all files in the directory tree
2. Group files by size (optimization: different sizes can't be duplicates)
3. For each size group with 2+ files:
   - Compute hash of file contents
   - Group files with identical hashes
4. Report duplicate groups

**Hash Algorithm Selection**:
- **SHA-256** (Recommended, default)
  - Secure: Virtually no collision risk
  - Fast: ~300-500 MB/s on modern CPUs
  - Size: 32 bytes per hash
  - Use case: General purpose, default choice
  
- **SHA-1** (Faster alternative)
  - Speed: ~500-700 MB/s
  - Security: Deprecated for security, but fine for deduplication
  - Size: 20 bytes per hash
  - Use case: Performance-critical scenarios
  
- **MD5** (Fastest, least secure)
  - Speed: ~800-1000 MB/s
  - Security: Known collisions exist
  - Size: 16 bytes per hash
  - Use case: Legacy systems, maximum speed needed
  
- **BLAKE2b** (Modern alternative)
  - Speed: ~700-900 MB/s
  - Security: More secure than SHA-256
  - Size: 32 bytes per hash (configurable)
  - Use case: Modern systems, security priority

**Decision**: Default to SHA-256 for balance of security and performance.

### FR3.2: Size-Based Pre-Filtering

**Description**: Optimize duplicate detection by only comparing files of identical size.

**Rationale**:
- Files with different sizes cannot be duplicates
- Comparing file sizes is instant (metadata only)
- Dramatically reduces number of hashes to compute

**Implementation**:
```python
# Pseudo-code
size_groups = {}
for file in all_files:
    size = file.stat().st_size
    size_groups[size].append(file)

# Only hash files where size group has 2+ members
candidates = [group for group in size_groups.values() if len(group) >= 2]
```

**Performance Impact**:
- Reduces hashing workload by 80-99% in typical scenarios
- Example: 100k files, 95k unique sizes → only hash 5k files

### FR3.3: Incremental Hashing

**Description**: Hash files in chunks for memory efficiency and progress reporting.

**Implementation**:
- Read file in 64KB chunks
- Update hash incrementally
- Report progress every N files
- Support cancellation mid-hash

**Benefits**:
- Constant memory usage (regardless of file size)
- Can hash files larger than available RAM
- Allows accurate progress tracking
- Supports keyboard interrupt gracefully

### FR3.4: Hash Caching

**Description**: Persist computed hashes to avoid recomputation on subsequent runs.

**Cache Structure**:
```json
{
  "version": "1.0",
  "hash_algorithm": "sha256",
  "files": {
    "/path/to/file.txt": {
      "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 1024,
      "mtime": 1699000000.123456,
      "cached_at": 1699000100.789012
    }
  }
}
```

**Cache Invalidation**:
- File modified (mtime changed)
- File size changed
- File moved/renamed (path changed)
- Hash algorithm changed
- Cache file corrupted

**Performance Impact**:
- First run: Full hashing required
- Subsequent runs: Only hash new/modified files
- Speedup: 10-100x for mostly-unchanged directories

### FR3.5: Duplicate Resolution Policies

**Description**: Apply configurable policies to decide which duplicate to keep.

#### Policy 1: Keep Newest (Default)
- Keep file with most recent modification time
- Rationale: Newest version likely has latest edits
- Sort by `mtime`, keep first

#### Policy 2: Keep Largest
- Keep file with largest size
- Rationale: Larger file may be higher quality
- Sort by size descending, keep first

#### Policy 3: Keep Oldest
- Keep file with oldest modification time
- Rationale: Original copy may be more trustworthy
- Sort by `mtime`, keep last

#### Policy 4: Keep First (by path)
- Keep file that appears first alphabetically by path
- Rationale: Predictable, deterministic
- Sort by path, keep first

#### Policy 5: Manual Review
- Don't delete anything automatically
- Generate report of duplicates for user review
- Mark duplicates with special prefix: `_DUPLICATE_1_`, `_DUPLICATE_2_`
- User decides what to delete

**Configuration**:
```yaml
duplicate_detection:
  resolution_policy: keep_newest  # or keep_largest, keep_oldest, keep_first, manual
```

### FR3.6: Duplicate Reporting

**Description**: Generate comprehensive reports of duplicates found and actions taken.

**Report Format** (dry-run):
```
================================================================================
                         STAGE 3: DUPLICATE DETECTION
================================================================================

[SCAN PHASE]
Scanning directory: /path/to/input
Files scanned: 10,043
Size groups: 9,512 (unique sizes)
Duplicate candidates: 531 files in 158 size groups

[HASH PHASE]
Hashing 531 files...
Progress: [████████████████████] 531/531 files (100%) - 2.3s elapsed

[DUPLICATE DETECTION]
Duplicate groups found: 47
Total duplicate files: 94 (2 files per group avg)
Wasted space: 1.2 GB

[DUPLICATE RESOLUTION POLICY: keep_newest]
Files to keep: 47 (newest versions)
Files to delete: 47 (older versions)

[PREVIEW: First 10 Duplicate Groups]

Group 1 (2 files, 24.5 MB each):
  KEEP: /data/downloads/vacation_2023.jpg (2024-06-15 14:23:01) ← Newest
  DELETE: /data/old/vacation.jpg (2023-08-20 10:15:33)

Group 2 (3 files, 1.2 MB each):
  KEEP: /data/documents/report_final.pdf (2024-11-01 09:45:12) ← Newest
  DELETE: /data/documents/report_draft.pdf (2024-10-28 16:20:05)
  DELETE: /data/backup/report.pdf (2024-10-25 11:10:00)

... [8 more groups] ...

[SUMMARY]
Total space to reclaim: 1.2 GB
Files to delete: 47
Files to keep: 9,996

! DRY-RUN MODE: No files were modified
! Run with --execute to apply changes
```

**Report Format** (execute mode):
```
[EXECUTION]
Deleting duplicate files...
Progress: [████████████████████] 47/47 files deleted (100%)

✓ Deleted 47 duplicate files
✓ Reclaimed 1.2 GB of disk space
✓ 9,996 unique files remain

Operation completed successfully!
```

### FR3.7: Dry-Run Mode Integration

**Description**: Show exactly what would be deleted without actually deleting.

**Requirements**:
- Show all duplicate groups
- Indicate which files would be kept vs deleted
- Display space reclamation estimate
- Generate summary statistics
- Require `--execute` flag to actually delete

---

## Performance Requirements

### PR3.1: Hashing Performance Targets

| File Count | Total Size | Target Time | Target Speed |
|------------|------------|-------------|--------------|
| 10,000 | 10 GB | < 30s | ~350 MB/s |
| 100,000 | 100 GB | < 5 min | ~350 MB/s |
| 500,000 | 500 GB | < 25 min | ~350 MB/s |

**Assumptions**:
- SHA-256 hashing on modern CPU (~350-500 MB/s)
- SSD storage (fast sequential reads)
- Size-based pre-filtering reduces workload by ~90%
- Parallel hashing with 8 workers

**Actual Performance Will Vary Based On**:
- Storage speed (HDD vs SSD vs NVMe)
- CPU speed and core count
- File size distribution (many small vs few large files)
- Duplicate ratio (affects number of files to hash)

### PR3.2: Memory Usage

**Target**: < 500 MB for 500k files

**Memory Breakdown**:
```
File list (500k files × 200 bytes avg path):    100 MB
Size groups (500k entries × 16 bytes):           8 MB
Hash results (50k hashes × 32 bytes):            1.6 MB
Hash cache (500k entries × 100 bytes):          50 MB
Working memory (chunk buffers, etc.):           50 MB
---------------------------------------------------
Total estimated:                                ~210 MB
Safety margin (2x):                             ~420 MB
```

**Memory Management**:
- Stream file contents (don't load entire files into RAM)
- Use generators where possible
- Clear intermediate data structures after use
- Lazy-load hash cache

### PR3.3: Progress Reporting

**Requirements**:
- Show current file being hashed
- Display progress bar (files processed / total)
- Show time elapsed and estimated time remaining
- Update frequency: Every 1% or every 2 seconds (whichever is less frequent)
- Adaptive update frequency (scale with file count)

**Example Output**:
```
[HASH PHASE]
Hashing duplicates candidates...
Progress: [████████░░░░░░░░░░░░] 2,145/5,234 files (41%) - 12.3s elapsed, ~17s remaining
Current: /data/downloads/large_video_file.mp4 (234 MB)
Speed: 285 MB/s avg
```

---

## Edge Cases & Error Handling

### EC3.1: File Access Errors

**Scenarios**:
- Permission denied (can't read file)
- File locked by another process
- File deleted during processing
- I/O errors (bad sectors, network issues)

**Handling**:
- Skip file with warning
- Log error details
- Continue processing remaining files
- Report skipped files in summary

### EC3.2: Hash Collisions

**Scenario**: Two different files produce the same hash (extremely rare with SHA-256)

**Handling**:
- Consider this functionally impossible with SHA-256
- If using MD5: Add byte-by-byte comparison as fallback
- Log collision event (would be noteworthy!)

### EC3.3: Very Large Files

**Scenario**: Files > 10 GB (slow to hash)

**Handling**:
- Option to skip files above threshold (`max_file_size_for_hash`)
- Show progress within large file hashing
- Consider partial hashing (first/last N bytes) for quick differentiation
- Warn user about estimated time for large file hashing

### EC3.4: Insufficient Disk Space

**Scenario**: Deleting duplicates on same filesystem (space not immediately reclaimed)

**Handling**:
- Not a concern for in-place deletion (always frees space)
- Will be relevant for Stage 4 (relocation to output folder)

### EC3.5: Symbolic Links

**Scenario**: Symlinks that point to the same file

**Handling**:
- Symlinks already removed in Stage 1
- Not a concern for Stage 3

### EC3.6: Empty Files

**Scenario**: Multiple empty files (all have same hash)

**Handling**:
- All empty files are technically duplicates
- Apply resolution policy
- Consider special handling: Keep all empty files with different names

### EC3.7: Cache Corruption

**Scenario**: Hash cache file is corrupted or format changes

**Handling**:
- Detect corruption on load (JSON parse errors, missing fields)
- If corrupted: Delete cache, start fresh
- Log warning about cache invalidation
- Graceful degradation (works without cache, just slower)

---

## Integration with Other Stages

### Integration with Stage 1

**Inputs from Stage 1**:
- Sanitized filenames (ASCII, lowercase)
- No hidden files
- No symlinks
- Collision-free naming

**Benefits for Stage 3**:
- Predictable filenames for reporting
- No special character issues in paths
- Simplified file tracking

### Integration with Stage 2

**Inputs from Stage 2**:
- Flattened directory structure
- No empty folders
- Optimized folder organization

**Benefits for Stage 3**:
- Fewer folders to scan
- More efficient duplicate detection
- Cleaner file paths in reports

### Outputs to Stage 4

**What Stage 3 Provides**:
- Deduplicated file set
- Unique files only
- Hash cache (for collision detection in Stage 4)
- Disk space savings

**Benefits for Stage 4**:
- Smaller dataset to relocate
- No duplicate file copying
- Known hashes for output folder collision detection

---

## Configuration File Schema

### Extended Configuration

```yaml
# ~/.file_organizer.yaml

# Operation mode
default_mode: dry-run  # or 'execute'

# Stage 1: Filename Detoxification
preserve_timestamps: true

# Stage 2: Folder Structure Optimization
flatten_threshold: 5

# Stage 3: Duplicate Detection (NEW)
duplicate_detection:
  # Enable/disable Stage 3
  enabled: true
  
  # Hash algorithm: sha256, sha1, md5, blake2b
  hash_algorithm: sha256
  
  # Resolution policy: keep_newest, keep_largest, keep_oldest, keep_first, manual
  resolution_policy: keep_newest
  
  # Hash caching
  hash_cache_enabled: true
  hash_cache_location: ~/.file_organizer_cache/hashes.json
  
  # Performance tuning
  parallel_hashing: true
  max_workers: 8  # Number of parallel hash workers (null = auto-detect CPU count)
  
  # File size filters
  min_file_size_for_dedup: 1024  # Only check files >= 1KB (skip tiny files)
  max_file_size_for_hash: null   # null = no limit, or size in bytes (e.g., 10737418240 for 10GB)
  
  # Progress reporting
  progress_update_interval: auto  # auto, or number of files between updates
  
  # Safety limits
  max_duplicates_to_delete: null  # null = no limit, or maximum number for safety

# Performance tuning (global)
max_errors_logged: 1000
scan_progress_interval: 10000
```

---

## Test Requirements

### Unit Tests

1. **test_hash_computation.py**
   - Verify hash computation for known files
   - Test incremental hashing
   - Validate multiple hash algorithms
   - Edge case: Empty file
   - Edge case: Very large file (mock)

2. **test_size_grouping.py**
   - Group files by size correctly
   - Handle edge cases (0 bytes, identical sizes)
   - Performance: Large number of files

3. **test_duplicate_detection.py**
   - Identify duplicates correctly
   - Handle no duplicates scenario
   - Handle all files identical scenario
   - Multiple duplicate groups

4. **test_resolution_policies.py**
   - Keep newest: Verify mtime comparison
   - Keep largest: Verify size comparison
   - Keep oldest: Verify mtime comparison (reverse)
   - Keep first: Verify path sorting
   - Manual: Verify no deletion, only marking

5. **test_hash_cache.py**
   - Save and load cache correctly
   - Invalidate on mtime change
   - Invalidate on size change
   - Invalidate on algorithm change
   - Handle corrupted cache gracefully

### Integration Tests

1. **test_stage3_small_dataset.py**
   - Small dataset (100 files, 20 duplicates)
   - Verify correct detection and resolution
   - Check dry-run accuracy
   - Verify execute mode deletion

2. **test_stage3_medium_dataset.py**
   - Medium dataset (10k files, 500 duplicates)
   - Performance validation
   - Memory usage monitoring

3. **test_stage3_large_dataset.py**
   - Large dataset (100k files, 5k duplicates)
   - Performance at scale
   - Cache effectiveness

4. **test_stage3_integration.py**
   - Run full pipeline: Stage 1 → Stage 2 → Stage 3
   - Verify seamless integration
   - Check combined statistics

### Performance Tests

1. **benchmark_hashing_speed.py**
   - Measure hashing throughput (MB/s)
   - Compare hash algorithms
   - Parallel vs sequential performance

2. **benchmark_memory_usage.py**
   - Monitor peak memory usage
   - Verify memory stays within limits
   - Test with 500k files

3. **benchmark_cache_performance.py**
   - Compare first run (no cache) vs subsequent run (with cache)
   - Measure cache load/save time
   - Verify speedup

### Test Data Requirements

**Generate test data with known duplicates**:

```python
# tools/generate_test_data_with_duplicates.py

# Create dataset:
# - 10,000 unique files
# - 500 duplicate groups (2-3 files each)
# - Various file sizes (1KB to 100MB)
# - Different modification times
# - Nested folder structure

def generate_duplicate_dataset(output_dir, num_unique, num_dup_groups):
    # Create unique files
    for i in range(num_unique):
        create_random_file(f"unique_{i}.txt", random_size())
    
    # Create duplicate groups
    for i in range(num_dup_groups):
        original = create_random_file(f"original_{i}.dat", random_size())
        # Create 2-3 duplicates with different names/locations
        for j in range(random.randint(2, 3)):
            copy_file(original, f"duplicate_{i}_{j}.dat")
            set_random_mtime(f"duplicate_{i}_{j}.dat")
```

---

## Success Criteria

### Functional Requirements
1. ✓ Correctly identifies all duplicate files (100% accuracy)
2. ✓ No false positives (different files never marked as duplicates)
3. ✓ Resolution policies work as specified
4. ✓ Dry-run preview matches execute mode actions
5. ✓ Hash cache improves subsequent run performance
6. ✓ Integration with Stages 1-2 seamless

### Performance Requirements
1. ✓ Hashes 100k files in < 5 minutes (on target hardware)
2. ✓ Memory usage < 500 MB for 500k files
3. ✓ Cache provides > 10x speedup on unchanged data
4. ✓ Parallel hashing provides > 4x speedup (on 8+ cores)

### Reliability Requirements
1. ✓ Handles file access errors gracefully
2. ✓ Survives keyboard interrupt without corruption
3. ✓ Works with corrupted/missing cache file
4. ✓ No data loss (dry-run default, execute requires explicit flag)

---

## Implementation Phases

### Phase 1: Core Duplicate Detection (Week 1-2)
- Implement file scanning
- Implement size-based grouping
- Implement SHA-256 hashing
- Implement duplicate identification
- Basic reporting

### Phase 2: Resolution Policies (Week 2-3)
- Implement all 5 resolution policies
- Add dry-run mode
- Add execute mode with deletion
- Comprehensive reporting

### Phase 3: Hash Caching (Week 3-4)
- Implement hash cache persistence
- Add cache invalidation logic
- Performance optimization
- Cache corruption handling

### Phase 4: Performance Optimization (Week 4-5)
- Implement parallel hashing
- Optimize memory usage
- Add progress reporting
- Performance benchmarking

### Phase 5: Testing & Integration (Week 5-6)
- Unit tests
- Integration tests
- Performance tests
- Documentation

---

## Open Questions / Decisions Needed

1. **Hash Algorithm Default**
   - Recommendation: SHA-256 (secure, fast enough)
   - Alternative: SHA-1 or BLAKE2b for speed
   - **Decision**: SHA-256 default, configurable

2. **Resolution Policy Default**
   - Recommendation: keep_newest (most intuitive)
   - Alternative: manual (safest)
   - **Decision**: keep_newest default, configurable

3. **Small File Threshold**
   - Files < 1KB: Skip duplicate detection? (minimal space savings)
   - **Decision**: Configurable, default 1KB

4. **Parallel Hashing**
   - Enable by default? (faster but more CPU intensive)
   - **Decision**: Enable by default, configurable

5. **Cache Location**
   - ~/.file_organizer_cache/ (hidden in home)
   - ~/.cache/file_organizer/ (XDG standard)
   - **Decision**: ~/.file_organizer_cache/ for simplicity

6. **Duplicate Groups with 3+ Files**
   - Keep only 1 file (delete all but one)
   - Keep 1 file per "version" (more complex logic)
   - **Decision**: Keep only 1 file based on policy

---

## Security Considerations

### S3.1: Hash Algorithm Security

**Not a security context**: Duplicate detection doesn't require cryptographic security
- MD5 collisions are theoretical concern but not practical risk
- SHA-256 provides comfortable margin of safety
- Focus on performance over paranoia

### S3.2: Cache File Security

**Concern**: Cache file contains file paths and metadata

**Mitigation**:
- Store in user home directory (user-readable only)
- Set restrictive permissions (600)
- No sensitive data (paths and hashes only)
- User can delete cache anytime without breaking functionality

### S3.3: Path Traversal

**Concern**: Malicious paths in cache could cause issues

**Mitigation**:
- Validate all paths before deletion
- Stay within input folder boundaries
- Use pathlib for safe path manipulation
- Never follow symlinks (already removed in Stage 1)

---

## Documentation Requirements

### User Documentation

1. **Stage 3 Usage Guide**
   - How duplicate detection works
   - Explanation of resolution policies
   - How to interpret duplicate reports
   - When to use manual review mode

2. **Configuration Guide**
   - All Stage 3 configuration options
   - Performance tuning recommendations
   - Cache management

3. **FAQ**
   - "How are duplicates detected?"
   - "Which hash algorithm should I use?"
   - "What happens to the files I don't keep?"
   - "Can I review duplicates before deletion?"
   - "Will this work on my external drive?"

### Developer Documentation

1. **Stage 3 Architecture**
   - Module breakdown
   - Class diagram
   - Data flow

2. **Hash Cache Format**
   - JSON schema
   - Versioning strategy
   - Migration path

3. **Adding New Resolution Policies**
   - How to implement new policy
   - Testing requirements

---

## Future Enhancements (Post-MVP)

1. **Smart Hashing**
   - Hash only first/last 1MB for quick differentiation
   - Full hash only if quick hash matches
   - Massive speedup for large files

2. **Partial File Comparison**
   - For very large files, compare size + first/last bytes
   - Trade accuracy for speed (user opt-in)

3. **Similarity Detection**
   - Find near-duplicates (similar but not identical)
   - Perceptual hashing for images
   - Edit distance for text files

4. **Interactive Duplicate Review**
   - Terminal UI for reviewing duplicate groups
   - Preview files before deletion
   - Manual selection of which to keep

5. **Duplicate Statistics**
   - Most duplicated files
   - Space savings by file type
   - Duplicate patterns (e.g., common backup patterns)

6. **Cloud Storage Integration**
   - Check cloud storage for duplicates
   - Avoid uploading files already in cloud

---

## Conclusion

Stage 3 (Duplicate Detection & Resolution) is a critical component for efficient file organization at scale. By identifying and removing duplicate files before relocation (Stage 4), we:

- **Save disk space**: Reclaim gigabytes of wasted storage
- **Reduce clutter**: Fewer files to manage
- **Improve performance**: Less data to copy in Stage 4
- **Increase clarity**: No confusion about which file is "the right one"

**Estimated Development Time**: 5-6 weeks
**Lines of Code**: ~1,000-1,500 lines
**Test Coverage Target**: > 90%

**Ready for implementation**: After Stage 2 completion and requirements approval.

---

**Document Version**: 1.0  
**Last Updated**: November 10, 2025  
**Status**: Requirements Complete, Ready for Review

