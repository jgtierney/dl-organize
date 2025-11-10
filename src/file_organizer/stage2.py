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
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime

from .filename_cleaner import FilenameCleaner
from .config import Config


class Stage2Processor:
    """Stage 2: Folder Structure Optimization."""
    
    def __init__(self, input_dir: Path, dry_run: bool = True, 
                 flatten_threshold: int = 5, config: Config = None):
        """
        Initialize Stage 2 processor.
        
        Args:
            input_dir: Directory to process
            dry_run: If True, preview changes without executing
            flatten_threshold: Number of items below which folders are flattened
            config: Configuration object (optional)
        """
        self.input_dir = input_dir.resolve()
        self.dry_run = dry_run
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
        
        # Operation log (for dry-run preview)
        self.operations: List[Tuple[str, str, str]] = []  # (operation, source, dest)
        
    def process(self):
        """Main processing entry point."""
        start_time = datetime.now()
        
        print("\n" + "=" * 70)
        print("STAGE 2: FOLDER STRUCTURE OPTIMIZATION")
        print("=" * 70)
        print(f"Flatten threshold: < {self.flatten_threshold} items")
        
        if self.dry_run:
            print("Mode: DRY-RUN (preview only)")
        else:
            print("Mode: EXECUTE")
        
        print("=" * 70)
        
        # Phase 1: Remove empty folders
        print("\nPhase 1: Removing empty folders...")
        self._remove_empty_folders()
        
        # Phase 2: Flatten folder chains (iterative)
        print("\nPhase 2: Flattening folder structure...")
        self._flatten_folders_iterative()
        
        # Phase 3: Sanitize remaining folder names
        print("\nPhase 3: Sanitizing folder names...")
        self._sanitize_folder_names()
        
        # Phase 4: Show summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 70)
        print("STAGE 2 SUMMARY")
        print("=" * 70)
        print(f"Folders scanned:      {self.stats['folders_scanned']:,}")
        print(f"Empty folders removed: {self.stats['empty_removed']:,}")
        print(f"Folders flattened:    {self.stats['folders_flattened']:,}")
        print(f"Folders renamed:      {self.stats['folders_renamed']:,}")
        print(f"Collisions resolved:  {self.stats['collisions_resolved']:,}")
        print(f"Flattening passes:    {self.stats['flattening_passes']}")
        print(f"Errors:               {self.stats['errors']:,}")
        print(f"Duration:             {duration.total_seconds():.1f}s")
        
        if self.dry_run:
            print("\n" + "=" * 70)
            print("DRY-RUN PREVIEW (showing first 20 operations):")
            print("=" * 70)
            for i, (op, src, dest) in enumerate(self.operations[:20]):
                print(f"{op}: {src}")
                if dest:
                    print(f"  → {dest}")
            if len(self.operations) > 20:
                print(f"\n... and {len(self.operations) - 20} more operations")
    
    def _remove_empty_folders(self):
        """
        Remove all empty folders (bottom-up, iterative).
        
        A folder is empty if it contains no files and no subfolders.
        Process iteratively because removing folders may make parents empty.
        """
        removed_count = 0
        pass_num = 0
        
        while True:
            pass_num += 1
            folders = self._scan_folders()
            
            if not folders:
                break
            
            pass_removed = 0
            
            # Process bottom-up (deepest first)
            for folder_path in folders:
                if self._is_empty_folder(folder_path):
                    self._remove_folder(folder_path)
                    pass_removed += 1
            
            if pass_removed == 0:
                break  # No more empty folders
            
            removed_count += pass_removed
            print(f"  Pass {pass_num}: Removed {pass_removed} empty folders")
        
        self.stats['empty_removed'] = removed_count
        print(f"  Total empty folders removed: {removed_count}")
    
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
        
        while True:
            pass_num += 1
            folders = self._scan_folders()
            
            if not folders:
                break
            
            pass_flattened = 0
            
            # Process bottom-up (deepest first)
            for folder_path in folders:
                # Skip root directory
                if folder_path == self.input_dir:
                    continue
                
                # Check if folder should be flattened
                if self._should_flatten_folder(folder_path):
                    self._flatten_folder(folder_path)
                    pass_flattened += 1
            
            if pass_flattened == 0:
                break  # No more flattening possible
            
            total_flattened += pass_flattened
            print(f"  Pass {pass_num}: Flattened {pass_flattened} folders")
        
        self.stats['folders_flattened'] = total_flattened
        self.stats['flattening_passes'] = pass_num - 1
        print(f"  Total folders flattened: {total_flattened} (in {pass_num - 1} passes)")
    
    def _sanitize_folder_names(self):
        """Sanitize all remaining folder names using Stage 1 rules."""
        folders = self._scan_folders()
        
        if not folders:
            return
        
        self.stats['folders_scanned'] = len(folders)
        renamed_count = 0
        
        # Process bottom-up to avoid path issues
        for folder_path in folders:
            # Skip root directory
            if folder_path == self.input_dir:
                continue
            
            foldername = folder_path.name
            parent_dir = folder_path.parent
            
            # Sanitize folder name
            new_foldername = self.cleaner.sanitize_filename(foldername, is_directory=True)
            
            # Check if rename is needed
            if new_foldername == foldername:
                continue
            
            # Check for collision
            new_foldername = self._resolve_collision(parent_dir, new_foldername)
            
            # Perform rename
            new_path = parent_dir / new_foldername
            self._rename_folder(folder_path, new_path)
            renamed_count += 1
        
        self.stats['folders_renamed'] = renamed_count
        print(f"  Folders renamed: {renamed_count}")
    
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
            print(f"  ERROR scanning directory: {e}")
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
            print(f"  ERROR checking folder {folder_path}: {e}")
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
            print(f"  ERROR checking folder {folder_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def _flatten_folder(self, folder_path: Path):
        """
        Flatten a folder by moving its contents to parent.
        
        Args:
            folder_path: Folder to flatten
        """
        try:
            parent_dir = folder_path.parent
            
            # Get all items in folder
            contents = list(folder_path.iterdir())
            
            if self.dry_run:
                self.operations.append(("FLATTEN FOLDER", str(folder_path), str(parent_dir)))
            else:
                # Move each item to parent directory
                for item in contents:
                    dest_name = item.name
                    
                    # Check for collision in parent
                    dest_name = self._resolve_collision(parent_dir, dest_name)
                    dest_path = parent_dir / dest_name
                    
                    # Move item
                    try:
                        shutil.move(str(item), str(dest_path))
                    except Exception as e:
                        print(f"  ERROR moving {item} to {dest_path}: {e}")
                        self.stats['errors'] += 1
                
                # Remove now-empty folder
                try:
                    folder_path.rmdir()
                except Exception as e:
                    print(f"  ERROR removing folder {folder_path}: {e}")
                    self.stats['errors'] += 1
                    
        except Exception as e:
            print(f"  ERROR flattening folder {folder_path}: {e}")
            self.stats['errors'] += 1
    
    def _remove_folder(self, folder_path: Path):
        """
        Remove an empty folder.
        
        Args:
            folder_path: Folder to remove
        """
        if self.dry_run:
            self.operations.append(("REMOVE EMPTY", str(folder_path), ""))
        else:
            try:
                folder_path.rmdir()
            except Exception as e:
                print(f"  ERROR removing folder {folder_path}: {e}")
                self.stats['errors'] += 1
    
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
                print(f"  ERROR renaming folder {old_path} to {new_path}: {e}")
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
