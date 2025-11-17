# Theme G: Edge Cases & Logic
## Remediation Plan

**Priority:** MEDIUM  
**Issues:** 15  
**Estimated Effort:** 18-28 hours  
**Complexity:** MEDIUM  
**ROI:** MEDIUM

**Related Documents:**
- [Main Remediation Plan](./REMEDIATION_PLAN_V3.md)
- [Theme A: Error Handling](./REMEDIATION_PLAN_THEME_A.md)

---

## Overview

Theme G addresses edge cases and logic issues that could cause unexpected behavior, infinite loops, or data corruption in unusual scenarios.

### Issue Summary

| ID | Issue | Priority | Effort | Phase |
|----|-------|----------|--------|-------|
| G1 | Infinite collision loop potential | MEDIUM | 3h | 3 |
| G2 | Filename truncation edge case | MEDIUM | 2h | 3 |
| G3 | Concurrent file modification race | MEDIUM | 2h | 3 |
| G4 | Empty filename after sanitization | MEDIUM | 2h | 3 |
| G5 | Hash collision false positives | MEDIUM | 2h | 3 |
| G6 | Extremely deep directory trees | MEDIUM | 2h | 3 |
| G7 | Files modified during Stage 3 | MEDIUM | 2h | 3 |
| G8 | Partial Stage 4 failure with no rollback | MEDIUM | 3h | 3 |
| G9 | Stage 3B cache invalidation | MEDIUM | 2h | 3 |
| G10 | Flattening order dependency | MEDIUM | 2h | 3 |
| G11 | Ownership change always fails on non-root | LOW | 1h | 4 |
| G12 | No resume/recovery capability | LOW | 8h | 4 |
| G13 | No undo/rollback functionality | LOW | 6h | 4 |
| G14 | No parallel processing | LOW | 4h | 4 |
| G15 | No incremental mode | LOW | 3h | 4 |

---

## Medium Priority Issues

### Issue G1: Infinite Collision Loop Potential

**Problem:**
If collision resolution creates new collisions, could loop infinitely.

**Solution:**
- Add maximum collision resolution attempts
- Detect circular collision patterns
- Fail gracefully after max attempts

**Estimated Effort:** 3 hours  
**Phase:** 3

---

### Issue G2: Filename Truncation Edge Case

**Problem:**
Very long filenames may truncate incorrectly, losing important information.

**Solution:**
- Improve truncation algorithm
- Preserve extension
- Handle edge cases

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G3: Concurrent File Modification Race

**Problem:**
If files are modified during processing, could cause inconsistencies.

**Solution:**
- Detect file modifications
- Handle concurrent modifications
- Validate file state

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G4: Empty Filename After Sanitization

**Problem:**
Some filenames may become empty after sanitization.

**Solution:**
- Handle empty filenames
- Provide default names
- Validate after sanitization

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G5: Hash Collision False Positives

**Problem:**
Hash collisions (different files, same hash) could cause false duplicates.

**Solution:**
- Use stronger hash algorithm if needed
- Verify duplicates by content comparison
- Handle hash collisions

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G6: Extremely Deep Directory Trees

**Problem:**
Very deep directory structures could cause stack overflow or performance issues.

**Solution:**
- Use iterative instead of recursive algorithms
- Limit recursion depth
- Handle deep trees efficiently

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G7: Files Modified During Stage 3

**Problem:**
If files are modified during hashing, hash may be incorrect.

**Solution:**
- Detect file modifications
- Re-hash modified files
- Handle modification scenarios

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G8: Partial Stage 4 Failure with No Rollback

**Problem:**
If Stage 4 fails partway through, some files may be moved while others are not.

**Solution:**
- Implement transaction-like pattern
- Track operations for rollback
- Provide recovery mechanism

**Estimated Effort:** 3 hours  
**Phase:** 3

---

### Issue G9: Stage 3B Cache Invalidation

**Problem:**
Cache may become invalid if files are modified between stages.

**Solution:**
- Validate cache entries
- Invalidate stale cache
- Rebuild cache if needed

**Estimated Effort:** 2 hours  
**Phase:** 3

---

### Issue G10: Flattening Order Dependency

**Problem:**
Flattening order may affect results in unexpected ways.

**Solution:**
- Document order dependencies
- Make order deterministic
- Test order variations

**Estimated Effort:** 2 hours  
**Phase:** 3

---

## Low Priority Issues

### Issue G11: Ownership Change Always Fails on Non-Root

**Problem:**
Ownership changes always fail for non-root users, but error is not clear.

**Solution:**
- Check root status before attempting
- Provide clear error messages
- Document requirements

**Estimated Effort:** 1 hour  
**Phase:** 4

---

### Issue G12: No Resume/Recovery Capability

**Problem:**
If process is interrupted, must start from beginning.

**Solution:**
- Implement checkpoint system
- Save progress state
- Resume from checkpoint

**Estimated Effort:** 8 hours  
**Phase:** 4

---

### Issue G13: No Undo/Rollback Functionality

**Problem:**
No way to undo file operations if mistakes are made.

**Solution:**
- Implement operation log
- Provide undo capability
- Support rollback

**Estimated Effort:** 6 hours  
**Phase:** 4

---

### Issue G14: No Parallel Processing

**Problem:**
Operations are sequential, could be parallelized for performance.

**Solution:**
- Implement parallel processing
- Use multiprocessing or threading
- Maintain thread safety

**Estimated Effort:** 4 hours  
**Phase:** 4

---

### Issue G15: No Incremental Mode

**Problem:**
Must process all files even if only some changed.

**Solution:**
- Implement incremental mode
- Track file changes
- Process only changed files

**Estimated Effort:** 3 hours  
**Phase:** 4

---

## Implementation Plan

### Phase 3 (Weeks 4-5) - 18 hours
- ✅ G1: Infinite loop prevention (3h)
- ✅ G2: Filename truncation (2h)
- ✅ G3: Concurrent modification (2h)
- ✅ G4: Empty filename handling (2h)
- ✅ G5: Hash collision handling (2h)
- ✅ G6: Deep directory trees (2h)
- ✅ G7: Files modified during processing (2h)
- ✅ G8: Partial failure rollback (3h)
- ✅ G9: Cache invalidation (2h)
- ✅ G10: Flattening order (2h)

### Phase 4 (Week 6+) - 22 hours
- ⭐ G11: Ownership change clarity (1h)
- ⭐ G12: Resume/recovery (8h)
- ⭐ G13: Undo/rollback (6h)
- ⭐ G14: Parallel processing (4h)
- ⭐ G15: Incremental mode (3h)

---

## Success Criteria

- ✅ No infinite loops
- ✅ All edge cases handled
- ✅ Race conditions prevented
- ✅ Graceful failure handling
- ✅ Recovery mechanisms in place
- ✅ Advanced features available (Phase 4)

---

**Back to:** [Main Remediation Plan](./REMEDIATION_PLAN_V3.md)

