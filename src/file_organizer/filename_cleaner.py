"""
Filename sanitization module.

Handles all filename cleaning operations according to Stage 1 requirements:
- ASCII-only transliteration
- Lowercase conversion
- Special character removal
- Extension normalization
- Collision detection and resolution
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
from unidecode import unidecode


class FilenameCleaner:
    """
    Core filename sanitization engine.
    
    Implements all Stage 1 filename detoxification rules:
    - Transliterate non-ASCII to ASCII
    - Convert to lowercase
    - Replace spaces with underscores
    - Remove special characters (keep only alphanumeric, underscore, period)
    - Normalize extensions (replace internal periods)
    - Handle collisions with date stamp + counter
    """
    
    # Maximum filename length (200 chars for safety, 255 is Linux limit)
    MAX_FILENAME_LENGTH = 200
    
    def __init__(self):
        """Initialize the filename cleaner."""
        self.collision_counters = {}  # Track collisions per directory
        
    def sanitize_filename(self, filename: str, is_directory: bool = False) -> str:
        """
        Sanitize a single filename according to Stage 1 rules.
        
        Args:
            filename: Original filename to sanitize
            is_directory: True if this is a directory name (no extension handling)
            
        Returns:
            Sanitized filename
            
        Rules applied:
        1. Transliterate non-ASCII characters (café → cafe)
        2. Convert to lowercase
        3. Replace spaces with underscores
        4. Remove special characters (keep alphanumeric, underscore, period)
        5. Normalize multiple extensions (archive.tar.gz → archive_tar.gz)
        6. Collapse consecutive underscores
        7. Strip leading/trailing underscores and periods
        8. Truncate if too long (preserving extension)
        """
        if not filename or filename in ('.', '..'):
            return filename
            
        # Separate extension for files (not directories)
        if is_directory:
            base = filename
            ext = ""
        else:
            base, ext = self._split_extension(filename)
        
        # Step 1: Transliterate non-ASCII to ASCII
        base = unidecode(base)
        if ext:
            ext = unidecode(ext)
        
        # Step 2: Convert to lowercase
        base = base.lower()
        if ext:
            ext = ext.lower()
        
        # Step 3: Replace spaces with underscores
        base = base.replace(' ', '_')
        
        # Step 4: Replace internal periods in base with underscores
        # (for extensions like .tar.gz)
        base = base.replace('.', '_')
        
        # Step 5: Remove special characters (keep only alphanumeric and underscore)
        base = re.sub(r'[^a-z0-9_]', '', base)
        
        # Step 6: Collapse consecutive underscores
        base = re.sub(r'_+', '_', base)
        
        # Step 7: Strip leading/trailing underscores
        base = base.strip('_')
        
        # Step 8: Handle empty base name
        if not base:
            base = "unnamed"
        
        # Step 9: Reconstruct filename with extension
        if ext:
            sanitized = f"{base}.{ext}"
        else:
            sanitized = base
        
        # Step 10: Truncate if necessary (preserving extension)
        sanitized = self._truncate_if_needed(sanitized, ext)
        
        return sanitized
    
    def _split_extension(self, filename: str) -> Tuple[str, str]:
        """
        Split filename into base and extension.
        
        Only the final extension is preserved. Multiple extensions
        like .tar.gz are treated as part of the base name and will
        be converted to underscores.
        
        Args:
            filename: Filename to split
            
        Returns:
            Tuple of (base, extension) where extension has no leading dot
        """
        if '.' not in filename:
            return filename, ""
        
        # Split on last period only
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return filename, ""
    
    def _truncate_if_needed(self, filename: str, extension: str) -> str:
        """
        Truncate filename if it exceeds maximum length.
        
        Preserves the extension and truncates the base name.
        
        Args:
            filename: Full filename to check
            extension: File extension (without dot)
            
        Returns:
            Truncated filename if necessary, original if within limits
        """
        if len(filename) <= self.MAX_FILENAME_LENGTH:
            return filename
        
        # Calculate how much space we have for the base
        if extension:
            # Account for the dot separator
            max_base_length = self.MAX_FILENAME_LENGTH - len(extension) - 1
            if max_base_length < 1:
                # Extension itself is too long - just truncate everything
                return filename[:self.MAX_FILENAME_LENGTH]
            
            base = filename[:-(len(extension) + 1)]  # Remove extension and dot
            truncated_base = base[:max_base_length]
            return f"{truncated_base}.{extension}"
        else:
            # No extension, just truncate
            return filename[:self.MAX_FILENAME_LENGTH]
    
    def generate_collision_name(self, base_name: str, directory: Path) -> str:
        """
        Generate a unique filename for collision resolution.

        Uses format: base_YYYYMMDD_N.ext
        where N is a counter starting from 1.

        Ensures the generated name doesn't exceed MAX_FILENAME_LENGTH.

        Args:
            base_name: The sanitized base name that has a collision
            directory: Directory where the file will be placed

        Returns:
            Unique filename with date stamp and counter, truncated if needed
        """
        # Get current date in YYYYMMDD format
        date_stamp = datetime.now().strftime("%Y%m%d")

        # Split extension if present
        if '.' in base_name:
            base, ext = base_name.rsplit('.', 1)
            has_ext = True
        else:
            base, ext = base_name, ""
            has_ext = False

        # Track collision counter for this base name in this directory
        collision_key = str(directory / base_name)
        if collision_key not in self.collision_counters:
            self.collision_counters[collision_key] = 0

        # Increment counter and generate new name
        counter = self.collision_counters[collision_key] + 1
        self.collision_counters[collision_key] = counter

        # Construct collision name
        if has_ext:
            new_name = f"{base}_{date_stamp}_{counter}.{ext}"
        else:
            new_name = f"{base}_{date_stamp}_{counter}"

        # IMPORTANT: Truncate if the collision name is too long
        # The collision suffix adds approximately 14-16 characters:
        # - "_" (1)
        # - "YYYYMMDD" (8)
        # - "_" (1)
        # - counter (1-5 digits, typically 1-2)
        # We need to ensure the final name fits within MAX_FILENAME_LENGTH

        if len(new_name) > self.MAX_FILENAME_LENGTH:
            # Calculate how much space the suffix takes
            suffix = f"_{date_stamp}_{counter}"
            if has_ext:
                suffix += f".{ext}"
            suffix_length = len(suffix)

            # Calculate maximum base length
            max_base_length = self.MAX_FILENAME_LENGTH - suffix_length

            if max_base_length < 1:
                # Suffix itself is too long (extremely rare)
                # Just truncate the whole thing
                new_name = new_name[:self.MAX_FILENAME_LENGTH]
            else:
                # Truncate the base, preserve suffix
                truncated_base = base[:max_base_length]
                if has_ext:
                    new_name = f"{truncated_base}_{date_stamp}_{counter}.{ext}"
                else:
                    new_name = f"{truncated_base}_{date_stamp}_{counter}"

        return new_name
    
    def is_hidden_file(self, filename: str) -> bool:
        """
        Check if a filename represents a hidden file.
        
        Hidden files start with a dot (.) and should be deleted
        according to Stage 1 requirements.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if hidden file, False otherwise
        """
        return filename.startswith('.') and filename not in ('.', '..')
    
    def reset_collision_counters(self):
        """Reset collision counters (useful between directory processing)."""
        self.collision_counters.clear()


def test_filename_cleaner():
    """Quick test function to validate sanitization rules."""
    cleaner = FilenameCleaner()
    
    test_cases = [
        # (input, expected_output, description)
        ("My File.TXT", "my_file.txt", "Basic case"),
        ("café menu.pdf", "cafe_menu.pdf", "Non-ASCII transliteration"),
        ("file@#$name.txt", "filename.txt", "Special character removal"),
        ("archive.tar.gz", "archive_tar.gz", "Multiple extensions"),
        ("file___name.txt", "file_name.txt", "Consecutive underscores"),
        ("___file___.txt", "file.txt", "Leading/trailing underscores"),
        (".hidden", ".hidden", "Hidden file (kept as-is)"),
        ("NO EXTENSION", "no_extension", "No extension"),
        ("Über File — Test.docx", "uber_file_test.docx", "Complex non-ASCII"),
    ]
    
    print("Testing FilenameCleaner...")
    for input_name, expected, description in test_cases:
        result = cleaner.sanitize_filename(input_name)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}: '{input_name}' → '{result}'")
        if result != expected:
            print(f"  Expected: '{expected}'")
    
    print("\nTesting collision generation...")
    base = cleaner.sanitize_filename("report.txt")
    collision1 = cleaner.generate_collision_name(base, Path("/tmp"))
    collision2 = cleaner.generate_collision_name(base, Path("/tmp"))
    print(f"Base: {base}")
    print(f"Collision 1: {collision1}")
    print(f"Collision 2: {collision2}")


if __name__ == "__main__":
    test_filename_cleaner()

