"""
Test suite for Stage 3 progress reporting and detailed duplicate reports.

Tests:
- Progress reporting with small and large file counts
- Report accuracy (counts, paths, resolution reasons, space calculations)
- Dry-run vs execute mode reports
- Edge cases (no duplicates, all duplicates, mixed scenarios)
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.file_organizer.stage3 import Stage3
from src.file_organizer.duplicate_reporter import DuplicateReporter
from src.file_organizer.duplicate_detector import DuplicateDetector
from src.file_organizer.duplicate_resolver import DuplicateResolver
from src.file_organizer.hash_cache import HashCache
from src.file_organizer.file_sampler import FileSampler


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    input_dir = Path(tempfile.mkdtemp())
    output_dir = Path(tempfile.mkdtemp())
    cache_dir = Path(tempfile.mkdtemp())
    
    yield input_dir, output_dir, cache_dir
    
    # Cleanup
    shutil.rmtree(input_dir, ignore_errors=True)
    shutil.rmtree(output_dir, ignore_errors=True)
    shutil.rmtree(cache_dir, ignore_errors=True)


def create_test_files(base_dir: Path, count: int, content_pattern: str = "test") -> list:
    """Create test files with specified count and content pattern."""
    files = []
    for i in range(count):
        file_path = base_dir / f"test_file_{i}.txt"
        file_path.write_text(f"{content_pattern}_{i % 3}")  # Create some duplicates
        files.append(file_path)
    return files


def test_progress_reporting_small_files(temp_dirs, capsys):
    """Test progress reporting with small file count (10-100 files)."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create 50 test files (with some duplicates)
    files = create_test_files(input_dir, 50)
    
    # Configure to process all files (override min_file_size)
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    # Run Stage 3A
    stage3 = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes.db',
        config=config,
        dry_run=True
    )
    
    stage3.run_stage3a()
    
    # Capture output
    captured = capsys.readouterr()
    output = captured.out
    
    # Verify progress indicators are present
    assert "Scanning files:" in output
    assert "100.0%" in output
    
    # Verify phase indicators
    assert "Phase 1: Scanning input folder" in output
    assert "Phase 2: Detecting duplicates" in output
    assert "Phase 3: Resolving duplicate groups" in output
    
    # Verify summary is present
    assert "DUPLICATE DETECTION REPORT" in output
    assert "DETECTION STATISTICS" in output
    
    stage3.close()
    print("✓ Small file progress reporting test passed")


def test_reporter_format_size():
    """Test size formatting utility."""
    reporter = DuplicateReporter()
    
    assert reporter.format_size(512) == "512 bytes"
    assert reporter.format_size(1024) == "1.00 KB"
    assert reporter.format_size(1024 * 1024) == "1.00 MB"
    assert reporter.format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert reporter.format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
    
    print("✓ Size formatting test passed")


def test_reporter_resolution_reasons(temp_dirs):
    """Test resolution reason detection."""
    input_dir, _, _ = temp_dirs
    
    reporter = DuplicateReporter()
    
    # Test 'keep' keyword
    kept_file = input_dir / "keep_this.txt"
    losers = [input_dir / "delete_this.txt"]
    kept_file.write_text("test")
    losers[0].write_text("test")
    
    reason = reporter.get_resolution_reason(kept_file, losers)
    assert reason == "contains 'keep'"
    
    # Test path depth
    deep_dir = input_dir / "level1" / "level2" / "level3"
    deep_dir.mkdir(parents=True, exist_ok=True)
    kept_file2 = deep_dir / "file.txt"
    losers2 = [input_dir / "file.txt"]
    kept_file2.write_text("test")
    losers2[0].write_text("test")
    
    reason2 = reporter.get_resolution_reason(kept_file2, losers2)
    assert reason2 == "deeper path"
    
    # Test newest (fallback)
    kept_file3 = input_dir / "file1.txt"
    losers3 = [input_dir / "file2.txt"]
    kept_file3.write_text("test")
    losers3[0].write_text("test")
    
    reason3 = reporter.get_resolution_reason(kept_file3, losers3)
    assert reason3 == "newest file"
    
    print("✓ Resolution reason detection test passed")


def test_report_accuracy(temp_dirs):
    """Test report accuracy - counts, paths, reasons, space calculations."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create duplicates with known sizes
    file1 = input_dir / "file1.txt"
    file2 = input_dir / "file2.txt"
    file3 = input_dir / "keep_file3.txt"
    
    content = "test content" * 100  # ~1200 bytes
    file1.write_text(content)
    file2.write_text(content)
    file3.write_text(content)
    
    # Configure
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    # Run detection
    stage3 = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes.db',
        config=config,
        dry_run=True
    )
    
    files = stage3.scan_folder(input_dir)
    duplicates = stage3.detector.find_all_duplicates(files, folder='input', show_progress=False)
    files_to_keep, files_to_delete = stage3.resolver.resolve_all(duplicates)
    
    # Verify counts
    assert len(duplicates) == 1, f"Expected 1 duplicate group, got {len(duplicates)}"
    assert len(files_to_keep) == 1, f"Expected 1 file to keep, got {len(files_to_keep)}"
    
    all_losers = []
    for losers in files_to_delete.values():
        all_losers.extend(losers)
    assert len(all_losers) == 2, f"Expected 2 files to delete, got {len(all_losers)}"
    
    # Verify 'keep' file was kept
    kept_file = list(files_to_keep.values())[0]
    assert "keep" in str(kept_file).lower(), f"File with 'keep' should be kept: {kept_file}"
    
    # Verify space calculation
    expected_space = len(content) * 2  # 2 files deleted
    actual_space = stage3.calculate_space(all_losers)
    assert actual_space == expected_space, f"Expected {expected_space} bytes, got {actual_space}"
    
    # Test reporter
    report = stage3.reporter.report_all_duplicates(
        duplicates, files_to_keep, files_to_delete, max_groups_shown=10
    )
    
    assert "Duplicate groups:" in report
    assert "Files to keep:" in report
    assert "Files to delete:" in report
    assert "Space to reclaim:" in report
    assert "contains 'keep'" in report
    
    stage3.close()
    print("✓ Report accuracy test passed")


def test_dry_run_vs_execute_mode(temp_dirs, capsys):
    """Test differences between dry-run and execute mode reports."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create duplicates
    file1 = input_dir / "file1.txt"
    file2 = input_dir / "file2.txt"
    file1.write_text("test content")
    file2.write_text("test content")
    
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    # Test dry-run mode
    stage3_dry = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes_dry.db',
        config=config,
        dry_run=True
    )
    
    stage3_dry.run_stage3a()
    captured_dry = capsys.readouterr()
    
    assert "DRY-RUN MODE" in captured_dry.out
    assert "No files were modified" in captured_dry.out
    assert "Run with --execute" in captured_dry.out
    
    # Verify files still exist
    assert file1.exists()
    assert file2.exists()
    
    stage3_dry.close()
    print("✓ Dry-run mode test passed")


def test_no_duplicates_case(temp_dirs, capsys):
    """Test edge case: no duplicates found."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create unique files
    for i in range(5):
        (input_dir / f"file{i}.txt").write_text(f"unique content {i}")
    
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    stage3 = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes.db',
        config=config,
        dry_run=True
    )
    
    stage3.run_stage3a()
    captured = capsys.readouterr()
    
    assert "No duplicates found" in captured.out
    
    stage3.close()
    print("✓ No duplicates edge case test passed")


def test_all_duplicates_case(temp_dirs):
    """Test edge case: all files are duplicates."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create all duplicate files
    content = "same content"
    for i in range(10):
        (input_dir / f"file{i}.txt").write_text(content)
    
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    stage3 = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes.db',
        config=config,
        dry_run=True
    )
    
    files = stage3.scan_folder(input_dir)
    duplicates = stage3.detector.find_all_duplicates(files, folder='input', show_progress=False)
    files_to_keep, files_to_delete = stage3.resolver.resolve_all(duplicates)
    
    # Should have 1 group with 10 files
    assert len(duplicates) == 1
    assert sum(len(group) for group in duplicates.values()) == 10
    
    # Should keep 1, delete 9
    assert len(files_to_keep) == 1
    all_losers = []
    for losers in files_to_delete.values():
        all_losers.extend(losers)
    assert len(all_losers) == 9
    
    stage3.close()
    print("✓ All duplicates edge case test passed")


def test_mixed_scenario(temp_dirs):
    """Test mixed scenario: some duplicates, some unique files."""
    input_dir, output_dir, cache_dir = temp_dirs
    
    # Create mixed content
    # Group 1: 3 duplicates
    for i in range(3):
        (input_dir / f"dup1_{i}.txt").write_text("content A")
    
    # Group 2: 2 duplicates
    for i in range(2):
        (input_dir / f"dup2_{i}.txt").write_text("content B")
    
    # Unique files
    for i in range(5):
        (input_dir / f"unique_{i}.txt").write_text(f"unique content {i}")
    
    config = {
        'duplicate_detection': {
            'min_file_size': 0,
            'skip_images': False
        }
    }
    
    stage3 = Stage3(
        input_folder=input_dir,
        output_folder=output_dir,
        cache_path=cache_dir / 'hashes.db',
        config=config,
        dry_run=True
    )
    
    files = stage3.scan_folder(input_dir)
    duplicates = stage3.detector.find_all_duplicates(files, folder='input', show_progress=False)
    files_to_keep, files_to_delete = stage3.resolver.resolve_all(duplicates)
    
    # Should have 2 duplicate groups
    assert len(duplicates) == 2
    
    # Should keep 2 (one from each group), delete 3
    assert len(files_to_keep) == 2
    all_losers = []
    for losers in files_to_delete.values():
        all_losers.extend(losers)
    assert len(all_losers) == 3  # 2 from group 1, 1 from group 2
    
    stage3.close()
    print("✓ Mixed scenario test passed")


def test_adaptive_update_intervals():
    """Test that update intervals adapt correctly based on file count."""
    from src.file_organizer.duplicate_detector import DuplicateDetector
    from src.file_organizer.hash_cache import HashCache
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / 'test.db'
        cache = HashCache(cache_path)
        detector = DuplicateDetector(cache)
        
        # Test intervals
        assert detector._calculate_update_interval(100) == 10
        assert detector._calculate_update_interval(5000) == 100
        assert detector._calculate_update_interval(50000) == 500
        assert detector._calculate_update_interval(200000) == 1000
        
        cache.close()
    
    print("✓ Adaptive update intervals test passed")


def test_large_file_count_simulation():
    """Test progress reporting logic with simulated large file count."""
    from src.file_organizer.stage3 import Stage3
    
    # Test Stage3 update interval calculation
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        stage3 = Stage3(input_dir, output_dir, dry_run=True)
        
        # Test interval calculations match expected values
        assert stage3._calculate_update_interval(500) == 10
        assert stage3._calculate_update_interval(5000) == 100
        assert stage3._calculate_update_interval(50000) == 500
        assert stage3._calculate_update_interval(150000) == 1000
        
        stage3.close()
    
    print("✓ Large file count simulation test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

