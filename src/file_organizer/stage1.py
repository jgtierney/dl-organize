"""
Stage 1: Filename Detoxification Processor

Implements the complete Stage 1 workflow:
- Directory scanning with progress
- Filename sanitization
- Collision detection and resolution
- Hidden file deletion  
- Symlink handling
- Dry-run preview mode
- Comprehensive logging
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime

from .filename_cleaner import FilenameCleaner


class Stage1Processor:
    """Stage 1: Filename Detoxification."""
    
    def __init__(self, input_dir: Path, dry_run: bool = True):
        """
        Initialize Stage 1 processor.
        
        Args:
            input_dir: Directory to process
            dry_run: If True, preview changes without executing
        """
        self.input_dir = input_dir.resolve()
        self.dry_run = dry_run
        self.cleaner = FilenameCleaner()
        
        # Statistics
        self.stats = {
            'files_scanned': 0,
            'folders_scanned': 0,
            'files_renamed': 0,
            'folders_renamed': 0,
            'hidden_deleted': 0,
            'symlinks_removed': 0,
            'collisions_resolved': 0,
            'errors': 0,
            'skipped': 0,
        }
        
        # Track all target names for collision detection
        self.used_names: Dict[str, Set[str]] = {}  # dir_path -> set of used names
        
        # Operation log (for dry-run preview)
        self.operations: List[Tuple[str, str, str]] = []  # (operation, source, dest)
        
    def process(self):
        """Main processing entry point."""
        start_time = datetime.now()
        
        # Phase 1: Scan directory tree
        print("Phase 1: Scanning directory tree...")
        files, folders = self._scan_directory()
        
        print(f"Found: {len(files):,} files, {len(folders):,} folders")
        self.stats['files_scanned'] = len(files)
        self.stats['folders_scanned'] = len(folders)
        
        if self.dry_run:
            print("\n⚠️  DRY-RUN MODE: No changes will be made\n")
        
        # Phase 2: Process files (bottom-up, so we process files before their parent folders)
        print("\nPhase 2: Processing files...")
        self._process_files(files)
        
        # Phase 3: Process folders (bottom-up)
        print("\nPhase 3: Processing folders...")
        self._process_folders(folders)
        
        # Phase 4: Show summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 70)
        print("STAGE 1 SUMMARY")
        print("=" * 70)
        print(f"Files scanned:        {self.stats['files_scanned']:,}")
        print(f"Folders scanned:      {self.stats['folders_scanned']:,}")
        print(f"Files renamed:        {self.stats['files_renamed']:,}")
        print(f"Folders renamed:      {self.stats['folders_renamed']:,}")
        print(f"Hidden files deleted: {self.stats['hidden_deleted']:,}")
        print(f"Symlinks removed:     {self.stats['symlinks_removed']:,}")
        print(f"Collisions resolved:  {self.stats['collisions_resolved']:,}")
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
        
    def _scan_directory(self) -> Tuple[List[Path], List[Path]]:
        """
        Scan directory tree and collect files and folders.
        
        Returns:
            Tuple of (files, folders) sorted bottom-up for processing
        """
        files = []
        folders = []
        
        for root, dirs, filenames in os.walk(self.input_dir, topdown=False):
            root_path = Path(root)
            
            # Collect files
            for filename in filenames:
                file_path = root_path / filename
                files.append(file_path)
            
            # Collect folders (excluding root)
            for dirname in dirs:
                folder_path = root_path / dirname
                folders.append(folder_path)
        
        return files, folders
    
    def _process_files(self, files: List[Path]):
        """Process all files."""
        total = len(files)
        update_interval = self._calculate_update_interval(total)
        
        for i, file_path in enumerate(files):
            # Progress update
            if (i + 1) % update_interval == 0 or i == total - 1:
                progress = (i + 1) / total * 100
                print(f"  Processing: {i + 1:,}/{total:,} ({progress:.1f}%)", end='\r')
            
            try:
                self._process_single_file(file_path)
            except Exception as e:
                self.stats['errors'] += 1
                print(f"\n  ERROR: {file_path}: {e}")
        
        print(f"  Processing: {total:,}/{total:,} (100.0%)")  # Final progress
    
    def _process_single_file(self, file_path: Path):
        """Process a single file."""
        filename = file_path.name
        parent_dir = file_path.parent
        
        # Check if it's a symlink
        if file_path.is_symlink():
            self._handle_symlink(file_path)
            return
        
        # Check if it's a hidden file
        if self.cleaner.is_hidden_file(filename):
            self._delete_hidden_file(file_path)
            return
        
        # Sanitize filename
        new_filename = self.cleaner.sanitize_filename(filename, is_directory=False)
        
        # Check if rename is needed
        if new_filename == filename:
            return  # No change needed
        
        # Check for collision
        new_filename = self._resolve_collision(parent_dir, new_filename)
        
        # Perform rename
        new_path = parent_dir / new_filename
        self._rename_item(file_path, new_path, is_file=True)
    
    def _process_folders(self, folders: List[Path]):
        """Process all folders."""
        total = len(folders)
        
        for i, folder_path in enumerate(folders):
            # Progress update
            if (i + 1) % 10 == 0 or i == total - 1:
                progress = (i + 1) / total * 100
                print(f"  Processing: {i + 1:,}/{total:,} ({progress:.1f}%)", end='\r')
            
            try:
                self._process_single_folder(folder_path)
            except Exception as e:
                self.stats['errors'] += 1
                print(f"\n  ERROR: {folder_path}: {e}")
        
        print(f"  Processing: {total:,}/{total:,} (100.0%)")
    
    def _process_single_folder(self, folder_path: Path):
        """Process a single folder."""
        foldername = folder_path.name
        parent_dir = folder_path.parent
        
        # Sanitize folder name
        new_foldername = self.cleaner.sanitize_filename(foldername, is_directory=True)
        
        # Check if rename is needed
        if new_foldername == foldername:
            return
        
        # Check for collision
        new_foldername = self._resolve_collision(parent_dir, new_foldername)
        
        # Perform rename
        new_path = parent_dir / new_foldername
        self._rename_item(folder_path, new_path, is_file=False)
    
    def _handle_symlink(self, symlink_path: Path):
        """Handle symbolic link (break/remove it)."""
        if self.dry_run:
            self.operations.append(("DELETE SYMLINK", str(symlink_path), ""))
        else:
            try:
                symlink_path.unlink()
                self.stats['symlinks_removed'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                raise
    
    def _delete_hidden_file(self, file_path: Path):
        """Delete a hidden file."""
        if self.dry_run:
            self.operations.append(("DELETE HIDDEN", str(file_path), ""))
            self.stats['hidden_deleted'] += 1
        else:
            try:
                file_path.unlink()
                self.stats['hidden_deleted'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                raise
    
    def _resolve_collision(self, parent_dir: Path, filename: str) -> str:
        """
        Check for naming collision and resolve if necessary.
        
        Args:
            parent_dir: Parent directory
            filename: Proposed filename
            
        Returns:
            Unique filename (may be modified with date stamp + counter)
        """
        # Track used names per directory
        dir_key = str(parent_dir)
        if dir_key not in self.used_names:
            # Initialize with existing files in directory
            self.used_names[dir_key] = {
                item.name.lower() for item in parent_dir.iterdir()
            }
        
        # Check for collision (case-insensitive)
        if filename.lower() in self.used_names[dir_key]:
            # Generate unique name
            original_filename = filename
            filename = self.cleaner.generate_collision_name(filename, parent_dir)
            self.stats['collisions_resolved'] += 1
            
            # Keep trying if still collides
            while filename.lower() in self.used_names[dir_key]:
                filename = self.cleaner.generate_collision_name(original_filename, parent_dir)
        
        # Mark this name as used
        self.used_names[dir_key].add(filename.lower())
        
        return filename
    
    def _rename_item(self, old_path: Path, new_path: Path, is_file: bool):
        """Rename a file or folder."""
        if self.dry_run:
            op_type = "RENAME FILE" if is_file else "RENAME FOLDER"
            self.operations.append((op_type, str(old_path), str(new_path)))
            if is_file:
                self.stats['files_renamed'] += 1
            else:
                self.stats['folders_renamed'] += 1
        else:
            try:
                # Perform rename
                old_path.rename(new_path)
                
                if is_file:
                    self.stats['files_renamed'] += 1
                else:
                    self.stats['folders_renamed'] += 1
                    
                # Set permissions (644 for files, 755 for folders)
                if is_file:
                    new_path.chmod(0o644)
                else:
                    new_path.chmod(0o755)
                    
                # Attempt to change ownership (may fail without sudo)
                try:
                    shutil.chown(str(new_path), user='nobody', group='users')
                except (PermissionError, LookupError):
                    pass  # Continue if ownership change fails
                    
            except Exception as e:
                self.stats['errors'] += 1
                raise
    
    def _calculate_update_interval(self, total: int) -> int:
        """Calculate adaptive progress update interval."""
        if total < 1000:
            return 10
        elif total < 10000:
            return 100
        elif total < 100000:
            return 500
        else:
            return 1000

