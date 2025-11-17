# Testing & Documentation Audit

**Date**: November 17, 2025
**Purpose**: Comprehensive review of test coverage and documentation completeness
**Reference**: Modeled after `progress_reporting_audit.md`

---

## Executive Summary

Conducted comprehensive audit of testing and documentation for the dl-organize project (5,853 lines of code, 130 functions, 18 classes). Found **excellent high-level documentation** but **critical gaps in automated testing**.

### Key Findings

**Testing Coverage**: ❌ **CRITICAL GAPS**
- Only **1 pytest file** with 27 tests (covers Stage 3 optimizations only)
- **~5% test coverage** of total codebase
- **8 of 12 modules** have ZERO automated tests
- No integration tests for full pipeline (Stages 1-2-3A-3B-4)
- No edge case or error handling tests

**Documentation**: ✅ **EXCELLENT** (with minor gaps)
- 1,600+ lines of comprehensive requirements documentation
- Well-documented inline code (docstrings present)
- Good README and onboarding guide
- Missing: API reference, testing guide, troubleshooting docs

### Priority Recommendations

**Immediate (High Priority)**:
1. Add unit tests for critical path modules (Stage 1, 2, 4)
2. Add integration tests for full pipeline
3. Add tests for error handling and edge cases
4. Create testing guide for contributors

**Important (Medium Priority)**:
5. Add tests for utility modules (config, CLI, progress_bar)
6. Add API/code reference documentation
7. Add troubleshooting guide

**Nice-to-Have (Low Priority)**:
8. Add performance regression tests
9. Add code coverage reporting (pytest-cov)
10. Add examples and tutorials

---

## Section 1: Current Test Coverage

### 1.1 Existing Tests ✓

#### File: `tests/test_stage3_optimizations.py` (432 lines)
**Coverage**: Stage 3 optimizations only

**Test Classes**:
1. `TestBatchQueryOptimization` (7 tests)
   - ✓ `test_get_files_by_paths_empty_list`
   - ✓ `test_get_files_by_paths_small_list`
   - ✓ `test_get_files_by_paths_large_list`
   - ✓ `test_get_files_by_paths_nonexistent_paths`
   - ✓ `test_get_files_by_paths_different_folders`
   - ✓ `test_duplicate_detector_uses_batch_query`

2. `TestStage3BCacheOptimization` (5 tests)
   - ✓ `test_input_files_cached_after_phase1`
   - ✓ `test_find_cross_folder_reuses_cached_input`
   - ✓ `test_incremental_reload_only_updates_hashed_files`
   - ✓ `test_incremental_reload_updates_dictionaries`

3. `TestPerformanceImprovements` (1 test)
   - ✓ `test_batch_query_vs_get_all_files_performance`

**Total**: 13 test methods covering HashCache batch queries and Stage 3B cache optimization

**Status**: ✅ Excellent coverage for Stage 3 optimizations

#### File: `test_progress.py` (82 lines)
**Type**: Manual test script (not pytest)

**Coverage**: ProgressBar and SimpleProgress classes

**Tests**:
- Test 1: Non-verbose progress bar
- Test 2: Verbose progress bar with stats
- Test 3: SimpleProgress counter
- Test 4: Fast operation (skip progress bar)

**Status**: ⚠️ Manual script, not integrated into automated test suite

---

### 1.2 Test Coverage Analysis

| Module | Lines | Functions | Classes | Test Coverage | Status |
|--------|-------|-----------|---------|---------------|--------|
| **stage1.py** | 393 | ~15 | 1 | ❌ **0%** | **CRITICAL** |
| **stage2.py** | 556 | ~20 | 1 | ❌ **0%** | **CRITICAL** |
| **stage3.py** | 960 | ~35 | 2 | ⚠️ **~30%** | Partial (optimizations only) |
| **stage4.py** | 663 | ~25 | 3 | ❌ **0%** | **CRITICAL** |
| **cli.py** | 458 | ~15 | 0 | ❌ **0%** | **CRITICAL** |
| **config.py** | 560 | ~15 | 1 | ❌ **0%** | **CRITICAL** |
| **filename_cleaner.py** | 261 | ~8 | 1 | ❌ **0%** | **CRITICAL** |
| **hash_cache.py** | 684 | ~20 | 2 | ✅ **~60%** | Good (batch queries) |
| **duplicate_detector.py** | 563 | ~12 | 3 | ⚠️ **~20%** | Partial (mocked only) |
| **duplicate_resolver.py** | 459 | ~10 | 2 | ❌ **0%** | **CRITICAL** |
| **progress_bar.py** | 251 | ~10 | 2 | ⚠️ Manual only | Needs pytest |
| **__init__.py** | 17 | 1 | 0 | N/A | N/A |
| **__main__.py** | 28 | 1 | 0 | N/A | N/A |

**Overall Coverage**: ~5-10% of codebase has automated tests

---

## Section 2: Critical Paths Lacking Testing

### 2.1 Stage 1: Filename Detoxification (HIGH PRIORITY)

**File**: `stage1.py` (393 lines)
**Test Coverage**: ❌ **0%**

#### Critical Paths to Test

##### Path 1: Filename Sanitization
**Location**: `filename_cleaner.py:sanitize_filename()` (lines 39-107)

**Functionality**:
- ASCII transliteration (café → cafe)
- Lowercase conversion
- Special character removal
- Extension normalization
- Collision resolution

**Why Critical**:
- Core functionality of Stage 1
- Handles 100k+ files
- Data loss risk if bugs present
- Complex edge cases (unicode, special chars)

**Test Scenarios Needed**:
```python
def test_sanitize_basic_filename():
    # "My File.txt" → "my_file.txt"

def test_sanitize_unicode():
    # "café_résumé.pdf" → "cafe_resume.pdf"

def test_sanitize_special_characters():
    # "file@#$%^&*.txt" → "file.txt"

def test_sanitize_multiple_extensions():
    # "archive.tar.gz" → "archive_tar.gz"

def test_sanitize_long_filename():
    # 300 char filename → truncated to 200

def test_collision_detection():
    # Two files → file_20251117_1.txt, file_20251117_2.txt
```

##### Path 2: Directory Scanning
**Location**: `stage1.py:_scan_directory()` (lines 108-131)

**Why Critical**:
- First operation, sets up entire pipeline
- Must handle large directories (100k+ files)
- Error here breaks everything downstream

**Test Scenarios Needed**:
```python
def test_scan_empty_directory()
def test_scan_nested_directories()
def test_scan_with_symlinks()  # Should skip
def test_scan_with_dotfiles()  # Should skip
def test_scan_with_permissions_error()
```

##### Path 3: File Processing
**Location**: `stage1.py:_process_files()` (lines 133-180)

**Why Critical**:
- Renames files in place (data risk)
- Handles collisions
- Must preserve directory structure

**Test Scenarios Needed**:
```python
def test_process_files_basic()
def test_process_files_with_collisions()
def test_process_files_dry_run()  # No changes
def test_process_files_execute()  # Actual renames
```

**Impact Estimate**: Stage 1 processes 25k-30k files/second. Bugs could corrupt 100k+ filenames.

---

### 2.2 Stage 2: Folder Optimization (HIGH PRIORITY)

**File**: `stage2.py` (556 lines)
**Test Coverage**: ❌ **0%**

#### Critical Paths to Test

##### Path 1: Empty Folder Removal
**Location**: `stage2.py:_remove_empty_folders()` (lines 120-169)

**Why Critical**:
- Deletes folders (destructive operation)
- Must handle nested empty folders
- Edge case: folder becomes empty after child removal

**Test Scenarios Needed**:
```python
def test_remove_empty_folders_single()
def test_remove_empty_folders_nested()
def test_remove_empty_folders_with_dotfiles()  # Should still remove
def test_remove_empty_folders_multipass()  # Iterative removal
```

##### Path 2: Folder Flattening
**Location**: `stage2.py:_flatten_folders_iterative()` (lines 171-229)

**Why Critical**:
- Moves files across directories
- Must respect threshold (default: 5 items)
- Collision handling

**Test Scenarios Needed**:
```python
def test_flatten_below_threshold()  # 3 items → flatten
def test_flatten_above_threshold()  # 10 items → keep
def test_flatten_with_collisions()
def test_flatten_multipass()  # Iterative until stable
```

##### Path 3: Configuration Loading
**Location**: `config.py:load_config()` (lines 90-180)

**Why Critical**:
- Determines all stage behavior
- Precedence: CLI > YAML > defaults
- Invalid config could break pipeline

**Test Scenarios Needed**:
```python
def test_load_config_defaults()
def test_load_config_from_yaml()
def test_load_config_cli_override()
def test_load_config_invalid_yaml()  # Error handling
def test_load_config_precedence()
```

**Impact Estimate**: Stage 2 can delete thousands of folders. Incorrect logic = data loss.

---

### 2.3 Stage 3: Duplicate Detection (MEDIUM PRIORITY)

**File**: `stage3.py` (960 lines)
**Test Coverage**: ⚠️ **~30%** (optimizations only)

#### Gaps in Current Coverage

**Tested** ✅:
- Batch query optimization (`get_files_by_paths`)
- Cache reuse in Stage 3B
- Incremental reload

**NOT Tested** ❌:
- Full duplicate detection workflow
- Resolution policy (three-tier: keep/depth/mtime)
- Cross-folder duplicate finding logic
- Deletion execution
- Error handling (file moved/deleted during scan)

#### Critical Paths to Test

##### Path 1: Duplicate Resolution Policy
**Location**: `duplicate_resolver.py:resolve_duplicates()` (lines 150-300)

**Why Critical**:
- Decides which files to DELETE
- Complex three-tier policy
- Bugs = wrong files deleted

**Test Scenarios Needed**:
```python
def test_resolution_keep_keyword_wins()
    # File with "keep" in path beats others

def test_resolution_keep_folder_vs_filename()
    # Folder "keep" beats filename "keep"

def test_resolution_depth_tiebreaker()
    # Deeper path wins if no "keep"

def test_resolution_mtime_tiebreaker()
    # Newest file wins if same depth

def test_resolution_full_policy()
    # Test all tiers together
```

##### Path 2: Hash Cache Operations
**Location**: `hash_cache.py` (684 lines)

**Current Coverage**: ⚠️ Batch queries only

**Missing Tests**:
```python
def test_save_to_cache()
def test_get_from_cache()
def test_cache_invalidation()  # File changed
def test_cache_persistence()  # Close and reopen
def test_cache_migration()  # Schema changes
```

##### Path 3: Duplicate Detector
**Location**: `duplicate_detector.py:detect_duplicates()` (lines 100-350)

**Why Critical**:
- Orchestrates metadata filtering → hashing → grouping
- Must skip images if configured
- Must respect min_file_size

**Test Scenarios Needed**:
```python
def test_detect_duplicates_basic()
def test_detect_duplicates_skip_images()
def test_detect_duplicates_min_size()
def test_detect_duplicates_no_size_collision()  # Skip hashing
def test_detect_duplicates_progress_callback()
```

**Impact Estimate**: Stage 3 deletes duplicates. Wrong resolution = data loss.

---

### 2.4 Stage 4: File Relocation (HIGH PRIORITY)

**File**: `stage4.py` (663 lines)
**Test Coverage**: ❌ **0%**

#### Critical Paths to Test

##### Path 1: Disk Space Validation
**Location**: `stage4.py:_validate_relocation()` (lines 150-240)

**Why Critical**:
- Must ensure enough space before moving files
- 10% safety margin
- Prevents out-of-space errors

**Test Scenarios Needed**:
```python
def test_validate_enough_space()
def test_validate_insufficient_space()  # Should abort
def test_validate_safety_margin()  # 10% buffer
def test_validate_same_filesystem()  # Fast move
def test_validate_different_filesystem()  # Requires copy
```

##### Path 2: File Relocation
**Location**: `stage4.py:_relocate_files()` (lines 271-318)

**Why Critical**:
- Moves 100k+ files
- Must preserve directory structure
- Top-level files → misc/

**Test Scenarios Needed**:
```python
def test_relocate_basic()
def test_relocate_top_level_files()  # → misc/
def test_relocate_nested_structure()  # Preserve structure
def test_relocate_with_collisions()
def test_relocate_progress_reporting()
```

##### Path 3: Input Cleanup
**Location**: `stage4.py:_cleanup_input_folder()` (lines 371-388)

**Why Critical**:
- Deletes input folder contents
- Must preserve root directory
- Optional (--preserve-input flag)

**Test Scenarios Needed**:
```python
def test_cleanup_removes_contents()
def test_cleanup_preserves_root()
def test_cleanup_respects_preserve_flag()
def test_cleanup_with_errors()  # Some files locked
```

**Impact Estimate**: Stage 4 moves all organized files. Bugs could lose access to 100k+ files.

---

### 2.5 CLI & Error Handling (MEDIUM PRIORITY)

**File**: `cli.py` (458 lines)
**Test Coverage**: ❌ **0%**

#### Critical Paths to Test

##### Path 1: Argument Parsing
**Location**: `cli.py:parse_args()` (lines 50-150)

**Test Scenarios Needed**:
```python
def test_parse_args_minimal()  # Just -if
def test_parse_args_all_stages()  # No --stage
def test_parse_args_specific_stage()  # --stage 1
def test_parse_args_output_folder()  # -of triggers 3B, 4
def test_parse_args_dry_run_default()  # No --execute
def test_parse_args_invalid_input()  # Missing -if
```

##### Path 2: Stage Orchestration
**Location**: `cli.py:main()` (lines 200-400)

**Why Critical**:
- Coordinates all stages
- Handles errors between stages
- Validates preconditions

**Test Scenarios Needed**:
```python
def test_orchestration_all_stages()
def test_orchestration_stage1_only()
def test_orchestration_stage3b_requires_output()
def test_orchestration_error_handling()
def test_orchestration_dry_run()
```

##### Path 3: System Directory Protection
**Location**: `cli.py:_validate_paths()` (lines 180-200)

**Why Critical**:
- Prevents operations on /, /usr, /etc
- Safety feature

**Test Scenarios Needed**:
```python
def test_validate_paths_blocks_root()
def test_validate_paths_blocks_system_dirs()
def test_validate_paths_allows_home()
def test_validate_paths_allows_tmp()
```

---

### 2.6 Progress Reporting (LOW PRIORITY)

**File**: `progress_bar.py` (251 lines)
**Test Coverage**: ⚠️ Manual tests only

**Why Lower Priority**: Manual tests exist, visual component

**Gaps**:
- No automated pytest tests
- No tests for adaptive interval calculation
- No tests for verbose vs. non-verbose modes

**Test Scenarios Needed**:
```python
def test_progress_bar_updates()
def test_progress_bar_adaptive_interval()
def test_progress_bar_verbose_mode()
def test_progress_bar_min_duration()
def test_simple_progress_counter()
```

---

## Section 3: Integration Tests (CRITICAL GAP)

### 3.1 Missing Integration Tests

**Current Status**: ❌ **ZERO integration tests**

#### Needed Integration Tests

##### Test 1: Full Pipeline (Stages 1-2-3A-3B-4)
```python
def test_full_pipeline_with_output():
    """
    Test complete workflow:
    1. Create messy input directory
    2. Run Stage 1 (filename cleaning)
    3. Run Stage 2 (folder optimization)
    4. Run Stage 3A (internal duplicates)
    5. Run Stage 3B (cross-folder duplicates)
    6. Run Stage 4 (relocation)
    7. Verify output folder correctness
    8. Verify input folder cleaned
    """
```

##### Test 2: Pipeline Without Output (Stages 1-2-3A)
```python
def test_pipeline_no_output():
    """
    Test in-place workflow:
    1. Run Stages 1-2-3A
    2. Verify input folder modified correctly
    3. Verify no output folder created
    """
```

##### Test 3: Error Recovery
```python
def test_pipeline_error_recovery():
    """
    Test error handling:
    1. Inject errors (permissions, locked files)
    2. Verify graceful handling
    3. Verify partial completion possible
    """
```

##### Test 4: Cache Persistence
```python
def test_cache_persistence_across_runs():
    """
    Test cache reuse:
    1. Run Stage 3A (first run, populates cache)
    2. Exit
    3. Run Stage 3A again (second run, uses cache)
    4. Verify performance improvement
    """
```

##### Test 5: Configuration Integration
```python
def test_configuration_end_to_end():
    """
    Test config precedence:
    1. Create .file_organizer.yaml
    2. Run with CLI overrides
    3. Verify CLI wins
    4. Verify YAML overrides defaults
    """
```

**Impact**: Integration tests catch bugs that unit tests miss (data flow, state management).

---

## Section 4: Edge Cases & Error Handling

### 4.1 Edge Cases Lacking Tests

#### Filesystem Edge Cases
- ❌ Files with permission errors (can't read/write)
- ❌ Files locked by other processes
- ❌ Symlinks (should skip)
- ❌ Hard links (how to handle?)
- ❌ Files > 2GB (hash performance)
- ❌ Filenames near 255 char limit
- ❌ Unicode normalization issues (NFC vs NFD)
- ❌ Case-insensitive filesystems (macOS)

#### Resource Edge Cases
- ❌ Out of disk space (mid-operation)
- ❌ Out of memory (100k+ files in RAM)
- ❌ SQLite database corruption
- ❌ Cache database locked by another process

#### Data Edge Cases
- ❌ Empty files (0 bytes)
- ❌ Duplicate filenames same directory
- ❌ Circular symlinks
- ❌ Files modified during scan (mtime changes)
- ❌ Files deleted during scan

#### Configuration Edge Cases
- ❌ Invalid YAML syntax
- ❌ Invalid config values (negative numbers, etc.)
- ❌ Config file permissions error

**Recommendation**: Create edge case test suite with 30-50 tests.

---

### 4.2 Error Handling Tests Needed

#### Critical Error Paths
```python
def test_error_handling_file_not_found():
    # File deleted between scan and process

def test_error_handling_permission_denied():
    # Can't read/write file

def test_error_handling_disk_full():
    # Out of space during Stage 4

def test_error_handling_cache_corruption():
    # SQLite database corrupted

def test_error_handling_invalid_utf8():
    # Filename with invalid UTF-8

def test_error_handling_interrupted_operation():
    # User Ctrl+C mid-operation
```

**Impact**: Error handling tests prevent crashes and data loss.

---

## Section 5: Documentation Review

### 5.1 Current Documentation ✅ **EXCELLENT**

#### High-Level Documentation (1,600+ lines)

**Files Reviewed**:
- ✅ `README.md` (380 lines) - Comprehensive project overview
- ✅ `docs/onboarding.md` (150+ lines) - Good contributor guide
- ✅ `docs/requirements.md` - High-level requirements
- ✅ `docs/stage1_requirements.md` (505 lines) - Detailed Stage 1 specs
- ✅ `docs/stage2_requirements.md` (580 lines) - Detailed Stage 2 specs
- ✅ `docs/stage3_requirements.md` - Stage 3 specifications
- ✅ `docs/design_decisions.md` (29 decisions) - Excellent rationale
- ✅ `docs/project-phases.md` - Roadmap
- ✅ `docs/progress_reporting_audit.md` - Example audit (reference)

**Strengths**:
- Clear project structure
- Detailed requirements for each stage
- Design decisions well documented
- Good onboarding guide

**Status**: ✅ **Excellent coverage**

---

#### Inline Documentation ✅ **GOOD**

**Reviewed Files**:
- ✅ `filename_cleaner.py` - Good docstrings
- ✅ `duplicate_resolver.py` - Good docstrings
- ✅ All classes have docstrings
- ✅ Most functions have docstrings

**Example** (from `filename_cleaner.py`):
```python
def sanitize_filename(self, filename: str, is_directory: bool = False) -> str:
    """
    Sanitize a single filename according to Stage 1 rules.

    Args:
        filename: Original filename to sanitize
        is_directory: True if this is a directory name

    Returns:
        Sanitized filename

    Rules applied:
    1. Transliterate non-ASCII characters
    2. Convert to lowercase
    ...
    """
```

**Status**: ✅ **Good inline documentation**

---

### 5.2 Documentation Gaps ⚠️

#### Missing: API/Code Reference
**Gap**: No comprehensive API documentation

**Needed**:
- Module-level API reference
- Class diagrams
- Data flow diagrams
- Function reference with examples

**Recommendation**: Generate with Sphinx or pdoc
```bash
# Example with pdoc
pdoc --html src/file_organizer -o docs/api
```

**Priority**: **Medium** (helps contributors)

---

#### Missing: Testing Guide
**Gap**: No guide for writing tests

**Needed**:
- How to run tests (`pytest`)
- How to write new tests
- Test structure and conventions
- How to generate coverage reports
- How to mock filesystem operations

**Recommendation**: Create `docs/testing_guide.md`

**Example Content**:
```markdown
# Testing Guide

## Running Tests
pytest tests/ -v

## Running with Coverage
pytest tests/ --cov=src/file_organizer --cov-report=html

## Writing Tests
- Use pytest fixtures for test data
- Use tempfile for filesystem tests
- Mock external dependencies
- Follow naming: test_<module>_<function>_<scenario>
```

**Priority**: **High** (blocks contributor testing)

---

#### Missing: Troubleshooting Guide
**Gap**: No troubleshooting documentation

**Needed**:
- Common errors and solutions
- How to debug issues
- How to report bugs
- Performance troubleshooting

**Recommendation**: Create `docs/troubleshooting.md`

**Example Content**:
```markdown
# Troubleshooting

## Common Errors

### Error: "Permission denied"
**Cause**: Insufficient permissions on input directory
**Solution**: Run with appropriate permissions or change ownership

### Error: "Out of disk space"
**Cause**: Not enough space in output directory
**Solution**: Free up space or use different output directory

## Performance Issues

### Slow Stage 3A (first run)
**Expected**: First run hashes all files (60+ min for 100k files)
**Solution**: Subsequent runs use cache (~5 min)
```

**Priority**: **Medium** (helps users)

---

#### Missing: Examples & Tutorials
**Gap**: No step-by-step tutorials

**Needed**:
- Tutorial: Basic usage walkthrough
- Tutorial: Advanced configuration
- Tutorial: Recovery from errors
- Examples: Common use cases

**Recommendation**: Create `docs/tutorials/` directory

**Priority**: **Low** (nice-to-have)

---

#### Missing: CONTRIBUTING.md
**Gap**: No formal contribution guidelines

**Needed**:
- Code style guide (PEP 8)
- Git workflow (branching, commits)
- Pull request process
- Testing requirements
- Documentation requirements

**Recommendation**: Create `CONTRIBUTING.md` in root

**Priority**: **Medium** (helps contributors)

---

### 5.3 Documentation Status Summary

| Document Type | Status | Priority | Notes |
|---------------|--------|----------|-------|
| **README** | ✅ Excellent | N/A | Comprehensive |
| **Requirements** | ✅ Excellent | N/A | 1,600+ lines |
| **Onboarding** | ✅ Good | N/A | Clear structure |
| **Inline docs** | ✅ Good | N/A | Docstrings present |
| **API Reference** | ❌ Missing | **Medium** | Use Sphinx/pdoc |
| **Testing Guide** | ❌ Missing | **High** | Blocks contributors |
| **Troubleshooting** | ❌ Missing | **Medium** | Helps users |
| **Tutorials** | ❌ Missing | Low | Nice-to-have |
| **CONTRIBUTING** | ❌ Missing | **Medium** | Standard practice |
| **Design docs** | ✅ Excellent | N/A | 29 decisions |

---

## Section 6: Test Recommendations by Priority

### 6.1 Immediate Priority (Must Have)

#### 1. Stage 1 Unit Tests
**File**: Create `tests/test_stage1.py`

**Estimated Tests**: 20-25 tests

**Key Tests**:
- Filename sanitization (10 tests)
  - Basic, unicode, special chars, extensions, length
- Directory scanning (5 tests)
  - Empty, nested, symlinks, dotfiles, errors
- File processing (5 tests)
  - Basic, collisions, dry-run, execute
- Integration (3 tests)
  - Full Stage 1 workflow

**Rationale**: Stage 1 is first in pipeline, touches all files

**Estimated Effort**: 4-6 hours

---

#### 2. Stage 2 Unit Tests
**File**: Create `tests/test_stage2.py`

**Estimated Tests**: 15-20 tests

**Key Tests**:
- Empty folder removal (5 tests)
- Folder flattening (5 tests)
- Folder name sanitization (3 tests)
- Integration (3 tests)

**Rationale**: Stage 2 deletes folders (data loss risk)

**Estimated Effort**: 3-5 hours

---

#### 3. Stage 4 Unit Tests
**File**: Create `tests/test_stage4.py`

**Estimated Tests**: 15-20 tests

**Key Tests**:
- Disk space validation (5 tests)
- File relocation (5 tests)
- Input cleanup (3 tests)
- Integration (3 tests)

**Rationale**: Stage 4 moves all files (critical path)

**Estimated Effort**: 3-5 hours

---

#### 4. Duplicate Resolver Tests
**File**: Create `tests/test_duplicate_resolver.py`

**Estimated Tests**: 15-20 tests

**Key Tests**:
- Resolution policy tier 1 (keep keyword) (5 tests)
- Resolution policy tier 2 (depth) (3 tests)
- Resolution policy tier 3 (mtime) (3 tests)
- Full policy integration (4 tests)

**Rationale**: Decides which files to DELETE

**Estimated Effort**: 3-4 hours

---

#### 5. Full Pipeline Integration Tests
**File**: Create `tests/test_integration.py`

**Estimated Tests**: 10-15 tests

**Key Tests**:
- Full pipeline with output (3 tests)
- Pipeline without output (2 tests)
- Error recovery (3 tests)
- Cache persistence (2 tests)
- Configuration (2 tests)

**Rationale**: Catches bugs unit tests miss

**Estimated Effort**: 4-6 hours

---

### 6.2 Important Priority (Should Have)

#### 6. Config Module Tests
**File**: Create `tests/test_config.py`

**Estimated Tests**: 10-12 tests

**Key Tests**:
- Load defaults (2 tests)
- Load from YAML (3 tests)
- CLI override (3 tests)
- Precedence (2 tests)

**Estimated Effort**: 2-3 hours

---

#### 7. CLI Tests
**File**: Create `tests/test_cli.py`

**Estimated Tests**: 15-20 tests

**Key Tests**:
- Argument parsing (8 tests)
- Stage orchestration (5 tests)
- Path validation (3 tests)

**Estimated Effort**: 3-4 hours

---

#### 8. Hash Cache Tests (Expand)
**File**: Expand `tests/test_stage3_optimizations.py` or create `tests/test_hash_cache.py`

**Estimated Tests**: 10-15 new tests

**Key Tests**:
- Save/get operations (3 tests)
- Cache invalidation (3 tests)
- Cache persistence (2 tests)
- Error handling (3 tests)

**Estimated Effort**: 2-3 hours

---

#### 9. Duplicate Detector Tests
**File**: Create `tests/test_duplicate_detector.py`

**Estimated Tests**: 10-15 tests

**Key Tests**:
- Basic detection (3 tests)
- Skip images (2 tests)
- Min file size (2 tests)
- Metadata filtering (3 tests)

**Estimated Effort**: 2-3 hours

---

### 6.3 Nice-to-Have Priority (Could Have)

#### 10. Progress Bar Tests
**File**: Convert `test_progress.py` to `tests/test_progress_bar.py`

**Estimated Tests**: 8-10 tests

**Estimated Effort**: 1-2 hours

---

#### 11. Edge Case Test Suite
**File**: Create `tests/test_edge_cases.py`

**Estimated Tests**: 30-50 tests

**Key Tests**:
- Filesystem edge cases (15 tests)
- Resource edge cases (10 tests)
- Data edge cases (15 tests)
- Configuration edge cases (5 tests)

**Estimated Effort**: 6-8 hours

---

#### 12. Error Handling Tests
**File**: Create `tests/test_error_handling.py`

**Estimated Tests**: 15-20 tests

**Estimated Effort**: 3-4 hours

---

#### 13. Performance Regression Tests
**File**: Create `tests/test_performance.py`

**Estimated Tests**: 5-10 tests

**Key Tests**:
- Stage 1 performance baseline
- Stage 2 performance baseline
- Stage 3A cache hit rate
- Stage 3A hashing speed
- Stage 4 relocation speed

**Estimated Effort**: 3-4 hours

---

### 6.4 Total Test Effort Estimate

| Priority | Tests | Hours | Status |
|----------|-------|-------|--------|
| **Immediate** (1-5) | 85-100 | 17-26 | ❌ 0% done |
| **Important** (6-9) | 45-62 | 9-13 | ⚠️ 20% done |
| **Nice-to-Have** (10-13) | 58-90 | 13-18 | ⚠️ 10% done |
| **TOTAL** | **188-252 tests** | **39-57 hours** | ❌ ~5% done |

**Current**: 13 automated tests (+ 4 manual)
**Target**: 188-252 automated tests
**Gap**: 175-239 tests needed

---

## Section 7: Documentation Recommendations

### 7.1 Immediate Priority

#### 1. Testing Guide
**File**: Create `docs/testing_guide.md`

**Content**:
- Running tests with pytest
- Writing new tests
- Test structure and conventions
- Coverage reporting
- Mocking filesystem operations

**Estimated Effort**: 2-3 hours

**Impact**: Enables contributors to write tests

---

#### 2. CONTRIBUTING.md
**File**: Create `CONTRIBUTING.md` in root

**Content**:
- Code style (PEP 8)
- Git workflow
- Testing requirements
- Documentation requirements
- Pull request process

**Estimated Effort**: 1-2 hours

**Impact**: Standard practice for open source

---

### 7.2 Important Priority

#### 3. API Reference
**File**: Generate `docs/api/` directory

**Method**: Use Sphinx or pdoc

**Commands**:
```bash
# Option 1: Sphinx
sphinx-quickstart docs/
sphinx-apidoc -o docs/source src/file_organizer

# Option 2: pdoc
pdoc --html src/file_organizer -o docs/api
```

**Estimated Effort**: 3-4 hours (setup + review)

**Impact**: Helps contributors understand code

---

#### 4. Troubleshooting Guide
**File**: Create `docs/troubleshooting.md`

**Content**:
- Common errors and solutions
- Performance troubleshooting
- Debugging tips
- How to report bugs

**Estimated Effort**: 2-3 hours

**Impact**: Reduces support burden

---

### 7.3 Nice-to-Have Priority

#### 5. Tutorials
**Files**: Create `docs/tutorials/` directory

**Tutorials**:
- Basic usage walkthrough
- Advanced configuration
- Recovery from errors
- Performance optimization

**Estimated Effort**: 4-6 hours

**Impact**: Improves user experience

---

#### 6. Architecture Documentation
**File**: Create `docs/architecture.md`

**Content**:
- System architecture diagrams
- Data flow diagrams
- Class diagrams
- Module dependencies

**Estimated Effort**: 3-4 hours

**Impact**: Helps new contributors

---

### 7.4 Documentation Effort Estimate

| Priority | Files | Hours | Status |
|----------|-------|-------|--------|
| **Immediate** | 2 | 3-5 | ❌ Missing |
| **Important** | 2 | 5-7 | ❌ Missing |
| **Nice-to-Have** | 2 | 7-10 | ❌ Missing |
| **TOTAL** | **6 files** | **15-22 hours** | ❌ 0% done |

---

## Section 8: Testing Best Practices (Reference)

### 8.1 Test Structure

```python
# tests/test_stage1.py
import pytest
import tempfile
from pathlib import Path
from src.file_organizer.stage1 import Stage1Processor

class TestFilenameSanitization:
    """Test filename sanitization functionality."""

    @pytest.fixture
    def cleaner(self):
        """Fixture: Create FilenameCleaner instance."""
        from src.file_organizer.filename_cleaner import FilenameCleaner
        return FilenameCleaner()

    def test_sanitize_basic(self, cleaner):
        """Test basic filename sanitization."""
        result = cleaner.sanitize_filename("My File.txt")
        assert result == "my_file.txt"

    def test_sanitize_unicode(self, cleaner):
        """Test unicode transliteration."""
        result = cleaner.sanitize_filename("café_résumé.pdf")
        assert result == "cafe_resume.pdf"
```

---

### 8.2 Filesystem Testing Pattern

```python
import tempfile
import shutil
from pathlib import Path

def test_stage1_workflow():
    """Test Stage 1 full workflow."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test files
        test_file = tmpdir / "My File.txt"
        test_file.write_text("test content")

        # Run Stage 1
        processor = Stage1Processor(tmpdir, dry_run=False)
        processor.run()

        # Verify result
        assert not test_file.exists()  # Old file gone
        assert (tmpdir / "my_file.txt").exists()  # New file exists
```

---

### 8.3 Mocking Example

```python
from unittest.mock import patch, MagicMock

def test_progress_callback():
    """Test progress callback is called."""
    with patch('src.file_organizer.duplicate_detector.DuplicateDetector._hash_file') as mock_hash:
        mock_hash.return_value = 'abc123'

        detector = DuplicateDetector(...)
        detector.detect_duplicates(test_dir, folder='test')

        # Verify hash was called
        assert mock_hash.call_count > 0
```

---

### 8.4 Parametrized Tests

```python
@pytest.mark.parametrize("input_name,expected", [
    ("My File.txt", "my_file.txt"),
    ("café.pdf", "cafe.pdf"),
    ("file@#$.txt", "file.txt"),
    ("archive.tar.gz", "archive_tar.gz"),
])
def test_sanitize_parametrized(cleaner, input_name, expected):
    """Test filename sanitization with multiple inputs."""
    result = cleaner.sanitize_filename(input_name)
    assert result == expected
```

---

## Section 9: Success Criteria

### 9.1 Test Coverage Goals

**Immediate Goals (3 months)**:
- ✅ 80%+ line coverage on critical modules (Stage 1, 2, 4, duplicate_resolver)
- ✅ 100% of public API tested
- ✅ Integration tests for all stage combinations
- ✅ Edge case test suite (30+ tests)

**Long-term Goals (6 months)**:
- ✅ 90%+ overall code coverage
- ✅ Performance regression tests
- ✅ Continuous integration (CI) setup
- ✅ Automated coverage reporting

---

### 9.2 Documentation Goals

**Immediate Goals (1 month)**:
- ✅ Testing guide published
- ✅ CONTRIBUTING.md created
- ✅ Troubleshooting guide published

**Long-term Goals (3 months)**:
- ✅ API reference generated
- ✅ Tutorials published
- ✅ Architecture documentation

---

## Section 10: Implementation Roadmap

### Phase 1: Critical Tests (Weeks 1-2)
**Tasks**:
1. Create `tests/test_stage1.py` (20-25 tests)
2. Create `tests/test_stage2.py` (15-20 tests)
3. Create `tests/test_stage4.py` (15-20 tests)
4. Create `tests/test_duplicate_resolver.py` (15-20 tests)

**Deliverable**: 65-85 tests, ~40% coverage on critical paths

---

### Phase 2: Integration Tests (Week 3)
**Tasks**:
1. Create `tests/test_integration.py` (10-15 tests)
2. Test full pipeline workflows
3. Test error recovery

**Deliverable**: Full pipeline tested end-to-end

---

### Phase 3: Support Modules (Week 4)
**Tasks**:
1. Create `tests/test_config.py` (10-12 tests)
2. Create `tests/test_cli.py` (15-20 tests)
3. Expand `tests/test_hash_cache.py` (10-15 tests)
4. Create `tests/test_duplicate_detector.py` (10-15 tests)

**Deliverable**: 45-62 tests, support modules covered

---

### Phase 4: Documentation (Week 5)
**Tasks**:
1. Create `docs/testing_guide.md`
2. Create `CONTRIBUTING.md`
3. Create `docs/troubleshooting.md`
4. Generate API reference

**Deliverable**: Complete contributor documentation

---

### Phase 5: Edge Cases & Polish (Week 6+)
**Tasks**:
1. Create `tests/test_edge_cases.py` (30-50 tests)
2. Create `tests/test_error_handling.py` (15-20 tests)
3. Convert `test_progress.py` to pytest
4. Create `tests/test_performance.py` (5-10 tests)
5. Create tutorials

**Deliverable**: Comprehensive test suite, 90%+ coverage

---

## Appendix A: Test File Templates

### Template: Unit Test File

```python
"""
Tests for <module_name>.

Tests:
1. <Category 1>
2. <Category 2>
"""

import pytest
import tempfile
from pathlib import Path
from src.file_organizer.<module> import <Class>


class Test<Category1>:
    """Test <category 1> functionality."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        # Setup code here
        yield
        # Teardown code here

    def test_<scenario_1>(self, setup):
        """Test <scenario 1>."""
        # Arrange
        # Act
        # Assert
        pass
```

---

### Template: Integration Test File

```python
"""
Integration tests for full pipeline.

Tests complete workflows across multiple stages.
"""

import pytest
import tempfile
from pathlib import Path
from src.file_organizer.cli import main


class TestFullPipeline:
    """Test full pipeline workflows."""

    @pytest.fixture
    def test_directory(self):
        """Create test directory with sample files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Create test structure
            yield tmpdir

    def test_pipeline_all_stages(self, test_directory):
        """Test running all stages."""
        # Test implementation
        pass
```

---

## Appendix B: Coverage Report Example

```bash
# Run tests with coverage
pytest tests/ --cov=src/file_organizer --cov-report=html --cov-report=term

# Expected output (after full implementation):
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/file_organizer/__init__.py              5      0   100%
src/file_organizer/stage1.py              120     10    92%
src/file_organizer/stage2.py              150     15    90%
src/file_organizer/stage3.py              280     30    89%
src/file_organizer/stage4.py              170     20    88%
src/file_organizer/filename_cleaner.py     80      5    94%
src/file_organizer/config.py              140     15    89%
src/file_organizer/cli.py                 120     20    83%
-----------------------------------------------------------
TOTAL                                    1465    115    92%
```

---

## Summary

### Critical Findings
1. ❌ **Only ~5% test coverage** - 175-239 tests needed
2. ❌ **8 of 12 modules have ZERO tests** - Critical modules untested
3. ❌ **No integration tests** - Pipeline workflows untested
4. ❌ **No edge case tests** - Error handling untested
5. ⚠️ **Missing testing guide** - Blocks contributors

### Strengths
1. ✅ **Excellent high-level documentation** (1,600+ lines)
2. ✅ **Good inline documentation** (docstrings present)
3. ✅ **Comprehensive README and onboarding**
4. ✅ **Good existing tests** (Stage 3 optimizations well tested)

### Priority Actions
**Immediate (Weeks 1-2)**:
1. Write unit tests for Stage 1, 2, 4 (critical paths)
2. Write tests for duplicate_resolver (decides deletions)
3. Create testing guide
4. Create CONTRIBUTING.md

**Important (Weeks 3-5)**:
1. Write integration tests (full pipeline)
2. Write tests for config, CLI, hash_cache
3. Generate API reference
4. Create troubleshooting guide

**Total Effort**: 54-79 hours (testing + docs)

---

**Document Status**: Complete
**Review Date**: November 17, 2025
**Next Steps**: Begin Phase 1 implementation (critical tests)
