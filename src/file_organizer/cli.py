"""
Command-line interface for File Organizer.

Handles argument parsing, validation, and orchestration of processing stages.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .stage1 import Stage1Processor
from .stage2 import Stage2Processor
from .config import Config


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Systematically organize and clean up large collections of files",
        epilog="For detailed documentation, see: docs/requirements/requirements.md"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "-if", "--input-folder",
        required=True,
        type=str,
        metavar="PATH",
        help="Input directory to process (required)"
    )
    
    parser.add_argument(
        "-of", "--output-folder",
        type=str,
        metavar="PATH",
        help="Output directory (reserved for Stage 3+, not used yet)"
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute operations (default is dry-run preview mode)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (future enhancement)"
    )
    
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2],
        help="Run specific stage only (default: run all stages)"
    )
    
    parser.add_argument(
        "--flatten-threshold",
        type=int,
        metavar="N",
        help="Folder flattening threshold (default: 5 items from config)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to configuration file (default: ~/.file_organizer.yaml)"
    )
    
    return parser.parse_args()


def confirm_proceed_to_next_stage(
    current_stage: int,
    next_stage: int,
    dry_run: bool = False
) -> bool:
    """
    Prompt user to confirm proceeding to next stage.
    
    Args:
        current_stage: Number of stage that just completed
        next_stage: Number of next stage to run
        dry_run: Whether in dry-run mode
        
    Returns:
        True if user wants to proceed, False to exit
    """
    stage_names = {
        1: "Filename Detoxification",
        2: "Folder Structure Optimization",
        3: "Duplicate Detection & Resolution",
        4: "File Relocation"
    }
    
    current_name = stage_names.get(current_stage, f"Stage {current_stage}")
    next_name = stage_names.get(next_stage, f"Stage {next_stage}")
    
    print("\n" + "=" * 70)
    print(f"Stage {current_stage} completed successfully.")
    print()
    
    mode_indicator = " (DRY-RUN)" if dry_run else " (EXECUTE MODE)"
    print(f"Proceed to Stage {next_stage}: {next_name}{mode_indicator}? (yes/no): ", end="")
    
    try:
        response = input().strip().lower()
        if response in ('yes', 'y'):
            return True
        else:
            return False
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        return False


def validate_arguments(args: argparse.Namespace) -> Optional[str]:
    """
    Validate command-line arguments.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Error message if invalid, None if valid
    """
    # Validate input folder
    input_path = Path(args.input_folder)
    if not input_path.exists():
        return f"Input directory does not exist: {args.input_folder}"
    
    if not input_path.is_dir():
        return f"Input path is not a directory: {args.input_folder}"
    
    # Check for dangerous system directories
    dangerous_dirs = [
        "/", "/usr", "/bin", "/sbin", "/etc", "/boot",
        "/sys", "/proc", "/dev", "/lib", "/lib64"
    ]
    
    abs_path = str(input_path.resolve())
    for dangerous in dangerous_dirs:
        if abs_path == dangerous or abs_path.startswith(dangerous + "/"):
            return f"DANGEROUS: Cannot process system directory: {abs_path}"
    
    # Warn about output folder if specified
    if args.output_folder:
        print("NOTE: --output-folder is reserved for Stage 3+")
        print("      Stages 1-2 perform in-place operations only.\n")
    
    return None


def main() -> int:
    """
    Main CLI entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse arguments
    args = parse_arguments()
    
    # Validate arguments
    error = validate_arguments(args)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    
    # Load configuration
    config_path = Path(args.config) if args.config else None
    config = Config(config_path)
    
    # Display header
    print("=" * 70)
    print(f"File Organizer v{__version__}")
    print("=" * 70)
    print(f"Input directory: {args.input_folder}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY-RUN (preview only)'}")
    
    # Show config info if loaded
    if config.has_config_file():
        print(f"Config file: {config.config_path}")
    
    print("=" * 70)
    print()
    
    # Confirm execution if not dry-run
    if args.execute:
        print("⚠️  EXECUTE MODE: Files and folders will be modified!")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Operation cancelled.")
            return 0
        print()
    
    try:
        # Determine which stages to run
        run_stage1 = args.stage is None or args.stage == 1
        run_stage2 = args.stage is None or args.stage == 2
        
        # Run Stage 1
        if run_stage1:
            print("Starting Stage 1: Filename Detoxification...")
            stage1 = Stage1Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute
            )
            stage1.process()
            
            # Confirm before Stage 2 if it will run
            if run_stage2:
                if not confirm_proceed_to_next_stage(1, 2, dry_run=not args.execute):
                    print("\n" + "=" * 70)
                    print("Stage 1 completed. Exiting.")
                    print("=" * 70)
                    return 0
        
        # Run Stage 2
        if run_stage2:
            # Get flatten threshold from CLI or config
            flatten_threshold = config.get_flatten_threshold(args.flatten_threshold)
            
            print("\nStarting Stage 2: Folder Structure Optimization...")
            stage2 = Stage2Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute,
                flatten_threshold=flatten_threshold,
                config=config
            )
            stage2.process()
        
        print("\n" + "=" * 70)
        print("✓ Processing complete!")
        print("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        raise  # Re-raise to be handled by __main__
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

