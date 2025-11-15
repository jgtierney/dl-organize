# Stage 3B Bottleneck Analysis

**Date**: November 13, 2025  
**Issue**: Slow performance between status messages in Stage 3B

---

## Status Messages Timeline

```
[   3.70s]   Cache initialized, starting cross-folder detection...

  ████████████████████ 100% (237,394/237,394) - 9.6s    ← Progress Bar #1

  ██████░░░░░░░░░░░░░░ 30% (34,257/114,189) - 398.4s - ~929s remaining  ← Progress Bar #2
```

---

## What's Happening Between Messages

### Progress Bar #1: "Building size index" (237,394/237,394) - 9.6s

**Location**: `stage3.py:380-400` in `_find_cross_folder_duplicates()`

**Operations**:
1. **Load input cache** (line 370) - `get_all_files('input')`
   - Loads ALL input files from cache (e.g., 100k+ entries)
   - **Bottleneck**: Loading entire cache when we already loaded it in Phase 1
   
2. **Load output cache** (line 371) - `get_all_files('output')`
   - Loads ALL output files from cache (e.g., 137k+ entries)
   - **Necessary**: Need all output files for cross-folder comparison
   
3. **Group by size** (lines 387-400)
   - Fast operation: Builds size index in memory
   - Processes 237,394 total files (input + output)
   - **Performance**: ~9.6s for 237k files = ~24,700 files/sec (good)

**Total Time**: 9.6s (acceptable)

---

### Progress Bar #2: "Computing hashes" (34,257/114,189) - 398.4s

**Location**: `stage3.py:441-494` in `_find_cross_folder_duplicates()`

**Operations**:
1. **Identify files needing hashing** (lines 411-428)
   - Finds size collisions between input and output folders
   - Identifies 114,189 files that need hashing
   - **Fast**: Just analysis, no I/O

2. **Sequential file hashing** (lines 462-494) - **MAJOR BOTTLENECK**
   ```python
   for idx, (file_info, folder) in enumerate(files_to_hash, 1):
       detector.hash_file_with_cache(file_meta, folder)  # Sequential!
   ```
   - **114,189 files** need to be hashed
   - **Sequential processing** (one file at a time)
   - **30% complete** (34,257 files) in **398.4 seconds**
   - **Estimated total time**: ~1,327 seconds (~22 minutes) for hashing alone

**Performance Analysis**:
- Current rate: 34,257 files / 398.4s = **86 files/second**
- At this rate, 114,189 files = **~1,327 seconds** (~22 minutes)
- **Bottleneck**: Sequential hashing, no parallelization

3. **Reload cache** (lines 496-521)
   - After hashing, reloads cache to get updated hashes
   - **Bottleneck**: Currently reloads ALL files (237k+ entries)
   - **Optimization**: Should only reload files that were hashed (114k entries)

**Total Time**: 398.4s+ (and counting) - **UNACCEPTABLE**

---

## Root Causes

### 1. Duplicate Cache Loading ⚠️ (Minor Impact)
- Input files loaded twice:
  - Once in Phase 1 (line 247)
  - Again in `_find_cross_folder_duplicates()` (line 370)
- **Fix**: Cache input_files in instance variable, reuse

### 2. Sequential File Hashing 🔴 (CRITICAL - Major Impact)
- **114,189 files** hashed sequentially
- No parallelization despite 16 cores available
- **Impact**: 398+ seconds for 30% = ~22 minutes total
- **Fix**: Implement parallel hashing (see `stage3_performance_analysis.md`)

### 3. Full Cache Reload After Hashing ⚠️ (Medium Impact)
- After hashing, reloads ALL 237k+ files from cache
- Only needs to reload 114k files that were hashed
- **Fix**: Incremental cache reload (only updated files)

---

## Performance Impact

### Current Performance
- **Phase 1** (Building size index): 9.6s ✅
- **Phase 2** (Hashing): ~1,327s (~22 min) 🔴
- **Total**: ~22+ minutes for Stage 3B

### With Optimizations

**Optimization 1: Avoid Duplicate Cache Load** (Minor)
- Saves: ~1-2 seconds
- **New Phase 1 time**: ~8s

**Optimization 2: Incremental Cache Reload** (Medium)
- Saves: ~2-5 seconds
- **New reload time**: ~0.5-1s (instead of 2-5s)

**Optimization 3: Parallel Hashing** (CRITICAL)
- **8-16x speedup** with 16 cores
- Current: ~1,327s (~22 min)
- With parallel: ~83-166s (~1.5-3 min)
- **Saves**: ~19-20 minutes

### Expected Performance After Optimizations
- **Phase 1**: ~8s
- **Phase 2**: ~1.5-3 min (with parallel hashing)
- **Total**: **~2-3 minutes** (down from ~22 minutes)
- **Speedup**: **7-11x faster**

---

## Implemented Fixes

### ✅ Fix 1: Avoid Duplicate Input Cache Load
- Cache `input_files` in `self._cached_input_files` after Phase 1
- Reuse in `_find_cross_folder_duplicates()` instead of reloading
- **Impact**: Saves ~1-2 seconds

### ✅ Fix 2: Incremental Cache Reload
- After hashing, only reload files that were hashed (not all files)
- Use `get_files_by_paths()` batch query
- **Impact**: Saves ~2-5 seconds

### ⏳ Fix 3: Parallel Hashing (Not Yet Implemented)
- **Highest priority** optimization
- See `stage3_performance_analysis.md` for implementation details
- **Impact**: 8-16x speedup (~19-20 minutes saved)

---

## Recommendations

### Immediate (Already Implemented)
1. ✅ Avoid duplicate cache loading
2. ✅ Incremental cache reload

### High Priority (Next Steps)
1. **Implement parallel hashing** (Critical - 8-16x speedup)
   - Use `ThreadPoolExecutor` with 16 workers
   - Thread-safe cache operations (SQLite WAL mode)
   - Estimated implementation: 2-3 days

2. **Add progress reporting for cache loading**
   - Show progress when loading large caches (100k+ files)
   - Helps identify bottlenecks

### Medium Priority
1. **Large file sampling** (5-10x speedup for large files)
   - Hash only head+tail for files > 20MB
   - Reduces hashing time for large videos

2. **Video metadata pre-filtering** (5-10x reduction in hashing)
   - Check video duration before hashing
   - Skip hashing if durations differ

---

## Testing Recommendations

1. **Measure current performance**:
   - Time Phase 1 (cache loading + size grouping)
   - Time Phase 2 (hashing)
   - Time Phase 3 (hash grouping)
   - Time Phase 4 (cross-folder duplicate finding)

2. **After optimizations**:
   - Verify same results (correctness)
   - Measure speedup
   - Check memory usage (parallel hashing may increase)

3. **Edge cases**:
   - Very large cache (500k+ entries)
   - Many files needing hashing (200k+)
   - Mixed file sizes (small + large)

---

## Conclusion

The **main bottleneck** is **sequential file hashing** (114,189 files taking ~22 minutes). The implemented fixes (duplicate cache load avoidance and incremental reload) provide minor improvements, but **parallel hashing is critical** for significant performance gains.

**Expected improvement**: 7-11x faster Stage 3B (from ~22 min to ~2-3 min) with parallel hashing implemented.

