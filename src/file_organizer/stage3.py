"""
Stage 3: Duplicate Detection and Resolution

Orchestrates the complete duplicate detection workflow:
1. Scan and detect duplicates (metadata-first optimization)
2. Resolve which files to keep using resolution policy
3. Delete duplicates (or dry-run report)

Supports:
- Stage 3A: Internal deduplication (input folder only)
- Stage 3B: Cross-folder deduplication (input vs output)
- Dry-run mode (show what would be deleted)
- Execute mode (actually delete files)
- Progress reporting (Option B format)
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

from .hash_cache import HashCache
from .duplicate_detector import DuplicateDetector, DuplicateGroup
from .duplicate_resolver import DuplicateResolver


@dataclass
class Stage3Results:
    """Results from Stage 3 execution."""
    total_duplicates: int
    files_deleted: int
    space_freed: int
    duplicate_groups: List[DuplicateGroup]
    dry_run: bool


class Stage3:
    """
    Stage 3 orchestrator for duplicate detection and resolution.

    Process:
    1. Initialize cache and detector
    2. Scan directory and detect duplicates
    3. Resolve which files to keep
    4. Delete duplicates (or dry-run)
    """

    def __init__(
        self,
        input_folder: Path,
        output_folder: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        skip_images: bool = True,
        min_file_size: int = 10 * 1024,
        dry_run: bool = True,
        verbose: bool = True
    ):
        """
        Initialize Stage 3 orchestrator.

        Args:
            input_folder: Input directory to scan
            output_folder: Output directory (for Stage 3B)
            cache_dir: Cache directory (defaults to .file_organizer_cache in CWD)
            skip_images: Skip image files (default True)
            min_file_size: Minimum file size in bytes (default 10KB)
            dry_run: Dry-run mode (default True, no actual deletions)
            verbose: Print progress messages (default True)
        """
        self.input_folder = input_folder.resolve()
        self.output_folder = output_folder.resolve() if output_folder else None
        self.skip_images = skip_images
        self.min_file_size = min_file_size
        self.dry_run = dry_run
        self.verbose = verbose

        # Initialize cache
        if cache_dir is None:
            cache_dir = Path.cwd() / '.file_organizer_cache'
        self.cache = HashCache(cache_dir)

        # Initialize resolver
        self.resolver = DuplicateResolver()

        # Statistics
        self.stats = {
            'groups_found': 0,
            'files_to_delete': 0,
            'space_to_free': 0,
            'files_deleted': 0,
            'space_freed': 0
        }

    def _print(self, message: str, end: str = '\n'):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message, end=end)
            sys.stdout.flush()

    def _print_header(self, title: str):
        """Print section header."""
        self._print(f"\n{'=' * 60}")
        self._print(f"  {title}")
        self._print('=' * 60)

    def _print_phase(self, phase_num: int, total_phases: int, title: str):
        """Print phase header (Option B format - remains visible)."""
        self._print(f"\n[Phase {phase_num}/{total_phases}] {title}")

    def _print_progress(self, message: str):
        """Print progress update (overwrites line with \\r)."""
        if self.verbose:
            print(f"  {message}", end='\r')
            sys.stdout.flush()

    def _print_result(self, message: str):
        """Print result (new line, remains visible)."""
        self._print(f"  ✓ {message}")

    def run_stage3a(self) -> Stage3Results:
        """
        Run Stage 3A: Internal deduplication for input folder.

        Returns:
            Stage3Results with execution summary
        """
        self._print_header("Stage 3A: Internal Duplicate Detection")
        self._print(f"Input folder: {self.input_folder}")
        self._print(f"Mode: {'DRY-RUN (no deletions)' if self.dry_run else 'EXECUTE (will delete duplicates)'}")
        self._print(f"Settings: skip_images={self.skip_images}, min_size={self.min_file_size:,} bytes")

        # Phase 1: Detect duplicates
        self._print_phase(1, 3, "Detecting Duplicates")

        detector = DuplicateDetector(
            cache=self.cache,
            skip_images=self.skip_images,
            min_file_size=self.min_file_size,
            progress_callback=self._progress_callback
        )

        duplicate_groups = detector.detect_duplicates(self.input_folder, folder='input')

        self._print_result(f"Found {len(duplicate_groups)} duplicate groups")
        self._print("\n" + detector.get_stats_summary())

        if not duplicate_groups:
            self._print("\nNo duplicates found. Nothing to do!")
            return Stage3Results(
                total_duplicates=0,
                files_deleted=0,
                space_freed=0,
                duplicate_groups=[],
                dry_run=self.dry_run
            )

        # Phase 2: Resolve duplicates
        self._print_phase(2, 3, "Resolving Duplicates (determining which to keep)")

        resolution_plan = []
        total_to_delete = 0
        total_space = 0

        for group in duplicate_groups:
            file_to_keep, files_to_delete = self.resolver.resolve_duplicates(group.files)

            if files_to_delete:
                resolution_plan.append({
                    'keep': file_to_keep,
                    'delete': files_to_delete,
                    'size': group.size,
                    'hash': group.hash
                })
                total_to_delete += len(files_to_delete)
                total_space += group.size * len(files_to_delete)

        self._print_result(f"Resolution complete: {total_to_delete} files to delete")
        self._print_result(f"Space to free: {self._format_bytes(total_space)}")

        self.stats['groups_found'] = len(duplicate_groups)
        self.stats['files_to_delete'] = total_to_delete
        self.stats['space_to_free'] = total_space

        # Phase 3: Execute (or dry-run)
        self._print_phase(3, 3, "Executing Deletions" if not self.dry_run else "Dry-Run Report")

        if self.dry_run:
            self._print_dry_run_report(resolution_plan)
        else:
            self._execute_deletions(resolution_plan)

        # Final summary
        self._print_header("Stage 3A Complete")
        self._print(f"Duplicate groups found: {self.stats['groups_found']}")
        self._print(f"Files to delete: {self.stats['files_to_delete']}")
        self._print(f"Space to free: {self._format_bytes(self.stats['space_to_free'])}")

        if not self.dry_run:
            self._print(f"Files deleted: {self.stats['files_deleted']}")
            self._print(f"Space freed: {self._format_bytes(self.stats['space_freed'])}")

        return Stage3Results(
            total_duplicates=self.stats['files_to_delete'],
            files_deleted=self.stats['files_deleted'],
            space_freed=self.stats['space_freed'],
            duplicate_groups=duplicate_groups,
            dry_run=self.dry_run
        )

    def run_stage3b(self) -> Stage3Results:
        """
        Run Stage 3B: Cross-folder deduplication (input vs output).

        Optimized workflow:
        1. Load input cache (from Stage 3A - no re-scanning!)
        2. Scan output folder only
        3. Find cross-folder duplicates
        4. Apply full resolution policy (can delete from either folder)
        5. Execute deletions

        Requires:
            - output_folder must be set
            - Input cache should exist from Stage 3A (best practice)

        Returns:
            Stage3Results with execution summary
        """
        # Validate output folder
        if not self.output_folder:
            raise ValueError("Stage 3B requires output_folder to be set")

        self._print_header("Stage 3B: Cross-Folder Deduplication")
        self._print(f"Input folder:  {self.input_folder}")
        self._print(f"Output folder: {self.output_folder}")
        self._print(f"Mode: {'DRY-RUN (no deletions)' if self.dry_run else 'EXECUTE (will delete duplicates)'}")
        self._print(f"Settings: skip_images={self.skip_images}, min_size={self.min_file_size:,} bytes")

        # Phase 1: Load input cache (instant - reuse from Stage 3A)
        self._print_phase(1, 5, "Loading Input Cache (from Stage 3A)")

        input_files = self.cache.get_all_files('input')

        if not input_files:
            self._print("  WARNING: No input cache found. Run Stage 3A first for optimal performance.")
            self._print("  Scanning input folder...")

            # Fallback: scan input folder if no cache exists
            detector = DuplicateDetector(
                cache=self.cache,
                skip_images=self.skip_images,
                min_file_size=self.min_file_size,
                progress_callback=self._progress_callback
            )
            detector.detect_duplicates(self.input_folder, folder='input')
            input_files = self.cache.get_all_files('input')

        self._print_result(f"Loaded {len(input_files)} input files from cache")

        # Phase 2: Scan output folder
        self._print_phase(2, 5, "Scanning Output Folder")

        detector = DuplicateDetector(
            cache=self.cache,
            skip_images=self.skip_images,
            min_file_size=self.min_file_size,
            progress_callback=self._progress_callback
        )

        # Scan output folder (metadata-first optimization)
        output_groups = detector.detect_duplicates(self.output_folder, folder='output')

        self._print_result(f"Scanned output folder")
        self._print("\n" + detector.get_stats_summary())

        # Phase 3: Find cross-folder duplicates
        self._print_phase(3, 5, "Finding Cross-Folder Duplicates")

        cross_folder_groups = self._find_cross_folder_duplicates()

        self._print_result(f"Found {len(cross_folder_groups)} cross-folder duplicate groups")

        if not cross_folder_groups:
            self._print("\nNo cross-folder duplicates found. Nothing to do!")
            return Stage3Results(
                total_duplicates=0,
                files_deleted=0,
                space_freed=0,
                duplicate_groups=[],
                dry_run=self.dry_run
            )

        # Phase 4: Resolve duplicates (apply full three-tier policy)
        self._print_phase(4, 5, "Resolving Duplicates (applying three-tier policy)")

        resolution_plan = []
        total_to_delete = 0
        total_space = 0

        for group in cross_folder_groups:
            file_to_keep, files_to_delete = self.resolver.resolve_duplicates(group.files)

            if files_to_delete:
                resolution_plan.append({
                    'keep': file_to_keep,
                    'delete': files_to_delete,
                    'size': group.size,
                    'hash': group.hash
                })
                total_to_delete += len(files_to_delete)
                total_space += group.size * len(files_to_delete)

        self._print_result(f"Resolution complete: {total_to_delete} files to delete")
        self._print_result(f"Space to free: {self._format_bytes(total_space)}")

        self.stats['groups_found'] = len(cross_folder_groups)
        self.stats['files_to_delete'] = total_to_delete
        self.stats['space_to_free'] = total_space

        # Phase 5: Execute (or dry-run)
        self._print_phase(5, 5, "Executing Deletions" if not self.dry_run else "Dry-Run Report")

        if self.dry_run:
            self._print_dry_run_report(resolution_plan)
        else:
            self._execute_deletions(resolution_plan)

        # Final summary
        self._print_header("Stage 3B Complete")
        self._print(f"Cross-folder duplicate groups found: {self.stats['groups_found']}")
        self._print(f"Files to delete: {self.stats['files_to_delete']}")
        self._print(f"Space to free: {self._format_bytes(self.stats['space_to_free'])}")

        if not self.dry_run:
            self._print(f"Files deleted: {self.stats['files_deleted']}")
            self._print(f"Space freed: {self._format_bytes(self.stats['space_freed'])}")

        return Stage3Results(
            total_duplicates=self.stats['files_to_delete'],
            files_deleted=self.stats['files_deleted'],
            space_freed=self.stats['space_freed'],
            duplicate_groups=cross_folder_groups,
            dry_run=self.dry_run
        )

    def _find_cross_folder_duplicates(self) -> List[DuplicateGroup]:
        """
        Find duplicate files that exist in BOTH input and output folders.

        Process:
        1. Get all cached files from both folders
        2. Group by size to find potential matches across folders
        3. For size collisions, ensure all files are hashed
        4. Group by hash to find actual duplicates

        Returns:
            List of DuplicateGroup objects containing files from both folders
        """
        from collections import defaultdict

        # Get all cached files from both folders
        input_files = self.cache.get_all_files('input')
        output_files = self.cache.get_all_files('output')

        # Phase 1: Group by size to find cross-folder size collisions
        self._print("  Phase 1/4: Building size index for cross-folder comparison...")
        size_groups = defaultdict(lambda: {'input': [], 'output': []})
        last_update_time = time.time()

        # Process input files
        for i, file_info in enumerate(input_files, 1):
            size_groups[file_info.file_size]['input'].append(file_info)
            # Time-based progress update (every 100 files, max 10 updates/sec)
            if i % 100 == 0:
                current_time = time.time()
                if current_time - last_update_time >= 0.1:
                    self._print_progress(f"Indexing input files: {i:,} / {len(input_files):,}")
                    last_update_time = current_time

        # Process output files
        for i, file_info in enumerate(output_files, 1):
            size_groups[file_info.file_size]['output'].append(file_info)
            # Time-based progress update (every 100 files, max 10 updates/sec)
            if i % 100 == 0:
                current_time = time.time()
                if current_time - last_update_time >= 0.1:
                    self._print_progress(f"Indexing output files: {i:,} / {len(output_files):,}")
                    last_update_time = current_time

        self._print_result(f"Indexed {len(input_files):,} input + {len(output_files):,} output files")

        # Phase 2: Identify cross-folder size collisions (need hashing)
        self._print("  Phase 2/4: Identifying files that need hashing...")
        files_to_hash = []
        last_update_time = time.time()

        for i, (size, folders) in enumerate(size_groups.items(), 1):
            if folders['input'] and folders['output']:
                # This size exists in both folders - need to hash all files of this size
                for file_info in folders['input']:
                    if not file_info.file_hash:
                        files_to_hash.append((file_info, 'input'))

                for file_info in folders['output']:
                    if not file_info.file_hash:
                        files_to_hash.append((file_info, 'output'))

            # Time-based progress update (every 1000 groups, max 10 updates/sec)
            if i % 1000 == 0:
                current_time = time.time()
                if current_time - last_update_time >= 0.1:
                    self._print_progress(f"Analyzed {i:,} / {len(size_groups):,} size groups")
                    last_update_time = current_time

        if files_to_hash:
            self._print_result(f"Found {len(files_to_hash):,} files needing hash calculation")
        else:
            self._print_result(f"Analyzed {len(size_groups):,} size groups - all files already hashed")

        # Hash files that need hashing
        if files_to_hash:
            self._print(f"\n  Additional hashing needed for {len(files_to_hash)} files with cross-folder size matches...")

            from .duplicate_detector import FileMetadata

            for file_info, folder in files_to_hash:
                # Create FileMetadata object for hashing
                file_path = Path(file_info.file_path)
                if not file_path.exists():
                    continue

                file_meta = FileMetadata(
                    path=str(file_path.absolute()),  # Convert to absolute string path
                    size=file_info.file_size,
                    mtime=file_info.file_mtime
                )

                # Hash and cache the file
                detector = DuplicateDetector(
                    cache=self.cache,
                    skip_images=self.skip_images,
                    min_file_size=self.min_file_size
                )
                detector.hash_file_with_cache(file_meta, folder)

            # Reload cached files to get updated hashes
            input_files = self.cache.get_all_files('input')
            output_files = self.cache.get_all_files('output')

        # Phase 3: Group by hash to find duplicates
        self._print("  Phase 3/4: Building hash index from cached data...")
        hash_groups = defaultdict(list)
        all_files = input_files + output_files
        last_update_time = time.time()

        for i, file_info in enumerate(all_files, 1):
            file_hash = file_info.file_hash
            if file_hash:
                hash_groups[file_hash].append(file_info)

            # Time-based progress update (every 100 files, max 10 updates/sec)
            if i % 100 == 0:
                current_time = time.time()
                if current_time - last_update_time >= 0.1:
                    self._print_progress(f"Indexing hashes: {i:,} / {len(all_files):,}")
                    last_update_time = current_time

        self._print_result(f"Indexed {len(all_files):,} files by hash")

        # Phase 4: Find groups that have files from BOTH folders
        self._print("  Phase 4/4: Finding cross-folder duplicates...")
        cross_folder_groups = []
        last_update_time = time.time()

        for i, (file_hash, files) in enumerate(hash_groups.items(), 1):
            # Check if this hash has files from both input and output
            folders = {f.folder for f in files}

            if 'input' in folders and 'output' in folders:
                # This is a cross-folder duplicate
                file_paths = [f.file_path for f in files]
                file_size = files[0].file_size  # All duplicates have same size

                group = DuplicateGroup(
                    hash=file_hash,
                    size=file_size,
                    files=file_paths
                )
                cross_folder_groups.append(group)

            # Time-based progress update (every 1000 hash groups, max 10 updates/sec)
            if i % 1000 == 0:
                current_time = time.time()
                if current_time - last_update_time >= 0.1:
                    self._print_progress(f"Analyzing hashes: {i:,} / {len(hash_groups):,}")
                    last_update_time = current_time

        self._print_result(f"Analyzed {len(hash_groups):,} unique hashes, found {len(cross_folder_groups):,} cross-folder duplicate groups")

        return cross_folder_groups

    def _print_dry_run_report(self, resolution_plan: List[Dict]):
        """Print dry-run report showing what would be deleted."""
        self._print("\n  DRY-RUN MODE: No files will be deleted\n")
        self._print("  The following files WOULD be deleted:\n")

        for i, plan in enumerate(resolution_plan, 1):
            self._print(f"  Group {i}:")
            self._print(f"    KEEP:   {plan['keep']}")
            for file_path in plan['delete']:
                self._print(f"    DELETE: {file_path}")
            self._print(f"    Space saved: {self._format_bytes(plan['size'] * len(plan['delete']))}")
            self._print("")

        self._print(f"  Total files that would be deleted: {self.stats['files_to_delete']}")
        self._print(f"  Total space that would be freed: {self._format_bytes(self.stats['space_to_free'])}")
        self._print("\n  To actually delete files, run with --execute flag")

    def _execute_deletions(self, resolution_plan: List[Dict]):
        """Execute actual file deletions."""
        self._print("\n  EXECUTE MODE: Deleting duplicate files...\n")

        deleted_count = 0
        deleted_space = 0
        errors = []

        for i, plan in enumerate(resolution_plan, 1):
            self._print_progress(f"Processing group {i}/{len(resolution_plan)}...")

            self._print(f"  Group {i}:")
            self._print(f"    KEEP:   {plan['keep']}")

            for file_path in plan['delete']:
                try:
                    # Get file size before deletion
                    file_size = Path(file_path).stat().st_size

                    # Delete file
                    os.remove(file_path)

                    deleted_count += 1
                    deleted_space += file_size

                    self._print(f"    DELETED: {file_path}")

                except FileNotFoundError:
                    self._print(f"    SKIPPED (not found): {file_path}")
                    errors.append(f"File not found: {file_path}")

                except PermissionError:
                    self._print(f"    ERROR (permission denied): {file_path}")
                    errors.append(f"Permission denied: {file_path}")

                except Exception as e:
                    self._print(f"    ERROR: {file_path} - {str(e)}")
                    errors.append(f"{file_path}: {str(e)}")

            self._print("")

        self.stats['files_deleted'] = deleted_count
        self.stats['space_freed'] = deleted_space

        self._print_result(f"Deleted {deleted_count} files")
        self._print_result(f"Freed {self._format_bytes(deleted_space)}")

        if errors:
            self._print(f"\n  Errors encountered ({len(errors)}):")
            for error in errors:
                self._print(f"    - {error}")

    def _progress_callback(self, phase: str, current: int, total: int, message: str):
        """Callback for progress updates from detector."""
        if phase == 'scan':
            self._print_progress(message)
        elif phase == 'hash':
            self._print_progress(message)
        elif phase == 'size_group':
            self._print_result(message)

    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"

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


if __name__ == "__main__":
    # Test Stage 3A with generated test data
    import tempfile
    import shutil

    print("Testing Stage 3A orchestrator...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_root = Path(tmpdir) / 'input'
        test_root.mkdir()

        # Create test files with duplicates
        print("\n[Setup] Creating test data...")

        # Group 1: 3 duplicates in different folders (one with "keep")
        folder1 = test_root / 'archive'
        folder1.mkdir()
        file1a = folder1 / 'video.mp4'
        file1a.write_bytes(b'Video content A' * 1000)  # 15KB

        folder2 = test_root / 'keep' / 'important'
        folder2.mkdir(parents=True)
        file1b = folder2 / 'video.mp4'
        file1b.write_bytes(b'Video content A' * 1000)  # Same content

        folder3 = test_root / 'backup'
        folder3.mkdir()
        file1c = folder3 / 'old_video.mp4'
        file1c.write_bytes(b'Video content A' * 1000)  # Same content

        # Group 2: 2 duplicates (deeper path wins)
        shallow = test_root / 'doc.pdf'
        shallow.write_bytes(b'Document content' * 1000)  # 16KB

        deep_folder = test_root / 'documents' / 'work' / 'projects'
        deep_folder.mkdir(parents=True)
        deep = deep_folder / 'doc.pdf'
        deep.write_bytes(b'Document content' * 1000)  # Same content

        # Unique file (no duplicate)
        unique = test_root / 'unique.txt'
        unique.write_bytes(b'Unique content' * 1000)  # 14KB

        print(f"Created 6 files (5 duplicates in 2 groups, 1 unique)")

        # Test Stage 3A in dry-run mode
        print("\n" + "=" * 60)
        print("TEST 1: Dry-Run Mode")
        print("=" * 60)

        cache_dir = Path(tmpdir) / 'cache'
        with Stage3(
            input_folder=test_root,
            cache_dir=cache_dir,
            skip_images=False,
            dry_run=True
        ) as stage3:
            results = stage3.run_stage3a()

            assert results.dry_run == True
            assert results.total_duplicates == 3, f"Expected 3 duplicates, got {results.total_duplicates}"
            assert results.files_deleted == 0, "Dry-run should not delete files"
            print("\n✓ Dry-run test passed")

        # Test Stage 3A in execute mode
        print("\n" + "=" * 60)
        print("TEST 2: Execute Mode")
        print("=" * 60)

        with Stage3(
            input_folder=test_root,
            cache_dir=cache_dir,
            skip_images=False,
            dry_run=False
        ) as stage3:
            results = stage3.run_stage3a()

            assert results.dry_run == False
            assert results.files_deleted == 3, f"Expected 3 files deleted, got {results.files_deleted}"
            assert results.space_freed > 0, "Should have freed space"

            # Verify files were actually deleted
            assert not file1a.exists(), "file1a should be deleted"
            assert file1b.exists(), "file1b should be kept (has 'keep')"
            assert not file1c.exists(), "file1c should be deleted"

            assert not shallow.exists(), "shallow should be deleted"
            assert deep.exists(), "deep should be kept (deeper path)"

            assert unique.exists(), "unique should still exist (no duplicate)"

            print("\n✓ Execute mode test passed")

    print("\n✓ All Stage 3A tests passed!")

    # ==================================================================
    # Stage 3B Tests: Cross-Folder Deduplication
    # ==================================================================

    print("\n" + "=" * 60)
    print("Testing Stage 3B: Cross-Folder Deduplication")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir2:
        input_root = Path(tmpdir2) / 'input'
        output_root = Path(tmpdir2) / 'output'
        input_root.mkdir()
        output_root.mkdir()

        print("\n[Setup] Creating cross-folder test data...")

        # Scenario 1: "keep" keyword priority
        # Input has "keep", output doesn't → keep input, delete output
        input_keep = input_root / 'keep' / 'important'
        input_keep.mkdir(parents=True)
        file1_input = input_keep / 'video_a.mp4'
        file1_input.write_bytes(b'Video A content' * 1000)  # 15KB

        output_regular = output_root / 'videos'
        output_regular.mkdir()
        file1_output = output_regular / 'video_a.mp4'
        file1_output.write_bytes(b'Video A content' * 1000)  # Same content

        # Scenario 2: Path depth priority
        # Output is deeper → keep output, delete input
        input_shallow = input_root / 'doc.pdf'
        input_shallow.write_bytes(b'Document B' * 1000)  # 10KB

        output_deep = output_root / 'documents' / 'work' / 'projects' / '2025'
        output_deep.mkdir(parents=True)
        file2_output = output_deep / 'doc.pdf'
        file2_output.write_bytes(b'Document B' * 1000)  # Same content

        # Scenario 3: mtime priority (same depth)
        # Input is newer → keep input, delete output
        import time

        output_old = output_root / 'data' / 'report.txt'
        output_old.parent.mkdir()
        output_old.write_bytes(b'Report C' * 1000)  # 8KB

        time.sleep(0.1)  # Ensure different mtime

        input_new = input_root / 'reports' / 'report.txt'
        input_new.parent.mkdir()
        input_new.write_bytes(b'Report C' * 1000)  # Same content, newer

        # Unique files (no cross-folder duplicates)
        unique_input = input_root / 'unique_input.txt'
        unique_input.write_bytes(b'Unique in input' * 1000)

        unique_output = output_root / 'unique_output.txt'
        unique_output.write_bytes(b'Unique in output' * 1000)

        print(f"Created input folder with 4 files")
        print(f"Created output folder with 4 files")
        print(f"Expected: 3 cross-folder duplicate groups")

        # Test Stage 3B: First run Stage 3A to populate input cache
        print("\n" + "=" * 60)
        print("TEST 3: Stage 3A (populate input cache)")
        print("=" * 60)

        cache_dir = Path(tmpdir2) / 'cache'

        with Stage3(
            input_folder=input_root,
            cache_dir=cache_dir,
            skip_images=False,
            min_file_size=1024,  # 1KB minimum
            dry_run=True
        ) as stage3:
            stage3.run_stage3a()

        print("\n✓ Input cache populated")

        # Test Stage 3B: Dry-run mode
        print("\n" + "=" * 60)
        print("TEST 4: Stage 3B Dry-Run Mode")
        print("=" * 60)

        with Stage3(
            input_folder=input_root,
            output_folder=output_root,
            cache_dir=cache_dir,
            skip_images=False,
            min_file_size=1024,
            dry_run=True
        ) as stage3:
            results = stage3.run_stage3b()

            assert results.dry_run == True
            assert results.total_duplicates == 3, f"Expected 3 duplicates, got {results.total_duplicates}"
            assert results.files_deleted == 0, "Dry-run should not delete files"
            print("\n✓ Stage 3B dry-run test passed")

        # Test Stage 3B: Execute mode
        print("\n" + "=" * 60)
        print("TEST 5: Stage 3B Execute Mode")
        print("=" * 60)

        with Stage3(
            input_folder=input_root,
            output_folder=output_root,
            cache_dir=cache_dir,
            skip_images=False,
            min_file_size=1024,
            dry_run=False
        ) as stage3:
            results = stage3.run_stage3b()

            assert results.dry_run == False
            assert results.files_deleted == 3, f"Expected 3 files deleted, got {results.files_deleted}"
            assert results.space_freed > 0, "Should have freed space"

            # Verify resolution policy worked correctly

            # Scenario 1: "keep" keyword priority
            assert file1_input.exists(), "Input file with 'keep' should be kept"
            assert not file1_output.exists(), "Output file without 'keep' should be deleted"

            # Scenario 2: Path depth priority
            assert not input_shallow.exists(), "Shallow input should be deleted"
            assert file2_output.exists(), "Deep output should be kept"

            # Scenario 3: mtime priority
            assert input_new.exists(), "Newer input should be kept"
            assert not output_old.exists(), "Older output should be deleted"

            # Verify unique files still exist
            assert unique_input.exists(), "Unique input file should still exist"
            assert unique_output.exists(), "Unique output file should still exist"

            print("\n✓ Stage 3B execute mode test passed")
            print("  - Scenario 1 (keep keyword): ✓")
            print("  - Scenario 2 (path depth):   ✓")
            print("  - Scenario 3 (mtime):        ✓")

    print("\n✓ All Stage 3B tests passed!")
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED (Stage 3A + 3B)")
    print("=" * 60)
