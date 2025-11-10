"""
Main entry point for File Organizer CLI.

Usage:
    python -m file_organizer -if /path/to/directory [--execute] [--verbose]
"""

import sys
import argparse
from pathlib import Path
from .cli import main as cli_main


def main():
    """Entry point for the application."""
    try:
        sys.exit(cli_main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

