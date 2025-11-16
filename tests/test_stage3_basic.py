"""
Basic functional test for Stage 3 Phase 1 implementation.

Tests core infrastructure:
- Hash cache operations
- File sampling
- xxHash integration
- Duplicate detection
- Resolution policy
"""

import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from file_organizer.hash_cache import HashCache
from file_organizer.file_sampler import FileSampler
from file_organizer.duplicate_detector import DuplicateDetector
from file_organizer.duplicate_resolver import DuplicateResolver
from file_organizer.stage3 import Stage3


def test_hash_cache():
    """Test SQLite hash cache operations."""
    print("\n=== Testing Hash Cache ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / 'test_cache.db'
        cache = HashCache(cache_path)
        
        # Test save and get
        test_path = Path('/tmp/test.txt')
        cache.save(test_path, 'input', 'abcd1234', 1024, 1699000000.0)
        
        result = cache.get(test_path, 'input')
        assert result is not None
        assert result['file_hash'] == 'abcd1234'
        assert result['file_size'] == 1024
        print("✓ Cache save/get works")
        
        # Test stats
        stats = cache.get_stats()
        assert stats['total_entries'] == 1
        print(f"✓ Cache stats: {stats}")
        
        cache.close()
    
    print("✓ Hash cache tests passed")


def test_file_sampler():
    """Test file sampling for large files."""
    print("\n=== Testing File Sampler ===")
    
    sampler = FileSampler(threshold=1024, head_size=256, tail_size=256)
    
    # Test should_sample
    assert not sampler.should_sample(512)  # Below threshold
    assert sampler.should_sample(2048)  # Above threshold
    print("✓ Sampling threshold works")
    
    # Test sample sizes
    head, tail = sampler.get_sample_sizes(2048)
    assert head == 256
    assert tail == 256
    print(f"✓ Sample sizes: head={head}, tail={tail}")
    
    print("✓ File sampler tests passed")


def test_duplicate_detection():
    """Test duplicate detection with real files."""
    print("\n=== Testing Duplicate Detection ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cache_path = tmpdir / 'cache.db'
        
        # Create test files
        file1 = tmpdir / 'file1.txt'
        file2 = tmpdir / 'file2.txt'  # Duplicate of file1
        file3 = tmpdir / 'file3.txt'  # Different content
        
        file1.write_text('Hello, this is test content')
        file2.write_text('Hello, this is test content')  # Same content
        file3.write_text('Different content here')
        
        # Create detector
        cache = HashCache(cache_path)
        detector = DuplicateDetector(cache, skip_images=False, min_file_size=0)
        
        # Find duplicates
        files = [file1, file2, file3]
        duplicates = detector.find_all_duplicates(files)
        
        print(f"Files tested: {len(files)}")
        print(f"Duplicate groups found: {len(duplicates)}")
        
        # Should find one duplicate group (file1 and file2)
        assert len(duplicates) == 1
        
        # Get the duplicate group
        dup_group = list(duplicates.values())[0]
        assert len(dup_group) == 2
        assert file1 in dup_group
        assert file2 in dup_group
        assert file3 not in dup_group
        
        print(f"✓ Detected duplicate group: {dup_group}")
        
        # Check statistics
        stats = detector.get_stats()
        print(f"✓ Detection stats: {stats}")
        
        cache.close()
    
    print("✓ Duplicate detection tests passed")


def test_resolution_policy():
    """Test custom resolution policy."""
    print("\n=== Testing Resolution Policy ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files with different paths
        file1 = tmpdir / 'shallow.txt'
        file2 = tmpdir / 'deep' / 'path' / 'file.txt'
        file3 = tmpdir / 'keep' / 'important.txt'
        
        file1.parent.mkdir(parents=True, exist_ok=True)
        file2.parent.mkdir(parents=True, exist_ok=True)
        file3.parent.mkdir(parents=True, exist_ok=True)
        
        file1.write_text('content')
        file2.write_text('content')
        file3.write_text('content')
        
        resolver = DuplicateResolver()
        
        # Test 1: "keep" keyword wins
        winner, losers = resolver.resolve([file1, file3])
        assert winner == file3  # Has "keep" in path
        print(f"✓ 'keep' keyword test: {winner}")
        
        # Test 2: Deeper path wins (when no "keep")
        winner, losers = resolver.resolve([file1, file2])
        assert winner == file2  # Deeper path
        print(f"✓ Path depth test: {winner}")
        
        print("✓ Resolution policy tests passed")


def test_full_stage3a():
    """Test full Stage 3A run."""
    print("\n=== Testing Full Stage 3A Run ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / 'input'
        input_dir.mkdir()
        
        # Create some duplicate files
        (input_dir / 'file1.txt').write_text('Duplicate content A')
        (input_dir / 'file2.txt').write_text('Duplicate content A')  # Dup of file1
        (input_dir / 'file3.txt').write_text('Unique content B')
        (input_dir / 'file4.txt').write_text('Duplicate content C')
        (input_dir / 'file5.txt').write_text('Duplicate content C')  # Dup of file4
        
        # Run Stage 3A in dry-run mode
        cache_path = Path(tmpdir) / 'cache.db'
        # Override min_file_size to test with small files
        config = {'duplicate_detection': {'min_file_size': 0}}
        stage3 = Stage3(input_dir, cache_path=cache_path, config=config, dry_run=True)
        
        stats = stage3.run_stage3a()
        
        print(f"✓ Duplicates found: {stats['duplicates_found']}")
        print(f"✓ Files to delete: {stats['files_deleted']}")
        print(f"✓ Space to reclaim: {stats['space_reclaimed']} bytes")
        
        # Should find 2 duplicate groups
        assert stats['duplicates_found'] == 2
        assert stats['files_deleted'] == 2  # One from each group
        
        stage3.close()
    
    print("✓ Full Stage 3A test passed")


def main():
    """Run all tests."""
    print("=" * 80)
    print("STAGE 3 PHASE 1 - BASIC FUNCTIONALITY TESTS")
    print("=" * 80)
    
    try:
        test_hash_cache()
        test_file_sampler()
        test_duplicate_detection()
        test_resolution_policy()
        test_full_stage3a()
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

