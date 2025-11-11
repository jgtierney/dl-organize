"""
Stage 3: Video-focused duplicate detection and resolution.

Two-phase architecture:
- Stage 3A: Internal deduplication within input folder
- Stage 3B: Cross-folder deduplication (input vs output)
"""

from pathlib import Path
from typing import List, Optional, Dict
import logging
import os

from .hash_cache import HashCache
from .file_sampler import FileSampler
from .duplicate_detector import DuplicateDetector
from .duplicate_resolver import DuplicateResolver

logger = logging.getLogger(__name__)


class Stage3:
    """
    Main orchestrator for Stage 3 duplicate detection.
    
    Coordinates hash caching, duplicate detection, and resolution policy.
    """
    
    def __init__(self, 
                 input_folder: Path,
                 output_folder: Optional[Path] = None,
                 cache_path: Optional[Path] = None,
                 config: Optional[dict] = None,
                 dry_run: bool = True):
        """
        Initialize Stage 3 processor.
        
        Args:
            input_folder: Path to input folder
            output_folder: Path to output folder (optional for Stage 3A only)
            cache_path: Path to cache database
            config: Configuration dictionary
            dry_run: If True, don't actually delete files
        """
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder) if output_folder else None
        self.dry_run = dry_run
        
        # Configuration
        self.config = config or {}
        dedup_config = self.config.get('duplicate_detection', {})
        
        # Initialize cache
        if cache_path is None:
            cache_dir = Path.home() / '.file_organizer_cache'
            cache_path = cache_dir / 'hashes.db'
        self.cache = HashCache(cache_path)
        
        # Initialize sampler
        threshold = dedup_config.get('large_file_threshold', 20 * 1024 * 1024)
        head_size = dedup_config.get('sample_head_size', 10 * 1024 * 1024)
        tail_size = dedup_config.get('sample_tail_size', 10 * 1024 * 1024)
        adaptive = dedup_config.get('adaptive_sampling', True)
        self.sampler = FileSampler(threshold, head_size, tail_size, adaptive)
        
        # Initialize detector
        skip_images = dedup_config.get('skip_images', True)
        min_size = dedup_config.get('min_file_size', 10 * 1024)
        use_video_metadata = dedup_config.get('use_video_metadata', True)
        self.detector = DuplicateDetector(
            self.cache, self.sampler, skip_images, min_size, use_video_metadata
        )
        
        # Initialize resolver
        self.resolver = DuplicateResolver()
        
        # Statistics
        self.stats = {
            'stage3a': {
                'duplicates_found': 0,
                'files_deleted': 0,
                'space_reclaimed': 0
            },
            'stage3b': {
                'duplicates_found': 0,
                'files_deleted': 0,
                'space_reclaimed': 0
            }
        }
    
    def scan_folder(self, folder: Path) -> List[Path]:
        """
        Recursively scan folder for files.
        
        Args:
            folder: Path to folder to scan
        
        Returns:
            List of file paths
        """
        files = []
        try:
            for item in folder.rglob('*'):
                if item.is_file():
                    files.append(item)
        except (OSError, PermissionError) as e:
            logger.error(f"Error scanning {folder}: {e}")
        
        logger.info(f"Scanned {folder}: found {len(files)} files")
        return files
    
    def delete_files(self, files: List[Path]) -> int:
        """
        Delete files (or report in dry-run mode).
        
        Args:
            files: List of file paths to delete
        
        Returns:
            Number of files actually deleted
        """
        deleted = 0
        for file_path in files:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would delete: {file_path}")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"Deleted: {file_path}")
                    deleted += 1
                except OSError as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        
        return deleted
    
    def calculate_space(self, files: List[Path]) -> int:
        """
        Calculate total space used by files.
        
        Args:
            files: List of file paths
        
        Returns:
            Total size in bytes
        """
        total = 0
        for file_path in files:
            try:
                total += file_path.stat().st_size
            except OSError:
                pass
        return total
    
    def run_stage3a(self) -> dict:
        """
        Run Stage 3A: Internal deduplication within input folder.
        
        Returns:
            Statistics dictionary
        """
        logger.info("=" * 80)
        logger.info("STAGE 3A: INTERNAL DEDUPLICATION")
        logger.info("=" * 80)
        
        # Scan input folder
        logger.info(f"Scanning input folder: {self.input_folder}")
        files = self.scan_folder(self.input_folder)
        
        # Find duplicates
        logger.info("Finding duplicates...")
        duplicates = self.detector.find_all_duplicates(files, folder='input')
        
        if not duplicates:
            logger.info("No duplicates found!")
            return self.stats['stage3a']
        
        # Resolve which to keep
        logger.info(f"Resolving {len(duplicates)} duplicate groups...")
        files_to_keep, files_to_delete = self.resolver.resolve_all(duplicates)
        
        # Calculate space to reclaim
        all_files_to_delete = []
        for losers in files_to_delete.values():
            all_files_to_delete.extend(losers)
        
        space_to_reclaim = self.calculate_space(all_files_to_delete)
        
        # Update statistics
        self.stats['stage3a']['duplicates_found'] = len(duplicates)
        self.stats['stage3a']['files_deleted'] = len(all_files_to_delete)
        self.stats['stage3a']['space_reclaimed'] = space_to_reclaim
        
        # Report
        logger.info(f"\n[SUMMARY]")
        logger.info(f"Duplicate groups found: {len(duplicates)}")
        logger.info(f"Files to keep: {len(files_to_keep)}")
        logger.info(f"Files to delete: {len(all_files_to_delete)}")
        logger.info(f"Space to reclaim: {space_to_reclaim / (1024**3):.2f} GB")
        
        if self.dry_run:
            logger.info("\n! DRY-RUN MODE: No files were modified")
            logger.info("! Run with --execute to apply changes")
        else:
            # Delete files
            logger.info("\n[EXECUTION]")
            deleted = self.delete_files(all_files_to_delete)
            logger.info(f"Deleted {deleted} files")
        
        return self.stats['stage3a']
    
    def run_stage3b(self) -> dict:
        """
        Run Stage 3B: Cross-folder deduplication (input vs output).
        
        Returns:
            Statistics dictionary
        """
        if not self.output_folder:
            logger.error("Stage 3B requires output folder")
            raise ValueError("Output folder not specified")
        
        if not self.output_folder.exists():
            logger.error(f"Output folder does not exist: {self.output_folder}")
            raise FileNotFoundError(f"Output folder not found: {self.output_folder}")
        
        logger.info("=" * 80)
        logger.info("STAGE 3B: CROSS-FOLDER DEDUPLICATION")
        logger.info("=" * 80)
        
        # Load output folder cache
        logger.info(f"Loading output folder cache...")
        output_hashes_list = self.cache.get_all_hashes('output')
        # Convert list of (path, hash, size) to dict of hash: path
        output_hashes = {h: p for p, h, s in output_hashes_list}
        logger.info(f"Output folder: {len(output_hashes)} files in cache")
        
        # Scan input folder
        logger.info(f"Scanning input folder: {self.input_folder}")
        input_files = self.scan_folder(self.input_folder)
        
        # Find files in input that exist in output
        logger.info("Comparing input files against output cache...")
        duplicates = {}
        
        for input_file in input_files:
            input_hash = self.detector.compute_hash(input_file, folder='input')
            if input_hash and input_hash in output_hashes:
                # File exists in both input and output
                output_path = output_hashes[input_hash]
                duplicates[input_hash] = [input_file, Path(output_path)]
        
        if not duplicates:
            logger.info("No cross-folder duplicates found!")
            return self.stats['stage3b']
        
        # Resolve which to keep
        logger.info(f"Resolving {len(duplicates)} cross-folder duplicates...")
        files_to_keep, files_to_delete = self.resolver.resolve_all(duplicates)
        
        # Separate deletions by folder
        input_deletions = []
        output_deletions = []
        
        for losers in files_to_delete.values():
            for loser in losers:
                if loser.is_relative_to(self.input_folder):
                    input_deletions.append(loser)
                elif self.output_folder and loser.is_relative_to(self.output_folder):
                    output_deletions.append(loser)
        
        # Calculate space
        input_space = self.calculate_space(input_deletions)
        output_space = self.calculate_space(output_deletions)
        
        # Update statistics
        self.stats['stage3b']['duplicates_found'] = len(duplicates)
        self.stats['stage3b']['files_deleted'] = len(input_deletions) + len(output_deletions)
        self.stats['stage3b']['space_reclaimed'] = input_space + output_space
        
        # Report
        logger.info(f"\n[SUMMARY]")
        logger.info(f"Cross-folder duplicates: {len(duplicates)}")
        logger.info(f"Files to delete from input: {len(input_deletions)} "
                   f"({input_space / (1024**3):.2f} GB)")
        logger.info(f"Files to delete from output: {len(output_deletions)} "
                   f"({output_space / (1024**3):.2f} GB)")
        
        if self.dry_run:
            logger.info("\n! DRY-RUN MODE: No files were modified")
            logger.info("! Run with --execute to apply changes")
        else:
            # Delete files
            logger.info("\n[EXECUTION]")
            deleted_input = self.delete_files(input_deletions)
            deleted_output = self.delete_files(output_deletions)
            logger.info(f"Deleted {deleted_input} files from input, "
                       f"{deleted_output} files from output")
        
        return self.stats['stage3b']
    
    def run(self, phases: Optional[List[str]] = None) -> dict:
        """
        Run Stage 3 (both phases or specified phases).
        
        Args:
            phases: List of phases to run (['3a'], ['3b'], or ['3a', '3b'])
                   If None, runs both phases
        
        Returns:
            Combined statistics dictionary
        """
        if phases is None:
            phases = ['3a', '3b']
        
        if '3a' in phases:
            self.run_stage3a()
        
        if '3b' in phases:
            self.run_stage3b()
        
        # Print combined summary
        total_duplicates = (self.stats['stage3a']['duplicates_found'] + 
                           self.stats['stage3b']['duplicates_found'])
        total_deleted = (self.stats['stage3a']['files_deleted'] + 
                        self.stats['stage3b']['files_deleted'])
        total_space = (self.stats['stage3a']['space_reclaimed'] + 
                      self.stats['stage3b']['space_reclaimed'])
        
        logger.info("=" * 80)
        logger.info("STAGE 3 COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total duplicates found: {total_duplicates}")
        logger.info(f"Total files deleted: {total_deleted}")
        logger.info(f"Total space reclaimed: {total_space / (1024**3):.2f} GB")
        
        return self.stats
    
    def close(self):
        """Close resources."""
        if self.cache:
            self.cache.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

