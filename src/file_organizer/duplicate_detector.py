"""
Duplicate file detection using metadata-first optimization.

Implements:
- xxHash-based file hashing (ultra-fast, non-cryptographic)
- Metadata-first strategy (only hash files in size collision groups)
- File filtering (skip images, small files < 10KB)
- Progress reporting
- Cache integration
"""

import os
import xxhash
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import time

from .hash_cache import HashCache, CachedFile
from .progress_bar import ProgressBar


# File extensions to skip
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico',
    '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw', '.dng', '.psd', '.ai'
}

# Minimum file size to process (10KB)
MIN_FILE_SIZE = 10 * 1024  # 10KB


@dataclass
class FileMetadata:
    """Lightweight metadata for a file."""
    path: str
    size: int
    mtime: float


@dataclass
class DuplicateGroup:
    """A group of duplicate files with the same hash."""
    hash: str
    files: List[str]
    size: int  # Size of each file in the group


class DuplicateDetector:
    """
    Detects duplicate files using metadata-first optimization.

    Process:
    1. Scan directory and collect metadata (path, size, mtime)
    2. Group files by size (different sizes can't be duplicates)
    3. Only hash files in size collision groups (2+ files same size)
    4. Group by hash to find duplicates

    This approach is 10x faster than hashing all files.
    """

    def __init__(
        self,
        cache: HashCache,
        skip_images: bool = True,
        min_file_size: int = MIN_FILE_SIZE,
        progress_callback: Optional[callable] = None,
        verbose: bool = True
    ):
        """
        Initialize duplicate detector.

        Args:
            cache: HashCache instance for storing/retrieving hashes
            skip_images: Skip image files (default True)
            min_file_size: Minimum file size to process in bytes (default 10KB)
            progress_callback: Optional callback for progress updates
            verbose: Show progress bars (default True)
        """
        self.cache = cache
        self.skip_images = skip_images
        self.min_file_size = min_file_size
        self.progress_callback = progress_callback
        self.verbose = verbose

        # Statistics
        self.stats = {
            'total_files': 0,
            'skipped_images': 0,
            'skipped_small': 0,
            'unique_sizes': 0,
            'size_collisions': 0,
            'files_hashed': 0,
            'cache_hits': 0,
            'duplicates_found': 0,
            'bytes_saved': 0
        }

    def should_skip_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Determine if a file should be skipped.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (should_skip, reason)
        """
        # Check if image
        if self.skip_images and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return True, 'image'

        # Check file size
        try:
            size = file_path.stat().st_size
            if size < self.min_file_size:
                return True, 'too_small'
        except (OSError, FileNotFoundError):
            return True, 'error'

        return False, None

    def scan_directory(self, directory: Path, folder: str) -> List[FileMetadata]:
        """
        Scan directory and collect file metadata.

        Args:
            directory: Root directory to scan
            folder: Folder label ('input' or 'output')

        Returns:
            List of FileMetadata objects for files to process
        """
        files = []
        scanned = 0

        if self.progress_callback:
            self.progress_callback('scan', 0, 0, "Scanning files...")

        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                file_path = Path(root) / filename
                scanned += 1

                # Progress update every 10,000 files
                if scanned % 10000 == 0 and self.progress_callback:
                    self.progress_callback('scan', scanned, 0, f"Scanned {scanned:,} files...")

                # Check if should skip
                skip, reason = self.should_skip_file(file_path)
                if skip:
                    if reason == 'image':
                        self.stats['skipped_images'] += 1
                    elif reason == 'too_small':
                        self.stats['skipped_small'] += 1
                    continue

                # Collect metadata
                try:
                    stat = file_path.stat()
                    files.append(FileMetadata(
                        path=str(file_path.absolute()),
                        size=stat.st_size,
                        mtime=stat.st_mtime
                    ))
                except (OSError, FileNotFoundError):
                    # Skip files with permission errors
                    continue

        self.stats['total_files'] = len(files)

        if self.progress_callback:
            self.progress_callback(
                'scan', scanned, len(files),
                f"Scan complete: {len(files):,} files to process"
            )

        return files

    def group_by_size(self, files: List[FileMetadata]) -> Dict[int, List[FileMetadata]]:
        """
        Group files by exact size.

        Args:
            files: List of FileMetadata objects

        Returns:
            Dict mapping size -> list of files with that size
        """
        size_groups = {}

        for file_meta in files:
            size = file_meta.size
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_meta)

        return size_groups

    def compute_file_hash(self, file_path: str) -> str:
        """
        Compute xxHash of a file.

        Args:
            file_path: Path to file

        Returns:
            xxHash hex digest
        """
        hasher = xxhash.xxh64()

        try:
            with open(file_path, 'rb') as f:
                # Read in 64KB chunks for efficiency
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    hasher.update(chunk)

            return hasher.hexdigest()
        except (OSError, FileNotFoundError) as e:
            # Return empty string on error (will be skipped)
            return ""

    def hash_file_with_cache(
        self,
        file_meta: FileMetadata,
        folder: str
    ) -> Optional[str]:
        """
        Hash a file, using cache if available.

        Args:
            file_meta: File metadata
            folder: Folder label ('input' or 'output')

        Returns:
            File hash or None if error
        """
        # Check cache first
        cached = self.cache.get_from_cache(file_meta.path, folder)

        if cached and cached.file_size == file_meta.size and cached.file_mtime == file_meta.mtime and cached.file_hash:
            # Cache hit - file unchanged and has hash
            self.stats['cache_hits'] += 1
            return cached.file_hash

        # Cache miss or no hash - compute hash
        file_hash = self.compute_file_hash(file_meta.path)

        if not file_hash:
            return None  # Error computing hash

        # Save to cache
        self.cache.save_to_cache(
            file_path=file_meta.path,
            folder=folder,
            file_size=file_meta.size,
            file_mtime=file_meta.mtime,
            file_hash=file_hash,
            hash_type='full'
        )

        self.stats['files_hashed'] += 1
        return file_hash

    def detect_duplicates(
        self,
        directory: Path,
        folder: str = 'input'
    ) -> List[DuplicateGroup]:
        """
        Detect duplicate files in a directory using metadata-first optimization.

        Process:
        1. Scan directory and collect metadata
        2. Group files by size
        3. Only hash files in size collision groups (2+ files same size)
        4. Group by hash to find duplicates

        Args:
            directory: Directory to scan
            folder: Folder label ('input' or 'output')

        Returns:
            List of DuplicateGroup objects (groups with 2+ files)
        """
        # Phase 1: Scan and collect metadata
        if self.progress_callback:
            self.progress_callback('phase', 1, 4, "Phase 1: Scanning directory...")

        files = self.scan_directory(directory, folder)

        if not files:
            return []

        # Cache all scanned files (even without hashes) for Stage 3B
        # This ensures the cache is complete for cross-folder deduplication
        for file_meta in files:
            # Check if already in cache
            cached = self.cache.get_from_cache(file_meta.path, folder)
            if not cached or cached.file_size != file_meta.size or cached.file_mtime != file_meta.mtime:
                # Not in cache or file changed - add/update metadata (without hash yet)
                self.cache.save_to_cache(
                    file_path=file_meta.path,
                    folder=folder,
                    file_size=file_meta.size,
                    file_mtime=file_meta.mtime,
                    file_hash=None,  # No hash yet - will be computed if needed
                    hash_type=None
                )

        # Phase 2: Group by size
        if self.progress_callback:
            self.progress_callback('phase', 2, 4, "Phase 2: Grouping by size...")

        size_groups = self.group_by_size(files)

        # Identify collision groups (2+ files with same size)
        collision_groups = {
            size: file_list
            for size, file_list in size_groups.items()
            if len(file_list) >= 2
        }

        unique_size_count = len(size_groups) - len(collision_groups)
        self.stats['unique_sizes'] = unique_size_count
        self.stats['size_collisions'] = sum(len(files) for files in collision_groups.values())

        if self.progress_callback:
            self.progress_callback(
                'size_group', unique_size_count, len(collision_groups),
                f"Unique sizes: {unique_size_count:,} files (no hashing needed)"
            )

        # Phase 3: Selective hashing (only collision groups)
        if self.progress_callback:
            self.progress_callback('phase', 3, 4, "Phase 3: Hashing collision groups...")

        hash_groups = {}
        total_to_hash = self.stats['size_collisions']
        hashed_count = 0
        skipped_count = 0

        # Create progress bar for hashing
        if total_to_hash > 0:
            hash_progress = ProgressBar(
                total=total_to_hash,
                description="Hashing files",
                verbose=self.verbose,
                min_duration=1.0
            )

        idx = 0
        for size, file_list in collision_groups.items():
            for file_meta in file_list:
                idx += 1
                file_hash = self.hash_file_with_cache(file_meta, folder)

                if not file_hash:
                    skipped_count += 1
                    if total_to_hash > 0:
                        hash_progress.update(idx, {"Hashed": hashed_count, "Skipped": skipped_count})
                    continue  # Skip files with hash errors

                # Group by hash
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append((file_meta.path, size))

                hashed_count += 1

                # Update progress bar
                if total_to_hash > 0:
                    hash_progress.update(idx, {"Hashed": hashed_count, "Skipped": skipped_count})

        # Finish progress bar
        if total_to_hash > 0:
            hash_progress.finish({"Hashed": hashed_count, "Skipped": skipped_count})

        # Phase 4: Find duplicates (groups with 2+ files)
        if self.progress_callback:
            self.progress_callback('phase', 4, 4, "Phase 4: Identifying duplicates...")

        duplicate_groups = []
        for file_hash, file_list in hash_groups.items():
            if len(file_list) >= 2:
                paths = [path for path, size in file_list]
                size = file_list[0][1]  # All files in group have same size

                duplicate_groups.append(DuplicateGroup(
                    hash=file_hash,
                    files=paths,
                    size=size
                ))

                # Calculate bytes saved (keep 1, delete N-1)
                self.stats['duplicates_found'] += len(paths) - 1
                self.stats['bytes_saved'] += size * (len(paths) - 1)

        return duplicate_groups

    def get_stats_summary(self) -> str:
        """
        Get formatted statistics summary.

        Returns:
            Formatted string with statistics
        """
        total_scanned = (
            self.stats['total_files'] +
            self.stats['skipped_images'] +
            self.stats['skipped_small']
        )

        lines = [
            "",
            "=== Duplicate Detection Statistics ===",
            f"Files scanned: {total_scanned:,}",
            f"  - Skipped (images): {self.stats['skipped_images']:,}",
            f"  - Skipped (too small): {self.stats['skipped_small']:,}",
            f"  - Processed: {self.stats['total_files']:,}",
            "",
            f"Size grouping:",
            f"  - Unique sizes: {self.stats['unique_sizes']:,} files (no hashing needed)",
            f"  - Size collisions: {self.stats['size_collisions']:,} files (hashed)",
            "",
            f"Hashing:",
            f"  - Files hashed: {self.stats['files_hashed']:,}",
            f"  - Cache hits: {self.stats['cache_hits']:,}",
            f"  - Cache hit rate: {self._cache_hit_rate():.1f}%",
            "",
            f"Duplicates:",
            f"  - Duplicate files found: {self.stats['duplicates_found']:,}",
            f"  - Space that can be freed: {self._format_bytes(self.stats['bytes_saved'])}",
            "=" * 40
        ]

        return "\n".join(lines)

    def _cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.stats['cache_hits'] + self.stats['files_hashed']
        if total == 0:
            return 0.0
        return (self.stats['cache_hits'] / total) * 100

    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"


if __name__ == "__main__":
    # Test the duplicate detector
    import tempfile
    import shutil

    print("Testing DuplicateDetector...")

    # Create temp directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / 'test_data'
        test_dir.mkdir()

        # Create test files (> 10KB to avoid being skipped)
        print("\n[Setup] Creating test files...")

        # File 1 and its duplicate (15KB each)
        file1 = test_dir / 'file1.txt'
        file1.write_bytes(b'Hello World!' * 1500)
        file1_dup = test_dir / 'file1_duplicate.txt'
        shutil.copy2(file1, file1_dup)

        # File 2 (unique, 20KB)
        file2 = test_dir / 'file2.txt'
        file2.write_bytes(b'Different content' * 1500)

        # File 3 (same size as file2, different content - size collision)
        file3 = test_dir / 'file3.txt'
        content3 = b'X' * len(b'Different content' * 1500)
        file3.write_bytes(content3)

        # Small file (should be skipped)
        small = test_dir / 'small.txt'
        small.write_bytes(b'tiny')

        # Image file (should be skipped)
        image = test_dir / 'image.jpg'
        image.write_bytes(b'fake image data' * 100)

        print(f"Created 5 test files in {test_dir}")

        # Test detector
        cache_dir = Path(tmpdir) / 'cache'
        with HashCache(cache_dir) as cache:
            detector = DuplicateDetector(
                cache=cache,
                skip_images=True,
                min_file_size=10 * 1024
            )

            print("\n[Test 1] Detecting duplicates...")
            duplicates = detector.detect_duplicates(test_dir, folder='test')

            print(f"✓ Found {len(duplicates)} duplicate group(s)")

            if duplicates:
                for group in duplicates:
                    print(f"  Group (hash={group.hash[:16]}...):")
                    for file_path in group.files:
                        print(f"    - {Path(file_path).name}")

            print("\n[Test 2] Statistics:")
            print(detector.get_stats_summary())

            # Verify results
            assert detector.stats['total_files'] == 4, "Should process 4 files (2 dupes + 2 size collision)"
            assert detector.stats['skipped_small'] >= 1, "Should skip small file"
            assert detector.stats['skipped_images'] >= 1, "Should skip image"
            assert len(duplicates) == 1, "Should find 1 duplicate group"
            assert len(duplicates[0].files) == 2, "Duplicate group should have 2 files"

    print("\n✓ All tests passed!")
