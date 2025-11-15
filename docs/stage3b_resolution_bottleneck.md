# Stage 3B Resolution Phase Bottleneck Analysis

**Date**: November 15, 2025  
**Issue**: ~46 minute delay between "Analyzing duplicates complete" and "Stage 3B complete"

---

## The Problem

**Timeline**:
```
✓ Analyzing duplicates complete (243,419 items, 0.6s)

[2792.73s]   Stage 3B complete  ← ~46.5 minutes delay!
```

**Location**: `stage3.py:309-320` - Phase 4: Resolving Duplicates

---

## Root Cause

### Phase 4: Resolve Duplicates (Lines 309-320)

```python
for group in cross_folder_groups:
    file_to_keep, files_to_delete = self.resolver.resolve_duplicates(group.files)
```

**What `resolve_duplicates()` does**:
1. Calls `analyze_file()` for each file path in the group
2. `analyze_file()` does `path.stat()` - **filesystem I/O call**
3. With 243,419 items analyzed, this could be **thousands of stat() calls**

**Performance Impact**:
- Each `stat()` call: ~0.1-1ms (local filesystem) to ~10-100ms (network filesystem)
- With 243k+ items: **Thousands of filesystem calls**
- **Total time**: ~46 minutes (2792 seconds)

---

## The Optimization Opportunity

**Key Insight**: We already have file metadata in memory!

In `_find_cross_folder_duplicates()`, we load:
- `input_files` - List of `CachedFile` objects (has `file_size`, `file_mtime`)
- `output_files` - List of `CachedFile` objects (has `file_size`, `file_mtime`)

**Current Flow**:
```
cross_folder_groups → resolve_duplicates() → analyze_file() → path.stat() ❌ SLOW
```

**Optimized Flow**:
```
cross_folder_groups → resolve_duplicates_with_cache() → Use cached metadata ✅ FAST
```

---

## Proposed Solution

### Option 1: Pass CachedFile Objects to Resolver (RECOMMENDED)

**Change**: Modify `resolve_duplicates()` to accept `CachedFile` objects instead of paths

**Benefits**:
- No filesystem calls needed
- Uses already-loaded cache data
- 100-1000x faster (dictionary lookup vs filesystem I/O)

**Implementation**:
```python
# In stage3.py, Phase 4
# Build lookup dictionary from cached files
file_cache_lookup = {}
for f in input_files + output_files:
    file_cache_lookup[f.file_path] = f

# Pass cache lookup to resolver
for group in cross_folder_groups:
    file_to_keep, files_to_delete = self.resolver.resolve_duplicates_with_cache(
        group.files, 
        file_cache_lookup
    )
```

**New method in duplicate_resolver.py**:
```python
def resolve_duplicates_with_cache(
    self, 
    file_paths: List[str],
    cache_lookup: Dict[str, CachedFile]
) -> Tuple[str, List[str]]:
    """Resolve duplicates using cached metadata (no filesystem calls)."""
    file_infos = []
    for path in file_paths:
        cached = cache_lookup.get(path)
        if cached:
            # Use cached metadata
            file_info = self.analyze_file_from_cache(path, cached)
        else:
            # Fallback to stat() if not in cache (rare)
            file_info = self.analyze_file(path)
        file_infos.append(file_info)
    
    # ... rest of resolution logic ...
```

### Option 2: Batch Cache Lookup (ALTERNATIVE)

**Change**: Batch query cache for all file paths, then use cached data

**Benefits**:
- Still uses cache, but requires batch query
- Slightly more complex

---

## Performance Estimate

### Current Performance
- **243,419 items** analyzed
- **~46 minutes** (2792 seconds) for resolution
- **Rate**: ~87 items/second
- **Bottleneck**: Filesystem `stat()` calls

### With Optimization
- **Dictionary lookup**: ~0.0001ms per file (in-memory)
- **243,419 items**: ~24ms total (vs 2792 seconds)
- **Speedup**: **~116,000x faster** (theoretical)
- **Realistic**: **100-1000x faster** (accounting for other overhead)

**Expected Time**: ~0.1-1 second (down from ~46 minutes)

---

## Implementation Complexity

**Difficulty**: Low-Medium

**Changes Required**:
1. Add `resolve_duplicates_with_cache()` method to `DuplicateResolver`
2. Add `analyze_file_from_cache()` helper method
3. Modify `stage3.py` Phase 4 to build cache lookup and use new method
4. Keep `analyze_file()` as fallback for files not in cache

**Estimated Time**: 1-2 hours implementation + testing

---

## Additional Optimizations

### 1. Limit Dry-Run Report Size
**Current**: Prints ALL duplicate groups (could be thousands)
**Optimization**: Limit to first 100 groups, show summary

**Impact**: Faster dry-run report generation

### 2. Progress Reporting for Resolution
**Current**: No progress bar during resolution
**Optimization**: Add progress bar for resolution phase

**Impact**: Better visibility into progress

---

## Recommendation

**Implement Option 1** (pass CachedFile objects to resolver):
- Highest impact (100-1000x speedup)
- Low complexity
- Uses existing cache infrastructure
- Minimal code changes

This should reduce the ~46 minute delay to **< 1 second**.

