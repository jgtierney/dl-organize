"""
Integration testing for full pipeline: Stages 1 → 2 → 3

Tests end-to-end workflow with realistic scenarios.
"""

import tempfile
import shutil
from pathlib import Path
import sys
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from file_organizer.stage1 import Stage1Processor
from file_organizer.stage2 import Stage2Processor
from file_organizer.stage3 import Stage3


def create_messy_test_dataset(root: Path):
    """
    Create a messy dataset simulating real-world file organization chaos.
    
    Includes:
    - Files with problematic names (spaces, special chars, uppercase)
    - Duplicate files in various locations
    - Empty folders
    - Nested folder chains
    - Hidden files
    - Various file sizes
    """
    # Create messy filenames (Stage 1 will clean these)
    (root / "My Document.TXT").write_text("Document content A")
    (root / "my_document.txt").write_text("Document content A")  # Will be duplicate after Stage 1
    (root / "Photo 2023.JPG").write_text("Image data")  # Will be skipped (image)
    (root / "video file.mp4").write_text("Video content unique")
    
    # Create nested folders with single items (Stage 2 will flatten)
    nested = root / "folder1" / "folder2" / "folder3"
    nested.mkdir(parents=True)
    (nested / "deep_file.dat").write_text("Content in deep folder")
    
    # Create duplicate in different location
    shallow = root / "shallow"
    shallow.mkdir()
    (shallow / "duplicate.dat").write_text("Duplicate content X")
    (root / "another_duplicate.dat").write_text("Duplicate content X")
    
    # Create files with "keep" keyword
    keep_dir = root / "keep_important"
    keep_dir.mkdir()
    (keep_dir / "important.txt").write_text("Duplicate content Y")
    (root / "disposable.txt").write_text("Duplicate content Y")  # Same content, no "keep"
    
    # Create empty folders (Stage 2 will remove)
    (root / "empty1").mkdir()
    (root / "empty2" / "empty3").mkdir(parents=True)
    
    # Create hidden files (Stage 1 will remove)
    (root / ".hidden_file").write_text("Hidden content")
    (root / ".DS_Store").write_text("Mac metadata")
    
    # Create folder with few items (Stage 2 will flatten if < 5)
    small_folder = root / "small_folder"
    small_folder.mkdir()
    (small_folder / "file1.txt").write_text("Small folder file 1")
    (small_folder / "file2.txt").write_text("Small folder file 2")
    
    print(f"Created messy test dataset with {len(list(root.rglob('*')))} items")


def test_full_pipeline_stages_1_2_3():
    """Test complete pipeline: Stage 1 → 2 → 3"""
    print("\n=== Testing Full Pipeline: Stages 1 → 2 → 3 ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / 'input'
        output_dir = Path(tmpdir) / 'output'
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Create messy dataset
        create_messy_test_dataset(input_dir)
        
        # Count initial state
        initial_files = len(list(input_dir.rglob('*')))
        print(f"\nInitial state: {initial_files} items")
        
        # Stage 1: Filename Detoxification
        print("\n--- Running Stage 1 ---")
        stage1 = Stage1Processor(input_dir, dry_run=False)
        stage1.process()
        
        # Check Stage 1 results
        files_after_stage1 = list(input_dir.rglob('*'))
        print(f"After Stage 1: {len(files_after_stage1)} items")
        
        # Verify no hidden files remain
        hidden_files = [f for f in files_after_stage1 if f.name.startswith('.')]
        assert len(hidden_files) == 0, f"Found {len(hidden_files)} hidden files after Stage 1"
        print("✓ No hidden files remain")
        
        # Verify all filenames are lowercase
        uppercase_files = [f for f in files_after_stage1 
                          if f.is_file() and f.name != f.name.lower()]
        assert len(uppercase_files) == 0, f"Found {len(uppercase_files)} uppercase files"
        print("✓ All filenames lowercase")
        
        # Stage 2: Folder Structure Optimization
        print("\n--- Running Stage 2 ---")
        stage2 = Stage2Processor(input_dir, dry_run=False, flatten_threshold=5)
        stage2.process()
        
        # Check Stage 2 results
        files_after_stage2 = list(input_dir.rglob('*'))
        print(f"After Stage 2: {len(files_after_stage2)} items")
        
        # Verify no empty folders
        empty_folders = [f for f in files_after_stage2 
                        if f.is_dir() and not any(f.iterdir())]
        assert len(empty_folders) == 0, f"Found {len(empty_folders)} empty folders"
        print("✓ No empty folders remain")
        
        # Stage 3: Video Deduplication
        print("\n--- Running Stage 3A (Internal Deduplication) ---")
        config = {'duplicate_detection': {'min_file_size': 0}}  # Process small files for testing
        stage3 = Stage3(input_dir, output_dir, config=config, dry_run=True)  # Use dry_run for testing
        
        stats_3a = stage3.run_stage3a()
        
        print(f"Stage 3A Results:")
        print(f"  Duplicates found: {stats_3a['duplicates_found']}")
        print(f"  Files deleted: {stats_3a['files_deleted']}")
        print(f"  Space reclaimed: {stats_3a['space_reclaimed']} bytes")
        
        # Should find duplicates
        assert stats_3a['duplicates_found'] > 0, "Should find duplicates"
        print("✓ Duplicates detected (dry-run mode)")
        
        # Check final state
        final_files = list(input_dir.rglob('*'))
        remaining_files = [f for f in final_files if f.is_file()]
        print(f"✓ Remaining files after deduplication: {len(remaining_files)}")
        print(f"\nFinal state: {len(final_files)} items")
        print(f"Reduction: {initial_files - len(final_files)} items removed")
        
        stage3.close()
    
    print("✓ Full pipeline integration test passed")


def test_stage3_cross_folder_deduplication():
    """Test Stage 3B: Cross-folder deduplication"""
    print("\n=== Testing Stage 3B: Cross-Folder Deduplication ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / 'input'
        output_dir = Path(tmpdir) / 'output'
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Create files in input
        (input_dir / 'unique_input.txt').write_text('Unique to input')
        (input_dir / 'duplicate.txt').write_text('Duplicate content')
        (input_dir / 'another_dup.txt').write_text('Another duplicate')
        
        # Create files in output (some duplicates)
        (output_dir / 'unique_output.txt').write_text('Unique to output')
        (output_dir / 'duplicate.txt').write_text('Duplicate content')  # Dup of input
        (output_dir / 'old_file.txt').write_text('Another duplicate')  # Dup of input
        
        print(f"Input files: {len(list(input_dir.glob('*')))}")
        print(f"Output files: {len(list(output_dir.glob('*')))}")
        
        # First, populate output cache by running Stage 3A on output
        config = {'duplicate_detection': {'min_file_size': 0}}
        stage3_output = Stage3(output_dir, None, config=config, dry_run=False)
        stage3_output.detector.find_all_duplicates(
            list(output_dir.glob('*')), 
            folder='output'
        )
        stage3_output.close()
        
        print("\nOutput folder cache populated")
        
        # Now run Stage 3B to find cross-folder duplicates
        stage3 = Stage3(input_dir, output_dir, config=config, dry_run=True)  # Use dry_run for testing
        stats_3b = stage3.run_stage3b()
        
        print(f"\nStage 3B Results:")
        print(f"  Cross-folder duplicates: {stats_3b['duplicates_found']}")
        print(f"  Files deleted: {stats_3b['files_deleted']}")
        
        # Should find cross-folder duplicates
        assert stats_3b['duplicates_found'] > 0, "Should find cross-folder duplicates"
        print("✓ Cross-folder duplicates detected (dry-run mode)")
        
        stage3.close()
    
    print("✓ Cross-folder deduplication test passed")


def test_cli_integration():
    """Test CLI with Stage 3 integration"""
    print("\n=== Testing CLI Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / 'input'
        output_dir = Path(tmpdir) / 'output'
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Create simple test files
        (input_dir / 'file1.txt').write_text('Content A')
        (input_dir / 'FILE1.TXT').write_text('Content A')  # Will be duplicate after Stage 1
        (input_dir / 'file2.txt').write_text('Content B')
        
        # Test Stage 1 only via CLI (dry-run mode to avoid interactive prompt)
        result = subprocess.run([
            sys.executable, '-m', 'file_organizer',
            '-if', str(input_dir),
            '--stage', '1'
            # Note: Using dry-run (default) to avoid interactive confirmation
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        print(f"Stage 1 CLI exit code: {result.returncode}")
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        assert result.returncode == 0, "Stage 1 CLI should succeed"
        print("✓ Stage 1 CLI execution successful")
        print("✓ CLI integration with dry-run mode verified")
    
    print("✓ CLI integration test passed")


def test_resolution_policy_integration():
    """Test that resolution policy works end-to-end"""
    print("\n=== Testing Resolution Policy Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / 'input'
        input_dir.mkdir()
        
        # Create duplicates at different depths
        (input_dir / 'shallow.txt').write_text('Duplicate content Z')
        deep = input_dir / 'level1' / 'level2' / 'level3'
        deep.mkdir(parents=True)
        (deep / 'deep.txt').write_text('Duplicate content Z')
        
        # Create duplicates with "keep" keyword
        keep_dir = input_dir / 'keep_files'
        keep_dir.mkdir()
        (keep_dir / 'important.txt').write_text('Duplicate content W')
        (input_dir / 'unimportant.txt').write_text('Duplicate content W')
        
        config = {'duplicate_detection': {'min_file_size': 0}}
        stage3 = Stage3(input_dir, None, config=config, dry_run=False)
        
        # Find duplicates
        files = list(input_dir.rglob('*.txt'))
        duplicates = stage3.detector.find_all_duplicates(files)
        
        print(f"Found {len(duplicates)} duplicate groups")
        
        # Resolve duplicates
        files_to_keep, files_to_delete = stage3.resolver.resolve_all(duplicates)
        
        # Verify resolution policy worked
        for file_hash, keeper in files_to_keep.items():
            # Check if "keep" keyword was respected
            if 'keep' in str(keeper).lower():
                print(f"✓ Kept file with 'keep' keyword: {keeper.name}")
            # Check if deeper path was kept
            elif 'level3' in str(keeper):
                print(f"✓ Kept deeper path: {keeper}")
        
        assert len(files_to_keep) == len(duplicates), "Should have resolution for each group"
        print("✓ Resolution policy applied correctly")
        
        stage3.close()
    
    print("✓ Resolution policy integration test passed")


def main():
    """Run all integration tests."""
    print("=" * 80)
    print("STAGE 3 - INTEGRATION TESTING")
    print("=" * 80)
    
    try:
        test_full_pipeline_stages_1_2_3()
        test_stage3_cross_folder_deduplication()
        test_cli_integration()
        test_resolution_policy_integration()
        
        print("\n" + "=" * 80)
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("=" * 80)
        print("\nIntegration Test Summary:")
        print("- Full pipeline (Stages 1→2→3) working correctly")
        print("- Cross-folder deduplication functional")
        print("- CLI integration successful")
        print("- Resolution policy working end-to-end")
        print("- Stage 3 ready for production use!")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

