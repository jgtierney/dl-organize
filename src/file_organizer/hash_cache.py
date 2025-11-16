"""
SQLite-based hash cache for Stage 3 duplicate detection.

Provides persistent caching of file hashes with moved file detection
based on (size, mtime, hash) identity matching.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class HashCache:
    """
    SQLite cache for file hashes with metadata-based moved file detection.
    
    Features:
    - Persistent hash storage with file metadata
    - Moved file detection (same size+mtime+hash, different path)
    - Cache invalidation on file modification
    - Video metadata caching
    - Support for full and sampled hashes
    """
    
    def __init__(self, cache_path: Path):
        """
        Initialize hash cache.
        
        Args:
            cache_path: Path to SQLite database file
        """
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(str(self.cache_path))
            self.conn.row_factory = sqlite3.Row
            
            # Create main cache table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    file_path TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_mtime REAL NOT NULL,
                    hash_type TEXT NOT NULL,
                    sample_size INTEGER,
                    video_duration REAL,
                    video_codec TEXT,
                    video_resolution TEXT,
                    last_checked REAL NOT NULL,
                    PRIMARY KEY (file_path, folder)
                )
            """)
            
            # Create indexes for performance
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_identity 
                ON file_cache(file_size, file_mtime, file_hash)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash_lookup 
                ON file_cache(file_hash)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_folder 
                ON file_cache(folder)
            """)
            
            self.conn.commit()
            logger.debug(f"Initialized cache database at {self.cache_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get(self, file_path: Path, folder: str) -> Optional[Dict[str, Any]]:
        """
        Get cached hash for a file.
        
        Args:
            file_path: Path to the file
            folder: 'input' or 'output'
        
        Returns:
            Cache entry dict or None if not found
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.execute("""
                SELECT * FROM file_cache 
                WHERE file_path = ? AND folder = ?
            """, (str(file_path), folder))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except sqlite3.Error as e:
            logger.warning(f"Cache lookup failed: {e}")
            return None
    
    def save(self, file_path: Path, folder: str, file_hash: str, 
             size: int, mtime: float, hash_type: str = 'full',
             sample_size: Optional[int] = None,
             video_duration: Optional[float] = None,
             video_codec: Optional[str] = None,
             video_resolution: Optional[str] = None):
        """
        Save or update cache entry for a file.
        
        Args:
            file_path: Path to the file
            folder: 'input' or 'output'
            file_hash: Hash digest (hex string)
            size: File size in bytes
            mtime: Modification time (Unix timestamp)
            hash_type: 'full' or 'sampled'
            sample_size: Total bytes sampled (if sampled)
            video_duration: Video duration in seconds (if video)
            video_codec: Video codec name (if video)
            video_resolution: Video resolution string (if video)
        """
        if not self.conn:
            return
        
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO file_cache 
                (file_path, folder, file_hash, file_size, file_mtime, 
                 hash_type, sample_size, video_duration, video_codec, 
                 video_resolution, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(file_path), folder, file_hash, size, mtime, hash_type,
                  sample_size, video_duration, video_codec, video_resolution,
                  time.time()))
            
            self.conn.commit()
            logger.debug(f"Cached hash for {file_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to save cache entry: {e}")
    
    def is_valid(self, cached_entry: Dict[str, Any], current_size: int, 
                 current_mtime: float) -> bool:
        """
        Check if cached entry is still valid.
        
        Args:
            cached_entry: Cache entry dict
            current_size: Current file size
            current_mtime: Current modification time
        
        Returns:
            True if cache entry is valid (file unchanged)
        """
        return (cached_entry['file_size'] == current_size and 
                abs(cached_entry['file_mtime'] - current_mtime) < 0.001)
    
    def find_moved_file(self, size: int, mtime: float, file_hash: str, 
                       folder: str) -> Optional[str]:
        """
        Find a file that was moved (same identity, different path).
        
        Args:
            size: File size
            mtime: Modification time
            file_hash: File hash
            folder: 'input' or 'output'
        
        Returns:
            Old file path if found, None otherwise
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.execute("""
                SELECT file_path FROM file_cache
                WHERE file_size = ? AND file_mtime = ? AND file_hash = ? 
                AND folder = ?
                LIMIT 1
            """, (size, mtime, file_hash, folder))
            
            row = cursor.fetchone()
            if row:
                return row['file_path']
            return None
            
        except sqlite3.Error as e:
            logger.warning(f"Moved file lookup failed: {e}")
            return None
    
    def update_path(self, old_path: Path, new_path: Path, folder: str):
        """
        Update file path in cache (for moved files).
        
        Args:
            old_path: Old file path
            new_path: New file path
            folder: 'input' or 'output'
        """
        if not self.conn:
            return
        
        try:
            self.conn.execute("""
                UPDATE file_cache 
                SET file_path = ?, last_checked = ?
                WHERE file_path = ? AND folder = ?
            """, (str(new_path), time.time(), str(old_path), folder))
            
            self.conn.commit()
            logger.debug(f"Updated cache path: {old_path} -> {new_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to update cache path: {e}")
    
    def get_all_hashes(self, folder: str) -> List[Tuple[str, str, int]]:
        """
        Get all hashes for a folder.
        
        Args:
            folder: 'input' or 'output'
        
        Returns:
            List of (file_path, file_hash, file_size) tuples
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.execute("""
                SELECT file_path, file_hash, file_size 
                FROM file_cache 
                WHERE folder = ?
            """, (folder,))
            
            return [(row['file_path'], row['file_hash'], row['file_size']) 
                    for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get all hashes: {e}")
            return []
    
    def clear_folder(self, folder: str):
        """
        Clear all cache entries for a folder.
        
        Args:
            folder: 'input' or 'output'
        """
        if not self.conn:
            return
        
        try:
            self.conn.execute("DELETE FROM file_cache WHERE folder = ?", (folder,))
            self.conn.commit()
            logger.info(f"Cleared cache for folder: {folder}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        if not self.conn:
            return {}
        
        try:
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(CASE WHEN folder = 'input' THEN 1 ELSE 0 END) as input_entries,
                    SUM(CASE WHEN folder = 'output' THEN 1 ELSE 0 END) as output_entries,
                    SUM(CASE WHEN hash_type = 'sampled' THEN 1 ELSE 0 END) as sampled_entries,
                    SUM(CASE WHEN video_duration IS NOT NULL THEN 1 ELSE 0 END) as video_entries
                FROM file_cache
            """)
            
            row = cursor.fetchone()
            return dict(row) if row else {}
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Closed cache database connection")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

