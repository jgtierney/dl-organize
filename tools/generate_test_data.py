#!/usr/bin/env python3
"""
Synthetic test data generator for File Organizer.

Creates realistic test datasets with various edge cases:
- Different sizes (small: 100 files, medium: 10k, large: 100k)
- Various problematic filenames
- Nested directory structures
- Hidden files
- Symbolic links
- Multiple extensions
- Non-ASCII characters
- Special characters

Stage 3 additions:
- Exact duplicate files (byte-for-byte copies)
- Files with "keep" keyword in paths
- Size collision groups (same size, different content)
- Varied modification times
"""

import os
import random
import argparse
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple


class TestDataGenerator:
    """Generate synthetic test data for File Organizer."""
    
    # Problematic filename patterns to test
    FILENAME_PATTERNS = [
        "Normal File {}.txt",
        "Spaces In Name {}.pdf",
        "UPPERCASE_{}.DOC",
        "MixedCase_File{}.jpg",
        "café_français_{}.txt",  # Non-ASCII
        "über_file_{}.pdf",
        "file@special#chars${}.txt",  # Special characters
        "file___multiple___underscores_{}.doc",
        "___leading_underscores_{}.txt",
        "trailing_underscores___{}.pdf",
        "archive.{}.tar.gz",  # Multiple extensions
        "backup.{}.old.zip",
        "file (copy).txt",  # Parentheses
        "file [version].doc",  # Brackets
        "file-with-dashes-{}.txt",
        "file.with.dots.{}.txt",
        "émoji_test_{}.txt",  # Emoji-adjacent
        "naïve_approach_{}.pdf",
        "Übermensch_{}.doc",
        "very_long_filename_that_should_test_truncation_limits_and_see_how_the_system_handles_extremely_long_names_that_might_exceed_filesystem_limits_{}.txt",
    ]
    
    FOLDER_PATTERNS = [
        "Normal Folder {}",
        "Folder With Spaces {}",
        "UPPERCASE_FOLDER_{}",
        "folder@special#chars${}",
        "café_français_{}",
        "___leading_underscores_{}",
        "folder.with.dots.{}",
        "deeply/nested/structure/{}",
    ]
    
    EXTENSIONS = [
        ".txt", ".pdf", ".doc", ".docx", ".jpg", ".png", ".zip",
        ".tar.gz", ".backup.zip", ".old.txt", ""
    ]
    
    def __init__(self, base_path: Path):
        """
        Initialize generator.
        
        Args:
            base_path: Base directory for test data
        """
        self.base_path = Path(base_path)
        self.file_count = 0
        self.folder_count = 0
        
    def generate_dataset(self, size: str = "small"):
        """
        Generate a complete test dataset.
        
        Args:
            size: Dataset size - "small" (100 files), "medium" (10k), "large" (100k)
        """
        sizes = {
            "small": (100, 10),
            "medium": (10000, 100),
            "large": (100000, 1000),
        }
        
        num_files, num_folders = sizes.get(size, sizes["small"])
        
        print(f"Generating {size} dataset...")
        print(f"Target: {num_files:,} files in ~{num_folders:,} folders")
        print(f"Location: {self.base_path}")
        
        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Generate nested folder structure
        folders = self._generate_folders(num_folders)
        
        # Generate files
        self._generate_files(folders, num_files)
        
        # Add edge cases
        self._generate_edge_cases()
        
        print(f"\nDataset generated successfully!")
        print(f"Files created: {self.file_count:,}")
        print(f"Folders created: {self.folder_count:,}")
        
    def _generate_folders(self, num_folders: int) -> List[Path]:
        """Generate nested folder structure."""
        folders = [self.base_path]
        
        for i in range(num_folders):
            # Randomly choose parent folder (creates nesting)
            parent = random.choice(folders)
            
            # Choose folder name pattern
            pattern = random.choice(self.FOLDER_PATTERNS)
            folder_name = pattern.format(i)
            
            # Handle nested pattern
            if "/" in folder_name:
                folder_path = parent / folder_name
            else:
                folder_path = parent / folder_name
            
            # Create folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                folders.append(folder_path)
                self.folder_count += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  Folders: {i + 1:,}/{num_folders:,}", end='\r')
            except OSError:
                pass  # Skip if folder creation fails
        
        print(f"  Folders: {self.folder_count:,} created" + " " * 20)
        return folders
    
    def _generate_files(self, folders: List[Path], num_files: int):
        """Generate files across the folder structure."""
        for i in range(num_files):
            # Choose random folder
            folder = random.choice(folders)
            
            # Choose filename pattern
            pattern = random.choice(self.FILENAME_PATTERNS)
            filename = pattern.format(i)
            
            # Randomly add or change extension
            if random.random() < 0.3:  # 30% chance to modify extension
                # Remove existing extension if any
                if '.' in filename:
                    base = filename.rsplit('.', 1)[0]
                else:
                    base = filename
                # Add random extension
                filename = base + random.choice(self.EXTENSIONS)
            
            file_path = folder / filename
            
            # Create file with some content
            try:
                with open(file_path, 'w') as f:
                    f.write(f"Test file {i}\n")
                    f.write(f"Filename: {filename}\n")
                    f.write(f"Path: {file_path}\n")
                self.file_count += 1
                
                if (i + 1) % 1000 == 0:
                    print(f"  Files: {i + 1:,}/{num_files:,}", end='\r')
            except OSError:
                pass  # Skip if file creation fails
        
        print(f"  Files: {self.file_count:,} created" + " " * 20)
    
    def _generate_edge_cases(self):
        """Generate specific edge case files and folders."""
        print("\n  Adding edge cases...")
        
        edge_cases_dir = self.base_path / "edge_cases"
        edge_cases_dir.mkdir(exist_ok=True)
        
        # Hidden files (should be deleted)
        hidden_files = [
            ".DS_Store",
            ".gitignore",
            ".hidden_file",
            ".Thumbs.db",
        ]
        for hf in hidden_files:
            (edge_cases_dir / hf).write_text("hidden file\n")
            self.file_count += 1
        
        # Files with same name (test collision handling)
        collision_dir = edge_cases_dir / "collisions"
        collision_dir.mkdir(exist_ok=True)
        for i in range(5):
            (collision_dir / "DUPLICATE.txt").write_text(f"Version {i}\n")
            (collision_dir / f"duplicate ({i}).txt").write_text(f"Copy {i}\n")
            self.file_count += 2
        
        # Very deeply nested structure (test recursion)
        deep_path = edge_cases_dir
        for i in range(20):
            deep_path = deep_path / f"level_{i}"
            deep_path.mkdir(exist_ok=True)
            (deep_path / f"file_at_level_{i}.txt").write_text(f"Deep file {i}\n")
            self.file_count += 1
            self.folder_count += 1
        
        # Empty folders (should be removed in Stage 2)
        for i in range(5):
            (edge_cases_dir / f"empty_folder_{i}").mkdir(exist_ok=True)
            self.folder_count += 1
        
        # Single-child folder chains (should be flattened in Stage 2)
        chain = edge_cases_dir / "chain_a" / "chain_b" / "chain_c" / "chain_d"
        chain.mkdir(parents=True, exist_ok=True)
        (chain / "final_file.txt").write_text("End of chain\n")
        self.file_count += 1
        self.folder_count += 4
        
        # Folders with < 5 items (should be flattened in Stage 2)
        small_folders = edge_cases_dir / "small_folders"
        small_folders.mkdir(exist_ok=True)
        for i in range(3):
            small_dir = small_folders / f"small_{i}"
            small_dir.mkdir(exist_ok=True)
            for j in range(random.randint(1, 4)):
                (small_dir / f"file_{j}.txt").write_text(f"File {j}\n")
                self.file_count += 1
            self.folder_count += 1
        
        print(f"    Added edge cases: {len(hidden_files)} hidden files, collision tests, deep nesting, etc.")

    def generate_stage3_dataset(self, size: str = "small"):
        """
        Generate Stage 3-specific test dataset with duplicates and collisions.

        Dataset includes:
        - Exact duplicate files (for deduplication testing)
        - Files with "keep" keyword in various path positions
        - Size collision groups (same size, different content)
        - Varied modification times

        Args:
            size: Dataset size - "small" (100 files), "medium" (1k), "stage3" (custom)
        """
        sizes = {
            "small": (100, 20, 10),  # (total files, duplicates, size collisions)
            "medium": (1000, 200, 50),
            "stage3": (500, 100, 30),  # Optimized for Stage 3 testing
        }

        num_files, num_duplicates, num_collisions = sizes.get(size, sizes["small"])

        print(f"\nGenerating Stage 3 test dataset ({size})...")
        print(f"Target: {num_files:,} total files")
        print(f"  - {num_duplicates} duplicate files")
        print(f"  - {num_collisions} size collision groups")
        print(f"  - Various 'keep' keyword paths")
        print(f"Location: {self.base_path}\n")

        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Generate components
        print("[1/4] Generating unique files...")
        unique_files = self._generate_stage3_unique_files(num_files - num_duplicates)

        print("[2/4] Generating exact duplicates...")
        self._generate_stage3_duplicates(unique_files, num_duplicates)

        print("[3/4] Generating 'keep' keyword paths...")
        self._generate_stage3_keep_paths()

        print("[4/4] Generating size collision groups...")
        self._generate_stage3_size_collisions(num_collisions)

        print(f"\n✓ Stage 3 test data generated successfully!")
        print(f"  Total files: {self.file_count:,}")
        print(f"  Total folders: {self.folder_count:,}")

    def _generate_stage3_unique_files(self, count: int) -> List[Path]:
        """Generate unique files with varied sizes and mtimes."""
        created_files = []

        # File size ranges (in bytes)
        size_ranges = [
            (100, 1024),           # Tiny: 100B - 1KB
            (1024, 10240),         # Small: 1KB - 10KB (some will be skipped)
            (10240, 102400),       # Medium: 10KB - 100KB
            (102400, 1048576),     # Large: 100KB - 1MB
        ]

        for i in range(count):
            # Create nested folder structure
            folder_depth = random.randint(1, 4)
            folder_parts = [f"folder_{random.randint(1, 5)}" for _ in range(folder_depth)]
            folder_path = self.base_path / Path(*folder_parts)
            folder_path.mkdir(parents=True, exist_ok=True)
            self.folder_count += 1

            # Create file with random size
            size_range = random.choice(size_ranges)
            file_size = random.randint(*size_range)
            file_path = folder_path / f"file_{i:04d}.dat"

            # Generate random content
            content = os.urandom(file_size)
            file_path.write_bytes(content)

            # Set random modification time (last 365 days)
            days_ago = random.randint(1, 365)
            mtime = (datetime.now() - timedelta(days=days_ago)).timestamp()
            os.utime(file_path, (mtime, mtime))

            created_files.append(file_path)
            self.file_count += 1

            if (i + 1) % 100 == 0:
                print(f"  Created {i + 1}/{count} unique files...")

        print(f"  ✓ Created {count} unique files")
        return created_files

    def _generate_stage3_duplicates(self, source_files: List[Path], num_duplicates: int):
        """Generate exact duplicates of randomly selected files."""
        duplicate_count = 0

        # Create duplicate groups (2-3 copies of some originals)
        num_groups = num_duplicates // 2  # Average 2 duplicates per group

        for group_idx in range(num_groups):
            # Select random source file
            if not source_files:
                break

            source = random.choice(source_files)

            # Create 2-3 duplicates
            num_copies = random.randint(2, 3)

            for copy_idx in range(num_copies):
                # Place duplicate in different location
                folder_depth = random.randint(1, 5)
                folder_parts = [f"dup_{random.randint(1, 10)}" for _ in range(folder_depth)]
                dup_folder = self.base_path / Path(*folder_parts)
                dup_folder.mkdir(parents=True, exist_ok=True)

                # Copy file (exact duplicate)
                dup_path = dup_folder / f"duplicate_{group_idx}_{copy_idx}.dat"
                shutil.copy2(source, dup_path)

                # Set different modification time
                days_ago = random.randint(1, 730)  # Up to 2 years ago
                mtime = (datetime.now() - timedelta(days=days_ago)).timestamp()
                os.utime(dup_path, (mtime, mtime))

                duplicate_count += 1
                self.file_count += 1

                if duplicate_count >= num_duplicates:
                    break

            if duplicate_count >= num_duplicates:
                break

        print(f"  ✓ Created {duplicate_count} duplicate files in {num_groups} groups")

    def _generate_stage3_keep_paths(self):
        """Generate files with 'keep' keyword in various path positions."""
        keep_scenarios = [
            # "keep" in grandparent folder (highest priority)
            ("keep", "subfolder1", "subfolder2", "file_in_keep_grandparent.dat"),

            # "keep" in parent folder
            ("data", "keep", "file_in_keep_parent.dat"),

            # "keep" in immediate folder
            ("data", "archive", "keep", "file_in_keep_immediate.dat"),

            # "keep" in filename only (lowest priority)
            ("data", "regular", "keep_this_file.dat"),
            ("data", "regular", "file_keep.dat"),

            # Multiple scenarios for testing
            ("KEEP", "important", "file.dat"),  # Case-insensitive
            ("keep_these", "videos", "file.dat"),  # "keep" in folder name
        ]

        content = b"Important data that should be kept!\n" * 100

        for path_parts in keep_scenarios:
            folder_path = self.base_path / Path(*path_parts[:-1])
            folder_path.mkdir(parents=True, exist_ok=True)

            file_path = folder_path / path_parts[-1]
            file_path.write_bytes(content)

            # Set recent modification time (these are "important")
            mtime = (datetime.now() - timedelta(days=random.randint(1, 30))).timestamp()
            os.utime(file_path, (mtime, mtime))

            self.file_count += 1

        # Create duplicates of some "keep" files to test priority
        keep_file1 = self.base_path / "keep" / "subfolder1" / "subfolder2" / "file_in_keep_grandparent.dat"
        dup1 = self.base_path / "archive" / "duplicate_of_keep.dat"
        dup1.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(keep_file1, dup1)
        self.file_count += 1

        print(f"  ✓ Created {len(keep_scenarios) + 1} files with 'keep' keyword paths")

    def _generate_stage3_size_collisions(self, num_groups: int):
        """Generate files with same size but different content."""
        target_sizes = [
            1024,      # 1KB
            10240,     # 10KB
            102400,    # 100KB
            524288,    # 512KB
        ]

        collision_count = 0

        for group_idx in range(num_groups):
            # Pick a target size
            target_size = random.choice(target_sizes)

            # Create 2-3 files with exact same size but different content
            files_in_group = random.randint(2, 3)

            for file_idx in range(files_in_group):
                # Random folder
                folder_path = self.base_path / f"collisions" / f"group_{group_idx}"
                folder_path.mkdir(parents=True, exist_ok=True)

                # Generate file with exact target size
                content = os.urandom(target_size)
                file_path = folder_path / f"collision_{file_idx}.dat"
                file_path.write_bytes(content)

                # Random mtime
                days_ago = random.randint(1, 365)
                mtime = (datetime.now() - timedelta(days=days_ago)).timestamp()
                os.utime(file_path, (mtime, mtime))

                collision_count += 1
                self.file_count += 1

        print(f"  ✓ Created {collision_count} files in {num_groups} size collision groups")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic test data for File Organizer"
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory for test data"
    )
    parser.add_argument(
        "--size",
        type=str,
        choices=["small", "medium", "large", "stage3"],
        default="small",
        help="Dataset size: small (100 files), medium (10k), large (100k), stage3 (500 files optimized for Stage 3)"
    )
    parser.add_argument(
        "--stage3",
        action="store_true",
        help="Generate Stage 3-specific test data (duplicates, collisions, 'keep' paths)"
    )

    args = parser.parse_args()

    generator = TestDataGenerator(Path(args.output_dir))

    if args.stage3:
        # Generate Stage 3-specific test data
        generator.generate_stage3_dataset(args.size)
        print(f"\nStage 3 test data ready at: {args.output_dir}")
        print(f"Test Stage 3 with: python -m file_organizer -if {args.output_dir} --stage 3a")
    else:
        # Generate regular test data (for Stages 1-2)
        generator.generate_dataset(args.size)
        print(f"\nTest data ready at: {args.output_dir}")
        print(f"You can now test with: python -m file_organizer -if {args.output_dir}")


if __name__ == "__main__":
    main()

