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
"""

import os
import random
import argparse
from pathlib import Path
from typing import List


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
        
        # Files with different names that will collide after sanitization
        collision_dir = edge_cases_dir / "collisions"
        collision_dir.mkdir(exist_ok=True)
        
        # These all sanitize to "duplicate.txt" causing collisions
        collision_names = [
            "DUPLICATE.txt",
            "Duplicate.TXT",
            "duplicate (1).txt",
            "duplicate - Copy.txt",
            "duplicate@#$.txt",
        ]
        for name in collision_names:
            (collision_dir / name).write_text(f"File: {name}\n")
            self.file_count += 1
        
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
        
        # Stage 2 specific test cases
        stage2_dir = edge_cases_dir / "stage2_tests"
        stage2_dir.mkdir(exist_ok=True)
        
        # Test 1: Nested empty folders
        nested_empty = stage2_dir / "nested_empty" / "level1" / "level2" / "level3"
        nested_empty.mkdir(parents=True, exist_ok=True)
        self.folder_count += 4
        
        # Test 2: Mixed chain with small folders
        mixed = stage2_dir / "mixed_A"
        mixed.mkdir(exist_ok=True)
        mixed_b = mixed / "mixed_B"
        mixed_b.mkdir(exist_ok=True)
        mixed_c = mixed_b / "mixed_C"
        mixed_c.mkdir(exist_ok=True)
        # Add 3 files to mixed_C (< 5 items, should flatten)
        for i in range(3):
            (mixed_c / f"item_{i}.txt").write_text(f"Item {i}\n")
            self.file_count += 1
        self.folder_count += 3
        
        # Test 3: Folder with exactly 5 items (should NOT flatten)
        threshold = stage2_dir / "at_threshold"
        threshold.mkdir(exist_ok=True)
        for i in range(5):
            (threshold / f"file_{i}.txt").write_text(f"File {i}\n")
            self.file_count += 1
        self.folder_count += 1
        
        # Test 4: Folder with 6 items (should NOT flatten)
        above = stage2_dir / "above_threshold"
        above.mkdir(exist_ok=True)
        for i in range(6):
            (above / f"file_{i}.txt").write_text(f"File {i}\n")
            self.file_count += 1
        self.folder_count += 1
        
        # Test 5: Complex nested structure requiring multiple flattening passes
        complex_root = stage2_dir / "complex_flattening"
        complex_root.mkdir(exist_ok=True)
        level1 = complex_root / "level1"
        level1.mkdir(exist_ok=True)
        level2 = level1 / "level2"
        level2.mkdir(exist_ok=True)
        level3 = level2 / "level3"
        level3.mkdir(exist_ok=True)
        # Add 2 files to level3 (will require 3 passes to flatten completely)
        (level3 / "file1.txt").write_text("File 1\n")
        (level3 / "file2.txt").write_text("File 2\n")
        self.file_count += 2
        self.folder_count += 4
        
        # Test 6: Folder name sanitization tests (Stage 2)
        sanitize = stage2_dir / "Folder Name Sanitization" / "UPPERCASE FOLDER" / "café_français"
        sanitize.mkdir(parents=True, exist_ok=True)
        (sanitize / "test.txt").write_text("Test\n")
        self.file_count += 1
        self.folder_count += 3
        
        print(f"    Added edge cases: {len(hidden_files)} hidden files, collision tests, Stage 2 scenarios, etc.")


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
        choices=["small", "medium", "large"],
        default="small",
        help="Dataset size: small (100 files), medium (10k), large (100k)"
    )
    
    args = parser.parse_args()
    
    generator = TestDataGenerator(Path(args.output_dir))
    generator.generate_dataset(args.size)
    
    print(f"\nTest data ready at: {args.output_dir}")
    print(f"You can now test with: python -m file_organizer -if {args.output_dir}")


if __name__ == "__main__":
    main()

