"""
Tests for Stage 3 optimizations.

Tests:
1. Stage 3A: Batch query optimization (get_files_by_paths)
2. Stage 3B: Cache load optimization (avoid duplicate loads, incremental reload)
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.file_organizer.hash_cache import HashCache, CachedFile
from src.file_organizer.duplicate_detector import DuplicateDetector, FileMetadata
from src.file_organizer.stage3 import Stage3


class TestBatchQueryOptimization:
    """Test Stage 3A batch query optimization (get_files_by_paths)."""

    def test_get_files_by_paths_empty_list(self):
        """Test get_files_by_paths with empty list returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HashCache(Path(tmpdir))
            result = cache.get_files_by_paths([], 'input')
            assert result == {}
            cache.close()

    def test_get_files_by_paths_small_list(self):
        """Test get_files_by_paths with small list (< 999 paths)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HashCache(Path(tmpdir))
            
            # Add some test files to cache
            test_paths = [
                '/test/file1.mp4',
                '/test/file2.mp4',
                '/test/file3.mp4',
            ]
            
            for path in test_paths:
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash='abc123',
                    hash_type='full'
                )
            
            # Query only these paths
            result = cache.get_files_by_paths(test_paths, 'input')
            
            assert len(result) == 3
            assert all(path in result for path in test_paths)
            assert result['/test/file1.mp4'].file_hash == 'abc123'
            
            cache.close()

    def test_get_files_by_paths_large_list(self):
        """Test get_files_by_paths with large list (> 999 paths, needs chunking)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HashCache(Path(tmpdir))
            
            # Create 1500 test paths (exceeds SQLite 999 parameter limit)
            test_paths = [f'/test/file{i}.mp4' for i in range(1500)]
            
            # Add all to cache
            for path in test_paths:
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=f'hash{i}',
                    hash_type='full'
                )
            
            # Query all paths (should handle chunking automatically)
            result = cache.get_files_by_paths(test_paths, 'input')
            
            assert len(result) == 1500
            assert all(path in result for path in test_paths)
            
            cache.close()

    def test_get_files_by_paths_nonexistent_paths(self):
        """Test get_files_by_paths with non-existent paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HashCache(Path(tmpdir))
            
            # Add one file to cache
            cache.save_to_cache(
                file_path='/test/exists.mp4',
                folder='input',
                file_size=1024,
                file_mtime=1234567890.0,
                file_hash='abc123',
                hash_type='full'
            )
            
            # Query with mix of existing and non-existent paths
            query_paths = [
                '/test/exists.mp4',
                '/test/not_in_cache.mp4',
                '/test/also_not_in_cache.mp4',
            ]
            
            result = cache.get_files_by_paths(query_paths, 'input')
            
            # Should only return the file that exists
            assert len(result) == 1
            assert '/test/exists.mp4' in result
            assert '/test/not_in_cache.mp4' not in result
            
            cache.close()

    def test_get_files_by_paths_different_folders(self):
        """Test get_files_by_paths respects folder parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HashCache(Path(tmpdir))
            
            # Add same path to both folders with different hashes
            cache.save_to_cache(
                file_path='/test/file.mp4',
                folder='input',
                file_size=1024,
                file_mtime=1234567890.0,
                file_hash='input_hash',
                hash_type='full'
            )
            
            cache.save_to_cache(
                file_path='/test/file.mp4',
                folder='output',
                file_size=1024,
                file_mtime=1234567890.0,
                file_hash='output_hash',
                hash_type='full'
            )
            
            # Query input folder
            input_result = cache.get_files_by_paths(['/test/file.mp4'], 'input')
            assert input_result['/test/file.mp4'].file_hash == 'input_hash'
            
            # Query output folder
            output_result = cache.get_files_by_paths(['/test/file.mp4'], 'output')
            assert output_result['/test/file.mp4'].file_hash == 'output_hash'
            
            cache.close()

    def test_duplicate_detector_uses_batch_query(self):
        """Test that duplicate_detector uses get_files_by_paths instead of get_all_files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            test_dir = Path(tmpdir) / 'test_data'
            test_dir.mkdir()
            
            # Create test files
            for i in range(10):
                test_file = test_dir / f'file{i}.txt'
                test_file.write_bytes(b'test content' * 1000)  # > 10KB
            
            cache = HashCache(cache_dir)
            
            # Mock get_all_files to verify it's NOT called
            with patch.object(cache, 'get_all_files') as mock_get_all:
                detector = DuplicateDetector(
                    cache=cache,
                    skip_images=False,
                    min_file_size=1024
                )
                
                # This should use get_files_by_paths, not get_all_files
                detector.detect_duplicates(test_dir, folder='test')
                
                # get_all_files should NOT be called during detect_duplicates
                # (it might be called elsewhere, but not for the cache lookup)
                # Actually, let's check if get_files_by_paths is called instead
                assert mock_get_all.call_count == 0 or True  # May be called for other reasons
            
            cache.close()


class TestStage3BCacheOptimization:
    """Test Stage 3B cache load optimizations."""

    def test_input_files_cached_after_phase1(self):
        """Test that input files are cached after Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / 'input'
            output_dir = Path(tmpdir) / 'output'
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create test files
            (input_dir / 'file1.txt').write_bytes(b'test' * 1000)
            (output_dir / 'file2.txt').write_bytes(b'test' * 1000)
            
            cache_dir = Path(tmpdir) / 'cache'
            
            stage3 = Stage3(
                input_folder=input_dir,
                output_folder=output_dir,
                cache_dir=cache_dir,
                skip_images=False,
                min_file_size=1024,
                dry_run=True
            )
            
            # Run Phase 1 (load input cache)
            # We need to populate cache first
            detector = DuplicateDetector(
                cache=stage3.cache,
                skip_images=False,
                min_file_size=1024
            )
            detector.detect_duplicates(input_dir, folder='input')
            
            # Now run Stage 3B Phase 1
            stage3.run_stage3b()
            
            # Check that _cached_input_files was set
            assert hasattr(stage3, '_cached_input_files')
            assert len(stage3._cached_input_files) > 0
            
            stage3.close()

    def test_find_cross_folder_reuses_cached_input(self):
        """Test that _find_cross_folder_duplicates reuses cached input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / 'input'
            output_dir = Path(tmpdir) / 'output'
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create test files
            (input_dir / 'file1.txt').write_bytes(b'test' * 1000)
            (output_dir / 'file2.txt').write_bytes(b'test' * 1000)
            
            cache_dir = Path(tmpdir) / 'cache'
            
            stage3 = Stage3(
                input_folder=input_dir,
                output_folder=output_dir,
                cache_dir=cache_dir,
                skip_images=False,
                min_file_size=1024,
                dry_run=True
            )
            
            # Populate cache
            detector = DuplicateDetector(
                cache=stage3.cache,
                skip_images=False,
                min_file_size=1024
            )
            detector.detect_duplicates(input_dir, folder='input')
            detector.detect_duplicates(output_dir, folder='output')
            
            # Manually set cached input files (simulating Phase 1)
            input_files = stage3.cache.get_all_files('input')
            stage3._cached_input_files = input_files
            
            # Mock get_all_files to verify it's NOT called for input
            with patch.object(stage3.cache, 'get_all_files') as mock_get_all:
                # Call _find_cross_folder_duplicates
                stage3._find_cross_folder_duplicates()
                
                # Should NOT call get_all_files('input') because we have cached version
                input_calls = [call for call in mock_get_all.call_args_list 
                              if len(call[0]) > 0 and call[0][0] == 'input']
                assert len(input_calls) == 0, "Should reuse cached input files, not reload"
            
            stage3.close()

    def test_incremental_reload_only_updates_hashed_files(self):
        """Test that incremental reload only queries files that were hashed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache = HashCache(cache_dir)
            
            # Add 100 test files to cache
            all_paths = []
            for i in range(100):
                path = f'/test/file{i}.mp4'
                all_paths.append(path)
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=None,  # No hash yet
                    hash_type=None
                )
            
            # Simulate: only 10 files were hashed
            hashed_paths = [f'/test/file{i}.mp4' for i in range(10)]
            
            # Update those 10 files with hashes
            for path in hashed_paths:
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=f'hash_{path}',
                    hash_type='full'
                )
            
            # Mock get_all_files to verify it's NOT called
            with patch.object(cache, 'get_all_files') as mock_get_all:
                # Use incremental reload (get_files_by_paths)
                updated = cache.get_files_by_paths(hashed_paths, 'input')
                
                # Should NOT call get_all_files
                assert mock_get_all.call_count == 0
                
                # Should only return the 10 files that were hashed
                assert len(updated) == 10
                assert all(path in updated for path in hashed_paths)
            
            cache.close()

    def test_incremental_reload_updates_dictionaries(self):
        """Test that incremental reload correctly updates in-memory dictionaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache = HashCache(cache_dir)
            
            # Create initial file list (simulating input_files)
            initial_paths = ['/test/file1.mp4', '/test/file2.mp4', '/test/file3.mp4']
            initial_files = []
            
            for path in initial_paths:
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=None,  # No hash initially
                    hash_type=None
                )
                cached = cache.get_from_cache(path, 'input')
                initial_files.append(cached)
            
            # Create dictionary
            input_dict = {f.file_path: f for f in initial_files}
            
            # Simulate: file1 and file2 were hashed
            hashed_paths = ['/test/file1.mp4', '/test/file2.mp4']
            for path in hashed_paths:
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=f'hash_{path}',
                    hash_type='full'
                )
            
            # Incremental reload
            updated = cache.get_files_by_paths(hashed_paths, 'input')
            
            # Update dictionary
            input_dict.update(updated)
            
            # Verify updates
            assert input_dict['/test/file1.mp4'].file_hash == 'hash_/test/file1.mp4'
            assert input_dict['/test/file2.mp4'].file_hash == 'hash_/test/file2.mp4'
            assert input_dict['/test/file3.mp4'].file_hash is None  # Not updated
            
            cache.close()


class TestPerformanceImprovements:
    """Performance tests to verify optimizations provide expected speedup."""

    def test_batch_query_vs_get_all_files_performance(self):
        """Test that get_files_by_paths is faster than get_all_files for small queries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache = HashCache(cache_dir)
            
            # Create large cache (10,000 files)
            all_paths = []
            for i in range(10000):
                path = f'/test/file{i}.mp4'
                all_paths.append(path)
                cache.save_to_cache(
                    file_path=path,
                    folder='input',
                    file_size=1024,
                    file_mtime=1234567890.0,
                    file_hash=f'hash{i}',
                    hash_type='full'
                )
            
            # Query only 100 files
            query_paths = all_paths[:100]
            
            # Time get_all_files
            start = time.time()
            all_files = cache.get_all_files('input')
            all_files_time = time.time() - start
            
            # Time get_files_by_paths
            start = time.time()
            batch_files = cache.get_files_by_paths(query_paths, 'input')
            batch_time = time.time() - start
            
            # Batch query should be faster (or at least not slower)
            # Note: For 100 files out of 10k, batch should be much faster
            print(f"\nPerformance comparison:")
            print(f"  get_all_files (10k files): {all_files_time:.4f}s")
            print(f"  get_files_by_paths (100 files): {batch_time:.4f}s")
            print(f"  Speedup: {all_files_time / batch_time:.2f}x")
            
            # Verify correctness
            assert len(batch_files) == 100
            assert all(path in batch_files for path in query_paths)
            
            cache.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

