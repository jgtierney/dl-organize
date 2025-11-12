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
from .stage3 import Stage3


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
        help="Output directory (required for Stage 3B cross-folder deduplication)"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute operations (default is dry-run preview mode)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--stage",
        type=str,
        choices=["1", "2", "3a", "3b"],
        help="Run specific stage only (1=filename, 2=folders, 3a=duplicates-input, 3b=duplicates-cross)"
    )

    # Stage 3-specific arguments
    parser.add_argument(
        "--skip-images",
        action="store_true",
        default=True,
        help="Skip image files in duplicate detection (default: enabled)"
    )

    parser.add_argument(
        "--no-skip-images",
        action="store_false",
        dest="skip_images",
        help="Include image files in duplicate detection"
    )

    parser.add_argument(
        "--min-file-size",
        type=int,
        default=10240,
        metavar="BYTES",
        help="Minimum file size to process in duplicate detection (default: 10240 bytes = 10KB)"
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

    # Validate output folder (fail fast - check before any processing)
    if args.output_folder:
        output_path = Path(args.output_folder)
        if not output_path.exists():
            return f"Output directory does not exist: {args.output_folder}"

        if not output_path.is_dir():
            return f"Output path is not a directory: {args.output_folder}"

        # Check if output is a system directory
        abs_output = str(output_path.resolve())
        for dangerous in dangerous_dirs:
            if abs_output == dangerous or abs_output.startswith(dangerous + "/"):
                return f"DANGEROUS: Cannot use system directory as output: {abs_output}"

    # Validate Stage 3B requires output folder
    if args.stage == "3b" and not args.output_folder:
        return "Stage 3B requires --output-folder for cross-folder deduplication"

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
    
    # Display header
    print("=" * 70)
    print(f"File Organizer v{__version__}")
    print("=" * 70)
    print(f"Input directory: {args.input_folder}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY-RUN (preview only)'}")
    print("=" * 70)
    print()
    
    # Confirm execution if not dry-run
    if args.execute:
        print("⚠️  EXECUTE MODE: Files will be modified!")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Operation cancelled.")
            return 0
        print()
    
    try:
        # Determine which stages to run
        run_all = args.stage is None

        # Stage 1: Filename Detoxification
        if run_all or args.stage == "1":
            print("Starting Stage 1: Filename Detoxification...")
            stage1 = Stage1Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute
            )
            stage1.process()

        # Stage 2: Folder Optimization (not yet implemented)
        if run_all or args.stage == "2":
            print("\nStarting Stage 2: Folder Optimization...")
            print("⚠️  Stage 2 not yet implemented")
            # TODO: Implement Stage 2
            # stage2 = Stage2Processor(...)
            # stage2.process()

        # Stage 3A: Internal Duplicate Detection
        if run_all or args.stage == "3a":
            print("\nStarting Stage 3A: Internal Duplicate Detection...")
            with Stage3(
                input_folder=Path(args.input_folder),
                output_folder=None,  # Stage 3A doesn't use output folder
                skip_images=args.skip_images,
                min_file_size=args.min_file_size,
                dry_run=not args.execute,
                verbose=True  # Always verbose for now
            ) as stage3:
                results = stage3.run_stage3a()

                if not args.execute and results.total_duplicates > 0:
                    print("\n💡 TIP: Run with --execute to actually delete duplicates")

        # Stage 3B: Cross-Folder Deduplication (not yet implemented)
        if args.stage == "3b":
            print("\nStarting Stage 3B: Cross-Folder Deduplication...")
            print("⚠️  Stage 3B not yet implemented")
            # TODO: Implement Stage 3B
            # with Stage3(...) as stage3:
            #     results = stage3.run_stage3b()

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

