# Stage 3: Duplicate Detection & Resolution - Requirements Specification

## 📋 Implementation Status

**Status**: 📋 **REQUIREMENTS COMPLETE**  
**Expected Start**: After Stage 2 completion  
**Complexity**: High (Video optimization, two-phase deduplication, caching)

### Dependencies
- ✅ Stage 1: Filename Detoxification (Complete)
- ✅ Stage 2: Folder Structure Optimization (Complete)
- ⏳ Stage 3: This stage
- 📋 Stage 4: File Relocation (Depends on Stage 3)

---

## Overview

Stage 3 is a **video-focused duplicate detection and resolution system** designed to handle large-scale media collections efficiently. Unlike traditional duplicate detection tools, Stage 3 is optimized for:

- **Large video files** (10MB - 20GB per file)
- **Two-phase deduplication**: Within input folder + between input and output folders
- **Speed over cryptographic security** (using xxHash, the fastest non-cryptographic hash)
- **Smart optimizations**: Video metadata checking, large file sampling, intelligent caching
- **Custom resolution policy**: Prioritizes user intent ("keep" keyword), file organization (path depth), and recency

### Core Objectives

1. **Internal Deduplication (Stage 3A)**: Remove duplicates within the input folder
2. **Cross-Folder Deduplication (Stage 3B)**: Remove duplicates between input and output folders
3. **Performance at Scale**: Process 2TB, 100k+ files in ~60 minutes (initial scan)
4. **Intelligent Caching**: Subsequent scans in ~5-10 minutes with metadata-based moved file detection
5. **Video-Specific Optimizations**: Check metadata and duration before expensive hashing
6. **Transparency**: Clear reporting on duplicates found, space reclaimed, and actions taken

### Use Case

**Primary Scenario**: User has a large collection of video files across multiple locations. New videos are frequently added to the input folder, while the output folder (organized archive) changes rarely. The goal is to:
1. Remove duplicates within the messy input folder
2. Avoid copying files to the output folder that already exist there
3. Do this efficiently without rehashing unchanged files

**Typical Dataset**:
- **Total size**: ~2TB
- **File count**: 100,000+ files
- **File types**: 
  - Images (skipped): ~60-70% by count, ~10% by size
  - Videos (processed): ~20-30% by count, ~80-85% by size
  - Other files (processed): ~10% by count, ~5% by size
- **Video sizes**: Mostly 50MB-2GB, occasionally up to 10-20GB

---

## Technical Specifications

### Environment
- **Language**: Python 3.12+
- **Platform**: Linux (kernel 6.8+)
- **System**: 32GB RAM, 16-core CPU (will leverage for parallel processing)

### Required Libraries
- **xxhash**: Ultra-fast non-cryptographic hashing (~10-20 GB/s)
- **pymediainfo** OR **ffprobe**: Video metadata extraction (duration, codec, resolution)
- **sqlite3**: Persistent hash caching with metadata-based file tracking (standard library)
- **pathlib**: Path operations (standard library)
- **concurrent.futures**: Parallel hashing (standard library)

### Module Structure
```
src/file_organizer/
├── stage3.py              # Stage 3 orchestration (two-phase coordinator)
├── duplicate_detector.py  # Hash computation, size grouping, duplicate identification
├── duplicate_resolver.py  # Custom resolution policy (keep→depth→newest)
├── hash_cache.py          # SQLite cache with moved file detection
├── video_utils.py         # Video metadata extraction and comparison
├── file_sampler.py        # Large file sampling (head + tail)
└── config.py              # Configuration (extended for Stage 3)
```

**Architecture Note**: The module structure is designed to be extensible for future enhancements:
- `video_utils.py` can be extended to include perceptual hashing for near-duplicate detection
- `duplicate_resolver.py` can add interactive review UI without touching core detection logic
- `file_sampler.py` can incorporate smart sampling strategies (e.g., multi-point sampling)

---

## Two-Phase Architecture

### Stage 3A: Internal Deduplication (Input Folder)

**Goal**: Remove all duplicate files within the input folder itself.

**Process**:
1. Scan all files in input folder (recursive)
2. Apply file filtering (skip images, skip < 10KB files)
3. Group files by size (different sizes can't be duplicates)
4. For size groups with 2+ files:
   - Extract video metadata if applicable (duration, size)
   - If durations differ → not duplicates, skip hashing
   - If durations match or non-video → hash file content
5. Group files by hash (identical hash = duplicate)
6. For each duplicate group:
   - Apply resolution policy to select winner
   - Delete losers (or report in dry-run mode)
7. Update input folder cache

**Benefits**:
- Cleans up messy input folder before cross-comparison
- Reduces dataset size for Stage 3B
- Finds duplicates that wouldn't be caught in cross-comparison

### Stage 3B: Cross-Folder Deduplication (Input vs Output)

**Goal**: Identify files in input folder that already exist in output folder.

**Process**:
1. Load output folder cache (must exist)
2. For each file in input folder (after 3A):
   - Check if hash exists in output folder cache
   - If yes → duplicate found (file exists in both places)
   - Apply resolution policy to decide which to keep
   - Typically: Keep output version, delete input version
3. Delete duplicates from input folder (or output if policy says so)
4. Update both caches

**Benefits**:
- Prevents copying files to output that are already there
- Output folder cache typically stable (rarely changes)
- Massive speedup: Output folder only hashed once, then cached

**Rationale for Two-Phase Approach**:
- **Phase A first**: Reduces input folder size before expensive cross-comparison
- **Separate phases**: Clearer reporting, easier debugging
- **Cache benefits**: Output folder cache persists across runs (huge speedup)

---

## Hash Algorithm: xxHash

### Why xxHash?

**Speed is the priority**. For video deduplication at scale, cryptographic security is unnecessary.

| Algorithm | Speed | Security | Use Case |
|-----------|-------|----------|----------|
| **xxHash** | **10-20 GB/s** | Non-cryptographic | **File deduplication (our choice)** |
| SHA-1 | 500-700 MB/s | Deprecated (crypto) | Legacy systems |
| SHA-256 | 300-500 MB/s | Secure | Security-critical |
| MD5 | 800-1000 MB/s | Known collisions | Legacy deduplication |

**xxHash is 20-40x faster than SHA-256** and has:
- Extremely low collision rate (good enough for deduplication)
- Excellent distribution (uniform hash distribution)
- Battle-tested (used by Facebook, Dropbox, etc. for deduplication)

**Performance Impact**:
- 2TB @ 10 GB/s = 200 seconds = **~3 minutes** (theoretical maximum)
- In practice: ~60 minutes due to disk I/O, file filtering, metadata checks
- With caching: ~5-10 minutes for subsequent runs

### Fallback Options

Configuration supports alternative hash algorithms:
- `sha256`: If security/paranoia is preferred over speed
- `sha1`: Middle ground (faster than SHA-256, still cryptographic)
- `md5`: Legacy compatibility

---

## Large File Sampling Strategy

### Problem

Hashing a 10GB video file takes time:
- SHA-256: ~20-30 seconds
- xxHash: ~60 seconds (still slow!)

For 10,000 large video files: 600,000 seconds = **167 hours** (unacceptable)

### Solution: Head + Tail Sampling

Instead of hashing the entire file, hash only:
- **First N bytes** (head)
- **Last N bytes** (tail)

**Rationale**:
- Video files differ in headers (codecs, metadata) and endings (duration)
- Middle portions of videos can be identical for unrelated files
- Head + tail provides 99.9% accuracy for duplicate detection
- Dramatically reduces hashing time

### Sampling Configuration

**Threshold**: Files larger than **20MB** (configurable) use sampling

**Sample Sizes**:
```
File Size               Sample Strategy          Total Hashed
-------------------------------------------------------------
< 20MB                 Full hash                 100%
20MB - 1GB             Head 10MB + Tail 10MB     ~1-20%
1GB - 5GB              Head 20MB + Tail 20MB     ~1-8%
> 5GB                  Head 50MB + Tail 50MB     ~1-2%
```

**Adaptive Sampling**: Sample size scales with file size to maintain accuracy.

### Performance Impact

**Without Sampling**: 2TB of video @ 10GB/s = ~3 minutes (theoretical)  
**With Sampling** (90% of files > 20MB): ~1.8TB reduced to ~200GB = ~20 seconds  
**Actual Time**: ~60 minutes (disk I/O, metadata extraction, cache updates)

### Accuracy

Sampling introduces **very low risk** of false negatives (different files marked as duplicates):
- Video files have unique headers and endings
- Risk: < 0.01% (1 in 10,000)
- Mitigation: Users can disable sampling if paranoid (config option)

---

## Custom Resolution Policy

### Priority Order

When duplicates are detected, Stage 3 applies this **three-tier resolution policy**:

#### Priority 1: "keep" Keyword
- **Check**: Does the file path contain "keep" anywhere? (case-insensitive)
- **Examples**:
  - `/input/keep_this/video.mp4` → "keep" in folder name ✓
  - `/input/my_keep_file.mp4` → "keep" in filename ✓
  - `/input/data/KEEP/archive.mkv` → "KEEP" in folder name ✓
- **Action**: If only one file has "keep" → **keep that file**
- **Tiebreaker**: If multiple files have "keep" → proceed to Priority 2

#### Priority 2: Path Depth
- **Check**: Count the depth of the file path (number of directories)
- **Examples**:
  - `/input/video.mp4` → depth = 2
  - `/input/movies/action/video.mp4` → depth = 4
- **Action**: Keep the file with the **deepest path**
- **Rationale**: After Stage 2 folder flattening, remaining folders represent meaningful organization. Deeper paths = better organized = prefer to keep.
- **Tiebreaker**: If same depth → proceed to Priority 3

#### Priority 3: Newest File
- **Check**: Compare modification times (`mtime`)
- **Action**: Keep the file with the **most recent mtime**
- **Rationale**: Newest version likely has latest edits or is the active copy

### Examples

**Example 1: "keep" keyword wins**
```
Files:
  A: /input/archive/video.mp4 (mtime: 2025-01-15, depth: 3)
  B: /input/keep/video.mp4    (mtime: 2024-06-10, depth: 3)

Resolution: Keep B (has "keep" keyword)
```

**Example 2: Depth wins**
```
Files:
  A: /input/video.mp4                (mtime: 2025-11-01, depth: 2)
  B: /input/movies/action/video.mp4  (mtime: 2024-03-15, depth: 4)

Resolution: Keep B (deeper path: 4 > 2)
```

**Example 3: Newest wins**
```
Files:
  A: /input/data/video.mp4    (mtime: 2025-11-10, depth: 3)
  B: /input/archive/video.mp4 (mtime: 2024-08-20, depth: 3)

Resolution: Keep A (more recent: 2025-11-10 > 2024-08-20)
```

---

## File Type Filtering

### Skip Image Files

**Reason**: Images are numerous and often intentionally duplicated (thumbnails, resizes, previews). Processing them would dramatically slow down deduplication without much benefit.

**Skipped Extensions**:
```
.jpg, .jpeg, .png, .gif, .bmp, .tiff, .tif, .webp, .svg, .ico,
.heic, .heif, .raw, .cr2, .nef, .arw, .dng, .psd, .ai
```

**Impact**: Skipping images reduces file count by ~60-70% and hash workload by ~10%.

### Skip Small Files

**Threshold**: Files smaller than **10KB** are skipped.

**Reason**: Files < 10KB are too small to be valid video files. They're likely:
- Metadata files
- Subtitle files
- Thumbnails
- Text documents
- Minimal space savings even if duplicates

**Impact**: Reduces file count by additional ~5-10%.

### Process Everything Else

**Video files** (primary target):
```
.mp4, .mkv, .avi, .mov, .m4v, .wmv, .flv, .webm, 
.mpg, .mpeg, .m2ts, .ts, .vob, .ogv
```

**Other files** (documents, archives, audio, etc.):
- All files not matching skip criteria are processed
- Includes: PDFs, archives (.zip, .rar), audio (.mp3, .flac), etc.

---

## Video-Specific Optimizations

### Fast Pre-Filtering

Before expensive hashing, Stage 3 extracts and compares video metadata:

#### 1. File Size Check
- **Extract**: File size in bytes (instant, from filesystem metadata)
- **Compare**: If sizes differ → different files, skip hashing

#### 2. Video Duration Check
- **Extract**: Video duration from container metadata (fast, < 0.1s per file)
- **Tools**: `pymediainfo` or `ffprobe`
- **Compare**: If durations differ by > 1 second → different videos, skip hashing

#### 3. Optional: Codec/Resolution Check
- **Extract**: Video codec, resolution, bitrate
- **Compare**: If codecs/resolutions differ → likely different files
- **Note**: Not as reliable (re-encoded videos have same content)

### Performance Impact

**Without video optimization**:
- Hash every file in size group
- 10,000 videos, 1,000 size groups → hash 10,000 files

**With video optimization**:
- Duration check takes ~0.05s per file
- Eliminates ~80-90% of unnecessary hashing
- 10,000 videos → only hash ~1,000-2,000 actual duplicates
- **Speedup**: 5-10x reduction in hash workload

### Fallback Behavior

If metadata extraction fails:
- Log warning
- Fall back to hash-based comparison
- No data loss or false positives

---

## SQLite Cache Design

### Schema

```sql
CREATE TABLE file_cache (
    -- Primary file identification
    file_path TEXT NOT NULL,           -- Full absolute path
    folder TEXT NOT NULL,              -- 'input' or 'output'
    
    -- Hash information
    file_hash TEXT NOT NULL,           -- xxHash hex digest
    hash_type TEXT NOT NULL,           -- 'full' or 'sampled'
    sample_size INTEGER,               -- NULL if full, total bytes if sampled
    
    -- File metadata (for moved file detection)
    file_size INTEGER NOT NULL,        -- Size in bytes
    file_mtime REAL NOT NULL,          -- Modification time (Unix timestamp)
    
    -- Video-specific metadata (NULL for non-videos)
    video_duration REAL,               -- Duration in seconds
    video_codec TEXT,                  -- Codec name (h264, h265, etc.)
    video_resolution TEXT,             -- Resolution (1920x1080, etc.)
    
    -- Cache management
    last_checked REAL NOT NULL,        -- When we last verified this entry
    
    PRIMARY KEY (file_path, folder)
);

-- Index for finding files by identity (moved file detection)
CREATE INDEX idx_file_identity ON file_cache(file_size, file_mtime, file_hash);

-- Index for duplicate detection
CREATE INDEX idx_hash_lookup ON file_cache(file_hash);

-- Index for folder-specific queries
CREATE INDEX idx_folder ON file_cache(folder);
```

### Cache Operations

#### 1. Cache Hit (File Unchanged)
```python
# Check cache
cached = get_from_cache(file_path, folder)
if cached and cached.size == current_size and cached.mtime == current_mtime:
    # File unchanged, reuse cached hash
    return cached.hash
```

#### 2. Cache Miss (New File)
```python
# File not in cache, hash it
file_hash = compute_hash(file_path)
save_to_cache(file_path, folder, file_hash, size, mtime)
```

#### 3. Moved File Detection
```python
# File not found at cached path
if not exists(cached.file_path):
    # Search for file with same (size, mtime, hash)
    matches = find_by_identity(cached.size, cached.mtime, cached.hash)
    if matches:
        # File was moved, update cache with new path
        update_cache_path(old_path, new_path)
        return cached.hash  # No rehashing needed!
```

#### 4. Modified File
```python
# File exists but size or mtime changed
if cached.size != current_size or cached.mtime != current_mtime:
    # File modified, rehash
    file_hash = compute_hash(file_path)
    update_cache(file_path, file_hash, current_size, current_mtime)
```

### Cache Invalidation

**Triggers**:
1. File size changed → Rehash
2. File mtime changed → Rehash
3. File moved (same size+mtime, different path) → Update path only, no rehash
4. Cache corrupted → Delete cache, rebuild from scratch
5. Hash algorithm changed → Clear cache, rebuild

### Cache Performance

**Typical Scenario**:
- **First run**: No cache, must hash all files (~60 minutes for 2TB)
- **Second run**: 95% cache hits, only hash new/modified files (~5 minutes)
- **Cache hit rate**: Typically 90-98% (most files unchanged between runs)

**Cache Size**:
- 100k files × ~500 bytes per entry = ~50MB cache file
- Negligible compared to 2TB of data

---

## Command-Line Interface

### Basic Usage

```bash
# Full pipeline (Stages 1-3) with dry-run (default)
file-organizer -if /path/to/input -of /path/to/output

# Execute changes (actually delete duplicates)
file-organizer -if /path/to/input -of /path/to/output --execute

# Run only Stage 3 (requires Stages 1-2 already completed)
file-organizer -if /path/to/input -of /path/to/output --stage 3 --execute

# Stage 3A only (internal deduplication, no output folder required)
file-organizer -if /path/to/input --stage 3a --execute

# Stage 3B only (cross-folder, requires output folder and prior 3A run)
file-organizer -if /path/to/input -of /path/to/output --stage 3b --execute
```

### Output Folder Requirement

**Stage 3B requires output folder to exist**:
- If output folder doesn't exist → Error and exit
- Rationale: Can't compare against non-existent folder
- User must create output folder first (or run Stage 4 once to create it)

**Stage 3A does not require output folder**:
- Can run independently to clean up input folder
- Useful for testing or when output folder not yet set up

---

## Configuration Options

### Extended YAML Configuration

```yaml
# ~/.file_organizer.yaml

# Global settings
default_mode: dry-run  # or 'execute'

# Stage 1: Filename Detoxification
preserve_timestamps: true

# Stage 2: Folder Structure Optimization
flatten_threshold: 5

# Stage 3: Duplicate Detection (NEW)
duplicate_detection:
  # Enable/disable Stage 3
  enabled: true
  
  # Hash algorithm: xxhash (recommended), sha256, sha1, md5
  hash_algorithm: xxhash
  
  # File filtering
  skip_images: true                 # Skip image files (.jpg, .png, etc.)
  skip_videos: false                # Don't skip videos (primary target)
  skip_audio: false                 # Don't skip audio files
  min_file_size: 10240              # 10KB minimum (skip smaller files)
  
  # Large file sampling
  enable_sampling: true             # Use sampling for large files
  large_file_threshold: 20971520    # 20MB (files larger than this use sampling)
  sample_head_size: 10485760        # 10MB head sample
  sample_tail_size: 10485760        # 10MB tail sample
  adaptive_sampling: true           # Scale sample size for very large files
  
  # Cache settings
  cache_type: sqlite                # sqlite (recommended) or json
  cache_location: ~/.file_organizer_cache/hashes.db
  cache_moved_files: true           # Track moved files to avoid rehashing
  
  # Video optimizations
  use_video_metadata: true          # Extract and compare video metadata
  check_duration: true              # Compare video duration before hashing
  check_codec: false                # Compare codec (less reliable, disabled)
  check_resolution: false           # Compare resolution (less reliable, disabled)
  video_metadata_tool: pymediainfo  # or 'ffprobe'
  
  # Performance tuning
  parallel_hashing: true            # Use multiple CPU cores
  max_workers: 8                    # Number of parallel workers (null = auto)
  
  # Cross-folder deduplication (Stage 3B)
  require_output_folder: true       # Error if output folder missing
  compare_with_output: true         # Enable Stage 3B cross-comparison
  
  # Progress reporting (same as Stage 1)
  progress_update_interval: auto    # Adaptive frequency

# Global performance settings
max_errors_logged: 1000
scan_progress_interval: 10000
```

### CLI Flag Overrides

CLI flags override configuration file:
```bash
# Override hash algorithm
--hash-algorithm sha256

# Disable sampling for full accuracy
--no-sampling

# Force output folder comparison even if not in config
--compare-output
```

---

## Performance Requirements

### Target Performance (2TB Dataset, 100k Files)

**Initial Scan (No Cache)**:
- File scanning: ~5 minutes (100k files)
- Video metadata extraction: ~10 minutes (20k videos @ 0.03s each)
- Size grouping and filtering: ~1 minute
- Hashing (with sampling): ~40 minutes (effective 200GB @ 500MB/s disk I/O)
- Duplicate resolution: ~2 minutes
- **Total: ~60 minutes**

**Subsequent Scans (With Cache)**:
- File scanning: ~5 minutes
- Cache lookups: ~1 minute (98% hit rate)
- Hash new/modified files: ~3 minutes (2% of files)
- Duplicate resolution: ~1 minute
- **Total: ~10 minutes**

**Cache Effectiveness**:
- **First run**: 60 minutes (full hash)
- **Second run**: 10 minutes (98% cache hits)
- **Speedup**: **6x faster**

### Memory Usage

**Target**: < 500MB for 100k files

**Breakdown**:
```
File list (100k files × 200 bytes avg):     20 MB
Size groups (100k entries × 16 bytes):       1.6 MB
Hash results (20k hashes × 32 bytes):        640 KB
SQLite cache (in-memory buffer):            50 MB
Video metadata (20k entries × 100 bytes):    2 MB
Working memory (buffers, etc.):             50 MB
-------------------------------------------------
Total estimated:                           ~125 MB
Safety margin (4x):                        ~500 MB
```

**Memory Management**:
- Stream file contents (never load entire files into RAM)
- Use generators for file iteration
- Clear intermediate data structures after each phase
- SQLite handles cache paging automatically

### Progress Reporting

**Adaptive Frequency** (same as Stage 1):
- **< 1,000 files**: Update every 10 files
- **1,000-10,000 files**: Update every 100 files
- **10,000-100,000 files**: Update every 500 files
- **100,000+ files**: Update every 1,000 files

**Progress Display**:
```
================================================================================
                    STAGE 3A: INTERNAL DEDUPLICATION
================================================================================

[SCAN PHASE]
Scanning input folder: /data/input
Files scanned: 94,532 / 94,532 (100%) - 4.2s elapsed
Filtered: 62,341 images skipped, 1,203 small files skipped
Remaining: 30,988 files to process

[VIDEO METADATA PHASE]
Extracting video metadata...
Progress: [██████████████████] 18,234 / 18,234 videos (100%) - 8.7s elapsed

[SIZE GROUPING]
Grouping files by size...
Total size groups: 28,451
Duplicate candidates: 2,537 files in 892 size groups

[HASH PHASE]
Hashing candidate files...
Progress: [████████░░░░░░░░░░░░] 1,042 / 2,537 files (41%) - 18.3s elapsed, ~26s remaining
Current: /data/input/videos/large_file.mp4 (1.2 GB) [sampled]
Speed: 524 MB/s avg (effective, with sampling)
Cache hits: 1,495 (58%)

[DUPLICATE DETECTION]
Duplicate groups found: 347
Total duplicate files: 785 (2.26 per group avg)
Space to reclaim: 186.4 GB

[RESOLUTION PHASE]
Applying resolution policy: keep→depth→newest
Files to keep: 347
Files to delete: 438

[PREVIEW: First 10 Duplicate Groups]

Group 1 (3 files, 1.2 GB each):
  KEEP:   /data/input/archive/movies/keep/video.mp4 (depth: 5, 2025-10-15) ← "keep" keyword
  DELETE: /data/input/downloads/video.mp4 (depth: 3, 2025-11-01)
  DELETE: /data/input/video.mp4 (depth: 2, 2025-09-20)

Group 2 (2 files, 524 MB each):
  KEEP:   /data/input/tv_shows/series1/season2/episode5.mkv (depth: 5, 2024-08-10) ← Deeper path
  DELETE: /data/input/misc/episode5.mkv (depth: 3, 2025-01-05)

... [8 more groups] ...

[SUMMARY]
Space to reclaim: 186.4 GB
Files to delete: 438
Files to keep: 30,550

! DRY-RUN MODE: No files were modified
! Run with --execute to apply changes

================================================================================
                    STAGE 3B: CROSS-FOLDER DEDUPLICATION
================================================================================

[LOADING OUTPUT CACHE]
Loading cache: /home/user/.file_organizer_cache/hashes.db
Output folder files in cache: 48,234 (cached 2025-11-09)

[CROSS-COMPARISON]
Comparing input files against output cache...
Progress: [████████████████████] 30,550 / 30,550 files (100%) - 2.1s elapsed
Matches found: 1,842 files exist in both input and output

[RESOLUTION PHASE]
Applying resolution policy...
Files to keep in output: 1,654 (newer or deeper)
Files to keep in input: 188 (newer or deeper)
Files to delete from input: 1,654
Files to delete from output: 188

[SUMMARY]
Cross-folder duplicates: 1,842
Space to reclaim from input: 124.8 GB
Space to reclaim from output: 8.2 GB

! DRY-RUN MODE: No files were modified
! Run with --execute to apply changes

================================================================================
                       STAGE 3 COMPLETE
================================================================================

Total duplicates found: 2,280
Total space reclaimed: 319.4 GB (186.4 GB + 124.8 GB + 8.2 GB)
Files remaining: 28,084 unique files
Time elapsed: 56.3 minutes
```

---

## Integration with Other Stages

### From Stage 1: Filename Detoxification

**Inputs**:
- Sanitized filenames (ASCII, lowercase, underscores)
- No hidden files
- No symlinks
- Collision-free naming

**Benefits for Stage 3**:
- Predictable filenames for reporting
- No special character issues in paths
- No symlink loops to worry about
- Simplified path comparison for resolution policy

### From Stage 2: Folder Structure Optimization

**Inputs**:
- Flattened directory structure
- No empty folders
- Optimized folder organization
- Sanitized folder names

**Benefits for Stage 3**:
- Fewer folders to scan (faster scanning)
- Meaningful folder depth (after flattening, remaining folders matter)
- Path depth resolution policy makes sense
- Cleaner paths in reports

### To Stage 4: File Relocation

**Outputs**:
- Deduplicated input folder (no internal duplicates)
- Input folder cleaned against output folder (no cross-duplicates)
- SQLite cache with all file hashes
- Known unique files ready for relocation

**Benefits for Stage 4**:
- Smaller dataset to copy (duplicates removed)
- No risk of copying duplicates to output
- Cache available for collision detection
- Output folder cache tracks what's already there

---

## Error Handling & Edge Cases

### File Access Errors

**Scenarios**:
- Permission denied
- File locked by another process
- File deleted during processing
- I/O errors (bad sectors, network timeouts)

**Handling**:
1. Log error with file path and error message
2. Skip file (don't abort entire operation)
3. Continue processing remaining files
4. Report skipped files in summary

**Example**:
```
[WARNING] Cannot read file: /data/input/locked.mp4
  Error: Permission denied (errno 13)
  Action: Skipped (continuing with remaining files)

[SUMMARY]
Files processed: 30,549
Files skipped (errors): 1
```

### Output Folder Missing

**Stage 3B requires output folder**:
```bash
$ file-organizer -if /input -of /nonexistent --stage 3b --execute

[ERROR] Output folder does not exist: /nonexistent
  Stage 3B (cross-folder deduplication) requires an existing output folder.
  
  Options:
  1. Create the output folder manually
  2. Run full pipeline (Stages 1-4) to initialize output folder
  3. Run Stage 3A only (internal deduplication, no output folder needed)
  
  Exiting.
```

### Empty Files

**Scenario**: Multiple empty files (0 bytes)

**Handling**:
- All empty files have the same hash (hash of empty data)
- Technically duplicates
- Apply resolution policy normally
- Usually keep based on "keep" keyword or depth

**Example**:
```
Group 47 (3 empty files, 0 bytes each):
  KEEP:   /data/input/keep/placeholder.txt (depth: 3) ← "keep" keyword
  DELETE: /data/input/empty.txt (depth: 2)
  DELETE: /data/input/temp/empty.txt (depth: 3)
```

### Very Large Files

**Scenario**: Files > 5GB (sampling recommended)

**Handling**:
1. Check if sampling enabled (default: yes)
2. If enabled: Use adaptive sampling (50MB head + 50MB tail)
3. If disabled: Hash full file (warn about time estimate)
4. Show progress within large file hashing

**Example**:
```
[HASH PHASE]
Hashing: /data/input/huge_video.mp4 (18.2 GB)
  Using sampling: 50MB head + 50MB tail (100MB total)
  Progress: [████████████████████] 100/100 MB (100%) - 0.8s elapsed
```

### Cache Corruption

**Detection**:
```python
try:
    load_cache(cache_path)
except sqlite3.DatabaseError:
    log.warning("Cache corrupted, rebuilding from scratch")
    delete_cache(cache_path)
    cache = initialize_new_cache()
```

**Handling**:
1. Detect corruption on load (SQLite errors)
2. Log warning
3. Delete corrupted cache
4. Create fresh cache
5. Continue normally (just slower, no cache hits)

### Keyboard Interrupt

**Scenario**: User presses Ctrl+C during processing

**Handling**:
1. Catch SIGINT signal
2. Clean up open file handles
3. Flush cache updates
4. Exit cleanly with message

**No resume capability** (atomic operations):
- Stage 3 is all-or-nothing
- No partial state saved
- Simpler implementation
- Future enhancement: Add resume capability

---

## Test Requirements

### Unit Tests

**test_hash_computation.py**:
- Hash known files (compare against expected xxHash values)
- Test incremental hashing (chunked reads)
- Test sampling strategy (head + tail)
- Edge case: Empty file
- Edge case: File smaller than sample size

**test_video_utils.py**:
- Extract video duration correctly
- Handle non-video files gracefully
- Handle corrupted video files
- Compare durations (tolerance ±1 second)

**test_duplicate_resolver.py**:
- Priority 1: "keep" keyword detection (case-insensitive, any position in path)
- Priority 2: Path depth calculation and comparison
- Priority 3: mtime comparison
- Multiple files with "keep" → depth tiebreaker
- Multiple files same depth → mtime tiebreaker

**test_hash_cache.py**:
- Save and load cache correctly
- Cache hit (file unchanged)
- Cache miss (new file)
- Moved file detection (same size+mtime+hash, different path)
- Invalidate on size change
- Invalidate on mtime change
- Handle corrupted cache gracefully

**test_file_sampler.py**:
- Sample head + tail correctly
- Adaptive sampling for large files
- Full hash for small files
- Handle files smaller than sample size

### Integration Tests

**test_stage3a_integration.py**:
- Full Stage 3A run on synthetic dataset
- Dataset: 1,000 files, 100 duplicates, various sizes
- Verify correct duplicate detection
- Verify resolution policy applied correctly
- Check dry-run vs execute mode

**test_stage3b_integration.py**:
- Full Stage 3B run with input and output folders
- Dataset: 1,000 files in input, 500 in output, 200 cross-duplicates
- Verify correct cross-comparison
- Verify cache loading
- Verify resolution policy

**test_full_pipeline.py**:
- Run Stages 1 → 2 → 3A → 3B sequentially
- Verify seamless integration
- Check combined statistics
- Verify caches persist across stages

### Performance Tests

**benchmark_hashing_speed.py**:
- Measure xxHash throughput (GB/s)
- Compare full hashing vs sampling
- Test on files of various sizes (10MB, 100MB, 1GB, 10GB)
- Verify parallel vs sequential performance

**benchmark_video_metadata.py**:
- Measure metadata extraction speed (files/second)
- Test on various video formats
- Verify fallback on non-video files

**benchmark_cache_effectiveness.py**:
- First run (no cache): Measure time
- Second run (with cache): Measure time
- Calculate speedup ratio (should be > 5x)
- Verify cache hit rate (should be > 95% for unchanged files)

### Test Data Generation

**tools/generate_test_data_stage3.py**:
```python
def generate_stage3_test_data(output_dir):
    """
    Generate realistic test dataset for Stage 3 testing.
    
    Dataset composition:
    - 1,000 unique video files (50MB-2GB each)
    - 500 duplicate video files (2-3 copies of some originals)
    - 5,000 image files (skipped, for realism)
    - 100 small files (< 10KB, skipped)
    - Varied modification times
    - Varied folder depths (1-5 levels)
    - Some files with "keep" in path
    """
    # Generate unique videos
    for i in range(1000):
        create_random_video(f"unique_{i}.mp4", random_size(50MB, 2GB))
    
    # Create duplicate groups
    for i in range(100):
        original = create_random_video(f"original_{i}.mkv", random_size(100MB, 1GB))
        # Create 2-3 duplicates at different paths with different mtimes
        for j in range(random.randint(2, 3)):
            duplicate_path = random_nested_path(f"dup_{i}_{j}.mkv", depth=random.randint(2, 5))
            copy_file(original, duplicate_path)
            set_random_mtime(duplicate_path, days_ago=random.randint(1, 365))
    
    # Add some with "keep" keyword
    for i in range(20):
        create_file_with_keep_keyword(f"video_{i}.mp4")
    
    # Add images (will be skipped)
    for i in range(5000):
        create_fake_image(f"image_{i}.jpg", random_size(500KB, 5MB))
    
    # Add small files (will be skipped)
    for i in range(100):
        create_small_file(f"small_{i}.txt", random_size(100, 5KB))
```

---

## Success Criteria

### Functional Requirements
1. ✓ Correctly identifies 100% of byte-identical duplicates (no false negatives)
2. ✓ No false positives (different files never marked as duplicates)
3. ✓ Resolution policy applied correctly (keep→depth→newest)
4. ✓ Dry-run preview exactly matches execute mode actions
5. ✓ Cache improves subsequent run performance significantly (> 5x)
6. ✓ Integration with Stages 1-2 seamless
7. ✓ Output folder requirement enforced (error if missing)

### Performance Requirements
1. ✓ Initial scan: 2TB, 100k files in < 60 minutes
2. ✓ Subsequent scans: < 10 minutes with cache
3. ✓ Memory usage: < 500 MB for 100k files
4. ✓ Video metadata extraction: > 100 files/second
5. ✓ Hash throughput: > 500 MB/s (effective, with sampling)

### Reliability Requirements
1. ✓ Handles file access errors gracefully (skip and continue)
2. ✓ Survives keyboard interrupt cleanly (no corruption)
3. ✓ Works with corrupted/missing cache (rebuilds automatically)
4. ✓ No data loss (dry-run default, execute requires explicit flag)
5. ✓ Video metadata extraction failures don't abort operation

---

## Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-2)
- SQLite cache implementation with schema
- xxHash integration
- File scanning with filtering (skip images, skip small files)
- Size grouping
- Basic duplicate detection (hash-based)

### Phase 2: Large File Sampling (Week 2-3)
- Implement head + tail sampling
- Adaptive sampling for very large files
- Integration with cache (store hash_type: full/sampled)
- Testing and validation

### Phase 3: Video Optimizations (Week 3-4)
- Integrate pymediainfo or ffprobe
- Duration extraction and comparison
- Metadata caching in SQLite
- Fallback handling (non-videos, extraction failures)

### Phase 4: Resolution Policy (Week 4-5)
- Implement "keep" keyword detection
- Path depth calculation
- mtime comparison
- Priority logic (keep→depth→newest)
- Comprehensive testing

### Phase 5: Two-Phase Architecture (Week 5-6)
- Stage 3A implementation (internal deduplication)
- Stage 3B implementation (cross-folder deduplication)
- Output folder cache management
- Integration testing

### Phase 6: Progress & Reporting (Week 6-7)
- Adaptive progress reporting (same as Stage 1)
- Comprehensive reporting (dry-run and execute modes)
- Summary statistics
- Error reporting

### Phase 7: Testing & Documentation (Week 7-8)
- Unit tests (> 90% coverage)
- Integration tests (full pipeline)
- Performance benchmarking
- User documentation
- Code documentation

**Total Estimated Time**: 7-8 weeks  
**Lines of Code**: ~2,500-3,000 (more complex than original estimate due to video optimizations)

---

## Future Enhancements (Post-MVP)

### Phase 5 Features (Planned)

**1. Perceptual Hashing for Near-Duplicates**
- **Goal**: Find similar but not identical videos (re-encoded, cropped, etc.)
- **Method**: Extract video thumbnails at keyframes, compute perceptual hashes
- **Libraries**: `imagehash`, `opencv-python`
- **Use case**: Find duplicate videos with different encodings
- **Architecture note**: Separate module `perceptual_hash.py`, optional feature

**2. Interactive Duplicate Review UI**
- **Goal**: Allow users to manually review duplicate groups before deletion
- **Method**: Terminal UI with preview thumbnails, file info, side-by-side comparison
- **Libraries**: `rich`, `textual`, `Pillow` (for thumbnail generation)
- **Features**:
  - Show duplicate groups with thumbnails
  - Play video previews (first 5 seconds)
  - Select which files to keep/delete
  - Batch operations
- **Architecture note**: Separate module `interactive_ui.py`, invoked with `--review` flag

**3. Smart Sampling Strategies**
- **Goal**: Improve sampling accuracy for edge cases
- **Methods**:
  - Multi-point sampling (head, middle, tail)
  - Keyframe-based sampling for videos
  - Scene detection and sample key scenes
- **Libraries**: `opencv-python`, `scenedetect`
- **Architecture note**: Extend `file_sampler.py` with additional strategies

**4. Cloud Storage Integration**
- **Goal**: Compare local files against cloud storage (Dropbox, Google Drive, etc.)
- **Method**: Fetch file hashes from cloud APIs, compare against local hashes
- **Use case**: Avoid uploading files already in cloud
- **Architecture note**: New module `cloud_integrations.py`

**5. Duplicate Statistics Dashboard**
- **Goal**: Visualize duplicate patterns and space savings
- **Features**:
  - Most duplicated files
  - Space savings by file type
  - Duplicate patterns (by folder, by date)
  - Historical tracking (duplicate growth over time)
- **Architecture note**: Generate JSON reports, optional web UI

**6. Resume Capability**
- **Goal**: Resume interrupted Stage 3 runs
- **Method**: Save progress after each phase, detect incomplete runs
- **Architecture note**: Extend cache with progress tracking table

---

## Conclusion

Stage 3 (Duplicate Detection & Resolution) is a **speed-optimized video deduplication system** designed for large-scale media collections. By combining:

- **xxHash** for blazing-fast hashing
- **Large file sampling** to avoid processing full 10GB+ files
- **Video metadata optimization** to eliminate 80-90% of unnecessary hashing
- **Intelligent SQLite caching** with moved file detection
- **Two-phase architecture** (internal + cross-folder)
- **Custom resolution policy** prioritizing user intent and organization

Stage 3 achieves:
- **60-minute initial scans** for 2TB, 100k files
- **5-10 minute subsequent scans** with caching
- **Massive space reclamation** (100+ GB typical)
- **Zero false positives** (different files never marked as duplicates)
- **Graceful error handling** (skip problems, continue processing)

The architecture is designed for extensibility, with future enhancements like perceptual hashing and interactive review planned as modular additions.

---

**Document Version**: 2.0  
**Last Updated**: November 11, 2025  
**Status**: Requirements Complete, Ready for Implementation  
**Previous Version**: 1.0 (November 10, 2025) - Replaced completely

---

## Appendix: Configuration Examples

### Minimal Configuration (Defaults)
```yaml
duplicate_detection:
  enabled: true
  hash_algorithm: xxhash
```

### Performance-Optimized Configuration
```yaml
duplicate_detection:
  enabled: true
  hash_algorithm: xxhash
  enable_sampling: true
  large_file_threshold: 20971520   # 20MB
  parallel_hashing: true
  max_workers: 16                  # Use all cores
  use_video_metadata: true
  check_duration: true
```

### Paranoid Configuration (Full Accuracy)
```yaml
duplicate_detection:
  enabled: true
  hash_algorithm: sha256           # Cryptographic security
  enable_sampling: false           # Full file hashing
  use_video_metadata: false        # Hash-only comparison
  parallel_hashing: true
```

### Minimal Invasive Configuration (Review Only)
```yaml
duplicate_detection:
  enabled: true
  hash_algorithm: xxhash
  # Don't automatically delete, just report
  # (Set in CLI with --dry-run, which is default)
```
