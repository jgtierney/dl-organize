"""
Security tests for Stage 4 file relocation.

Tests path traversal prevention and folder validation.
"""

import tempfile
import pytest
from pathlib import Path

from src.file_organizer.stage4 import Stage4Processor
from src.file_organizer.cli import validate_folder_paths


class TestPathTraversalPrevention:
    """Test that path traversal attempts are blocked."""

    def test_validate_destination_path_normal(self):
        """Test that normal paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True
            )

            # Normal path should be valid
            normal_path = output_dir / "subdir" / "file.txt"
            assert processor._validate_destination_path(normal_path) is True

    def test_validate_destination_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True
            )

            # Path traversal should be blocked
            malicious_path = output_dir / ".." / "etc" / "passwd"
            assert processor._validate_destination_path(malicious_path) is False

    def test_validate_destination_path_absolute_outside(self):
        """Test that absolute paths outside output are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True
            )

            # Absolute path outside output should be blocked
            outside_path = Path("/tmp/evil.txt")
            assert processor._validate_destination_path(outside_path) is False

    def test_validate_destination_path_nested_ok(self):
        """Test that deeply nested paths within output are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True
            )

            # Deeply nested path should be valid
            nested_path = output_dir / "a" / "b" / "c" / "d" / "file.txt"
            assert processor._validate_destination_path(nested_path) is True

    def test_security_violation_tracking(self):
        """Test that security violations are tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a test file
            test_file = input_dir / "test.txt"
            test_file.write_text("test content")

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True
            )

            # Initially no violations
            assert processor.security_violations == 0

            # Process would detect violations if we could create malicious filenames
            # (filesystem limitations prevent creating actual ".." filenames)
            # So we test the validation method directly
            malicious_dest = output_dir / ".." / "etc" / "passwd"
            is_valid = processor._validate_destination_path(malicious_dest)
            assert is_valid is False


class TestFolderPathValidation:
    """Test folder path relationship validation."""

    def test_same_folder_rejected(self):
        """Test that same input/output folder is rejected."""
        folder = Path("/data/test")
        error = validate_folder_paths(folder, folder)
        assert error is not None
        assert "cannot be the same" in error.lower()

    def test_output_in_input_rejected(self):
        """Test that output inside input is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input"
            output_path = Path(tmpdir) / "input" / "output"
            input_path.mkdir(parents=True)
            output_path.mkdir(parents=True)

            error = validate_folder_paths(input_path, output_path)
            assert error is not None
            assert "infinite recursion" in error.lower()

    def test_input_in_output_rejected(self):
        """Test that input inside output is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output"
            input_path = Path(tmpdir) / "output" / "input"
            output_path.mkdir(parents=True)
            input_path.mkdir(parents=True)

            error = validate_folder_paths(input_path, output_path)
            assert error is not None
            assert "unexpected behavior" in error.lower()

    def test_sibling_folders_accepted(self):
        """Test that sibling folders are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input"
            output_path = Path(tmpdir) / "output"
            input_path.mkdir(parents=True)
            output_path.mkdir(parents=True)

            error = validate_folder_paths(input_path, output_path)
            assert error is None

    def test_none_output_accepted(self):
        """Test that None output folder is accepted."""
        input_path = Path("/data/input")
        error = validate_folder_paths(input_path, None)
        assert error is None

    def test_different_trees_accepted(self):
        """Test that folders in different trees are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                input_path = Path(tmpdir1) / "input"
                output_path = Path(tmpdir2) / "output"
                input_path.mkdir(parents=True)
                output_path.mkdir(parents=True)

                error = validate_folder_paths(input_path, output_path)
                assert error is None


class TestIntegrationSecurity:
    """Integration tests for security features."""

    def test_relocate_files_with_normal_names(self):
        """Test that files with normal names are processed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create test files
            (input_dir / "file1.txt").write_text("content1")
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("content2")

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True,
                verbose=False
            )

            results = processor.process()

            # Should process both files successfully
            assert results.files_moved == 2
            assert len(results.failed_files) == 0
            assert processor.security_violations == 0

    def test_dry_run_mode_safe(self):
        """Test that dry-run mode doesn't actually move files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create test file
            test_file = input_dir / "test.txt"
            test_file.write_text("content")

            processor = Stage4Processor(
                input_folder=input_dir,
                output_folder=output_dir,
                dry_run=True,
                verbose=False
            )

            results = processor.process()

            # File should still exist in input
            assert test_file.exists()
            # Output should be empty (dry run)
            assert len(list(output_dir.rglob("*"))) == 0
            assert results.dry_run is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
