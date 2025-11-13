"""
Stage 2: Folder Structure Optimization Processor

Implements the complete Stage 2 workflow:
- Empty folder detection and removal
- Folder chain flattening (< threshold items)
- Iterative flattening (multiple passes)
- Folder name sanitization
- Comprehensive logging
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime

from .filename_cleaner import FilenameCleaner
from .config import Config
from .progress_bar import ProgressBar, SimpleProgress


class Stage2Processor:
    """Stage 2: Folder Structure Optimization."""
    
    def __init__(self, input_dir: Path, dry_run: bool = True,
                 flatten_threshold: int = 5, config: Config = None, verbose: bool = True):
        """
        Initialize Stage 2 processor.

        Args:
            input_dir: Directory to process
            dry_run: If True, preview changes without executing
            flatten_threshold: Number of items below which folders are flattened
            config: Configuration object (optional)
            verbose: If True, print progress messages
        """
        self.input_dir = input_dir.resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        self.flatten_threshold = flatten_threshold
        self.config = config or Config()
        self.cleaner = FilenameCleaner()
        
        # Statistics
        self.stats = {
            'folders_scanned': 0,
            'empty_removed': 0,
            'folders_flattened': 0,
            'folders_renamed': 0,
            'collisions_resolved': 0,
            'errors': 0,
            'flattening_passes': 0,
        }
        
        # Track all target names for collision detection
        self.used_names: Dict[str, Set[str]] = {}  # dir_path -> set of used names
        
        # Track failed operations to prevent infinite loops
        self.failed_folders: Set[str] = set()  # Folders that failed to process
        
        # Track processed folders in dry-run mode (prevent infinite loops)
        self.processed_folders: Set[str] = set()  # Folders already processed in dry-run
        
        # Operation log (for dry-run preview)
        self.operations: List[Tuple[str, str, str]] = []  # (operation, source, dest)

    def _print(self, message: str = "", end: str = '\n'):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message, end=end, flush=True)

    def process(self):
        """Main processing entry point."""
        start_time = datetime.now()

        self._print("\n" + "=" * 70)
        self._print("STAGE 2: FOLDER STRUCTURE OPTIMIZATION")
        self._print("=" * 70)
        self._print(f"Flatten threshold: < {self.flatten_threshold} items")

        if self.dry_run:
            self._print("Mode: DRY-RUN (preview only)")
        else:
            self._print("Mode: EXECUTE")

        self._print("=" * 70)

        # Phase 1: Remove empty folders
        self._print("\nStage 2/4: Folder Optimization - Removing Empty Folders")
        self._remove_empty_folders()

        # Phase 2: Flatten folder chains (iterative)
        self._print("\nStage 2/4: Folder Optimization - Flattening Structure")
        self._flatten_folders_iterative()

        # Phase 3: Sanitize remaining folder names
        self._print("\nStage 2/4: Folder Optimization - Sanitizing Names")
        self._sanitize_folder_names()

        # Phase 4: Show summary
        end_time = datetime.now()
        duration = end_time - start_time

        self._print("\n" + "=" * 70)
        self._print("STAGE 2 SUMMARY")
        self._print("=" * 70)
        self._print(f"Folders scanned:      {self.stats['folders_scanned']:,}")
        self._print(f"Empty folders removed: {self.stats['empty_removed']:,}")
        self._print(f"Folders flattened:    {self.stats['folders_flattened']:,}")
        self._print(f"Folders renamed:      {self.stats['folders_renamed']:,}")
        self._print(f"Collisions resolved:  {self.stats['collisions_resolved']:,}")
        self._print(f"Flattening passes:    {self.stats['flattening_passes']}")
        self._print(f"Errors:               {self.stats['errors']:,}")
        self._print(f"Duration:             {duration.total_seconds():.1f}s")

        if self.dry_run:
            self._print("\n" + "=" * 70)
            self._print("DRY-RUN PREVIEW (showing first 20 operations):")
            self._print("=" * 70)
            for i, (op, src, dest) in enumerate(self.operations[:20]):
                self._print(f"{op}: {src}")
                if dest:
                    self._print(f"  → {dest}")
            if len(self.operations) > 20:
                self._print(f"\n... and {len(self.operations) - 20} more operations")
    
    def _remove_empty_folders(self):
        """
        Remove all empty folders (bottom-up, iterative).

        A folder is empty if it contains no files and no subfolders.
        Process iteratively because removing folders may make parents empty.
        """
        removed_count = 0
        pass_num = 0
        max_passes = 100  # Safety limit to prevent infinite loops

        while pass_num < max_passes:
            pass_num += 1
            folders = self._scan_folders()

            if not folders:
                break

            pass_removed = 0

            # Process bottom-up (deepest first)
            for folder_path in folders:
                folder_key = str(folder_path)

                # Skip folders that previously failed or were already processed
                if folder_key in self.failed_folders or folder_key in self.processed_folders:
                    continue

                if self._is_empty_folder(folder_path):
                    success = self._remove_folder(folder_path)
                    if success:
                        pass_removed += 1
                        # In dry-run, track as processed to prevent re-scanning
                        if self.dry_run:
                            self.processed_folders.add(folder_key)
                    else:
                        # Track failed folder to prevent retrying
                        self.failed_folders.add(folder_key)

            if pass_removed == 0:
                break  # No more empty folders

            removed_count += pass_removed
            # Show pass info in verbose mode
            if self.verbose and pass_removed > 0:
                self._print(f"  Pass {pass_num}: Removed {pass_removed} empty folders")

        if pass_num >= max_passes:
            self._print(f"  WARNING: Reached maximum pass limit ({max_passes})")

        self.stats['empty_removed'] = removed_count
        if removed_count > 0:
            self._print(f"  ✓ Total empty folders removed: {removed_count}")
        else:
            self._print(f"  ✓ No empty folders found")
    
    def _flatten_folders_iterative(self):
        """
        Flatten folder structure iteratively.

        Two flattening rules:
        1. Single-child chains: If folder A contains only folder B, flatten B into A
        2. Small folders: If folder has < threshold items, move contents to parent

        Process iteratively until no more flattening is possible.
        """
        total_flattened = 0
        pass_num = 0
        max_passes = 100  # Safety limit to prevent infinite loops

        while pass_num < max_passes:
            pass_num += 1
            folders = self._scan_folders()

            if not folders:
                break

            pass_flattened = 0

            # Process bottom-up (deepest first)
            for folder_path in folders:
                folder_key = str(folder_path)

                # Skip root directory
                if folder_path == self.input_dir:
                    continue

                # Skip folders that previously failed or were already processed
                if folder_key in self.failed_folders or folder_key in self.processed_folders:
                    continue

                # Check if folder should be flattened
                if self._should_flatten_folder(folder_path):
                    success = self._flatten_folder(folder_path)
                    if success:
                        pass_flattened += 1
                        # In dry-run, track as processed to prevent re-scanning
                        if self.dry_run:
                            self.processed_folders.add(folder_key)
                    else:
                        # Track failed folder to prevent retrying
                        self.failed_folders.add(folder_key)

            if pass_flattened == 0:
                break  # No more flattening possible

            total_flattened += pass_flattened
            # Show pass info in verbose mode
            if self.verbose and pass_flattened > 0:
                self._print(f"  Pass {pass_num}: Flattened {pass_flattened} folders")

        if pass_num >= max_passes:
            self._print(f"  WARNING: Reached maximum pass limit ({max_passes})")

        self.stats['folders_flattened'] = total_flattened
        self.stats['flattening_passes'] = pass_num - 1
        if total_flattened > 0:
            self._print(f"  ✓ Total folders flattened: {total_flattened} (in {pass_num} passes)")
        else:
            self._print(f"  ✓ No folders to flatten")
    
    def _sanitize_folder_names(self):
        """Sanitize all remaining folder names using Stage 1 rules."""
        folders = self._scan_folders()

        if not folders:
            self._print(f"  ✓ No folders to process")
            return

        self.stats['folders_scanned'] = len(folders)
        renamed_count = 0
        collision_count = 0

        # Filter out root directory
        folders_to_process = [f for f in folders if f != self.input_dir]

        if not folders_to_process:
            self._print(f"  ✓ No folders to process")
            return

        progress = ProgressBar(
            total=len(folders_to_process),
            description="Sanitizing Folders",
            verbose=self.verbose,
            min_duration=5.0
        )

        # Process bottom-up to avoid path issues
        for i, folder_path in enumerate(folders_to_process):
            foldername = folder_path.name
            parent_dir = folder_path.parent

            # Sanitize folder name
            new_foldername = self.cleaner.sanitize_filename(foldername, is_directory=True)

            # Check if rename is needed
            if new_foldername != foldername:
                # Track collisions before resolution
                prev_collisions = self.stats['collisions_resolved']

                # Check for collision
                new_foldername = self._resolve_collision(parent_dir, new_foldername)

                # Perform rename
                new_path = parent_dir / new_foldername
                self._rename_folder(folder_path, new_path)
                renamed_count += 1

                # Update collision count
                collision_count = self.stats['collisions_resolved'] - prev_collisions

            # Update progress
            stats = {
                "Renamed": renamed_count,
                "Collisions": collision_count
            }
            progress.update(i + 1, stats)

        # Finish progress
        final_stats = {
            "Renamed": renamed_count,
            "Collisions": collision_count
        }
        progress.finish(final_stats)
        self.stats['folders_renamed'] = renamed_count
    
    def _scan_folders(self) -> List[Path]:
        """
        Scan directory tree and return all folders (bottom-up order).
        
        Returns:
            List of folder paths sorted by depth (deepest first)
        """
        folders = []
        
        try:
            for root, dirs, files in os.walk(self.input_dir, topdown=False):
                root_path = Path(root)
                
                # Collect folders (excluding root itself)
                for dirname in dirs:
                    folder_path = root_path / dirname
                    if folder_path.exists():  # May have been removed/moved
                        folders.append(folder_path)
        except Exception as e:
            self._print(f"  ERROR scanning directory: {e}")
            self.stats['errors'] += 1

        return folders
    
    def _is_empty_folder(self, folder_path: Path) -> bool:
        """
        Check if a folder is empty (no files, no subfolders).
        
        Args:
            folder_path: Folder to check
            
        Returns:
            True if empty, False otherwise
        """
        try:
            # Check if folder exists
            if not folder_path.exists() or not folder_path.is_dir():
                return False
            
            # Check contents
            contents = list(folder_path.iterdir())
            return len(contents) == 0

        except Exception as e:
            self._print(f"  ERROR checking folder {folder_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def _should_flatten_folder(self, folder_path: Path) -> bool:
        """
        Check if a folder should be flattened.
        
        Flattening criteria:
        1. Single-child: Folder contains only one subfolder
        2. Small folder: Folder contains < threshold items (files + folders)
        
        Args:
            folder_path: Folder to check
            
        Returns:
            True if should be flattened, False otherwise
        """
        try:
            # Check if folder exists
            if not folder_path.exists() or not folder_path.is_dir():
                return False
            
            # Don't flatten root directory
            if folder_path == self.input_dir:
                return False
            
            # Count contents
            contents = list(folder_path.iterdir())
            num_items = len(contents)
            
            # Empty folders handled separately
            if num_items == 0:
                return False
            
            # Check if single-child chain (only one subfolder, no files)
            if num_items == 1 and contents[0].is_dir():
                return True
            
            # Check if small folder (< threshold items)
            if num_items < self.flatten_threshold:
                return True
            
            return False

        except Exception as e:
            self._print(f"  ERROR checking folder {folder_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def _flatten_folder(self, folder_path: Path) -> bool:
        """
        Flatten a folder by moving its contents to parent.
        
        Args:
            folder_path: Folder to flatten
            
        Returns:
            True if successful, False if failed
        """
        try:
            parent_dir = folder_path.parent
            
            # Get all items in folder
            contents = list(folder_path.iterdir())
            
            if self.dry_run:
                self.operations.append(("FLATTEN FOLDER", str(folder_path), str(parent_dir)))
                return True
            else:
                # Move each item to parent directory
                move_failed = False
                for item in contents:
                    dest_name = item.name
                    
                    # Check for collision in parent
                    dest_name = self._resolve_collision(parent_dir, dest_name)
                    dest_path = parent_dir / dest_name
                    
                    # Move item
                    try:
                        shutil.move(str(item), str(dest_path))
                    except Exception as e:
                        self._print(f"  ERROR moving {item} to {dest_path}: {e}")
                        self.stats['errors'] += 1
                        move_failed = True

                # If moves failed, don't try to remove folder
                if move_failed:
                    return False

                # Remove now-empty folder
                try:
                    folder_path.rmdir()
                    return True
                except Exception as e:
                    self._print(f"  ERROR removing folder {folder_path}: {e}")
                    self.stats['errors'] += 1
                    return False

        except Exception as e:
            self._print(f"  ERROR flattening folder {folder_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def _remove_folder(self, folder_path: Path) -> bool:
        """
        Remove an empty folder.
        
        Args:
            folder_path: Folder to remove
            
        Returns:
            True if successful, False if failed
        """
        if self.dry_run:
            self.operations.append(("REMOVE EMPTY", str(folder_path), ""))
            return True
        else:
            try:
                folder_path.rmdir()
                return True
            except Exception as e:
                self._print(f"  ERROR removing folder {folder_path}: {e}")
                self.stats['errors'] += 1
                return False
    
    def _rename_folder(self, old_path: Path, new_path: Path):
        """
        Rename a folder.
        
        Args:
            old_path: Current folder path
            new_path: New folder path
        """
        if self.dry_run:
            self.operations.append(("RENAME FOLDER", str(old_path), str(new_path)))
        else:
            try:
                old_path.rename(new_path)
                
                # Set permissions
                new_path.chmod(0o755)
                
                # Attempt to change ownership (may fail without sudo)
                try:
                    shutil.chown(str(new_path), user='nobody', group='users')
                except (PermissionError, LookupError):
                    pass  # Continue if ownership change fails

            except Exception as e:
                self._print(f"  ERROR renaming folder {old_path} to {new_path}: {e}")
                self.stats['errors'] += 1
    
    def _resolve_collision(self, parent_dir: Path, name: str) -> str:
        """
        Check for naming collision and resolve if necessary.
        
        Args:
            parent_dir: Parent directory
            name: Proposed name
            
        Returns:
            Unique name (may be modified with date stamp + counter)
        """
        # Track used names per directory
        dir_key = str(parent_dir)
        if dir_key not in self.used_names:
            # Initialize with existing items in directory
            try:
                self.used_names[dir_key] = {
                    item.name.lower() for item in parent_dir.iterdir()
                }
            except Exception:
                self.used_names[dir_key] = set()
        
        # Check for collision (case-insensitive)
        if name.lower() in self.used_names[dir_key]:
            # Generate unique name
            original_name = name
            name = self.cleaner.generate_collision_name(name, parent_dir)
            self.stats['collisions_resolved'] += 1
            
            # Keep trying if still collides
            while name.lower() in self.used_names[dir_key]:
                name = self.cleaner.generate_collision_name(original_name, parent_dir)
        
        # Mark this name as used
        self.used_names[dir_key].add(name.lower())
        
        return name
