"""
SQLite-based file hash cache for duplicate detection.

Stores file metadata (path, size, mtime) and hashes (nullable for unique sizes).
Supports metadata-first deduplication strategy and moved file detection.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import time


@dataclass
class CachedFile:
    """Represents a cached file entry."""
    file_path: str
    folder: str
    file_hash: Optional[str]
    hash_type: Optional[str]
    sample_size: Optional[int]
    file_size: int
    file_mtime: float
    video_duration: Optional[float]
    video_codec: Optional[str]
    video_resolution: Optional[str]
    last_checked: float


class HashCache:
    """
    SQLite-based cache for file hashes and metadata.

    Supports:
    - Metadata-first deduplication (nullable hashes for unique sizes)
    - Moved file detection (size + mtime + hash identity)
    - Video metadata storage
    - Cache invalidation on size/mtime changes

    Database location: .file_organizer_cache/hashes.db in execution directory
    """

    def __init__(self, cache_dir: Optional[Path] = None, verbose: bool = False):
        """
        Initialize hash cache.

        Args:
            cache_dir: Directory for cache database (defaults to .file_organizer_cache in CWD)
            verbose: Print status messages during initialization
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / '.file_organizer_cache'

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.verbose = verbose

        self.db_path = self.cache_dir / 'hashes.db'
        self.conn: Optional[sqlite3.Connection] = None

        # Open database and create schema if needed
        if self.verbose:
            print(f"  Opening cache database: {self.db_path}")
            import sys
            sys.stdout.flush()

        self._open_database()

        if self.verbose:
            print("  Checking database schema and indexes...")
            import sys
            sys.stdout.flush()

        self._create_schema()

        if self.verbose:
            print("  ✓ Cache database ready")
            import sys
            sys.stdout.flush()

    def _open_database(self):
        """Open SQLite database connection."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

    def _create_schema(self):
        """Create database schema and indexes if they don't exist."""
        cursor = self.conn.cursor()

        # Check if table exists to avoid unnecessary work
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='file_cache'
        """)
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # First-time setup - set performance optimizations
            if self.verbose:
                print("  Setting database performance optimizations...")
                import sys
                sys.stdout.flush()

            # Write-Ahead Logging mode for better concurrency and performance
            cursor.execute("PRAGMA journal_mode=WAL")

            # Normal synchronous mode (faster than FULL, still safe)
            cursor.execute("PRAGMA synchronous=NORMAL")

            # Larger cache size (10MB default, increase to 50MB)
            cursor.execute("PRAGMA cache_size=-51200")  # Negative = KB

            # Store temp tables in memory for speed
            cursor.execute("PRAGMA temp_store=MEMORY")

            # Memory-mapped I/O (64MB - sufficient for ~80K files)
            cursor.execute("PRAGMA mmap_size=67108864")  # 64MB

            # Create main cache table
            cursor.execute("""
                CREATE TABLE file_cache (
                    -- Primary file identification
                    file_path TEXT NOT NULL,
                    folder TEXT NOT NULL,

                    -- Hash information (nullable for unique-sized files)
                    file_hash TEXT,
                    hash_type TEXT,
                    sample_size INTEGER,

                    -- File metadata (for moved file detection)
                    file_size INTEGER NOT NULL,
                    file_mtime REAL NOT NULL,

                    -- Video-specific metadata (NULL for non-videos)
                    video_duration REAL,
                    video_codec TEXT,
                    video_resolution TEXT,

                    -- Cache management
                    last_checked REAL NOT NULL,

                    PRIMARY KEY (file_path, folder)
                )
            """)

            # Create all indexes at once (faster than checking each one)
            cursor.execute("""
                CREATE INDEX idx_file_identity
                ON file_cache(file_size, file_mtime, file_hash)
            """)

            cursor.execute("""
                CREATE INDEX idx_hash_lookup
                ON file_cache(file_hash)
            """)

            cursor.execute("""
                CREATE INDEX idx_folder
                ON file_cache(folder)
            """)

            cursor.execute("""
                CREATE INDEX idx_size_grouping
                ON file_cache(file_size)
            """)

            self.conn.commit()
        # else: Table and indexes already exist, skip creation and PRAGMA settings

    def get_from_cache(self, file_path: str, folder: str) -> Optional[CachedFile]:
        """
        Retrieve cached entry for a file.

        Args:
            file_path: Full absolute path to file
            folder: 'input' or 'output'

        Returns:
            CachedFile object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM file_cache
            WHERE file_path = ? AND folder = ?
        """, (file_path, folder))

        row = cursor.fetchone()
        if row is None:
            return None

        return CachedFile(
            file_path=row['file_path'],
            folder=row['folder'],
            file_hash=row['file_hash'],
            hash_type=row['hash_type'],
            sample_size=row['sample_size'],
            file_size=row['file_size'],
            file_mtime=row['file_mtime'],
            video_duration=row['video_duration'],
            video_codec=row['video_codec'],
            video_resolution=row['video_resolution'],
            last_checked=row['last_checked']
        )

    def save_to_cache(
        self,
        file_path: str,
        folder: str,
        file_size: int,
        file_mtime: float,
        file_hash: Optional[str] = None,
        hash_type: Optional[str] = None,
        sample_size: Optional[int] = None,
        video_duration: Optional[float] = None,
        video_codec: Optional[str] = None,
        video_resolution: Optional[str] = None
    ):
        """
        Save or update a cache entry.

        Args:
            file_path: Full absolute path to file
            folder: 'input' or 'output'
            file_size: File size in bytes
            file_mtime: Modification time (Unix timestamp)
            file_hash: xxHash hex digest (None for unique-sized files)
            hash_type: 'full' or 'sampled' (None if not hashed)
            sample_size: Total bytes if sampled, None if full hash
            video_duration: Video duration in seconds (None for non-videos)
            video_codec: Video codec name (None for non-videos)
            video_resolution: Video resolution (None for non-videos)
        """
        cursor = self.conn.cursor()
        now = time.time()

        cursor.execute("""
            INSERT OR REPLACE INTO file_cache (
                file_path, folder, file_hash, hash_type, sample_size,
                file_size, file_mtime, video_duration, video_codec,
                video_resolution, last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_path, folder, file_hash, hash_type, sample_size,
            file_size, file_mtime, video_duration, video_codec,
            video_resolution, now
        ))

        self.conn.commit()

    def save_batch(
        self,
        entries: List[Dict[str, Any]]
    ):
        """
        Save or update multiple cache entries in a single transaction.

        This is MUCH faster than calling save_to_cache() repeatedly because:
        - Single executemany() instead of N execute() calls
        - Single commit() instead of N commits
        - SQLite optimizes batch inserts internally

        Args:
            entries: List of dictionaries with cache entry data

        Each entry dict should contain:
            - file_path (str, required)
            - folder (str, required)
            - file_size (int, required)
            - file_mtime (float, required)
            - file_hash (str, optional)
            - hash_type (str, optional)
            - sample_size (int, optional)
            - video_duration (float, optional)
            - video_codec (str, optional)
            - video_resolution (str, optional)
        """
        if not entries:
            return

        cursor = self.conn.cursor()
        now = time.time()

        # Prepare batch data
        batch_data = []
        for entry in entries:
            batch_data.append((
                entry['file_path'],
                entry['folder'],
                entry.get('file_hash'),
                entry.get('hash_type'),
                entry.get('sample_size'),
                entry['file_size'],
                entry['file_mtime'],
                entry.get('video_duration'),
                entry.get('video_codec'),
                entry.get('video_resolution'),
                now
            ))

        # Execute batch insert with executemany (much faster than loop)
        cursor.executemany("""
            INSERT OR REPLACE INTO file_cache (
                file_path, folder, file_hash, hash_type, sample_size,
                file_size, file_mtime, video_duration, video_codec,
                video_resolution, last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)

        # Single commit for entire batch
        self.conn.commit()

    def update_cache(
        self,
        file_path: str,
        folder: str,
        file_hash: str,
        file_size: int,
        file_mtime: float,
        hash_type: str = 'full'
    ):
        """
        Update an existing cache entry with new hash/metadata.

        Args:
            file_path: Full absolute path to file
            folder: 'input' or 'output'
            file_hash: New xxHash hex digest
            file_size: New file size
            file_mtime: New modification time
            hash_type: 'full' or 'sampled'
        """
        cursor = self.conn.cursor()
        now = time.time()

        cursor.execute("""
            UPDATE file_cache
            SET file_hash = ?, file_size = ?, file_mtime = ?,
                hash_type = ?, last_checked = ?
            WHERE file_path = ? AND folder = ?
        """, (file_hash, file_size, file_mtime, hash_type, now, file_path, folder))

        self.conn.commit()

    def find_by_identity(
        self,
        file_size: int,
        file_mtime: float,
        file_hash: str
    ) -> List[Tuple[str, str]]:
        """
        Find files with matching identity (for moved file detection).

        Args:
            file_size: File size in bytes
            file_mtime: Modification time
            file_hash: File hash

        Returns:
            List of (file_path, folder) tuples for matching files
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_path, folder FROM file_cache
            WHERE file_size = ? AND file_mtime = ? AND file_hash = ?
        """, (file_size, file_mtime, file_hash))

        return [(row['file_path'], row['folder']) for row in cursor.fetchall()]

    def update_cache_path(self, old_path: str, folder: str, new_path: str):
        """
        Update file path for a moved file.

        Args:
            old_path: Old file path
            folder: 'input' or 'output'
            new_path: New file path
        """
        cursor = self.conn.cursor()
        now = time.time()

        cursor.execute("""
            UPDATE file_cache
            SET file_path = ?, last_checked = ?
            WHERE file_path = ? AND folder = ?
        """, (new_path, now, old_path, folder))

        self.conn.commit()

    def get_size_groups(self, folder: str, min_group_size: int = 2) -> Dict[int, List[str]]:
        """
        Group files by size (for metadata-first optimization).

        Returns only groups with 2+ files (size collisions).

        Args:
            folder: 'input' or 'output'
            min_group_size: Minimum files in group to include (default 2)

        Returns:
            Dict mapping file_size -> list of file_paths
        """
        cursor = self.conn.cursor()

        # Get all files grouped by size
        cursor.execute("""
            SELECT file_size, file_path FROM file_cache
            WHERE folder = ?
            ORDER BY file_size
        """, (folder,))

        # Build size groups
        size_groups = {}
        for row in cursor.fetchall():
            size = row['file_size']
            path = row['file_path']

            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(path)

        # Filter to only collision groups (2+ files)
        return {
            size: paths
            for size, paths in size_groups.items()
            if len(paths) >= min_group_size
        }

    def get_files_by_hash(self, file_hash: str, folder: Optional[str] = None) -> List[str]:
        """
        Find all files with a specific hash (for duplicate detection).

        Args:
            file_hash: Hash to search for
            folder: Optional folder filter ('input' or 'output')

        Returns:
            List of file paths with matching hash
        """
        cursor = self.conn.cursor()

        if folder:
            cursor.execute("""
                SELECT file_path FROM file_cache
                WHERE file_hash = ? AND folder = ?
            """, (file_hash, folder))
        else:
            cursor.execute("""
                SELECT file_path FROM file_cache
                WHERE file_hash = ?
            """, (file_hash,))

        return [row['file_path'] for row in cursor.fetchall()]

    def get_files_by_paths(self, file_paths: List[str], folder: str) -> Dict[str, CachedFile]:
        """
        Get cached files for specific paths (batch query, much faster than loading all).

        Args:
            file_paths: List of file paths to look up
            folder: 'input' or 'output'

        Returns:
            Dictionary mapping file_path -> CachedFile (only includes found entries)
        """
        if not file_paths:
            return {}

        cursor = self.conn.cursor()
        
        # Use batch query with IN clause (SQLite supports up to 999 parameters)
        # For large lists, split into chunks
        BATCH_SIZE = 999
        result_dict = {}

        for i in range(0, len(file_paths), BATCH_SIZE):
            batch_paths = file_paths[i:i + BATCH_SIZE]
            placeholders = ','.join('?' * len(batch_paths))

            # Build query without f-string to follow SQL injection prevention best practices
            query = """
                SELECT * FROM file_cache
                WHERE folder = ? AND file_path IN ({})
            """.format(placeholders)

            cursor.execute(query, (folder, *batch_paths))

            for row in cursor.fetchall():
                cached = CachedFile(
                    file_path=row['file_path'],
                    folder=row['folder'],
                    file_hash=row['file_hash'],
                    hash_type=row['hash_type'],
                    sample_size=row['sample_size'],
                    file_size=row['file_size'],
                    file_mtime=row['file_mtime'],
                    video_duration=row['video_duration'],
                    video_codec=row['video_codec'],
                    video_resolution=row['video_resolution'],
                    last_checked=row['last_checked']
                )
                result_dict[cached.file_path] = cached

        return result_dict

    def get_all_files(self, folder: str) -> List[CachedFile]:
        """
        Get all cached files for a folder.

        WARNING: This loads ALL cached files into memory. For performance,
        use get_files_by_paths() if you only need specific files.

        Args:
            folder: 'input' or 'output'

        Returns:
            List of CachedFile objects
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM file_cache WHERE folder = ?
        """, (folder,))

        files = []
        for row in cursor.fetchall():
            files.append(CachedFile(
                file_path=row['file_path'],
                folder=row['folder'],
                file_hash=row['file_hash'],
                hash_type=row['hash_type'],
                sample_size=row['sample_size'],
                file_size=row['file_size'],
                file_mtime=row['file_mtime'],
                video_duration=row['video_duration'],
                video_codec=row['video_codec'],
                video_resolution=row['video_resolution'],
                last_checked=row['last_checked']
            ))

        return files

    def clear_cache(self):
        """Clear all cache entries (useful for testing or cache corruption)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM file_cache")
        self.conn.commit()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        cursor = self.conn.cursor()

        # Total files
        cursor.execute("SELECT COUNT(*) as count FROM file_cache")
        total_files = cursor.fetchone()['count']

        # Files with hashes
        cursor.execute("SELECT COUNT(*) as count FROM file_cache WHERE file_hash IS NOT NULL")
        hashed_files = cursor.fetchone()['count']

        # Unique sizes
        cursor.execute("SELECT COUNT(DISTINCT file_size) as count FROM file_cache")
        unique_sizes = cursor.fetchone()['count']

        # Size collision groups
        cursor.execute("""
            SELECT COUNT(*) as count FROM (
                SELECT file_size FROM file_cache
                GROUP BY file_size
                HAVING COUNT(*) >= 2
            )
        """)
        collision_groups = cursor.fetchone()['count']

        # Database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            'total_files': total_files,
            'hashed_files': hashed_files,
            'unhashed_files': total_files - hashed_files,
            'unique_sizes': unique_sizes,
            'size_collision_groups': collision_groups,
            'db_size_bytes': db_size,
            'db_size_mb': round(db_size / (1024 * 1024), 2)
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test the cache module
    import tempfile
    import shutil

    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / 'test_cache'

        print("Testing HashCache...")
        with HashCache(cache_dir) as cache:
            # Test 1: Save entries
            print("\n[Test 1] Saving cache entries...")
            cache.save_to_cache(
                file_path="/test/file1.mp4",
                folder="input",
                file_size=1024000,
                file_mtime=1234567890.0,
                file_hash="abc123",
                hash_type="full"
            )

            cache.save_to_cache(
                file_path="/test/file2.mp4",
                folder="input",
                file_size=1024000,  # Same size (collision)
                file_mtime=1234567891.0,
                file_hash="def456",
                hash_type="full"
            )

            cache.save_to_cache(
                file_path="/test/file3.txt",
                folder="input",
                file_size=5000,  # Unique size
                file_mtime=1234567892.0
                # No hash (unique size)
            )

            print("✓ Saved 3 entries (2 collision, 1 unique)")

            # Test 2: Retrieve entry
            print("\n[Test 2] Retrieving cached entry...")
            cached = cache.get_from_cache("/test/file1.mp4", "input")
            assert cached is not None
            assert cached.file_hash == "abc123"
            assert cached.file_size == 1024000
            print(f"✓ Retrieved: {cached.file_path} (hash: {cached.file_hash})")

            # Test 3: Size grouping
            print("\n[Test 3] Size grouping...")
            groups = cache.get_size_groups("input")
            assert 1024000 in groups
            assert len(groups[1024000]) == 2
            print(f"✓ Found collision group: size={1024000}, files={len(groups[1024000])}")

            # Test 4: Find by hash
            print("\n[Test 4] Finding by hash...")
            matches = cache.get_files_by_hash("abc123", "input")
            assert len(matches) == 1
            assert matches[0] == "/test/file1.mp4"
            print(f"✓ Found {len(matches)} file(s) with hash 'abc123'")

            # Test 5: Cache stats
            print("\n[Test 5] Cache statistics...")
            stats = cache.get_cache_stats()
            print(f"Total files: {stats['total_files']}")
            print(f"Hashed files: {stats['hashed_files']}")
            print(f"Unhashed files: {stats['unhashed_files']}")
            print(f"Unique sizes: {stats['unique_sizes']}")
            print(f"Collision groups: {stats['size_collision_groups']}")
            print(f"Database size: {stats['db_size_mb']} MB")

            assert stats['total_files'] == 3
            assert stats['hashed_files'] == 2
            assert stats['unhashed_files'] == 1
            assert stats['size_collision_groups'] == 1

        print("\n✓ All tests passed!")
