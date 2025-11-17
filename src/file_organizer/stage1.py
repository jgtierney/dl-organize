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
import sys
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime

from .filename_cleaner import FilenameCleaner
from .progress_bar import ProgressBar, SimpleProgress

logger = logging.getLogger(__name__)


class Stage1Processor:
    """Stage 1: Filename Detoxification."""
    
    def __init__(self, input_dir: Path, dry_run: bool = True, verbose: bool = True):
        """
        Initialize Stage 1 processor.

        Args:
            input_dir: Directory to process
            dry_run: If True, preview changes without executing
            verbose: If True, print progress messages
        """
        self.input_dir = input_dir.resolve()
        self.dry_run = dry_run
        self.verbose = verbose
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
            'permission_warnings': 0,
        }
        
        # Track all target names for collision detection
        self.used_names: Dict[str, Set[str]] = {}  # dir_path -> set of used names
        
        # Operation log (for dry-run preview)
        self.operations: List[Tuple[str, str, str]] = []  # (operation, source, dest)

    def _print(self, message: str = "", end: str = '\n'):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message, end=end, flush=True)

    def process(self):
        """Main processing entry point."""
        start_time = datetime.now()

        if self.dry_run:
            self._print("⚠️  DRY-RUN MODE: No changes will be made\n")

        # Phase 1: Scan directory tree
        self._print("Stage 1/4: Filename Detoxification - Scanning Directory")
        sys.stdout.flush()  # Ensure message appears immediately
        files, folders = self._scan_directory()

        self.stats['files_scanned'] = len(files)
        self.stats['folders_scanned'] = len(folders)

        # Phase 2: Process files (bottom-up, so we process files before their parent folders)
        if len(files) > 0:
            self._print("\nStage 1/4: Filename Detoxification - Processing Files")
            self._process_files(files)

        # Phase 3: Process folders (bottom-up)
        if len(folders) > 0:
            self._print("\nStage 1/4: Filename Detoxification - Processing Folders")
            self._process_folders(folders)

        # Phase 4: Show summary
        end_time = datetime.now()
        duration = end_time - start_time

        self._print("\n" + "=" * 70)
        self._print("STAGE 1 SUMMARY")
        self._print("=" * 70)
        self._print(f"Files scanned:        {self.stats['files_scanned']:,}")
        self._print(f"Folders scanned:      {self.stats['folders_scanned']:,}")
        self._print(f"Files renamed:        {self.stats['files_renamed']:,}")
        self._print(f"Folders renamed:      {self.stats['folders_renamed']:,}")
        self._print(f"Hidden files deleted: {self.stats['hidden_deleted']:,}")
        self._print(f"Symlinks removed:     {self.stats['symlinks_removed']:,}")
        self._print(f"Collisions resolved:  {self.stats['collisions_resolved']:,}")
        self._print(f"Errors:               {self.stats['errors']:,}")
        self._print(f"Duration:             {duration.total_seconds():.1f}s")

        # Show permission warning summary if any
        if self.stats['permission_warnings'] > 0:
            self._print()
            self._print(f"⚠️  Warning: Encountered {self.stats['permission_warnings']} permission warnings.")
            self._print(f"   Some files may have incorrect ownership or permissions.")
            self._print(f"   Run as root to change ownership, or ignore if not needed.")

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
        
    def _scan_directory(self) -> Tuple[List[Path], List[Path]]:
        """
        Scan directory tree and collect files and folders.

        Returns:
            Tuple of (files, folders) sorted bottom-up for processing
        """
        files = []
        folders = []
        progress = SimpleProgress("Scanning", verbose=self.verbose)

        # Show immediate feedback (update at 0 items to display starting message)
        progress.update(0, force=True)

        for root, dirs, filenames in os.walk(self.input_dir, topdown=False):
            root_path = Path(root)

            # Collect files
            for filename in filenames:
                file_path = root_path / filename
                files.append(file_path)

                # Update progress every 50 items (more frequent feedback)
                if len(files) % 50 == 0:
                    progress.update(len(files) + len(folders))

            # Collect folders (excluding root)
            for dirname in dirs:
                folder_path = root_path / dirname
                folders.append(folder_path)

        progress.count = len(files) + len(folders)
        progress.finish()

        return files, folders
    
    def _process_files(self, files: List[Path]):
        """Process all files."""
        total = len(files)

        # Track stats for progress bar
        renamed_count = 0
        deleted_count = 0
        symlink_count = 0
        collision_count = 0

        progress = ProgressBar(
            total=total,
            description="Processing Files",
            verbose=self.verbose,
            min_duration=1.0
        )

        for i, file_path in enumerate(files):
            # Save current stats
            prev_renamed = self.stats['files_renamed']
            prev_deleted = self.stats['hidden_deleted']
            prev_symlinks = self.stats['symlinks_removed']
            prev_collisions = self.stats['collisions_resolved']

            try:
                self._process_single_file(file_path)
            except Exception as e:
                self.stats['errors'] += 1
                progress.message(f"ERROR: {file_path}: {e}")

            # Update counters
            renamed_count = self.stats['files_renamed']
            deleted_count = self.stats['hidden_deleted']
            symlink_count = self.stats['symlinks_removed']
            collision_count = self.stats['collisions_resolved']

            # Update progress bar with stats
            stats = {
                "Renamed": renamed_count,
                "Deleted": deleted_count,
                "Symlinks": symlink_count,
                "Collisions": collision_count
            }
            progress.update(i + 1, stats)

        # Finish progress bar
        final_stats = {
            "Renamed": renamed_count,
            "Deleted": deleted_count,
            "Symlinks": symlink_count,
            "Collisions": collision_count
        }
        progress.finish(final_stats)
    
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

        # Track stats for progress bar
        renamed_count = 0
        collision_count = 0

        progress = ProgressBar(
            total=total,
            description="Processing Folders",
            verbose=self.verbose,
            min_duration=1.0
        )

        for i, folder_path in enumerate(folders):
            try:
                self._process_single_folder(folder_path)
            except Exception as e:
                self.stats['errors'] += 1
                progress.message(f"ERROR: {folder_path}: {e}")

            # Update counters
            renamed_count = self.stats['folders_renamed']
            collision_count = self.stats['collisions_resolved'] - self.stats.get('file_collisions', 0)

            # Update progress bar with stats
            stats = {
                "Renamed": renamed_count,
                "Collisions": collision_count
            }
            progress.update(i + 1, stats)

        # Finish progress bar
        final_stats = {
            "Renamed": renamed_count,
            "Collisions": collision_count
        }
        progress.finish(final_stats)
    
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
                    # Only attempt ownership change if running as root
                    # Non-root users cannot change ownership to other users
                    if os.getuid() == 0:
                        shutil.chown(str(new_path), user='nobody', group='users')
                        logger.debug(f"Changed ownership: {new_path} -> nobody:users")
                    else:
                        # Not root - skip ownership change
                        logger.debug(f"Skipping ownership change (not root): {new_path}")
                except PermissionError as e:
                    # Expected error - log as warning
                    logger.warning(
                        f"Permission denied changing ownership for {new_path}: {e}. "
                        f"File may have incorrect permissions."
                    )
                    self.stats['permission_warnings'] += 1
                except LookupError as e:
                    # User/group doesn't exist
                    logger.warning(
                        f"User 'nobody' or group 'users' not found on this system. "
                        f"Skipping ownership change for {new_path}."
                    )
                    self.stats['permission_warnings'] += 1
                except Exception as e:
                    # Unexpected error
                    logger.error(f"Unexpected error changing ownership for {new_path}: {e}")
                    self.stats['errors'] += 1
                    
            except Exception as e:
                self.stats['errors'] += 1
                raise
    

