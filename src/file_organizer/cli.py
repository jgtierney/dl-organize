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
from .stage4 import Stage4Processor
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
        choices=["1", "2", "3a", "3b", "4"],
        help="Run specific stage only (1=filename, 2=folders, 3a=duplicates-input, 3b=duplicates-cross, 4=relocation)"
    )

    # Stage 3-specific arguments
    parser.add_argument(
        "--skip-images",
        action="store_true",
        default=None,
        dest="skip_images_flag",
        help="Skip image files in duplicate detection (default: from config or True)"
    )

    parser.add_argument(
        "--no-skip-images",
        action="store_true",
        default=None,
        dest="no_skip_images_flag",
        help="Include image files in duplicate detection"
    )

    parser.add_argument(
        "--min-file-size",
        type=int,
        default=None,
        metavar="BYTES",
        help="Minimum file size to process in duplicate detection (default: from config or 10240 bytes = 10KB)"
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        metavar="PATH",
        help="Cache directory for duplicate detection database (default: from config or .file_organizer_cache in current directory)"
    )

    # Stage 2-specific arguments
    parser.add_argument(
        "--flatten-threshold",
        type=int,
        default=None,
        metavar="N",
        help="Flatten folders with N or fewer items (default: from config or 5)"
    )

    # Stage 4-specific arguments
    parser.add_argument(
        "--preserve-input",
        action="store_true",
        help="Keep input folder with files after relocation (default: clean input folder)"
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

    # Validate Stage 4 requires output folder
    if args.stage == "4" and not args.output_folder:
        return "Stage 4 requires --output-folder for file relocation"

    return None


def check_cache_database(cache_dir: Optional[Path]) -> bool:
    """
    Check if cache database exists, prompt user to create if it doesn't.

    Args:
        cache_dir: Cache directory path (None = default CWD/.file_organizer_cache)

    Returns:
        True if should continue, False if user cancelled
    """
    # Determine actual cache path
    if cache_dir is None:
        cache_path = Path.cwd() / '.file_organizer_cache' / 'hashes.db'
    else:
        cache_path = cache_dir / 'hashes.db'

    # Check if database exists
    if cache_path.exists():
        return True

    # Database doesn't exist - prompt user
    print()
    print("⚠️  Cache database not found!")
    print(f"   Location: {cache_path}")
    print()
    print("The cache database stores file hashes for duplicate detection.")
    print("Creating a new cache will scan and hash all files (may take time).")
    print()

    response = input("Create new cache database? (yes/no): ").strip().lower()

    if response in ('yes', 'y'):
        print("✓ Will create new cache database")
        return True
    else:
        print("✗ Operation cancelled by user")
        return False


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
        # Load configuration (CLI args override config file)
        config = Config()

        # Determine which stages to run
        run_all = args.stage is None

        # Stage 1: Filename Detoxification
        if run_all or args.stage == "1":
            print("Starting Stage 1: Filename Detoxification...")
            verbose = config.get_verbose(cli_override=args.verbose if args.verbose else None)
            stage1 = Stage1Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute,
                verbose=verbose
            )
            stage1.process()

        # Stage 2: Folder Optimization
        if run_all or args.stage == "2":
            print("\nStarting Stage 2: Folder Structure Optimization...")

            # Get flatten threshold from config (CLI override if provided)
            flatten_threshold = config.get_flatten_threshold(cli_override=args.flatten_threshold)
            verbose = config.get_verbose(cli_override=args.verbose if args.verbose else None)

            stage2 = Stage2Processor(
                input_dir=Path(args.input_folder),
                dry_run=not args.execute,
                flatten_threshold=flatten_threshold,
                config=config,
                verbose=verbose
            )
            stage2.process()

        # Stage 3A: Internal Duplicate Detection
        if run_all or args.stage == "3a":
            print("\nStarting Stage 3A: Internal Duplicate Detection...")

            # Get Stage 3 settings from config (CLI override if provided)
            # Determine skip_images from CLI flags or config
            skip_images_cli = None
            if args.skip_images_flag:
                skip_images_cli = True
            elif args.no_skip_images_flag:
                skip_images_cli = False
            skip_images = config.get_skip_images(cli_override=skip_images_cli)

            min_file_size = config.get_min_file_size(cli_override=args.min_file_size)
            cache_dir = config.get_cache_dir(cli_override=args.cache_dir)
            verbose = config.get_verbose(cli_override=args.verbose if args.verbose else None)

            # Check if cache database exists, prompt if not
            if not check_cache_database(cache_dir):
                return 0  # User cancelled

            print("  Initializing cache database...")
            sys.stdout.flush()

            with Stage3(
                input_folder=Path(args.input_folder),
                output_folder=None,  # Stage 3A doesn't use output folder
                cache_dir=cache_dir,
                skip_images=skip_images,
                min_file_size=min_file_size,
                dry_run=not args.execute,
                verbose=verbose
            ) as stage3:
                results = stage3.run_stage3a()

                if not args.execute and results.total_duplicates > 0:
                    print("\n💡 TIP: Run with --execute to actually delete duplicates")

        # Stage 3B: Cross-Folder Deduplication
        # Run if explicitly requested OR if run_all and output folder is provided
        should_run_3b = args.stage == "3b" or (run_all and args.output_folder)

        if should_run_3b:
            # Validate output folder is provided
            if not args.output_folder:
                print("\n❌ ERROR: Stage 3B requires --output-folder (-of) to be specified")
                print("   Stage 3B compares input folder against output folder for duplicates")
                return 1

            print("\nStarting Stage 3B: Cross-Folder Deduplication...")
            if run_all:
                print("💡 Output folder detected - running Stage 3B to find cross-folder duplicates")

            # Get Stage 3 settings from config (CLI override if provided)
            # Determine skip_images from CLI flags or config
            skip_images_cli = None
            if args.skip_images_flag:
                skip_images_cli = True
            elif args.no_skip_images_flag:
                skip_images_cli = False
            skip_images = config.get_skip_images(cli_override=skip_images_cli)

            min_file_size = config.get_min_file_size(cli_override=args.min_file_size)
            cache_dir = config.get_cache_dir(cli_override=args.cache_dir)
            verbose = config.get_verbose(cli_override=args.verbose if args.verbose else None)

            # Check if cache database exists, prompt if not
            if not check_cache_database(cache_dir):
                return 0  # User cancelled

            print("  Initializing cache database...")
            sys.stdout.flush()

            with Stage3(
                input_folder=Path(args.input_folder),
                output_folder=Path(args.output_folder),
                cache_dir=cache_dir,
                skip_images=skip_images,
                min_file_size=min_file_size,
                dry_run=not args.execute,
                verbose=verbose
            ) as stage3:
                results = stage3.run_stage3b()

                if not args.execute and results.total_duplicates > 0:
                    print("\n💡 TIP: Run with --execute to actually delete duplicates")

        # Stage 4: File Relocation
        # Run if explicitly requested OR if run_all and output folder provided
        should_run_4 = args.stage == "4" or (run_all and args.output_folder)

        if should_run_4:
            # Validate output folder is provided
            if not args.output_folder:
                print("\n❌ ERROR: Stage 4 requires --output-folder (-of)")
                return 1

            print("\nStarting Stage 4: File Relocation...")
            if run_all:
                print("💡 Output folder detected - running Stage 4 to relocate files")

            verbose = config.get_verbose(cli_override=args.verbose if args.verbose else None)
            stage4 = Stage4Processor(
                input_folder=Path(args.input_folder),
                output_folder=Path(args.output_folder),
                preserve_input=args.preserve_input,
                dry_run=not args.execute,
                verbose=verbose
            )

            results = stage4.process()

            if not args.execute:
                print("\n💡 TIP: Run with --execute to actually move files")

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

