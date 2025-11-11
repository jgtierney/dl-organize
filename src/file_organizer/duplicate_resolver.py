"""
Duplicate resolution policy for Stage 3.

Implements custom three-tier resolution policy:
Priority 1: "keep" keyword in path (case-insensitive)
Priority 2: Path depth (deeper = better organized = keep)
Priority 3: Newest modification time
"""

from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DuplicateResolver:
    """
    Resolves which duplicate to keep using custom policy.
    
    Resolution priority:
    1. "keep" keyword anywhere in path (case-insensitive)
    2. Deeper path (more organized)
    3. Newest modification time
    """
    
    def __init__(self, keep_keyword: str = "keep", 
                 case_sensitive: bool = False):
        """
        Initialize resolver.
        
        Args:
            keep_keyword: Keyword to look for in paths
            case_sensitive: Whether keyword matching is case-sensitive
        """
        self.keep_keyword = keep_keyword
        self.case_sensitive = case_sensitive
    
    def has_keep_keyword(self, file_path: Path) -> bool:
        """
        Check if path contains "keep" keyword.
        
        Args:
            file_path: Path to check
        
        Returns:
            True if path contains keyword
        """
        path_str = str(file_path)
        keyword = self.keep_keyword
        
        if not self.case_sensitive:
            path_str = path_str.lower()
            keyword = keyword.lower()
        
        return keyword in path_str
    
    def get_path_depth(self, file_path: Path) -> int:
        """
        Calculate path depth (number of path components).
        
        Args:
            file_path: Path to measure
        
        Returns:
            Depth (number of components)
        """
        return len(file_path.parts)
    
    def get_mtime(self, file_path: Path) -> float:
        """
        Get modification time of file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Modification time (Unix timestamp)
        """
        try:
            return file_path.stat().st_mtime
        except OSError as e:
            logger.warning(f"Cannot get mtime for {file_path}: {e}")
            return 0.0
    
    def resolve(self, duplicates: List[Path]) -> Tuple[Path, List[Path]]:
        """
        Resolve which duplicate to keep.
        
        Args:
            duplicates: List of duplicate file paths (2+ files)
        
        Returns:
            Tuple of (file_to_keep, files_to_delete)
        """
        if len(duplicates) < 2:
            raise ValueError("Need at least 2 duplicates to resolve")
        
        # Priority 1: Check for "keep" keyword
        keep_files = [f for f in duplicates if self.has_keep_keyword(f)]
        
        if len(keep_files) == 1:
            # Exactly one file has "keep" keyword
            winner = keep_files[0]
            losers = [f for f in duplicates if f != winner]
            logger.debug(f"Resolved by 'keep' keyword: {winner}")
            return (winner, losers)
        
        elif len(keep_files) > 1:
            # Multiple files have "keep" keyword, need tiebreaker
            logger.debug(f"{len(keep_files)} files have 'keep' keyword, using depth tiebreaker")
            candidates = keep_files
        else:
            # No files have "keep" keyword
            candidates = duplicates
        
        # Priority 2: Path depth (keep deepest)
        depths = [(f, self.get_path_depth(f)) for f in candidates]
        max_depth = max(d for _, d in depths)
        deepest_files = [f for f, d in depths if d == max_depth]
        
        if len(deepest_files) == 1:
            # Exactly one file has deepest path
            winner = deepest_files[0]
            losers = [f for f in duplicates if f != winner]
            logger.debug(f"Resolved by path depth ({max_depth}): {winner}")
            return (winner, losers)
        
        elif len(deepest_files) > 1:
            # Multiple files have same depth, need tiebreaker
            logger.debug(f"{len(deepest_files)} files have depth {max_depth}, using mtime tiebreaker")
            candidates = deepest_files
        
        # Priority 3: Newest modification time
        mtimes = [(f, self.get_mtime(f)) for f in candidates]
        newest_mtime = max(t for _, t in mtimes)
        newest_files = [f for f, t in mtimes if abs(t - newest_mtime) < 0.001]
        
        if len(newest_files) >= 1:
            # Pick first if multiple have same mtime
            winner = newest_files[0]
            losers = [f for f in duplicates if f != winner]
            logger.debug(f"Resolved by mtime: {winner}")
            return (winner, losers)
        
        # Fallback: Just pick first (shouldn't reach here)
        winner = candidates[0]
        losers = [f for f in duplicates if f != winner]
        logger.warning(f"Resolved by fallback (first): {winner}")
        return (winner, losers)
    
    def resolve_all(self, duplicate_groups: dict) -> Tuple[dict, dict]:
        """
        Resolve all duplicate groups.
        
        Args:
            duplicate_groups: Dict mapping hash to list of duplicate paths
        
        Returns:
            Tuple of (files_to_keep, files_to_delete)
            files_to_keep: Dict mapping hash to file to keep
            files_to_delete: Dict mapping hash to list of files to delete
        """
        files_to_keep = {}
        files_to_delete = {}
        
        for file_hash, duplicates in duplicate_groups.items():
            if len(duplicates) < 2:
                continue
            
            keeper, losers = self.resolve(duplicates)
            files_to_keep[file_hash] = keeper
            files_to_delete[file_hash] = losers
        
        total_to_delete = sum(len(losers) for losers in files_to_delete.values())
        logger.info(f"Resolution complete: {len(files_to_keep)} files to keep, "
                   f"{total_to_delete} files to delete")
        
        return (files_to_keep, files_to_delete)
    
    def explain_resolution(self, duplicates: List[Path]) -> str:
        """
        Explain how a duplicate group would be resolved.
        
        Args:
            duplicates: List of duplicate paths
        
        Returns:
            Human-readable explanation
        """
        if len(duplicates) < 2:
            return "Not a duplicate group (< 2 files)"
        
        winner, losers = self.resolve(duplicates)
        
        # Determine which rule was used
        has_keep = [self.has_keep_keyword(f) for f in duplicates]
        winner_has_keep = self.has_keep_keyword(winner)
        
        if winner_has_keep and sum(has_keep) == 1:
            reason = '"keep" keyword'
        else:
            depths = [self.get_path_depth(f) for f in duplicates]
            winner_depth = self.get_path_depth(winner)
            max_depth = max(depths)
            
            if winner_depth == max_depth and depths.count(max_depth) == 1:
                reason = f'deepest path (depth={winner_depth})'
            else:
                reason = 'newest modification time'
        
        return f"Keep: {winner} ({reason})"

