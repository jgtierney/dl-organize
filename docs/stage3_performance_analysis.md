# Stage 3 Performance Optimization Analysis

**Date**: November 13, 2025  
**Analyzed By**: AI Code Review  
**Status**: High-Value Opportunities Identified

---

## Executive Summary

After reviewing all Stage 3 code (`stage3.py`, `duplicate_detector.py`, `duplicate_resolver.py`, `hash_cache.py`), I've identified **7 high-value performance optimization opportunities** that could provide **5-16x speedup** for typical workloads.

**Current Performance** (from requirements):
- First run: ~60 minutes for 2TB, 100k files
- Subsequent runs: ~5-10 minutes (cache hits)

**Potential Performance** (with optimizations):
- First run: ~4-12 minutes (5-15x faster)
- Subsequent runs: ~1-2 minutes (5x faster)

---

## Optimization Opportunities (Ranked by Impact)

### 1. ⭐⭐⭐ **Parallel File Hashing** (CRITICAL - 8-16x speedup)

**Current State**: Sequential hashing in loops
- `duplicate_detector.py:392-416` - Sequential loop through collision groups
- `stage3.py:462-480` - Sequential loop for cross-folder hashing

**Problem**: 
- CPU cores idle while hashing files sequentially
- With 16 cores available, only using 1 core (6.25% utilization)
- xxHash is CPU-bound, perfect for parallelization

**Solution**: Use `concurrent.futures.ThreadPoolExecutor` for parallel hashing
- ThreadPoolExecutor (not ProcessPoolExecutor) because:
  - xxHash releases GIL, threads work well
  - Shared cache object (SQLite is thread-safe with WAL mode)
  - Lower overhead than processes

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def hash_files_parallel(self, files_to_hash, folder, max_workers=16):
    """Hash files in parallel using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(self.hash_file_with_cache, file_meta, folder): file_meta
            for file_meta in files_to_hash
        }
        
        results = []
        for future in as_completed(futures):
            file_hash = future.result()
            if file_hash:
                results.append((futures[future], file_hash))
    return results
```

**Performance Impact**:
- **8-16x speedup** for hashing phase (depending on CPU cores)
- Typical dataset: 10,000 files to hash
  - Sequential: ~40 minutes (0.24s per file avg)
  - Parallel (16 cores): ~2.5-5 minutes
- **Overall Stage 3A speedup**: 5-8x (hashing is ~60% of total time)

**Estimated Benefit**: 
- First run: 60 min → **8-12 min** (5-7.5x faster)
- Subsequent runs: 5 min → **1-2 min** (2.5-5x faster)

**Complexity**: Medium (requires thread-safe cache operations, progress tracking)

---

### 2. ⭐⭐⭐ **Large File Sampling** (CRITICAL - 5-10x speedup for large files)

**Current State**: NOT IMPLEMENTED (mentioned in requirements but missing)

**Problem**:
- Hashing 10GB video files takes ~60 seconds each
- For 1,000 large videos: 60,000 seconds = **16.7 hours** (unacceptable)
- Most video files differ in headers/endings, not middle portions

**Solution**: Implement head+tail sampling for files > 20MB
- Files < 20MB: Full hash (100%)
- Files 20MB-1GB: Hash first 10MB + last 10MB (~1-20% of file)
- Files 1GB-5GB: Hash first 20MB + last 20MB (~1-8% of file)
- Files > 5GB: Hash first 50MB + last 50MB (~1-2% of file)

**Implementation**:
```python
def compute_file_hash_sampled(self, file_path: str, file_size: int) -> str:
    """Compute hash using head+tail sampling for large files."""
    hasher = xxhash.xxh64()
    
    # Determine sample strategy
    if file_size < 20 * 1024 * 1024:  # < 20MB
        # Full hash
        return self.compute_file_hash(file_path)
    
    # Adaptive sampling
    if file_size < 1024 * 1024 * 1024:  # < 1GB
        head_size = 10 * 1024 * 1024  # 10MB
        tail_size = 10 * 1024 * 1024  # 10MB
    elif file_size < 5 * 1024 * 1024 * 1024:  # < 5GB
        head_size = 20 * 1024 * 1024  # 20MB
        tail_size = 20 * 1024 * 1024  # 20MB
    else:  # >= 5GB
        head_size = 50 * 1024 * 1024  # 50MB
        tail_size = 50 * 1024 * 1024  # 50MB
    
    # Hash head
    with open(file_path, 'rb') as f:
        head_data = f.read(head_size)
        hasher.update(head_data)
        
        # Seek to tail
        f.seek(max(0, file_size - tail_size))
        tail_data = f.read(tail_size)
        hasher.update(tail_data)
    
    return hasher.hexdigest()
```

**Performance Impact**:
- **5-10x speedup** for large file hashing
- Typical dataset: 1,000 large videos (avg 2GB each)
  - Without sampling: ~33 hours (2GB @ 500MB/s = 4s, but disk I/O overhead)
  - With sampling: ~3-6 hours (40MB @ 500MB/s = 0.08s + seek overhead)
- **Overall Stage 3A speedup**: 2-3x (if 50%+ files are large)

**Estimated Benefit**:
- First run: 60 min → **20-30 min** (2-3x faster, stacks with parallel hashing)

**Complexity**: Low-Medium (requires file seeking, cache hash_type='sampled')

---

### 3. ⭐⭐ **Video Metadata Pre-Filtering** (HIGH - 5-10x reduction in hashing)

**Current State**: NOT IMPLEMENTED (mentioned in requirements but missing)

**Problem**:
- Many size collisions are false positives (different videos, same size)
- Hashing is expensive even with sampling
- Video duration check is fast (~0.05s per file) vs hashing (~0.5s per file)

**Solution**: Extract video duration before hashing
- For size collision groups with videos:
  - Extract duration using `pymediainfo` or `ffprobe`
  - If durations differ by > 1 second → skip hashing (not duplicates)
  - Only hash videos with matching durations

**Implementation**:
```python
def extract_video_duration(self, file_path: str) -> Optional[float]:
    """Extract video duration using pymediainfo or ffprobe."""
    try:
        from pymediainfo import MediaInfo
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == 'Video':
                return float(track.duration) / 1000.0  # Convert to seconds
    except:
        # Fallback to ffprobe
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    return None

def filter_by_duration(self, size_group: List[FileMetadata]) -> List[FileMetadata]:
    """Filter size collision group by video duration."""
    # Group by duration
    duration_groups = defaultdict(list)
    for file_meta in size_group:
        duration = self.extract_video_duration(file_meta.path)
        if duration:
            duration_groups[round(duration)].append(file_meta)
        else:
            # Non-video or extraction failed - must hash
            duration_groups[None].append(file_meta)
    
    # Only hash groups with 2+ files of same duration
    files_to_hash = []
    for duration, files in duration_groups.items():
        if len(files) >= 2:
            files_to_hash.extend(files)
    
    return files_to_hash
```

**Performance Impact**:
- **5-10x reduction** in files that need hashing
- Typical dataset: 10,000 size collisions
  - Without duration check: Hash all 10,000 files
  - With duration check: Hash only ~1,000-2,000 files (80-90% eliminated)
- **Overall Stage 3A speedup**: 2-3x (stacks with other optimizations)

**Estimated Benefit**:
- First run: 60 min → **20-30 min** (2-3x faster, stacks with parallel + sampling)

**Complexity**: Medium (requires pymediainfo/ffprobe dependency, error handling)

---

### 4. ⭐⭐ **Optimize Cache Reloads** (MEDIUM - 30-50% faster Stage 3B)

**Current State**: Full cache reload after hashing (`stage3.py:485-487`)

**Problem**:
- After hashing files in Stage 3B, entire cache is reloaded
- `get_all_files()` loads ALL files from database (100k+ files)
- Unnecessary I/O when we only need updated hashes

**Solution**: Incremental cache updates instead of full reload
- Track which files were hashed
- Query only those files from cache
- Merge with existing in-memory data

**Implementation**:
```python
# Instead of:
input_files = self.cache.get_all_files('input')
output_files = self.cache.get_all_files('output')

# Do:
# Track files that were hashed
hashed_paths = {file_info.file_path for file_info, _ in files_to_hash}

# Query only updated files
updated_files = []
for file_path in hashed_paths:
    cached = self.cache.get_from_cache(file_path, folder)
    if cached:
        updated_files.append(cached)

# Update in-memory dictionaries
for cached in updated_files:
    # Update existing entry or add new one
    file_dict[cached.file_path] = cached
```

**Performance Impact**:
- **30-50% faster** Stage 3B cross-folder duplicate finding
- Typical dataset: 100k files, 1k need hashing
  - Full reload: ~2-3 seconds (load 100k entries)
  - Incremental: ~0.1-0.2 seconds (load 1k entries)
- **Overall Stage 3B speedup**: 1.3-1.5x

**Estimated Benefit**:
- Stage 3B: 5 min → **3-4 min** (1.3-1.5x faster)

**Complexity**: Low (refactor cache update logic)

---

### 5. ⭐ **Batch SQLite Operations** (MEDIUM - 20-30% faster cache updates)

**Current State**: Some batching exists, but could be optimized further

**Problem**:
- `save_to_cache()` commits after each file (line 251 in `hash_cache.py`)
- Multiple small transactions instead of one large batch
- SQLite overhead per transaction

**Solution**: Increase batch size, reduce commit frequency
- Batch 1,000 entries before commit (instead of 1)
- Use `executemany()` for inserts (already done in `save_batch()`)
- Commit every N files instead of every file

**Implementation**:
```python
# In duplicate_detector.py, batch cache saves:
BATCH_SIZE = 1000
cache_batch = []

for file_meta in files_to_hash:
    file_hash = self.compute_file_hash(...)
    cache_batch.append({
        'file_path': file_meta.path,
        'folder': folder,
        'file_hash': file_hash,
        ...
    })
    
    if len(cache_batch) >= BATCH_SIZE:
        self.cache.save_batch(cache_batch)
        cache_batch = []

# Final batch
if cache_batch:
    self.cache.save_batch(cache_batch)
```

**Performance Impact**:
- **20-30% faster** cache updates
- Typical dataset: 10,000 files to hash
  - Individual commits: ~30 seconds (3ms per commit × 10k)
  - Batch commits: ~20 seconds (1ms per commit × 10 batches)
- **Overall Stage 3A speedup**: 1.2-1.3x

**Estimated Benefit**:
- First run: 60 min → **50 min** (1.2x faster, stacks with other optimizations)

**Complexity**: Low (refactor cache save logic)

---

### 6. ⭐ **SQLite PRAGMA Optimizations** (LOW-MEDIUM - 10-20% faster)

**Current State**: PRAGMA settings only applied on first creation (`hash_cache.py:100-119`)

**Problem**:
- PRAGMA settings (WAL mode, cache size, etc.) only set when table doesn't exist
- If database exists, no optimizations applied
- Missing some optimizations that could help

**Solution**: Always apply PRAGMA settings on database open
- Move PRAGMA settings to `_open_database()` method
- Apply every time, not just on creation
- Add additional optimizations:
  - `PRAGMA busy_timeout = 30000` (30s timeout for concurrent access)
  - `PRAGMA foreign_keys = OFF` (not needed, slight speedup)

**Implementation**:
```python
def _open_database(self):
    """Open SQLite database connection with optimizations."""
    self.conn = sqlite3.connect(str(self.db_path))
    self.conn.row_factory = sqlite3.Row
    
    cursor = self.conn.cursor()
    
    # Always apply performance optimizations
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-51200")  # 50MB
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=67108864")  # 64MB
    cursor.execute("PRAGMA busy_timeout=30000")  # 30s timeout
    cursor.execute("PRAGMA foreign_keys=OFF")  # Not needed
    
    self.conn.commit()
```

**Performance Impact**:
- **10-20% faster** database operations
- Especially noticeable on slower storage (network drives, HDDs)
- **Overall Stage 3A speedup**: 1.1-1.2x

**Estimated Benefit**:
- First run: 60 min → **50-55 min** (1.1-1.2x faster)

**Complexity**: Very Low (move existing code)

---

### 7. ⭐ **Optimize Cross-Folder Duplicate Finding** (LOW-MEDIUM - 20-30% faster Stage 3B)

**Current State**: Multiple loops, could be optimized (`stage3.py:353-564`)

**Problem**:
- Phase 1: Build size index (loop through all files)
- Phase 2: Identify collisions (loop through size groups)
- Phase 3: Build hash index (loop through all files again)
- Phase 4: Find cross-folder duplicates (loop through hash groups)
- Multiple passes over same data

**Solution**: Combine phases where possible, use SQL queries
- Use SQL `GROUP BY` and `HAVING` for size collision detection
- Use SQL `JOIN` for cross-folder duplicate finding
- Reduce Python loops, leverage SQLite's optimized queries

**Implementation**:
```python
def _find_cross_folder_duplicates_sql(self) -> List[DuplicateGroup]:
    """Find cross-folder duplicates using SQL queries."""
    cursor = self.conn.cursor()
    
    # Single SQL query to find cross-folder duplicates
    cursor.execute("""
        SELECT file_hash, file_size, 
               GROUP_CONCAT(file_path || '|' || folder) as files
        FROM file_cache
        WHERE file_hash IS NOT NULL
        GROUP BY file_hash
        HAVING COUNT(DISTINCT folder) = 2
    """)
    
    groups = []
    for row in cursor.fetchall():
        file_paths = []
        for file_str in row['files'].split(','):
            path, folder = file_str.split('|')
            file_paths.append(path)
        
        groups.append(DuplicateGroup(
            hash=row['file_hash'],
            size=row['file_size'],
            files=file_paths
        ))
    
    return groups
```

**Performance Impact**:
- **20-30% faster** cross-folder duplicate finding
- Typical dataset: 100k files
  - Python loops: ~5-10 seconds
  - SQL query: ~2-5 seconds
- **Overall Stage 3B speedup**: 1.2-1.3x

**Estimated Benefit**:
- Stage 3B: 5 min → **4 min** (1.2x faster)

**Complexity**: Low-Medium (refactor to use SQL)

---

## Combined Performance Impact

### Best Case (All Optimizations Implemented)

**First Run** (2TB, 100k files):
- Current: ~60 minutes
- With optimizations: **~4-8 minutes** (7.5-15x faster)
  - Parallel hashing: 8-16x → 60 min → 4-7.5 min
  - Large file sampling: 2-3x → 4-7.5 min → 2-3.5 min
  - Video metadata: 2-3x → 2-3.5 min → 1-1.5 min
  - Other optimizations: 1.2-1.5x → 1-1.5 min → **~1 min** (theoretical)
  - **Realistic**: ~4-8 minutes (disk I/O still bottleneck)

**Subsequent Runs** (with cache):
- Current: ~5-10 minutes
- With optimizations: **~1-2 minutes** (5x faster)
  - Parallel hashing: 2-3x → 5 min → 2-3 min
  - Other optimizations: 1.2-1.5x → 2-3 min → **~1-2 min**

### Realistic Case (High-Impact Optimizations Only)

**Priority 1-3 Implemented** (Parallel + Sampling + Video Metadata):
- First run: 60 min → **~8-15 min** (4-7.5x faster)
- Subsequent runs: 5 min → **~1.5-2.5 min** (2-3x faster)

---

## Implementation Priority

### Phase 1: Critical Optimizations (Weeks 1-2)
1. **Parallel File Hashing** (8-16x speedup)
   - Highest impact, medium complexity
   - Requires thread-safe cache operations
   - Estimated: 2-3 days implementation + testing

2. **Large File Sampling** (5-10x speedup for large files)
   - High impact, low-medium complexity
   - Already specified in requirements
   - Estimated: 1-2 days implementation + testing

### Phase 2: High-Value Optimizations (Weeks 3-4)
3. **Video Metadata Pre-Filtering** (5-10x reduction in hashing)
   - High impact, medium complexity
   - Requires pymediainfo/ffprobe dependency
   - Estimated: 2-3 days implementation + testing

4. **Optimize Cache Reloads** (30-50% faster Stage 3B)
   - Medium impact, low complexity
   - Quick win for Stage 3B
   - Estimated: 1 day implementation + testing

### Phase 3: Polish Optimizations (Week 5)
5. **Batch SQLite Operations** (20-30% faster)
6. **SQLite PRAGMA Optimizations** (10-20% faster)
7. **Optimize Cross-Folder Finding** (20-30% faster)

---

## Risk Assessment

### Low Risk
- SQLite PRAGMA optimizations
- Batch SQLite operations
- Optimize cache reloads

### Medium Risk
- Large file sampling (requires testing accuracy)
- Optimize cross-folder finding (SQL refactoring)

### Higher Risk
- Parallel file hashing (thread safety, race conditions)
- Video metadata pre-filtering (dependency management, error handling)

---

## Testing Requirements

### Parallel Hashing
- Test thread safety with concurrent cache access
- Verify progress tracking accuracy
- Test with various file sizes and types
- Measure actual speedup on 16-core system

### Large File Sampling
- Verify accuracy (no false positives/negatives)
- Test edge cases (files smaller than sample size)
- Measure speedup on large file datasets
- Compare sampled vs full hash results

### Video Metadata
- Test with various video formats
- Verify fallback to hashing when metadata extraction fails
- Test duration comparison tolerance (±1 second)
- Measure speedup on video-heavy datasets

---

## Conclusion

Stage 3 has **excellent optimization potential**. The top 3 optimizations (parallel hashing, large file sampling, video metadata) could provide **4-7.5x speedup** with moderate implementation effort.

**Recommended Approach**:
1. Implement parallel hashing first (biggest win)
2. Add large file sampling (high impact, already specified)
3. Add video metadata pre-filtering (high impact, stacks well)
4. Polish with remaining optimizations

**Expected Outcome**: 
- First run: 60 min → **~8-15 min** (4-7.5x faster)
- Subsequent runs: 5 min → **~1.5-2.5 min** (2-3x faster)

This would make Stage 3 **production-ready for large-scale operations** (500k+ files) while maintaining correctness and safety.

