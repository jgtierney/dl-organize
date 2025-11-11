"""
Core duplicate detection logic for Stage 3.

Provides hash computation (xxHash), size-based grouping, and duplicate identification.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import logging

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False
    import hashlib
    logging.warning("xxhash not available, falling back to SHA-1")

from .file_sampler import FileSampler, read_file_chunked
from .video_utils import is_video_file, extract_video_metadata, videos_likely_different
from .hash_cache import HashCache

logger = logging.getLogger(__name__)

# Image file extensions to skip
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', 
    '.svg', '.ico', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw', 
    '.dng', '.psd', '.ai'
}


class DuplicateDetector:
    """
    Detects duplicate files using hash-based comparison.
    
    Features:
    - xxHash for speed (fallback to SHA-1)
    - Large file sampling
    - Video metadata pre-filtering
    - Size-based grouping optimization
    - File type filtering (skip images, small files)
    """
    
    def __init__(self, 
                 cache: HashCache,
                 sampler: Optional[FileSampler] = None,
                 skip_images: bool = True,
                 min_file_size: int = 10 * 1024,  # 10KB
                 use_video_metadata: bool = True):
        """
        Initialize duplicate detector.
        
        Args:
            cache: Hash cache instance
            sampler: File sampler instance (None = create default)
            skip_images: Skip image files
            min_file_size: Minimum file size to process (bytes)
            use_video_metadata: Use video metadata for pre-filtering
        """
        self.cache = cache
        self.sampler = sampler or FileSampler()
        self.skip_images = skip_images
        self.min_file_size = min_file_size
        self.use_video_metadata = use_video_metadata
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'skipped_images': 0,
            'skipped_small': 0,
            'cache_hits': 0,
            'files_hashed': 0,
            'sampled_files': 0,
            'video_metadata_checks': 0
        }
    
    def should_process_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Determine if file should be processed.
        
        Args:
            file_path: Path to file
        
        Returns:
            Tuple of (should_process, reason)
        """
        # Check if it's an image (skip if configured)
        if self.skip_images and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return (False, "image file")
        
        # Check minimum file size
        try:
            size = file_path.stat().st_size
            if size < self.min_file_size:
                return (False, "too small")
        except OSError as e:
            logger.warning(f"Cannot stat file {file_path}: {e}")
            return (False, "stat error")
        
        return (True, "")
    
    def compute_hash(self, file_path: Path, folder: str = 'input') -> Optional[str]:
        """
        Compute hash for a file (with caching and sampling).
        
        Args:
            file_path: Path to file
            folder: 'input' or 'output'
        
        Returns:
            Hash digest (hex string) or None on error
        """
        try:
            # Get file info
            stat = file_path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            
            # Check cache first
            cached = self.cache.get(file_path, folder)
            if cached and self.cache.is_valid(cached, size, mtime):
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit for {file_path}")
                return cached['file_hash']
            
            # Need to compute hash
            self.stats['files_hashed'] += 1
            
            # Determine if we should sample
            should_sample = self.sampler.should_sample(size)
            hash_type = 'sampled' if should_sample else 'full'
            sample_size = None
            
            # Create hash object
            if XXHASH_AVAILABLE:
                hasher = xxhash.xxh3_128()
            else:
                hasher = hashlib.sha1()
            
            # Compute hash (sampled or full)
            if should_sample:
                samples = self.sampler.read_samples(file_path)
                if samples:
                    head, tail = samples
                    hasher.update(head)
                    hasher.update(tail)
                    sample_size = len(head) + len(tail)
                    self.stats['sampled_files'] += 1
                    logger.debug(f"Sampled hash for {file_path} "
                               f"({sample_size} of {size} bytes)")
                else:
                    # Sampling failed, fall back to full hash
                    for chunk in read_file_chunked(file_path):
                        hasher.update(chunk)
                    hash_type = 'full'
            else:
                # Full hash
                for chunk in read_file_chunked(file_path):
                    hasher.update(chunk)
            
            file_hash = hasher.hexdigest()
            
            # Extract video metadata if applicable
            video_duration = None
            video_codec = None
            video_resolution = None
            
            if self.use_video_metadata and is_video_file(file_path):
                metadata = extract_video_metadata(file_path)
                if metadata:
                    video_duration = metadata.duration
                    video_codec = metadata.codec
                    video_resolution = metadata.resolution
                    self.stats['video_metadata_checks'] += 1
            
            # Save to cache
            self.cache.save(
                file_path, folder, file_hash, size, mtime, hash_type,
                sample_size, video_duration, video_codec, video_resolution
            )
            
            return file_hash
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to hash file {file_path}: {e}")
            return None
    
    def group_by_size(self, files: List[Path]) -> Dict[int, List[Path]]:
        """
        Group files by size.
        
        Args:
            files: List of file paths
        
        Returns:
            Dict mapping size to list of files
        """
        size_groups = defaultdict(list)
        
        for file_path in files:
            self.stats['total_files'] += 1
            
            # Check if should process
            should_process, reason = self.should_process_file(file_path)
            if not should_process:
                if reason == "image file":
                    self.stats['skipped_images'] += 1
                elif reason == "too small":
                    self.stats['skipped_small'] += 1
                continue
            
            # Get size
            try:
                size = file_path.stat().st_size
                size_groups[size].append(file_path)
            except OSError as e:
                logger.warning(f"Cannot stat file {file_path}: {e}")
                continue
        
        logger.info(f"Grouped {self.stats['total_files']} files into "
                   f"{len(size_groups)} size groups")
        logger.info(f"Skipped: {self.stats['skipped_images']} images, "
                   f"{self.stats['skipped_small']} small files")
        
        return dict(size_groups)
    
    def find_duplicates_in_size_group(self, files: List[Path], 
                                     folder: str = 'input') -> Dict[str, List[Path]]:
        """
        Find duplicates within a size group.
        
        Args:
            files: List of files (all same size)
            folder: 'input' or 'output'
        
        Returns:
            Dict mapping hash to list of duplicate files
        """
        hash_groups = defaultdict(list)
        
        # Quick video metadata pre-check (before hashing)
        if self.use_video_metadata and len(files) >= 2:
            # Check if any pair has different durations
            # (can skip hashing if we know they're different)
            pass  # TODO: Implement pairwise duration comparison optimization
        
        # Hash all files in the group
        for file_path in files:
            file_hash = self.compute_hash(file_path, folder)
            if file_hash:
                hash_groups[file_hash].append(file_path)
        
        # Return only groups with duplicates (2+ files)
        duplicates = {h: paths for h, paths in hash_groups.items() 
                     if len(paths) >= 2}
        
        if duplicates:
            logger.debug(f"Found {len(duplicates)} duplicate groups in size group "
                        f"of {len(files)} files")
        
        return duplicates
    
    def find_all_duplicates(self, files: List[Path], 
                           folder: str = 'input') -> Dict[str, List[Path]]:
        """
        Find all duplicates in a list of files.
        
        Args:
            files: List of file paths
            folder: 'input' or 'output'
        
        Returns:
            Dict mapping hash to list of duplicate files
        """
        # Group by size first (optimization)
        size_groups = self.group_by_size(files)
        
        # Find candidates (size groups with 2+ files)
        candidates = {size: paths for size, paths in size_groups.items() 
                     if len(paths) >= 2}
        
        logger.info(f"Found {len(candidates)} size groups with potential duplicates")
        
        # Find duplicates within each size group
        all_duplicates = {}
        for size, paths in candidates.items():
            duplicates = self.find_duplicates_in_size_group(paths, folder)
            all_duplicates.update(duplicates)
        
        logger.info(f"Found {len(all_duplicates)} duplicate groups total")
        logger.info(f"Cache hits: {self.stats['cache_hits']}, "
                   f"Files hashed: {self.stats['files_hashed']}, "
                   f"Sampled: {self.stats['sampled_files']}")
        
        return all_duplicates
    
    def get_stats(self) -> Dict[str, int]:
        """Get detection statistics."""
        return self.stats.copy()

