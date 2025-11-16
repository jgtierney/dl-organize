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
from .stage3 import Stage3
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
        epilog="For detailed documentation, see: docs/requirements.md"
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
        type=str,
        choices=["1", "2", "3", "3a", "3b"],
        help="Run specific stage only (1, 2, 3, 3a=internal dedup, 3b=cross-folder dedup)"
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
    
    # Validate output folder for Stage 3
    if args.stage in ["3", "3b"]:
        if not args.output_folder:
            return "Stage 3B requires --output-folder to be specified"
        
        output_path = Path(args.output_folder)
        if not output_path.exists():
            return f"Output directory does not exist: {args.output_folder}"
        
        if not output_path.is_dir():
            return f"Output path is not a directory: {args.output_folder}"
    
    # Warn about output folder if specified for Stages 1-2 only
    if args.output_folder and args.stage in [None, "1", "2"]:
        print("NOTE: --output-folder is only used for Stage 3")
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
        run_stage1 = args.stage is None or args.stage == "1"
        run_stage2 = args.stage is None or args.stage == "2"
        run_stage3 = args.stage in [None, "3", "3a", "3b"]
        
        # Determine Stage 3 phases
        run_stage3a = args.stage in [None, "3", "3a"]
        run_stage3b = args.stage in [None, "3", "3b"]
        
        # Run Stage 1
        if run_stage1:
            print("Starting Stage 1: Filename Detoxification...")
            stage1 = Stage1Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute
            )
            stage1.process()
        
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
        
        # Run Stage 3
        if run_stage3 and args.output_folder:
            output_folder = Path(args.output_folder) if args.output_folder else None
            
            # Determine which phases to run
            phases = []
            if run_stage3a:
                phases.append('3a')
            if run_stage3b:
                phases.append('3b')
            
            print("\nStarting Stage 3: Video Deduplication...")
            stage3 = Stage3(
                input_folder=Path(args.input_folder),
                output_folder=output_folder,
                config=config.config_data,
                dry_run=not args.execute
            )
            
            stage3.run(phases=phases)
            stage3.close()
        
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

