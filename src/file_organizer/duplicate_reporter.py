"""
Comprehensive duplicate detection reporting for Stage 3.

Provides detailed reports for dry-run and execute modes, including:
- Duplicate group details
- Resolution decisions with reasons
- Space savings calculations
- Sampling and video optimization statistics
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class DuplicateReporter:
    """
    Generate comprehensive duplicate detection reports.
    
    Formats dry-run previews, execute confirmations, and post-execution summaries.
    """
    
    def __init__(self):
        """Initialize reporter."""
        self.report_lines = []
    
    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
        
        Returns:
            Formatted string (e.g., "1.23 GB", "456 MB")
        """
        if size_bytes >= 1024**4:  # TB
            return f"{size_bytes / (1024**4):.2f} TB"
        elif size_bytes >= 1024**3:  # GB
            return f"{size_bytes / (1024**3):.2f} GB"
        elif size_bytes >= 1024**2:  # MB
            return f"{size_bytes / (1024**2):.2f} MB"
        elif size_bytes >= 1024:  # KB
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} bytes"
    
    def format_path(self, path: Path, max_len: int = 70) -> str:
        """
        Format path with truncation if too long.
        
        Args:
            path: Path to format
            max_len: Maximum length
        
        Returns:
            Formatted path string
        """
        path_str = str(path)
        if len(path_str) <= max_len:
            return path_str
        
        # Truncate middle
        prefix_len = max_len // 2 - 2
        suffix_len = max_len // 2 - 2
        return f"{path_str[:prefix_len]}...{path_str[-suffix_len:]}"
    
    def get_resolution_reason(self, kept_file: Path, losers: List[Path]) -> str:
        """
        Determine the reason why a file was kept.
        
        Args:
            kept_file: The file that was kept
            losers: List of files that were deleted
        
        Returns:
            Reason string
        """
        kept_str = str(kept_file).lower()
        
        # Check for 'keep' keyword
        if 'keep' in kept_str:
            return "contains 'keep'"
        
        # Check path depth
        kept_depth = len(kept_file.parts)
        loser_depths = [len(loser.parts) for loser in losers]
        
        if all(kept_depth > depth for depth in loser_depths):
            return "deeper path"
        
        # Must be newest
        return "newest file"
    
    def report_duplicate_group(self, hash_value: str, files: List[Path], 
                               files_to_keep: Dict[str, Path],
                               files_to_delete: Dict[str, List[Path]],
                               show_details: bool = True) -> List[str]:
        """
        Generate report for a single duplicate group.
        
        Args:
            hash_value: Hash of the duplicate group
            files: All files in the group
            files_to_keep: Mapping of hash to kept file
            files_to_delete: Mapping of hash to deleted files
            show_details: Show file details
        
        Returns:
            List of report lines
        """
        lines = []
        
        kept_file = files_to_keep.get(hash_value)
        losers = files_to_delete.get(hash_value, [])
        
        if not kept_file or not losers:
            return lines
        
        # Calculate space saved
        try:
            file_size = kept_file.stat().st_size
            space_saved = file_size * len(losers)
        except OSError:
            file_size = 0
            space_saved = 0
        
        # Get resolution reason
        reason = self.get_resolution_reason(kept_file, losers)
        
        # Format header
        lines.append(f"\n  Duplicate Group (saves {self.format_size(space_saved)}):")
        lines.append(f"    Size: {self.format_size(file_size)}, Files: {len(files)}, Reason: {reason}")
        
        if show_details:
            # Show kept file
            lines.append(f"    ✓ KEEP:   {self.format_path(kept_file)}")
            
            # Show deleted files
            for loser in losers:
                lines.append(f"    ✗ DELETE: {self.format_path(loser)}")
        
        return lines
    
    def report_all_duplicates(self, duplicates: Dict[str, List[Path]],
                             files_to_keep: Dict[str, Path],
                             files_to_delete: Dict[str, List[Path]],
                             max_groups_shown: int = 10,
                             show_details: bool = True) -> str:
        """
        Generate comprehensive duplicate report.
        
        Args:
            duplicates: All duplicate groups
            files_to_keep: Mapping of hash to kept file
            files_to_delete: Mapping of hash to deleted files
            max_groups_shown: Maximum groups to show in detail
            show_details: Show file details for each group
        
        Returns:
            Formatted report string
        """
        lines = []
        
        lines.append("\n" + "=" * 70)
        lines.append("DUPLICATE DETECTION REPORT")
        lines.append("=" * 70)
        
        # Calculate totals
        total_groups = len(duplicates)
        total_files_to_delete = sum(len(losers) for losers in files_to_delete.values())
        total_space_saved = 0
        
        for hash_value, losers in files_to_delete.items():
            kept_file = files_to_keep.get(hash_value)
            if kept_file:
                try:
                    file_size = kept_file.stat().st_size
                    total_space_saved += file_size * len(losers)
                except OSError:
                    pass
        
        # Summary
        lines.append(f"\nSummary:")
        lines.append(f"  Duplicate groups:     {total_groups:,}")
        lines.append(f"  Files to keep:        {len(files_to_keep):,}")
        lines.append(f"  Files to delete:      {total_files_to_delete:,}")
        lines.append(f"  Space to reclaim:     {self.format_size(total_space_saved)}")
        
        # Show detailed groups
        if show_details and total_groups > 0:
            lines.append(f"\nDuplicate Groups (showing {min(max_groups_shown, total_groups)} of {total_groups}):")
            
            shown = 0
            for hash_value, file_list in duplicates.items():
                if shown >= max_groups_shown:
                    break
                
                group_lines = self.report_duplicate_group(
                    hash_value, file_list, files_to_keep, files_to_delete, show_details=True
                )
                lines.extend(group_lines)
                shown += 1
            
            if total_groups > max_groups_shown:
                remaining = total_groups - max_groups_shown
                lines.append(f"\n  ... and {remaining:,} more duplicate groups")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def report_statistics(self, detector_stats: Dict[str, int],
                         sampler_enabled: bool = True,
                         video_metadata_enabled: bool = True) -> str:
        """
        Generate statistics report for detection process.
        
        Args:
            detector_stats: Statistics from DuplicateDetector
            sampler_enabled: Whether sampling is enabled
            video_metadata_enabled: Whether video metadata is enabled
        
        Returns:
            Formatted statistics string
        """
        lines = []
        
        lines.append("\n" + "=" * 70)
        lines.append("DETECTION STATISTICS")
        lines.append("=" * 70)
        
        # File processing stats
        total_files = detector_stats.get('total_files', 0)
        skipped_images = detector_stats.get('skipped_images', 0)
        skipped_small = detector_stats.get('skipped_small', 0)
        processed = total_files - skipped_images - skipped_small
        
        lines.append(f"\nFile Processing:")
        lines.append(f"  Total files scanned:  {total_files:,}")
        lines.append(f"  Files processed:      {processed:,}")
        lines.append(f"  Skipped (images):     {skipped_images:,}")
        lines.append(f"  Skipped (too small):  {skipped_small:,}")
        
        # Hashing stats
        cache_hits = detector_stats.get('cache_hits', 0)
        files_hashed = detector_stats.get('files_hashed', 0)
        total_hashing_ops = cache_hits + files_hashed
        cache_hit_rate = (cache_hits / total_hashing_ops * 100) if total_hashing_ops > 0 else 0
        
        lines.append(f"\nHashing:")
        lines.append(f"  Cache hits:           {cache_hits:,} ({cache_hit_rate:.1f}%)")
        lines.append(f"  Files hashed:         {files_hashed:,}")
        
        # Sampling stats
        if sampler_enabled:
            sampled_files = detector_stats.get('sampled_files', 0)
            full_hashed = files_hashed - sampled_files
            sample_rate = (sampled_files / files_hashed * 100) if files_hashed > 0 else 0
            
            lines.append(f"\nLarge File Sampling:")
            lines.append(f"  Files sampled:        {sampled_files:,} ({sample_rate:.1f}%)")
            lines.append(f"  Files fully hashed:   {full_hashed:,}")
        
        # Video metadata stats
        if video_metadata_enabled:
            video_checks = detector_stats.get('video_metadata_checks', 0)
            lines.append(f"\nVideo Optimizations:")
            lines.append(f"  Metadata extractions: {video_checks:,}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def confirm_execution(self, files_to_delete_count: int, 
                         space_to_reclaim: int) -> str:
        """
        Generate confirmation prompt for execute mode.
        
        Args:
            files_to_delete_count: Number of files to delete
            space_to_reclaim: Total space in bytes
        
        Returns:
            Formatted confirmation message
        """
        lines = []
        
        lines.append("\n" + "!" * 70)
        lines.append("EXECUTION CONFIRMATION")
        lines.append("!" * 70)
        lines.append(f"\nYou are about to DELETE {files_to_delete_count:,} files!")
        lines.append(f"This will free up {self.format_size(space_to_reclaim)} of disk space.")
        lines.append(f"\nThis operation CANNOT be undone!")
        lines.append("\n" + "!" * 70)
        
        return "\n".join(lines)
    
    def report_execution_results(self, files_deleted: int, 
                                 space_freed: int,
                                 errors: int = 0) -> str:
        """
        Generate post-execution summary report.
        
        Args:
            files_deleted: Number of files actually deleted
            space_freed: Space freed in bytes
            errors: Number of errors encountered
        
        Returns:
            Formatted results string
        """
        lines = []
        
        lines.append("\n" + "=" * 70)
        lines.append("EXECUTION RESULTS")
        lines.append("=" * 70)
        lines.append(f"\nFiles deleted:          {files_deleted:,}")
        lines.append(f"Space freed:            {self.format_size(space_freed)}")
        
        if errors > 0:
            lines.append(f"Errors encountered:     {errors:,}")
            lines.append(f"\n⚠️  Some files could not be deleted. Check the logs for details.")
        else:
            lines.append(f"\n✓ All files successfully deleted!")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)

