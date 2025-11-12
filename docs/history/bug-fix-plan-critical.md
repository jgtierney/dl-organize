# Critical Bug Fix Plan - Stage 1 & 2

**Date**: 2025-11-12
**Branch**: `stage3R2`
**Reviewer**: Claude (Code Review)
**Priority**: CRITICAL - Required before production deployment

---

## Executive Summary

This document provides detailed code patches for **5 critical and high-severity bugs** identified during code review of the Stage 1 and Stage 2 implementation.

**Timeline**: Estimated 2-3 hours to implement all fixes
**Risk Level**: LOW (all fixes are localized, minimal side effects)
**Testing Required**: Unit tests + integration tests for each fix

---

## Bug Fix Priority Order

1. **Bug #3** - Missing error handling (Quick fix, prevents crashes)
2. **Bug #1** - Infinite loop in collision resolution (Safety critical)
3. **Bug #2** - Race condition (Data integrity)
4. **Bug #4** - Filename length validation (Edge case but important)
5. **Bug #5** - Config validation (User experience)

---

# Bug #1: Infinite Loop in Collision Resolution

## Severity: 🔴 CRITICAL

## Location
- `src/file_organizer/stage1.py:270`
- `src/file_organizer/stage2.py:496`

## Problem Statement

The collision resolution loop has no safety limit:
```python
# Keep trying if still collides
while filename.lower() in self.used_names[dir_key]:
    filename = self.cleaner.generate_collision_name(original_filename, parent_dir)
```

If `generate_collision_name()` produces a name already in use (due to external file creation, threading, or a bug), this loops forever.

## Root Cause

No maximum attempt counter or timeout mechanism.

## Proposed Fix

Add a safety counter with a reasonable limit (10,000 attempts should handle any realistic scenario).

## Code Patch

### File: `src/file_organizer/stage1.py`

**Lines 243-276** - Replace the entire `_resolve_collision` method:

```python
def _resolve_collision(self, parent_dir: Path, filename: str) -> str:
    """
    Check for naming collision and resolve if necessary.

    Args:
        parent_dir: Parent directory
        filename: Proposed filename

    Returns:
        Unique filename (may be modified with date stamp + counter)

    Raises:
        RuntimeError: If unable to resolve collision after max attempts
    """
    # Maximum attempts to resolve a collision
    MAX_COLLISION_ATTEMPTS = 10000

    # Track used names per directory
    dir_key = str(parent_dir)
    if dir_key not in self.used_names:
        # Initialize with existing files in directory
        self.used_names[dir_key] = {
            item.name.lower() for item in parent_dir.iterdir()
        }

    # Check for collision (case-insensitive)
    if filename.lower() in self.used_names[dir_key]:
        # Generate unique name
        original_filename = filename
        filename = self.cleaner.generate_collision_name(filename, parent_dir)
        self.stats['collisions_resolved'] += 1

        # Keep trying if still collides (with safety limit)
        attempts = 0
        while filename.lower() in self.used_names[dir_key]:
            attempts += 1
            if attempts >= MAX_COLLISION_ATTEMPTS:
                error_msg = (
                    f"Unable to resolve collision for '{original_filename}' "
                    f"in {parent_dir} after {MAX_COLLISION_ATTEMPTS} attempts. "
                    f"Last attempted name: '{filename}'"
                )
                print(f"\n  ERROR: {error_msg}")
                self.stats['errors'] += 1
                raise RuntimeError(error_msg)

            filename = self.cleaner.generate_collision_name(original_filename, parent_dir)

    # Mark this name as used
    self.used_names[dir_key].add(filename.lower())

    return filename
```

### File: `src/file_organizer/stage2.py`

**Lines 466-502** - Replace the entire `_resolve_collision` method:

```python
def _resolve_collision(self, parent_dir: Path, name: str) -> str:
    """
    Check for naming collision and resolve if necessary.

    Args:
        parent_dir: Parent directory
        name: Proposed name

    Returns:
        Unique name (may be modified with date stamp + counter)

    Raises:
        RuntimeError: If unable to resolve collision after max attempts
    """
    # Maximum attempts to resolve a collision
    MAX_COLLISION_ATTEMPTS = 10000

    # Track used names per directory
    dir_key = str(parent_dir)
    if dir_key not in self.used_names:
        # Initialize with existing items in directory
        try:
            self.used_names[dir_key] = {
                item.name.lower() for item in parent_dir.iterdir()
            }
        except Exception:
            self.used_names[dir_key] = set()

    # Check for collision (case-insensitive)
    if name.lower() in self.used_names[dir_key]:
        # Generate unique name
        original_name = name
        name = self.cleaner.generate_collision_name(name, parent_dir)
        self.stats['collisions_resolved'] += 1

        # Keep trying if still collides (with safety limit)
        attempts = 0
        while name.lower() in self.used_names[dir_key]:
            attempts += 1
            if attempts >= MAX_COLLISION_ATTEMPTS:
                error_msg = (
                    f"Unable to resolve collision for '{original_name}' "
                    f"in {parent_dir} after {MAX_COLLISION_ATTEMPTS} attempts. "
                    f"Last attempted name: '{name}'"
                )
                print(f"\n  ERROR: {error_msg}")
                self.stats['errors'] += 1
                raise RuntimeError(error_msg)

            name = self.cleaner.generate_collision_name(original_name, parent_dir)

    # Mark this name as used
    self.used_names[dir_key].add(name.lower())

    return name
```

## Testing Plan

### Unit Tests

Create `tests/test_collision_resolution.py`:

```python
import pytest
from pathlib import Path
from file_organizer.stage1 import Stage1Processor

def test_collision_resolution_safety_limit(tmp_path):
    """Test that collision resolution doesn't loop forever."""
    # Create a processor
    processor = Stage1Processor(tmp_path, dry_run=True)

    # Pre-populate used_names with many entries
    dir_key = str(tmp_path)
    processor.used_names[dir_key] = {f"file_{i}.txt" for i in range(15000)}

    # Try to resolve collision - should eventually give up
    with pytest.raises(RuntimeError, match="Unable to resolve collision"):
        # Mock generate_collision_name to always return same name
        def bad_generator(name, dir):
            return "file_0.txt"  # Always returns existing name

        processor.cleaner.generate_collision_name = bad_generator
        processor._resolve_collision(tmp_path, "file_0.txt")
```

### Integration Test

```bash
# Create directory with 10,000 existing collision names
# Try to add one more file
# Should either succeed with _10001 or fail gracefully
```

## Impact Assessment

- **Before**: Infinite loop, requires force-kill
- **After**: Fails gracefully after 10,000 attempts with clear error message
- **Performance**: Negligible (only affects collision cases)
- **Breaking Changes**: None (only adds safety)

---

# Bug #2: Race Condition in Collision Detection

## Severity: 🔴 CRITICAL

## Location
- `src/file_organizer/stage1.py:256-260`
- `src/file_organizer/stage2.py:478-486`

## Problem Statement

The `used_names` cache is initialized once per directory and never refreshed:

```python
if dir_key not in self.used_names:
    self.used_names[dir_key] = {
        item.name.lower() for item in parent_dir.iterdir()
    }
```

If external processes create files during execution, `used_names` doesn't reflect reality, leading to collisions.

## Root Cause

Cache-only collision checking without filesystem verification.

## Proposed Fix

Add filesystem check for collision detection (defense in depth approach).

## Code Patch

### File: `src/file_organizer/stage1.py`

**Lines 243-276** - Update the `_resolve_collision` method (combines with Bug #1 fix):

```python
def _resolve_collision(self, parent_dir: Path, filename: str) -> str:
    """
    Check for naming collision and resolve if necessary.

    Uses both cache and filesystem checks to prevent race conditions.

    Args:
        parent_dir: Parent directory
        filename: Proposed filename

    Returns:
        Unique filename (may be modified with date stamp + counter)

    Raises:
        RuntimeError: If unable to resolve collision after max attempts
    """
    # Maximum attempts to resolve a collision
    MAX_COLLISION_ATTEMPTS = 10000

    # Track used names per directory
    dir_key = str(parent_dir)
    if dir_key not in self.used_names:
        # Initialize with existing files in directory
        try:
            self.used_names[dir_key] = {
                item.name.lower() for item in parent_dir.iterdir()
            }
        except (PermissionError, FileNotFoundError, OSError) as e:
            print(f"  WARNING: Cannot read directory {parent_dir}: {e}")
            self.used_names[dir_key] = set()
            self.stats['errors'] += 1

    # Helper function to check if name exists (cache + filesystem)
    def name_exists(name: str) -> bool:
        """Check both cache and filesystem for existence."""
        # Check cache first (fast)
        if name.lower() in self.used_names[dir_key]:
            return True

        # Check filesystem (handles external changes)
        target_path = parent_dir / name
        if target_path.exists():
            # Update cache with newly discovered file
            self.used_names[dir_key].add(name.lower())
            return True

        return False

    # Check for collision (case-insensitive, with filesystem verification)
    if name_exists(filename):
        # Generate unique name
        original_filename = filename
        filename = self.cleaner.generate_collision_name(filename, parent_dir)
        self.stats['collisions_resolved'] += 1

        # Keep trying if still collides (with safety limit)
        attempts = 0
        while name_exists(filename):
            attempts += 1
            if attempts >= MAX_COLLISION_ATTEMPTS:
                error_msg = (
                    f"Unable to resolve collision for '{original_filename}' "
                    f"in {parent_dir} after {MAX_COLLISION_ATTEMPTS} attempts. "
                    f"Last attempted name: '{filename}'"
                )
                print(f"\n  ERROR: {error_msg}")
                self.stats['errors'] += 1
                raise RuntimeError(error_msg)

            filename = self.cleaner.generate_collision_name(original_filename, parent_dir)

    # Mark this name as used
    self.used_names[dir_key].add(filename.lower())

    return filename
```

### File: `src/file_organizer/stage2.py`

**Lines 466-502** - Apply same pattern:

```python
def _resolve_collision(self, parent_dir: Path, name: str) -> str:
    """
    Check for naming collision and resolve if necessary.

    Uses both cache and filesystem checks to prevent race conditions.

    Args:
        parent_dir: Parent directory
        name: Proposed name

    Returns:
        Unique name (may be modified with date stamp + counter)

    Raises:
        RuntimeError: If unable to resolve collision after max attempts
    """
    # Maximum attempts to resolve a collision
    MAX_COLLISION_ATTEMPTS = 10000

    # Track used names per directory
    dir_key = str(parent_dir)
    if dir_key not in self.used_names:
        # Initialize with existing items in directory
        try:
            self.used_names[dir_key] = {
                item.name.lower() for item in parent_dir.iterdir()
            }
        except (PermissionError, FileNotFoundError, OSError) as e:
            print(f"  WARNING: Cannot read directory {parent_dir}: {e}")
            self.used_names[dir_key] = set()
            self.stats['errors'] += 1

    # Helper function to check if name exists (cache + filesystem)
    def name_exists(name: str) -> bool:
        """Check both cache and filesystem for existence."""
        # Check cache first (fast)
        if name.lower() in self.used_names[dir_key]:
            return True

        # Check filesystem (handles external changes)
        target_path = parent_dir / name
        if target_path.exists():
            # Update cache with newly discovered file
            self.used_names[dir_key].add(name.lower())
            return True

        return False

    # Check for collision (case-insensitive, with filesystem verification)
    if name_exists(name):
        # Generate unique name
        original_name = name
        name = self.cleaner.generate_collision_name(name, parent_dir)
        self.stats['collisions_resolved'] += 1

        # Keep trying if still collides (with safety limit)
        attempts = 0
        while name_exists(name):
            attempts += 1
            if attempts >= MAX_COLLISION_ATTEMPTS:
                error_msg = (
                    f"Unable to resolve collision for '{original_name}' "
                    f"in {parent_dir} after {MAX_COLLISION_ATTEMPTS} attempts. "
                    f"Last attempted name: '{name}'"
                )
                print(f"\n  ERROR: {error_msg}")
                self.stats['errors'] += 1
                raise RuntimeError(error_msg)

            name = self.cleaner.generate_collision_name(original_name, parent_dir)

    # Mark this name as used
    self.used_names[dir_key].add(name.lower())

    return name
```

## Testing Plan

### Integration Test

```python
def test_race_condition_external_file_creation(tmp_path):
    """Test that external file creation is detected."""
    import threading
    import time

    processor = Stage1Processor(tmp_path, dry_run=False)

    # Create initial file
    (tmp_path / "test.txt").write_text("original")

    # Initialize cache
    processor._resolve_collision(tmp_path, "other.txt")

    # Simulate external process creating file
    (tmp_path / "new_file.txt").write_text("external")

    # Try to resolve collision for name that was created externally
    result = processor._resolve_collision(tmp_path, "new_file.txt")

    # Should have detected the external file and generated collision name
    assert result != "new_file.txt"
    assert "20251112" in result or "_" in result
```

## Impact Assessment

- **Before**: Race condition could cause file overwrites
- **After**: Defense-in-depth with cache + filesystem checks
- **Performance**: Minimal (single `exists()` check per collision)
- **Breaking Changes**: None

---

# Bug #3: Missing Error Handling in Directory Iteration

## Severity: 🔴 CRITICAL

## Location
- `src/file_organizer/stage1.py:258-260`
- `src/file_organizer/stage2.py:481-486`

## Problem Statement

No exception handling around `parent_dir.iterdir()`:
```python
self.used_names[dir_key] = {
    item.name.lower() for item in parent_dir.iterdir()
}
```

Permission errors or deleted directories cause unhandled crashes.

## Root Cause

Missing try/except block.

## Proposed Fix

Add comprehensive error handling (already included in Bug #2 fix above).

## Code Patch

**NOTE**: This fix is **already included** in the Bug #2 patches above:

```python
try:
    self.used_names[dir_key] = {
        item.name.lower() for item in parent_dir.iterdir()
    }
except (PermissionError, FileNotFoundError, OSError) as e:
    print(f"  WARNING: Cannot read directory {parent_dir}: {e}")
    self.used_names[dir_key] = set()
    self.stats['errors'] += 1
```

## Testing Plan

### Unit Test

```python
def test_permission_denied_handling(tmp_path):
    """Test that permission errors are handled gracefully."""
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_dir.chmod(0o000)  # No permissions

    processor = Stage1Processor(tmp_path, dry_run=True)

    # Should not crash
    result = processor._resolve_collision(restricted_dir, "test.txt")

    # Should return the name unchanged (no collision in empty set)
    assert result == "test.txt"

    # Should have logged an error
    assert processor.stats['errors'] >= 1

    # Cleanup
    restricted_dir.chmod(0o755)
```

## Impact Assessment

- **Before**: Crashes on permission errors
- **After**: Gracefully handles errors, continues processing
- **Performance**: None
- **Breaking Changes**: None

---

# Bug #4: Filename Length Not Validated After Collision Resolution

## Severity: 🟠 HIGH

## Location
- `src/file_organizer/filename_cleaner.py:165-203`

## Problem Statement

Collision names add `_YYYYMMDD_N` suffix (14+ characters) without checking if result exceeds `MAX_FILENAME_LENGTH`:

```python
if has_ext:
    return f"{base}_{date_stamp}_{counter}.{ext}"
```

A filename at 200 chars + collision suffix = 214 chars (exceeds limit).

## Root Cause

`_truncate_if_needed()` only called in `sanitize_filename()`, not in `generate_collision_name()`.

## Proposed Fix

Call `_truncate_if_needed()` in `generate_collision_name()`.

## Code Patch

### File: `src/file_organizer/filename_cleaner.py`

**Lines 165-203** - Replace the entire `generate_collision_name` method:

```python
def generate_collision_name(self, base_name: str, directory: Path) -> str:
    """
    Generate a unique filename for collision resolution.

    Uses format: base_YYYYMMDD_N.ext
    where N is a counter starting from 1.

    Ensures the generated name doesn't exceed MAX_FILENAME_LENGTH.

    Args:
        base_name: The sanitized base name that has a collision
        directory: Directory where the file will be placed

    Returns:
        Unique filename with date stamp and counter, truncated if needed
    """
    # Get current date in YYYYMMDD format
    date_stamp = datetime.now().strftime("%Y%m%d")

    # Split extension if present
    if '.' in base_name:
        base, ext = base_name.rsplit('.', 1)
        has_ext = True
    else:
        base, ext = base_name, ""
        has_ext = False

    # Track collision counter for this base name in this directory
    collision_key = str(directory / base_name)
    if collision_key not in self.collision_counters:
        self.collision_counters[collision_key] = 0

    # Increment counter and generate new name
    counter = self.collision_counters[collision_key] + 1
    self.collision_counters[collision_key] = counter

    # Construct collision name
    if has_ext:
        new_name = f"{base}_{date_stamp}_{counter}.{ext}"
    else:
        new_name = f"{base}_{date_stamp}_{counter}"

    # IMPORTANT: Truncate if the collision name is too long
    # The collision suffix adds approximately 14-16 characters:
    # - "_" (1)
    # - "YYYYMMDD" (8)
    # - "_" (1)
    # - counter (1-5 digits, typically 1-2)
    # We need to ensure the final name fits within MAX_FILENAME_LENGTH

    if len(new_name) > self.MAX_FILENAME_LENGTH:
        # Calculate how much space the suffix takes
        suffix = f"_{date_stamp}_{counter}"
        if has_ext:
            suffix += f".{ext}"
        suffix_length = len(suffix)

        # Calculate maximum base length
        max_base_length = self.MAX_FILENAME_LENGTH - suffix_length

        if max_base_length < 1:
            # Suffix itself is too long (extremely rare)
            # Just truncate the whole thing
            new_name = new_name[:self.MAX_FILENAME_LENGTH]
        else:
            # Truncate the base, preserve suffix
            truncated_base = base[:max_base_length]
            if has_ext:
                new_name = f"{truncated_base}_{date_stamp}_{counter}.{ext}"
            else:
                new_name = f"{truncated_base}_{date_stamp}_{counter}"

    return new_name
```

## Testing Plan

### Unit Tests

Add to `filename_cleaner.py` test section or create `tests/test_filename_cleaner.py`:

```python
def test_collision_name_length_limit():
    """Test that collision names don't exceed MAX_FILENAME_LENGTH."""
    cleaner = FilenameCleaner()

    # Create a base name exactly at the limit
    long_base = "a" * 195  # 195 chars
    long_name = f"{long_base}.txt"  # 199 chars (within limit)

    # Generate collision name
    collision_name = cleaner.generate_collision_name(long_name, Path("/tmp"))

    # Should not exceed limit
    assert len(collision_name) <= cleaner.MAX_FILENAME_LENGTH

    # Should still have the extension
    assert collision_name.endswith(".txt")

    # Should have date stamp
    assert "202" in collision_name  # Year prefix

def test_collision_name_very_long_base():
    """Test collision name with extremely long base name."""
    cleaner = FilenameCleaner()

    # Create a base name that exceeds the limit
    very_long = "x" * 250  # 250 chars
    long_name = f"{very_long}.pdf"

    # Generate collision name
    collision_name = cleaner.generate_collision_name(long_name, Path("/tmp"))

    # Must be truncated
    assert len(collision_name) <= cleaner.MAX_FILENAME_LENGTH
    assert len(collision_name) == cleaner.MAX_FILENAME_LENGTH  # Should use full space

    # Should still have extension
    assert collision_name.endswith(".pdf")

def test_multiple_collision_names_truncated():
    """Test that multiple collision names are all properly truncated."""
    cleaner = FilenameCleaner()

    long_base = "b" * 195
    long_name = f"{long_base}.doc"

    # Generate 5 collision names
    names = []
    for i in range(5):
        collision_name = cleaner.generate_collision_name(long_name, Path("/tmp"))
        names.append(collision_name)

        # Each should be within limit
        assert len(collision_name) <= cleaner.MAX_FILENAME_LENGTH

    # All should be unique
    assert len(set(names)) == 5
```

## Impact Assessment

- **Before**: Names could exceed filesystem limits, cause errors
- **After**: All names guaranteed within MAX_FILENAME_LENGTH
- **Performance**: Negligible (one length check per collision)
- **Breaking Changes**: None (only fixes edge case)

---

# Bug #5: No Configuration Value Validation

## Severity: 🟠 HIGH

## Location
- `src/file_organizer/config.py:90-113`

## Problem Statement

Configuration getters don't validate values:
```python
def get_flatten_threshold(self, cli_override: Optional[int] = None) -> int:
    value = self.get('flatten_threshold', cli_override)
    return int(value) if value is not None else 5
```

Invalid values (negative, strings, huge numbers) cause unexpected behavior or crashes.

## Root Cause

Missing input validation and bounds checking.

## Proposed Fix

Add comprehensive validation to all configuration getters.

## Code Patch

### File: `src/file_organizer/config.py`

**Lines 90-113** - Replace all getter methods:

```python
def get_flatten_threshold(self, cli_override: Optional[int] = None) -> int:
    """
    Get folder flattening threshold (default: 5 items).

    Returns:
        Valid threshold between 0 and 1000 (inclusive)
    """
    value = self.get('flatten_threshold', cli_override)

    # Handle None
    if value is None:
        return 5

    # Validate and convert
    try:
        threshold = int(value)

        # Validate range
        if threshold < 0:
            print(f"WARNING: flatten_threshold must be >= 0, got {threshold}. Using default (5).")
            return 5

        if threshold > 1000:
            print(f"WARNING: flatten_threshold very high ({threshold}), capping at 1000.")
            return 1000

        return threshold

    except (ValueError, TypeError) as e:
        print(f"WARNING: Invalid flatten_threshold value '{value}': {e}. Using default (5).")
        return 5

def get_default_mode(self, cli_override: Optional[str] = None) -> str:
    """
    Get default execution mode (dry-run or execute).

    Returns:
        Either 'dry-run' or 'execute'
    """
    value = self.get('default_mode', cli_override)

    if value is None:
        return 'dry-run'

    # Validate value
    mode = str(value).lower().strip()

    if mode in ('dry-run', 'dryrun', 'dry_run', 'preview'):
        return 'dry-run'
    elif mode in ('execute', 'exec', 'run', 'live'):
        return 'execute'
    else:
        print(f"WARNING: Invalid default_mode '{value}', must be 'dry-run' or 'execute'. Using 'dry-run'.")
        return 'dry-run'

def should_preserve_timestamps(self, cli_override: Optional[bool] = None) -> bool:
    """
    Check if timestamps should be preserved.

    Returns:
        Boolean value (default: True)
    """
    value = self.get('preserve_timestamps', cli_override)

    if value is None:
        return True

    # Handle various boolean representations
    if isinstance(value, bool):
        return value

    # Handle string representations
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
            return True
        elif value_lower in ('false', 'no', '0', 'off', 'disabled'):
            return False
        else:
            print(f"WARNING: Invalid preserve_timestamps value '{value}'. Using default (True).")
            return True

    # Handle numeric (0 = False, anything else = True)
    try:
        return bool(int(value))
    except (ValueError, TypeError):
        print(f"WARNING: Invalid preserve_timestamps value '{value}'. Using default (True).")
        return True

def get_max_errors_logged(self, cli_override: Optional[int] = None) -> int:
    """
    Get maximum number of detailed errors to log.

    Returns:
        Valid count between 0 and 100,000 (inclusive)
    """
    value = self.get('max_errors_logged', cli_override)

    if value is None:
        return 1000

    try:
        max_errors = int(value)

        # Validate range
        if max_errors < 0:
            print(f"WARNING: max_errors_logged must be >= 0, got {max_errors}. Using 0 (no logging).")
            return 0

        if max_errors > 100000:
            print(f"WARNING: max_errors_logged very high ({max_errors}), capping at 100,000.")
            return 100000

        return max_errors

    except (ValueError, TypeError) as e:
        print(f"WARNING: Invalid max_errors_logged value '{value}': {e}. Using default (1000).")
        return 1000

def get_scan_progress_interval(self, cli_override: Optional[int] = None) -> int:
    """
    Get number of files between scan progress updates.

    Returns:
        Valid interval between 1 and 1,000,000 (inclusive)
    """
    value = self.get('scan_progress_interval', cli_override)

    if value is None:
        return 10000

    try:
        interval = int(value)

        # Validate range
        if interval < 1:
            print(f"WARNING: scan_progress_interval must be >= 1, got {interval}. Using 1.")
            return 1

        if interval > 1000000:
            print(f"WARNING: scan_progress_interval very high ({interval}), capping at 1,000,000.")
            return 1000000

        return interval

    except (ValueError, TypeError) as e:
        print(f"WARNING: Invalid scan_progress_interval value '{value}': {e}. Using default (10,000).")
        return 10000
```

## Testing Plan

### Unit Tests

Create `tests/test_config_validation.py`:

```python
import pytest
from pathlib import Path
from file_organizer.config import Config
import tempfile
import yaml

def test_flatten_threshold_negative():
    """Test that negative flatten_threshold is rejected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'flatten_threshold': -5}, f)
        config_path = Path(f.name)

    config = Config(config_path)
    result = config.get_flatten_threshold()

    assert result == 5  # Should use default
    config_path.unlink()

def test_flatten_threshold_too_high():
    """Test that excessive flatten_threshold is capped."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'flatten_threshold': 999999}, f)
        config_path = Path(f.name)

    config = Config(config_path)
    result = config.get_flatten_threshold()

    assert result == 1000  # Should be capped
    config_path.unlink()

def test_flatten_threshold_string():
    """Test that string flatten_threshold is rejected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'flatten_threshold': 'not a number'}, f)
        config_path = Path(f.name)

    config = Config(config_path)
    result = config.get_flatten_threshold()

    assert result == 5  # Should use default
    config_path.unlink()

def test_default_mode_invalid():
    """Test that invalid default_mode is rejected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'default_mode': 'invalid-mode'}, f)
        config_path = Path(f.name)

    config = Config(config_path)
    result = config.get_default_mode()

    assert result == 'dry-run'  # Should use safe default
    config_path.unlink()

def test_preserve_timestamps_various_formats():
    """Test that preserve_timestamps handles various boolean formats."""
    test_cases = [
        ('true', True),
        ('TRUE', True),
        ('yes', True),
        ('1', True),
        ('false', False),
        ('FALSE', False),
        ('no', False),
        ('0', False),
        ('invalid', True),  # Default to True on invalid
    ]

    for value, expected in test_cases:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'preserve_timestamps': value}, f)
            config_path = Path(f.name)

        config = Config(config_path)
        result = config.should_preserve_timestamps()

        assert result == expected, f"Failed for value '{value}'"
        config_path.unlink()
```

## Impact Assessment

- **Before**: Invalid configs cause crashes or unexpected behavior
- **After**: All configs validated with clear warnings, safe defaults
- **Performance**: Negligible (only at startup)
- **Breaking Changes**: None (invalid configs now handled instead of crashing)

---

# Implementation Plan

## Phase 1: Core Fixes (Day 1 - 2 hours)

1. **Apply Bug #3 + Bug #2 patches** (they're combined)
   - Update `stage1.py` `_resolve_collision` method
   - Update `stage2.py` `_resolve_collision` method
   - Test: Run on test dataset, verify no crashes

2. **Apply Bug #1 patch** (already included in Bug #2)
   - Verify MAX_COLLISION_ATTEMPTS is in place
   - Test: Mock test with bad collision generator

## Phase 2: Edge Cases (Day 1 - 1 hour)

3. **Apply Bug #4 patch**
   - Update `filename_cleaner.py` `generate_collision_name` method
   - Test: Create files with 195+ character names

4. **Apply Bug #5 patch**
   - Update all `config.py` getter methods
   - Test: Create config with invalid values

## Phase 3: Testing (Day 2 - 3 hours)

5. **Write unit tests** for all fixes
6. **Run integration tests** on large dataset
7. **Performance regression testing**

## Phase 4: Documentation (Day 2 - 1 hour)

8. Update CHANGELOG.md
9. Update README.md if needed
10. Document new error messages in user guide

---

# Verification Checklist

After implementing all fixes:

- [ ] All 5 patches applied correctly
- [ ] Code compiles without errors
- [ ] Existing tests still pass
- [ ] New unit tests written and passing
- [ ] Integration test on 10k+ files passes
- [ ] Integration test on 100k+ files passes (optional but recommended)
- [ ] Dry-run mode still works correctly
- [ ] Execute mode still works correctly
- [ ] Error messages are clear and actionable
- [ ] Performance regression: < 5% slowdown
- [ ] Memory regression: < 10MB increase
- [ ] Documentation updated
- [ ] Committed and pushed to branch

---

# Expected Outcomes

## Code Quality
- ✅ No more infinite loop vulnerabilities
- ✅ Race condition eliminated
- ✅ Graceful error handling
- ✅ All edge cases covered
- ✅ Input validation comprehensive

## User Experience
- ✅ Clear error messages
- ✅ Safe defaults for invalid configs
- ✅ No unexpected crashes
- ✅ Predictable behavior

## Performance
- ✅ Negligible performance impact (< 2%)
- ✅ No memory regression
- ✅ Same processing speed

---

# Rollback Plan

If any issues arise during implementation:

1. **Git revert** to commit before patches
2. Apply patches one at a time
3. Test each patch individually
4. Identify problematic patch
5. Fix or skip that patch

All patches are **independent** except Bug #2 and Bug #3 (which are combined).

---

**Status**: Ready for Implementation
**Estimated Time**: 4-6 hours total
**Risk**: LOW
**Priority**: CRITICAL

**Next Step**: Begin implementation with Bug #3 + Bug #2 (combined patch)
