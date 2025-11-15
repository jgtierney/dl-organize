"""
Duplicate resolution policy implementation.

Implements three-tier resolution policy:
1. Priority 1: "keep" keyword (with ancestor priority tiebreaker)
2. Priority 2: Path depth (deeper paths preferred)
3. Priority 3: Newest mtime (most recent file)
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from .hash_cache import CachedFile

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Extended file information for resolution."""
    path: str
    size: int
    mtime: float
    depth: int
    has_keep: bool
    keep_in_folder: bool  # True if "keep" is in folder path, False if only in filename
    keep_ancestor_depth: Optional[int]  # Depth of "keep" ancestor folder (None if no keep)


class DuplicateResolver:
    """
    Resolves duplicate files using custom three-tier policy.

    Resolution Policy:
    1. Priority 1: "keep" keyword (case-insensitive)
       - Files under "keep" folder beat "keep" in filename only
       - Higher ancestor "keep" folders beat lower ones
    2. Priority 2: Path depth (deeper paths preferred)
    3. Priority 3: Newest mtime
    """

    def __init__(self):
        """Initialize duplicate resolver."""
        pass

    def analyze_file(self, file_path: str) -> FileInfo:
        """
        Analyze a file path and extract resolution metadata.

        Args:
            file_path: Absolute path to file

        Returns:
            FileInfo with all resolution metadata
        """
        path = Path(file_path)

        # Get file stats
        try:
            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
        except (OSError, FileNotFoundError):
            size = 0
            mtime = 0.0

        # Calculate path depth (number of path components)
        depth = len(path.parts)

        # Check for "keep" keyword (case-insensitive)
        path_lower = file_path.lower()
        has_keep = 'keep' in path_lower

        # Determine if "keep" is in folder path or just filename
        keep_in_folder = False
        keep_ancestor_depth = None

        if has_keep:
            # Check each ancestor folder for "keep"
            parent_path = path.parent
            parent_parts = parent_path.parts

            for i, part in enumerate(parent_parts):
                if 'keep' in part.lower():
                    keep_in_folder = True
                    # Calculate depth from root to "keep" folder
                    # Higher value = closer to root = higher priority
                    keep_ancestor_depth = i + 1
                    break  # Use first (highest) "keep" ancestor

        return FileInfo(
            path=file_path,
            size=size,
            mtime=mtime,
            depth=depth,
            has_keep=has_keep,
            keep_in_folder=keep_in_folder,
            keep_ancestor_depth=keep_ancestor_depth
        )

    def compare_files(self, file1: FileInfo, file2: FileInfo) -> int:
        """
        Compare two files using resolution policy.

        Args:
            file1: First file info
            file2: Second file info

        Returns:
            -1 if file1 should be kept (file2 deleted)
            1 if file2 should be kept (file1 deleted)
            0 if equal priority (shouldn't happen with 3-tier policy)
        """
        # Priority 1: "keep" keyword
        if file1.has_keep and not file2.has_keep:
            return -1  # Keep file1
        if file2.has_keep and not file1.has_keep:
            return 1  # Keep file2

        if file1.has_keep and file2.has_keep:
            # Both have "keep" - apply tiebreaker rules

            # Rule 1: "keep" in folder beats "keep" in filename only
            if file1.keep_in_folder and not file2.keep_in_folder:
                return -1  # Keep file1
            if file2.keep_in_folder and not file1.keep_in_folder:
                return 1  # Keep file2

            # Rule 2: Higher ancestor "keep" folders beat lower ones
            if file1.keep_in_folder and file2.keep_in_folder:
                # Both under "keep" folders - compare ancestor depths
                # LOWER depth number = HIGHER in tree = HIGHER priority
                # Example: /keep/sub/file.mp4 (depth=1) > /data/keep/file.mp4 (depth=2)
                if file1.keep_ancestor_depth < file2.keep_ancestor_depth:
                    return -1  # Keep file1 (higher ancestor)
                if file2.keep_ancestor_depth < file1.keep_ancestor_depth:
                    return 1  # Keep file2 (higher ancestor)

        # Priority 2: Path depth (deeper paths preferred)
        if file1.depth > file2.depth:
            return -1  # Keep file1 (deeper)
        if file2.depth > file1.depth:
            return 1  # Keep file2 (deeper)

        # Priority 3: Newest mtime
        if file1.mtime > file2.mtime:
            return -1  # Keep file1 (newer)
        if file2.mtime > file1.mtime:
            return 1  # Keep file2 (newer)

        # Equal priority (shouldn't happen in practice)
        return 0

    def resolve_duplicates(self, file_paths: List[str]) -> Tuple[str, List[str]]:
        """
        Resolve a group of duplicate files.

        Determines which file to keep and which to delete.

        Args:
            file_paths: List of duplicate file paths (2+ files)

        Returns:
            Tuple of (file_to_keep, files_to_delete)
        """
        if not file_paths:
            return None, []

        if len(file_paths) == 1:
            return file_paths[0], []

        # Analyze all files
        file_infos = [self.analyze_file(path) for path in file_paths]

        # Find the file with highest priority
        best_file = file_infos[0]
        for file_info in file_infos[1:]:
            comparison = self.compare_files(best_file, file_info)
            if comparison > 0:
                # Current file_info is better
                best_file = file_info

        # Build delete list (all files except the best one)
        files_to_delete = [
            f.path for f in file_infos
            if f.path != best_file.path
        ]

        return best_file.path, files_to_delete

    def resolve_duplicates_with_cache(
        self, 
        file_paths: List[str],
        cache_lookup: Dict[str, CachedFile]
    ) -> Tuple[str, List[str]]:
        """
        Resolve duplicates using cached metadata (no filesystem calls).
        
        This is the optimized version that uses cached metadata instead of
        calling stat() for each file. Much faster (100-1000x) but doesn't
        verify files still exist.
        
        Args:
            file_paths: List of duplicate file paths
            cache_lookup: Dictionary mapping file_path -> CachedFile
            
        Returns:
            Tuple of (file_to_keep, files_to_delete)
        """
        if not file_paths:
            return None, []
        
        if len(file_paths) == 1:
            return file_paths[0], []
        
        # Analyze all files using cached metadata
        file_infos = []
        for path in file_paths:
            cached = cache_lookup.get(path)
            if cached:
                # Use cached metadata (fast - no filesystem call)
                file_info = self.analyze_file_from_cache(path, cached)
            else:
                # Fallback to stat() if not in cache (rare - should not happen)
                # Log warning for debugging
                logger.warning(f"File not in cache, using stat(): {path}")
                file_info = self.analyze_file(path)
            file_infos.append(file_info)
        
        # Find the file with highest priority (same logic as resolve_duplicates)
        best_file = file_infos[0]
        for file_info in file_infos[1:]:
            comparison = self.compare_files(best_file, file_info)
            if comparison > 0:
                # Current file_info is better
                best_file = file_info
        
        # Build delete list (all files except the best one)
        files_to_delete = [
            f.path for f in file_infos
            if f.path != best_file.path
        ]
        
        return best_file.path, files_to_delete

    def analyze_file_from_cache(self, file_path: str, cached: CachedFile) -> FileInfo:
        """
        Analyze a file using cached metadata (no filesystem calls).
        
        Args:
            file_path: Absolute path to file
            cached: CachedFile object with metadata
            
        Returns:
            FileInfo with all resolution metadata
        """
        path = Path(file_path)
        
        # Use cached metadata (no stat() call!)
        size = cached.file_size
        mtime = cached.file_mtime
        
        # Calculate path depth (number of path components)
        depth = len(path.parts)
        
        # Check for "keep" keyword (case-insensitive)
        path_lower = file_path.lower()
        has_keep = 'keep' in path_lower
        
        # Determine if "keep" is in folder path or just filename
        keep_in_folder = False
        keep_ancestor_depth = None
        
        if has_keep:
            # Check each ancestor folder for "keep"
            parent_path = path.parent
            parent_parts = parent_path.parts
            
            for i, part in enumerate(parent_parts):
                if 'keep' in part.lower():
                    keep_in_folder = True
                    keep_ancestor_depth = i + 1
                    break
        
        return FileInfo(
            path=file_path,
            size=size,
            mtime=mtime,
            depth=depth,
            has_keep=has_keep,
            keep_in_folder=keep_in_folder,
            keep_ancestor_depth=keep_ancestor_depth
        )

    def explain_decision(self, file_to_keep: str, files_to_delete: List[str]) -> str:
        """
        Generate human-readable explanation of resolution decision.

        Args:
            file_to_keep: Path to file that will be kept
            files_to_delete: List of paths that will be deleted

        Returns:
            Formatted explanation string
        """
        if not files_to_delete:
            return "No duplicates to resolve."

        keep_info = self.analyze_file(file_to_keep)
        delete_infos = [self.analyze_file(path) for path in files_to_delete]

        lines = ["", "=== Duplicate Resolution ==="]
        lines.append(f"Keeping: {Path(file_to_keep).name}")
        lines.append(f"Deleting: {len(files_to_delete)} duplicate(s)")
        lines.append("")
        lines.append("Resolution reason:")

        # Determine primary reason
        if keep_info.has_keep:
            if all(not info.has_keep for info in delete_infos):
                lines.append("  ✓ Priority 1: Has 'keep' keyword")
            else:
                # Multiple files with "keep" - explain tiebreaker
                if keep_info.keep_in_folder:
                    lines.append("  ✓ Priority 1: 'keep' in folder path (beats filename only)")
                    if keep_info.keep_ancestor_depth:
                        lines.append(f"    Ancestor depth: {keep_info.keep_ancestor_depth} (higher ancestor wins)")
                else:
                    lines.append("  ✓ Priority 1: 'keep' in filename")
        else:
            # No "keep" keyword - check other priorities
            if any(keep_info.depth > info.depth for info in delete_infos):
                lines.append(f"  ✓ Priority 2: Deeper path (depth={keep_info.depth})")
            else:
                lines.append(f"  ✓ Priority 3: Newest file (mtime={keep_info.mtime:.0f})")

        lines.append("")
        lines.append("Details:")
        lines.append(f"  Keep: {file_to_keep}")
        lines.append(f"    depth={keep_info.depth}, mtime={keep_info.mtime:.0f}, has_keep={keep_info.has_keep}")

        for delete_path in files_to_delete:
            delete_info = self.analyze_file(delete_path)
            lines.append(f"  Delete: {delete_path}")
            lines.append(f"    depth={delete_info.depth}, mtime={delete_info.mtime:.0f}, has_keep={delete_info.has_keep}")

        lines.append("=" * 40)
        return "\n".join(lines)


if __name__ == "__main__":
    # Test the resolver
    import tempfile
    import time

    print("Testing DuplicateResolver...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_root = Path(tmpdir)

        # Create test directory structure
        print("\n[Setup] Creating test files...")

        # Scenario 1: "keep" keyword wins
        keep_dir = test_root / 'keep' / 'important'
        keep_dir.mkdir(parents=True)
        keep_file = keep_dir / 'video.mp4'
        keep_file.write_bytes(b'test')

        archive_dir = test_root / 'archive'
        archive_dir.mkdir(parents=True)
        archive_file = archive_dir / 'video.mp4'
        archive_file.write_bytes(b'test')

        # Scenario 2: Ancestor priority (grandparent > parent)
        grandparent_keep = test_root / 'keep' / 'videos' / 'action'
        grandparent_keep.mkdir(parents=True)
        grandparent_file = grandparent_keep / 'movie.mkv'
        grandparent_file.write_bytes(b'test')

        parent_keep = test_root / 'data' / 'keep'
        parent_keep.mkdir(parents=True)
        parent_file = parent_keep / 'movie.mkv'
        parent_file.write_bytes(b'test')

        # Scenario 3: Folder beats filename
        folder_keep = test_root / 'keep' / 'old'
        folder_keep.mkdir(parents=True)
        folder_keep_file = folder_keep / 'file.mp4'
        folder_keep_file.write_bytes(b'test')

        filename_keep = test_root / 'data' / 'keep_this_file.mp4'
        filename_keep.write_bytes(b'test')

        # Scenario 4: Depth wins
        shallow = test_root / 'video.mp4'
        shallow.write_bytes(b'test')

        deep_dir = test_root / 'movies' / 'action' / 'adventure'
        deep_dir.mkdir(parents=True)
        deep = deep_dir / 'video.mp4'
        deep.write_bytes(b'test')

        # Scenario 5: Newest wins
        old_file = test_root / 'old' / 'doc.pdf'
        old_file.parent.mkdir(parents=True)
        old_file.write_bytes(b'test')
        old_mtime = time.time() - 365 * 24 * 3600  # 1 year ago
        os.utime(old_file, (old_mtime, old_mtime))

        new_file = test_root / 'new' / 'doc.pdf'
        new_file.parent.mkdir(parents=True)
        new_file.write_bytes(b'test')
        # Current time

        print("✓ Created test directory structure")

        # Test resolver
        resolver = DuplicateResolver()

        # Test 1: "keep" keyword wins
        print("\n[Test 1] 'keep' keyword priority...")
        to_keep, to_delete = resolver.resolve_duplicates([str(archive_file), str(keep_file)])
        assert str(keep_file) == to_keep, "Should keep file with 'keep' keyword"
        print(f"✓ Kept: {Path(to_keep).name}")
        print(resolver.explain_decision(to_keep, to_delete))

        # Test 2: Ancestor priority (grandparent > parent)
        print("\n[Test 2] Ancestor priority (higher ancestor wins)...")
        to_keep, to_delete = resolver.resolve_duplicates([str(parent_file), str(grandparent_file)])
        assert str(grandparent_file) == to_keep, "Should keep file with higher 'keep' ancestor"
        print(f"✓ Kept: {Path(to_keep).name} (grandparent 'keep' > parent 'keep')")
        print(resolver.explain_decision(to_keep, to_delete))

        # Test 3: Folder beats filename
        print("\n[Test 3] Folder 'keep' beats filename 'keep'...")
        to_keep, to_delete = resolver.resolve_duplicates([str(filename_keep), str(folder_keep_file)])
        assert str(folder_keep_file) == to_keep, "Should keep file under 'keep' folder"
        print(f"✓ Kept: {Path(to_keep).name} (folder > filename)")
        print(resolver.explain_decision(to_keep, to_delete))

        # Test 4: Depth wins
        print("\n[Test 4] Path depth priority...")
        to_keep, to_delete = resolver.resolve_duplicates([str(shallow), str(deep)])
        assert str(deep) == to_keep, "Should keep deeper path"
        print(f"✓ Kept: {Path(to_keep).name} (deeper path)")
        print(resolver.explain_decision(to_keep, to_delete))

        # Test 5: Newest wins
        print("\n[Test 5] Newest mtime priority...")
        to_keep, to_delete = resolver.resolve_duplicates([str(old_file), str(new_file)])
        assert str(new_file) == to_keep, "Should keep newest file"
        print(f"✓ Kept: {Path(to_keep).name} (newest)")
        print(resolver.explain_decision(to_keep, to_delete))

    print("\n✓ All tests passed!")
