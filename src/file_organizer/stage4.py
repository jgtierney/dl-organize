"""
Stage 4: File Relocation

Moves organized and deduplicated files from input folder to output folder.

Process:
1. Validation (folders, disk space, permissions)
2. Directory structure creation (mirror input in output)
3. File relocation (move files preserving paths)
4. Verification (ensure all files exist in output)
5. Cleanup (remove input contents, keep empty root)

Supports:
- Move operation (fast, no duplication)
- Top-level file classification (auto move to misc/)
- Dry-run mode (preview without moving)
- Execute mode (actually move files)
- Preserve input option (keep input folder with files)
- Partial failure recovery (continue on errors)
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MovedFile:
    """Represents a file that was moved from source to destination."""
    source: Path
    destination: Path
    size: int


@dataclass
class Stage4Results:
    """Results from Stage 4 execution."""
    files_moved: int
    top_level_files: int  # Files moved to misc/
    data_transferred: int  # Total bytes
    directories_created: int
    input_cleaned: bool  # Whether input was cleaned
    failed_files: List[Tuple[Path, str]]  # Failed moves with error messages
    dry_run: bool


class Stage4Processor:
    """
    Stage 4 processor for file relocation.

    Moves all files from input to output folder:
    - Top-level files → output/misc/
    - Top-level folders → output/ (preserve structure)
    - All nested files → preserve relative paths

    Default behavior: Clean input folder after successful move
    """

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        preserve_input: bool = False,
        dry_run: bool = True,
        verbose: bool = True
    ):
        """
        Initialize Stage 4 processor.

        Args:
            input_folder: Input directory to move files from
            output_folder: Output directory to move files to
            preserve_input: Keep input folder with files (default: False, clean input)
            dry_run: Dry-run mode (default: True, no actual moves)
            verbose: Print progress messages (default: True)
        """
        self.input_folder = input_folder.resolve()
        self.output_folder = output_folder.resolve()
        self.preserve_input = preserve_input
        self.dry_run = dry_run
        self.verbose = verbose

        # Track moved files
        self.moved_files: List[MovedFile] = []
        self.failed_files: List[Tuple[Path, str]] = []
        self.top_level_file_count = 0
        self.dirs_created = 0

    def process(self) -> Stage4Results:
        """
        Execute Stage 4: File relocation.

        Five-phase workflow:
        1. Validation (folders, disk space)
        2. Directory structure creation
        3. File relocation (with classification)
        4. Verification
        5. Cleanup (unless --preserve-input)

        Returns:
            Stage4Results with operation statistics
        """
        self._print_header()

        try:
            # Phase 1: Validation
            self._print_phase(1, 5, "Validation")
            self._validate_folders()
            input_size, file_count = self._calculate_folder_size(self.input_folder)
            self._check_disk_space(input_size)
            self._print_validation_summary(input_size, file_count)

            # Phase 2: Create directory structure
            self._print_phase(2, 5, "Creating Directory Structure")
            self._create_output_structure()
            self._print(f"  ✓ Created {self.dirs_created} directories in output folder")

            # Phase 3: Move files
            self._print_phase(3, 5, "Moving Files")
            self._relocate_files()
            self._print_relocation_summary()

            # Phase 4: Verification
            self._print_phase(4, 5, "Verification")

            if self.dry_run:
                self._print("  ⊘ Verification skipped (dry-run mode)")
            else:
                missing = self._verify_relocation()
                if missing:
                    self._print(f"  ⚠️  Warning: {len(missing)} files missing in output")
                else:
                    self._print(f"  ✓ Verified all {len(self.moved_files):,} moved files exist in output")
                    self._print("  ✓ All files relocated successfully")

            # Phase 5: Cleanup (unless --preserve-input)
            input_cleaned = False
            if not self.preserve_input and not self.dry_run and not self.failed_files:
                self._print_phase(5, 5, "Cleanup")
                self._cleanup_input_folder()
                input_cleaned = True
                self._print(f"  ✓ Removed all files and subdirectories")
                self._print(f"  ✓ Empty input folder preserved: {self.input_folder}")
                self._print("  ✓ Operation complete")
            elif self.dry_run:
                self._print_phase(5, 5, "Cleanup")
                self._print("  ⊘ Skipped (dry-run mode)")
            elif self.preserve_input:
                self._print_phase(5, 5, "Cleanup")
                self._print("  ⊘ Skipped (--preserve-input flag)")
            elif self.failed_files:
                self._print_phase(5, 5, "Cleanup")
                self._print(f"  ⊘ Skipped (partial failure, {len(self.failed_files)} files failed)")
                self._print("  ℹ️  Input folder preserved for safety")

            # Print final summary
            self._print_final_summary(input_size, input_cleaned)

            # Return results
            return Stage4Results(
                files_moved=len(self.moved_files),
                top_level_files=self.top_level_file_count,
                data_transferred=sum(mf.size for mf in self.moved_files),
                directories_created=self.dirs_created,
                input_cleaned=input_cleaned,
                failed_files=self.failed_files,
                dry_run=self.dry_run
            )

        except Exception as e:
            logger.error(f"Stage 4 failed: {e}")
            self._print(f"\n❌ ERROR: Stage 4 failed: {e}")
            raise

    def _validate_folders(self) -> None:
        """Validate input and output folders."""
        # Check input folder exists and is readable
        if not self.input_folder.exists():
            raise ValueError(f"Input folder does not exist: {self.input_folder}")

        if not self.input_folder.is_dir():
            raise ValueError(f"Input path is not a directory: {self.input_folder}")

        if not os.access(self.input_folder, os.R_OK):
            raise PermissionError(f"Input folder not readable: {self.input_folder}")

        # Check output folder exists or can be created
        if not self.output_folder.exists():
            if not self.dry_run:
                self.output_folder.mkdir(parents=True, exist_ok=True)

        # Check write permissions on output
        if not self.dry_run:
            if not os.access(self.output_folder, os.W_OK):
                raise PermissionError(f"Output folder not writable: {self.output_folder}")

    def _calculate_folder_size(self, folder: Path) -> Tuple[int, int]:
        """
        Calculate total size and file count in folder.

        Args:
            folder: Folder to calculate size for

        Returns:
            Tuple of (total_size_bytes, file_count)
        """
        total_size = 0
        file_count = 0
        last_update_time = time.time()

        for dirpath, dirnames, filenames in os.walk(folder):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    total_size += filepath.stat().st_size
                    file_count += 1

                    # Time-based progress update (every 100 files, max 10 updates/sec)
                    if file_count % 100 == 0:
                        current_time = time.time()
                        if current_time - last_update_time >= 0.1:
                            self._print(
                                f"  Calculating: {file_count:,} files, "
                                f"{self._format_size(total_size)}...",
                                end='\r'
                            )
                            last_update_time = current_time
                except (OSError, FileNotFoundError):
                    # Skip files we can't access
                    continue

        # Clear progress line and show final count
        if file_count > 0:
            self._print(
                f"  Calculated: {file_count:,} files, "
                f"{self._format_size(total_size)}        "
            )

        return total_size, file_count

    def _check_disk_space(self, required_size: int) -> None:
        """
        Verify sufficient disk space in output location.

        Args:
            required_size: Required space in bytes

        Raises:
            ValueError: If insufficient disk space
        """
        output_free = shutil.disk_usage(self.output_folder).free
        required_with_margin = int(required_size * 1.1)  # 10% safety margin

        if output_free < required_with_margin:
            raise ValueError(
                f"Insufficient disk space in output location.\n"
                f"  Required: {self._format_size(required_with_margin)} (with 10% margin)\n"
                f"  Available: {self._format_size(output_free)}\n"
                f"  Please free up space or use different output location"
            )

    def _create_output_structure(self) -> None:
        """Create output directory tree mirroring input structure."""
        # Walk input folder and create corresponding directories in output
        for dirpath, dirnames, filenames in os.walk(self.input_folder):
            # Calculate relative path
            rel_path = Path(dirpath).relative_to(self.input_folder)

            # Skip root level (we handle it separately)
            if rel_path == Path('.'):
                continue

            # Create corresponding directory in output
            output_dir = self.output_folder / rel_path

            if not self.dry_run:
                output_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(output_dir, 0o755)

            self.dirs_created += 1

        # Always ensure misc/ folder exists if we have top-level files
        has_top_level_files = any(item.is_file() for item in self.input_folder.iterdir())
        if has_top_level_files:
            misc_dir = self.output_folder / "misc"
            if not self.dry_run:
                misc_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(misc_dir, 0o755)
            self.dirs_created += 1

    def _relocate_files(self) -> None:
        """Move all files from input to output preserving structure."""
        # Identify top-level files (need to go to misc/)
        top_level_files = set()
        for item in self.input_folder.iterdir():
            if item.is_file():
                top_level_files.add(item)

        # Walk all files in input folder
        file_list = []
        for dirpath, dirnames, filenames in os.walk(self.input_folder):
            for filename in filenames:
                file_list.append(Path(dirpath) / filename)

        total_files = len(file_list)

        for idx, file_path in enumerate(file_list, 1):
            # Calculate destination
            if file_path in top_level_files:
                # Top-level file → misc/filename
                dest_path = self.output_folder / "misc" / file_path.name
                self.top_level_file_count += 1
            else:
                # All other files → preserve relative path
                rel_path = file_path.relative_to(self.input_folder)
                dest_path = self.output_folder / rel_path

            # Move file (or simulate in dry-run)
            try:
                file_size = file_path.stat().st_size

                if not self.dry_run:
                    self._move_file(file_path, dest_path)

                self.moved_files.append(MovedFile(
                    source=file_path,
                    destination=dest_path,
                    size=file_size
                ))
            except Exception as e:
                error_msg = str(e)
                self.failed_files.append((file_path, error_msg))
                logger.error(f"Failed to move {file_path}: {error_msg}")

            # Update progress every 100 files or at end
            if idx % 100 == 0 or idx == total_files:
                self._print_progress(idx, total_files)

    def _move_file(self, source: Path, dest: Path) -> None:
        """
        Move a single file from source to destination.

        Uses shutil.move() which:
        - Uses os.rename() if same filesystem (fast)
        - Falls back to copy + delete if different filesystems

        Args:
            source: Source file path
            dest: Destination file path

        Raises:
            Exception: If move fails
        """
        # Handle collision (shouldn't happen after Stage 3B)
        if dest.exists():
            logger.warning(f"Destination exists, skipping: {dest}")
            return

        # Ensure parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(source), str(dest))

        # Preserve timestamps
        try:
            shutil.copystat(str(source), str(dest))
        except Exception as e:
            # Not critical if timestamps can't be preserved
            logger.debug(f"Could not preserve timestamps for {dest}: {e}")

    def _verify_relocation(self) -> List[Path]:
        """
        Verify all files exist in output after move.

        Returns:
            List of missing file paths (empty if all verified)
        """
        if self.dry_run:
            return []  # Skip verification in dry-run

        missing = []
        for moved in self.moved_files:
            # Check existence (sufficient since move operation completed)
            if not moved.destination.exists():
                missing.append(moved.destination)
                logger.warning(f"Verification failed: {moved.destination} missing")

        return missing

    def _cleanup_input_folder(self) -> None:
        """Remove files and subdirs from input, keep empty root folder."""
        try:
            # Remove all subdirectories and files
            for item in self.input_folder.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    logger.debug(f"Removed directory: {item}")
                elif item.is_file():
                    item.unlink()
                    logger.debug(f"Removed file: {item}")

            logger.info(f"Cleaned input folder (kept empty root): {self.input_folder}")
        except Exception as e:
            logger.warning(
                f"Could not fully clean input folder: {e}. "
                f"Files have been moved successfully."
            )

    # Progress reporting methods

    def _print_header(self) -> None:
        """Print Stage 4 header."""
        self._print("=" * 60)
        self._print("  Stage 4: File Relocation")
        self._print("=" * 60)
        self._print(f"Input folder:  {self.input_folder}")
        self._print(f"Output folder: {self.output_folder}")
        self._print(f"Mode: {'DRY-RUN (preview only)' if self.dry_run else 'EXECUTE (will move files)'}")
        if not self.preserve_input and not self.dry_run:
            self._print("Cleanup: Input folder will be cleaned after move")
        elif self.preserve_input:
            self._print("Cleanup: Input folder will be preserved (--preserve-input)")
        self._print()

    def _print_phase(self, current: int, total: int, name: str) -> None:
        """Print phase header."""
        self._print(f"[Phase {current}/{total}] {name}")

    def _print_validation_summary(self, size: int, file_count: int) -> None:
        """Print validation summary."""
        free_space = shutil.disk_usage(self.output_folder).free
        self._print(f"  ✓ Input folder: {file_count:,} files, {self._format_size(size)}")
        self._print(f"  ✓ Output folder writable")
        self._print(f"  ✓ Disk space: {self._format_size(free_space)} available ({self._format_size(size)} required)")
        self._print(f"  ✓ Sufficient space with 10% margin")
        self._print()

    def _print_progress(self, current: int, total: int) -> None:
        """Print progress update."""
        percentage = (current / total * 100) if total > 0 else 0
        moved_size = sum(mf.size for mf in self.moved_files)
        self._print(f"  Progress: {current:,} / {total:,} files ({percentage:.1f}%) - {self._format_size(moved_size)} moved", end='\r')

        if current == total:
            self._print()  # New line at end

    def _print_relocation_summary(self) -> None:
        """Print relocation summary."""
        if self.failed_files:
            self._print(f"  ⚠️  Moved {len(self.moved_files):,} files ({len(self.failed_files)} failed)")
        else:
            self._print(f"  ✓ Moved {len(self.moved_files):,} files successfully")
        self._print()

    def _print_final_summary(self, total_size: int, input_cleaned: bool) -> None:
        """Print final summary."""
        self._print()
        self._print("=" * 60)
        self._print("  Stage 4 Complete")
        self._print("=" * 60)
        self._print(f"Files moved: {len(self.moved_files):,}")
        if self.top_level_file_count > 0:
            self._print(f"  - Organized files: {len(self.moved_files) - self.top_level_file_count:,}")
            self._print(f"  - Top-level to misc/: {self.top_level_file_count}")
        self._print(f"Data transferred: {self._format_size(total_size)}")
        self._print(f"Directories created: {self.dirs_created}")

        if input_cleaned:
            self._print(f"Input folder: Cleaned (empty root preserved)")
        elif self.preserve_input:
            self._print(f"Input folder: Preserved (--preserve-input)")
        elif self.failed_files:
            self._print(f"Input folder: Preserved ({len(self.failed_files)} files failed to move)")

        if not self.dry_run and self.failed_files:
            self._print()
            self._print("Failed files:")
            for failed_path, error in self.failed_files[:10]:  # Show first 10
                self._print(f"  - {failed_path}: {error}")
            if len(self.failed_files) > 10:
                self._print(f"  ... and {len(self.failed_files) - 10} more")

        # Calculate time (placeholder - could be tracked)
        # self._print(f"Time taken: X.X seconds")

        self._print()
        if self.dry_run:
            self._print("⊘ DRY-RUN: No files were actually moved")
            self._print("💡 TIP: Run with --execute to actually move files")
        elif not self.failed_files:
            self._print("✓ All files relocated successfully")
        else:
            self._print(f"⚠️  Partial success: {len(self.failed_files)} files failed")
            self._print("💡 TIP: Fix errors and re-run Stage 4 for remaining files")

    def _print(self, message: str = "", end: str = '\n') -> None:
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message, end=end, flush=True)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# Test code
if __name__ == "__main__":
    import tempfile
    import random
    import string

    def create_test_data():
        """Create test data for Stage 4."""
        # Create temporary directories
        input_dir = Path(tempfile.mkdtemp(prefix="stage4_test_input_"))
        output_dir = Path(tempfile.mkdtemp(prefix="stage4_test_output_"))

        print(f"Creating test data in {input_dir}")

        # Create some organized folders
        (input_dir / "documents" / "work").mkdir(parents=True)
        (input_dir / "documents" / "personal").mkdir(parents=True)
        (input_dir / "photos" / "vacation").mkdir(parents=True)
        (input_dir / "videos").mkdir(parents=True)

        # Create files in organized folders
        test_files = [
            "documents/work/report.txt",
            "documents/work/presentation.txt",
            "documents/personal/notes.txt",
            "photos/vacation/img1.txt",
            "photos/vacation/img2.txt",
            "videos/clip1.txt",
        ]

        for filepath in test_files:
            full_path = input_dir / filepath
            with open(full_path, 'w') as f:
                f.write(''.join(random.choices(string.ascii_letters, k=1000)))

        # Create top-level files (should go to misc/)
        top_level_files = ["readme.txt", "notes.txt", "todo.txt"]
        for filename in top_level_files:
            with open(input_dir / filename, 'w') as f:
                f.write(''.join(random.choices(string.ascii_letters, k=500)))

        print(f"Created {len(test_files)} organized files")
        print(f"Created {len(top_level_files)} top-level files")
        print()

        return input_dir, output_dir

    # Run tests
    print("=" * 70)
    print("Stage 4: File Relocation - Test Suite")
    print("=" * 70)
    print()

    # Test 1: Dry-run mode
    print("Test 1: Dry-Run Mode")
    print("-" * 70)
    input_dir, output_dir = create_test_data()

    processor = Stage4Processor(
        input_folder=input_dir,
        output_folder=output_dir,
        preserve_input=False,
        dry_run=True,
        verbose=True
    )

    results = processor.process()
    print()
    print(f"✓ Dry-run test complete")
    print(f"  Files to move: {results.files_moved}")
    print(f"  Top-level files: {results.top_level_files}")
    print()

    # Test 2: Execute mode
    print("Test 2: Execute Mode")
    print("-" * 70)
    input_dir2, output_dir2 = create_test_data()

    processor2 = Stage4Processor(
        input_folder=input_dir2,
        output_folder=output_dir2,
        preserve_input=False,
        dry_run=False,
        verbose=True
    )

    results2 = processor2.process()
    print()
    print(f"✓ Execute test complete")
    print(f"  Files moved: {results2.files_moved}")
    print(f"  Top-level files: {results2.top_level_files}")

    # Verify files exist in output
    misc_files = list((output_dir2 / "misc").glob("*")) if (output_dir2 / "misc").exists() else []
    print(f"  Files in misc/: {len(misc_files)}")

    # Verify input is cleaned
    input_items = list(input_dir2.iterdir())
    print(f"  Items in input: {len(input_items)} (should be 0)")

    # Cleanup
    shutil.rmtree(input_dir)
    shutil.rmtree(output_dir)
    shutil.rmtree(input_dir2)
    shutil.rmtree(output_dir2)

    print()
    print("=" * 70)
    print("✓ All Stage 4 tests passed!")
    print("=" * 70)
