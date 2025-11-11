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
from .duplicate_reporter import DuplicateReporter

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
        
        # Initialize reporter
        self.reporter = DuplicateReporter()
        
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
        print("\n" + "=" * 70)
        print("STAGE 3A: INTERNAL DEDUPLICATION")
        print("=" * 70)
        
        # Scan input folder
        print(f"\nPhase 1: Scanning input folder...")
        print(f"  Path: {self.input_folder}")
        files = self.scan_folder(self.input_folder)
        print(f"  Found: {len(files):,} files")
        
        # Find duplicates
        print(f"\nPhase 2: Detecting duplicates...")
        duplicates = self.detector.find_all_duplicates(files, folder='input', show_progress=True)
        
        if not duplicates:
            print("\n✓ No duplicates found!")
            return self.stats['stage3a']
        
        # Resolve which to keep
        print(f"\nPhase 3: Resolving duplicate groups...")
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
        
        # Generate detailed duplicate report
        report = self.reporter.report_all_duplicates(
            duplicates, files_to_keep, files_to_delete,
            max_groups_shown=10, show_details=True
        )
        print(report)
        
        # Generate statistics report
        stats_report = self.reporter.report_statistics(
            self.detector.get_stats(),
            sampler_enabled=True,
            video_metadata_enabled=self.detector.use_video_metadata
        )
        print(stats_report)
        
        if self.dry_run:
            print("\n" + "=" * 70)
            print("⚠️  DRY-RUN MODE: No files were modified")
            print("⚠️  Run with --execute to apply changes")
            print("=" * 70)
        else:
            # Confirm execution
            confirmation = self.reporter.confirm_execution(
                len(all_files_to_delete), space_to_reclaim
            )
            print(confirmation)
            
            response = input("\nType 'yes' to confirm deletion: ").strip().lower()
            if response != 'yes':
                print("\n✗ Execution cancelled")
                return self.stats['stage3a']
            
            # Delete files
            print("\nPhase 4: Deleting duplicate files...")
            deleted = self.delete_files(all_files_to_delete)
            
            # Post-execution report
            execution_report = self.reporter.report_execution_results(
                deleted, space_to_reclaim, errors=len(all_files_to_delete) - deleted
            )
            print(execution_report)
        
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
        
        print("\n" + "=" * 70)
        print("STAGE 3B: CROSS-FOLDER DEDUPLICATION")
        print("=" * 70)
        
        # Load output folder cache
        print(f"\nPhase 1: Loading output folder cache...")
        output_hashes_list = self.cache.get_all_hashes('output')
        # Convert list of (path, hash, size) to dict of hash: path
        output_hashes = {h: p for p, h, s in output_hashes_list}
        print(f"  Output folder: {len(output_hashes):,} files in cache")
        
        # Scan input folder
        print(f"\nPhase 2: Scanning input folder...")
        print(f"  Path: {self.input_folder}")
        input_files = self.scan_folder(self.input_folder)
        print(f"  Found: {len(input_files):,} files")
        
        # Find files in input that exist in output
        print(f"\nPhase 3: Comparing input files against output...")
        duplicates = {}
        total = len(input_files)
        update_interval = self._calculate_update_interval(total)
        
        for i, input_file in enumerate(input_files):
            # Progress update
            if (i + 1) % update_interval == 0 or i == total - 1:
                progress = (i + 1) / total * 100
                print(f"  Comparing: {i + 1:,}/{total:,} ({progress:.1f}%)", end='\r')
            
            input_hash = self.detector.compute_hash(input_file, folder='input')
            if input_hash and input_hash in output_hashes:
                # File exists in both input and output
                output_path = output_hashes[input_hash]
                duplicates[input_hash] = [input_file, Path(output_path)]
        
        print(f"  Comparing: {total:,}/{total:,} (100.0%)")
        
        if not duplicates:
            print("\n✓ No cross-folder duplicates found!")
            return self.stats['stage3b']
        
        # Resolve which to keep
        print(f"\nPhase 4: Resolving {len(duplicates):,} duplicate groups...")
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
        total_space = input_space + output_space
        total_deletions = len(input_deletions) + len(output_deletions)
        
        # Update statistics
        self.stats['stage3b']['duplicates_found'] = len(duplicates)
        self.stats['stage3b']['files_deleted'] = total_deletions
        self.stats['stage3b']['space_reclaimed'] = total_space
        
        # Generate detailed duplicate report
        report = self.reporter.report_all_duplicates(
            duplicates, files_to_keep, files_to_delete,
            max_groups_shown=10, show_details=True
        )
        print(report)
        
        # Print folder-specific breakdown
        print(f"\nCross-Folder Breakdown:")
        print(f"  Delete from input:  {len(input_deletions):,} files "
              f"({self.reporter.format_size(input_space)})")
        print(f"  Delete from output: {len(output_deletions):,} files "
              f"({self.reporter.format_size(output_space)})")
        
        # Generate statistics report
        stats_report = self.reporter.report_statistics(
            self.detector.get_stats(),
            sampler_enabled=True,
            video_metadata_enabled=self.detector.use_video_metadata
        )
        print(stats_report)
        
        if self.dry_run:
            print("\n" + "=" * 70)
            print("⚠️  DRY-RUN MODE: No files were modified")
            print("⚠️  Run with --execute to apply changes")
            print("=" * 70)
        else:
            # Confirm execution
            confirmation = self.reporter.confirm_execution(total_deletions, total_space)
            print(confirmation)
            
            response = input("\nType 'yes' to confirm deletion: ").strip().lower()
            if response != 'yes':
                print("\n✗ Execution cancelled")
                return self.stats['stage3b']
            
            # Delete files
            print("\nPhase 5: Deleting duplicate files...")
            deleted_input = self.delete_files(input_deletions)
            deleted_output = self.delete_files(output_deletions)
            total_deleted = deleted_input + deleted_output
            total_errors = total_deletions - total_deleted
            
            # Post-execution report
            execution_report = self.reporter.report_execution_results(
                total_deleted, total_space, errors=total_errors
            )
            print(execution_report)
        
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
        
        # Print combined summary if both phases were run
        if len(phases) > 1:
            total_duplicates = (self.stats['stage3a']['duplicates_found'] + 
                               self.stats['stage3b']['duplicates_found'])
            total_deleted = (self.stats['stage3a']['files_deleted'] + 
                            self.stats['stage3b']['files_deleted'])
            total_space = (self.stats['stage3a']['space_reclaimed'] + 
                          self.stats['stage3b']['space_reclaimed'])
            
            print("\n" + "=" * 70)
            print("STAGE 3 COMPLETE")
            print("=" * 70)
            print(f"Total duplicates found: {total_duplicates:,}")
            print(f"Total files deleted:    {total_deleted:,}")
            print(f"Total space reclaimed:  {total_space / (1024**3):.2f} GB")
            print("=" * 70)
        
        return self.stats
    
    def _calculate_update_interval(self, total: int) -> int:
        """
        Calculate adaptive progress update interval.
        
        Args:
            total: Total number of items
        
        Returns:
            Update interval
        """
        if total < 1000:
            return 10
        elif total < 10000:
            return 100
        elif total < 100000:
            return 500
        else:
            return 1000
    
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

