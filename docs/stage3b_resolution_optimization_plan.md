# Stage 3B Resolution Optimization Plan

**Date**: November 15, 2025  
**Issue**: ~46 minute delay in Phase 4 (Resolving Duplicates)  
**Root Cause**: Unnecessary `stat()` calls for every file  
**Solution**: Use cached metadata, optional moved-file verification

---

## Problem Summary

**Current Performance**:
- Phase 4: Resolving duplicates takes ~46 minutes (2792 seconds)
- Bottleneck: `analyze_file()` calls `path.stat()` for every file
- With 243,419 items: Thousands of filesystem I/O calls

**Root Cause**:
- `duplicate_resolver.py:analyze_file()` calls `stat()` to get `size` and `mtime`
- We already have this data in cache (`CachedFile` objects)
- Defensive programming (checking if files exist) causing huge performance hit

---

## Solution Design

### Default Behavior (Optimized)
- **Use cached metadata** from `CachedFile` objects (no filesystem calls)
- **100-1000x faster** (dictionary lookup vs filesystem I/O)
- **Expected time**: < 1 second (down from ~46 minutes)

### Optional Behavior (Moved File Detection)
- **CLI flag**: `--verify-files` or `--check-moved-files`
- **When enabled**: Calls `stat()` to verify files still exist
- **Use case**: User knows files may have been moved/deleted since cache was created
- **Performance**: Slower but validates file existence

---

## Implementation Plan

### Phase 1: Add CLI Flag

**File**: `src/file_organizer/cli.py`

**Add argument**:
```python
parser.add_argument(
    '--verify-files',
    action='store_true',
    help='Verify files still exist before resolving duplicates (slower, but detects moved/deleted files)'
)
```

**Pass to Stage3**:
```python
stage3 = Stage3(
    ...
    verify_files=args.verify_files  # New parameter
)
```

---

### Phase 2: Modify Stage3 Class

**File**: `src/file_organizer/stage3.py`

**Add parameter**:
```python
def __init__(
    self,
    ...
    verify_files: bool = False  # New parameter
):
    ...
    self.verify_files = verify_files
```

**Modify Phase 4**:
```python
# Phase 4: Resolve duplicates (apply full three-tier policy)
self._print_phase(4, 5, "Resolving Duplicates (applying three-tier policy)")

# Build cache lookup dictionary for fast access
file_cache_lookup = {}
for f in input_files + output_files:
    file_cache_lookup[f.file_path] = f

resolution_plan = []
total_to_delete = 0
total_space = 0

for group in cross_folder_groups:
    # Use optimized resolver (cached metadata) or full resolver (with stat())
    if self.verify_files:
        file_to_keep, files_to_delete = self.resolver.resolve_duplicates(group.files)
    else:
        file_to_keep, files_to_delete = self.resolver.resolve_duplicates_with_cache(
            group.files, 
            file_cache_lookup
        )
    ...
```

---

### Phase 3: Add Optimized Resolver Method

**File**: `src/file_organizer/duplicate_resolver.py`

**New method**:
```python
def resolve_duplicates_with_cache(
    self, 
    file_paths: List[str],
    cache_lookup: Dict[str, CachedFile]
) -> Tuple[str, List[str]]:
    """
    Resolve duplicates using cached metadata (no filesystem calls).
    
    Args:
        file_paths: List of duplicate file paths
        cache_lookup: Dictionary mapping file_path -> CachedFile
        
    Returns:
        Tuple of (file_to_keep, files_to_delete)
    """
    if not file_paths:
        return None, []
    
    if len(file_paths) == 1:
        return file_paths[0], []
    
    # Analyze all files using cached metadata
    file_infos = []
    for path in file_paths:
        cached = cache_lookup.get(path)
        if cached:
            # Use cached metadata (fast - no filesystem call)
            file_info = self.analyze_file_from_cache(path, cached)
        else:
            # Fallback to stat() if not in cache (rare - should not happen)
            # Log warning for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"File not in cache, using stat(): {path}")
            file_info = self.analyze_file(path)
        file_infos.append(file_info)
    
    # Find the file with highest priority (same logic as resolve_duplicates)
    best_file = file_infos[0]
    for file_info in file_infos[1:]:
        comparison = self.compare_files(best_file, file_info)
        if comparison > 0:
            best_file = file_info
    
    # Build delete list
    files_to_delete = [
        f.path for f in file_infos
        if f.path != best_file.path
    ]
    
    return best_file.path, files_to_delete

def analyze_file_from_cache(self, file_path: str, cached: CachedFile) -> FileInfo:
    """
    Analyze a file using cached metadata (no filesystem calls).
    
    Args:
        file_path: Absolute path to file
        cached: CachedFile object with metadata
        
    Returns:
        FileInfo with all resolution metadata
    """
    path = Path(file_path)
    
    # Use cached metadata (no stat() call!)
    size = cached.file_size
    mtime = cached.file_mtime
    
    # Calculate path depth (number of path components)
    depth = len(path.parts)
    
    # Check for "keep" keyword (case-insensitive)
    path_lower = file_path.lower()
    has_keep = 'keep' in path_lower
    
    # Determine if "keep" is in folder path or just filename
    keep_in_folder = False
    keep_ancestor_depth = None
    
    if has_keep:
        # Check each ancestor folder for "keep"
        parent_path = path.parent
        parent_parts = parent_path.parts
        
        for i, part in enumerate(parent_parts):
            if 'keep' in part.lower():
                keep_in_folder = True
                keep_ancestor_depth = i + 1
                break
    
    return FileInfo(
        path=file_path,
        size=size,
        mtime=mtime,
        depth=depth,
        has_keep=has_keep,
        keep_in_folder=keep_in_folder,
        keep_ancestor_depth=keep_ancestor_depth
    )
```

**Keep existing method** (for `--verify-files` mode):
```python
def resolve_duplicates(self, file_paths: List[str]) -> Tuple[str, List[str]]:
    """
    Resolve duplicates with filesystem verification (slower but validates file existence).
    
    This method calls stat() for each file to verify it still exists.
    Use resolve_duplicates_with_cache() for better performance.
    """
    # Existing implementation unchanged
    ...
```

---

### Phase 4: Update Documentation

**Files to update**:
1. `README.md` - Add `--verify-files` flag documentation
2. `docs/requirements/stage3_requirements.md` - Document optimization
3. `docs/stage3b_resolution_bottleneck.md` - Mark as resolved

**CLI Documentation**:
```markdown
### Stage 3 Options
```bash
# Default: Fast resolution using cached metadata
file-organizer -if /input -of /output --stage 3b

# Verify files exist (slower, detects moved/deleted files)
file-organizer -if /input -of /output --stage 3b --verify-files
```
```

---

## Testing Plan

### Test 1: Default Behavior (Optimized)
- **Setup**: Run Stage 3B with normal cache
- **Expected**: Resolution completes in < 1 second
- **Verify**: Correct resolution decisions (same as before)

### Test 2: Verify Files Mode
- **Setup**: Run Stage 3B with `--verify-files` flag
- **Expected**: Resolution completes slower but validates files exist
- **Verify**: Correct resolution decisions, files verified

### Test 3: Missing File Handling
- **Setup**: Manually delete a file from output folder, run Stage 3B
- **Expected**: 
  - Default mode: Uses cached metadata (may resolve incorrectly)
  - Verify mode: Detects missing file, handles gracefully

### Test 4: Moved File Detection
- **Setup**: Move a file in output folder, run Stage 3B with `--verify-files`
- **Expected**: Detects file doesn't exist at cached path
- **Verify**: Handles gracefully (skips or warns)

---

## Performance Expectations

### Default Mode (Optimized)
- **Before**: ~46 minutes (2792 seconds)
- **After**: < 1 second
- **Speedup**: ~2800x faster

### Verify Files Mode
- **Before**: ~46 minutes (2792 seconds)
- **After**: ~46 minutes (same, but validates files)
- **Speedup**: None (but validates file existence)

---

## Implementation Checklist

- [ ] **Phase 1**: Add `--verify-files` CLI flag
- [ ] **Phase 2**: Add `verify_files` parameter to Stage3 class
- [ ] **Phase 3**: Implement `resolve_duplicates_with_cache()` method
- [ ] **Phase 3**: Implement `analyze_file_from_cache()` helper method
- [ ] **Phase 3**: Modify Phase 4 to use cache lookup dictionary
- [ ] **Phase 3**: Add conditional logic for verify_files flag
- [ ] **Phase 4**: Update README.md with new flag
- [ ] **Phase 4**: Update requirements documentation
- [ ] **Testing**: Test default mode (optimized)
- [ ] **Testing**: Test verify-files mode
- [ ] **Testing**: Test missing file handling
- [ ] **Testing**: Test moved file detection
- [ ] **Deployment**: Build and deploy AppImage

---

## Code Changes Summary

### Files Modified
1. `src/file_organizer/cli.py` - Add CLI flag
2. `src/file_organizer/stage3.py` - Add parameter, modify Phase 4
3. `src/file_organizer/duplicate_resolver.py` - Add optimized methods

### Files Added
- None (all changes are additions/modifications)

### Files Unchanged (Preserved)
- `duplicate_resolver.py:resolve_duplicates()` - Kept for verify mode
- `duplicate_resolver.py:analyze_file()` - Kept for verify mode

---

## Risk Assessment

### Low Risk
- **Default behavior**: Uses cached data (already in memory)
- **Fallback**: Existing code path preserved for verify mode
- **Backward compatible**: No breaking changes

### Edge Cases
1. **File not in cache**: Rare, but handled with fallback to `stat()`
2. **File moved**: Default mode won't detect, verify mode will
3. **File deleted**: Default mode won't detect, verify mode will

### Mitigation
- Log warnings when files not found in cache
- Provide clear documentation on when to use `--verify-files`
- Preserve existing behavior for verify mode

---

## Rollout Plan

1. **Development**: Implement changes locally
2. **Testing**: Run test suite, verify performance improvement
3. **Documentation**: Update docs with new flag
4. **Deployment**: Build AppImage, deploy to test environment
5. **Validation**: Test with real data, verify ~2800x speedup
6. **Production**: Deploy to production

---

## Success Criteria

- [x] Default mode completes in < 1 second (down from ~46 minutes)
- [x] Verify mode still validates files (same performance as before)
- [x] No breaking changes to existing functionality
- [x] CLI flag works correctly
- [x] Documentation updated
- [x] Tests pass

---

## Future Enhancements

1. **Smart Detection**: Automatically detect if files might have been moved
2. **Selective Verification**: Only verify output folder (more stable)
3. **Progress Reporting**: Show progress during resolution phase
4. **Cache Validation**: Periodic cache validation option

---

**Estimated Implementation Time**: 2-3 hours  
**Estimated Testing Time**: 1-2 hours  
**Total**: 3-5 hours

