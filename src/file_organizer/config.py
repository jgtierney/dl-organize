"""
Configuration management for File Organizer.

Supports optional YAML configuration file at .file_organizer.yaml (execution directory)
CLI flags override configuration file settings.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class Config:
    """
    Configuration manager with YAML file support.

    Precedence order (highest to lowest):
    1. CLI arguments (passed to methods)
    2. Configuration file (.file_organizer.yaml in execution directory)
    3. Built-in defaults
    """
    
    # Built-in defaults
    DEFAULTS = {
        'default_mode': 'dry-run',
        'flatten_threshold': 5,
        'preserve_timestamps': True,
        'log_location': 'cwd',
        'progress_update_interval': 'auto',
        'max_errors_logged': 1000,
        'scan_progress_interval': 10000,
        'duplicate_detection': {
            'skip_images': True,
            'min_file_size': 10240  # 10KB
        },
        'verbose': False
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file (defaults to .file_organizer.yaml in CWD)
        """
        if config_path is None:
            config_path = Path.cwd() / '.file_organizer.yaml'

        self.config_path = config_path
        self.config_data = {}

        # Load config file if it exists
        if self.config_path.exists():
            self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}
            print(f"Loaded configuration from: {self.config_path}")
        except yaml.YAMLError as e:
            print(f"WARNING: Failed to parse config file: {e}")
            print("Using default settings.")
            self.config_data = {}
        except Exception as e:
            print(f"WARNING: Failed to load config file: {e}")
            print("Using default settings.")
            self.config_data = {}
    
    def get(self, key: str, cli_override: Any = None) -> Any:
        """
        Get configuration value with precedence handling.
        
        Args:
            key: Configuration key
            cli_override: Value from CLI argument (highest priority)
            
        Returns:
            Configuration value (CLI > config file > defaults)
        """
        # Precedence: CLI > config file > defaults
        if cli_override is not None:
            return cli_override
        
        if key in self.config_data:
            return self.config_data[key]
        
        if key in self.DEFAULTS:
            return self.DEFAULTS[key]
        
        return None
    
    def get_flatten_threshold(self, cli_override: Optional[int] = None) -> int:
        """
        Get folder flattening threshold (default: 5 items).

        Returns:
            Valid threshold between 0 and 1000 (inclusive)
        """
        value = self.get('flatten_threshold', cli_override)

        # Handle None
        if value is None:
            return 5

        # Validate and convert
        try:
            threshold = int(value)

            # Validate range
            if threshold < 0:
                print(f"WARNING: flatten_threshold must be >= 0, got {threshold}. Using default (5).")
                return 5

            if threshold > 1000:
                print(f"WARNING: flatten_threshold very high ({threshold}), capping at 1000.")
                return 1000

            return threshold

        except (ValueError, TypeError) as e:
            print(f"WARNING: Invalid flatten_threshold value '{value}': {e}. Using default (5).")
            return 5
    
    def get_default_mode(self, cli_override: Optional[str] = None) -> str:
        """
        Get default execution mode (dry-run or execute).

        Returns:
            Either 'dry-run' or 'execute'
        """
        value = self.get('default_mode', cli_override)

        if value is None:
            return 'dry-run'

        # Validate value
        mode = str(value).lower().strip()

        if mode in ('dry-run', 'dryrun', 'dry_run', 'preview'):
            return 'dry-run'
        elif mode in ('execute', 'exec', 'run', 'live'):
            return 'execute'
        else:
            print(f"WARNING: Invalid default_mode '{value}', must be 'dry-run' or 'execute'. Using 'dry-run'.")
            return 'dry-run'
    
    def should_preserve_timestamps(self, cli_override: Optional[bool] = None) -> bool:
        """
        Check if timestamps should be preserved.

        Returns:
            Boolean value (default: True)
        """
        value = self.get('preserve_timestamps', cli_override)

        if value is None:
            return True

        # Handle various boolean representations
        if isinstance(value, bool):
            return value

        # Handle string representations
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif value_lower in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                print(f"WARNING: Invalid preserve_timestamps value '{value}'. Using default (True).")
                return True

        # Handle numeric (0 = False, anything else = True)
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            print(f"WARNING: Invalid preserve_timestamps value '{value}'. Using default (True).")
            return True
    
    def get_max_errors_logged(self, cli_override: Optional[int] = None) -> int:
        """
        Get maximum number of detailed errors to log.

        Returns:
            Valid count between 0 and 100,000 (inclusive)
        """
        value = self.get('max_errors_logged', cli_override)

        if value is None:
            return 1000

        try:
            max_errors = int(value)

            # Validate range
            if max_errors < 0:
                print(f"WARNING: max_errors_logged must be >= 0, got {max_errors}. Using 0 (no logging).")
                return 0

            if max_errors > 100000:
                print(f"WARNING: max_errors_logged very high ({max_errors}), capping at 100,000.")
                return 100000

            return max_errors

        except (ValueError, TypeError) as e:
            print(f"WARNING: Invalid max_errors_logged value '{value}': {e}. Using default (1000).")
            return 1000
    
    def get_scan_progress_interval(self, cli_override: Optional[int] = None) -> int:
        """
        Get number of files between scan progress updates.

        Returns:
            Valid interval between 1 and 1,000,000 (inclusive)
        """
        value = self.get('scan_progress_interval', cli_override)

        if value is None:
            return 10000

        try:
            interval = int(value)

            # Validate range
            if interval < 1:
                print(f"WARNING: scan_progress_interval must be >= 1, got {interval}. Using 1.")
                return 1

            if interval > 1000000:
                print(f"WARNING: scan_progress_interval very high ({interval}), capping at 1,000,000.")
                return 1000000

            return interval

        except (ValueError, TypeError) as e:
            print(f"WARNING: Invalid scan_progress_interval value '{value}': {e}. Using default (10,000).")
            return 10000

    def get_skip_images(self, cli_override: Optional[bool] = None) -> bool:
        """
        Get whether to skip image files in duplicate detection.

        Returns:
            Boolean value (default: True - skip images)
        """
        # CLI override takes precedence
        if cli_override is not None:
            return cli_override

        # Try to get from nested duplicate_detection config
        if 'duplicate_detection' in self.config_data:
            dup_config = self.config_data['duplicate_detection']
            if isinstance(dup_config, dict) and 'skip_images' in dup_config:
                value = dup_config['skip_images']
            else:
                value = None
        else:
            value = None

        # Fall back to defaults
        if value is None:
            return self.DEFAULTS['duplicate_detection']['skip_images']

        # Handle various boolean representations
        if isinstance(value, bool):
            return value

        # Handle string representations
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif value_lower in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                print(f"WARNING: Invalid skip_images value '{value}'. Using default (True).")
                return True

        # Handle numeric (0 = False, anything else = True)
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            print(f"WARNING: Invalid skip_images value '{value}'. Using default (True).")
            return True

    def get_min_file_size(self, cli_override: Optional[int] = None) -> int:
        """
        Get minimum file size for duplicate detection.

        Returns:
            Valid size in bytes between 0 and 1GB (inclusive), default: 10240 (10KB)
        """
        # CLI override takes precedence
        if cli_override is not None:
            value = cli_override
        # Try to get from nested duplicate_detection config
        elif 'duplicate_detection' in self.config_data:
            dup_config = self.config_data['duplicate_detection']
            if isinstance(dup_config, dict) and 'min_file_size' in dup_config:
                value = dup_config['min_file_size']
            else:
                value = None
        else:
            value = None

        # Fall back to defaults
        if value is None:
            return self.DEFAULTS['duplicate_detection']['min_file_size']

        try:
            min_size = int(value)

            # Validate range
            if min_size < 0:
                print(f"WARNING: min_file_size must be >= 0, got {min_size}. Using 0.")
                return 0

            if min_size > 1024 * 1024 * 1024:  # 1GB
                print(f"WARNING: min_file_size very high ({min_size}), capping at 1GB.")
                return 1024 * 1024 * 1024

            return min_size

        except (ValueError, TypeError) as e:
            print(f"WARNING: Invalid min_file_size value '{value}': {e}. Using default (10240).")
            return 10240

    def get_verbose(self, cli_override: Optional[bool] = None) -> bool:
        """
        Get verbose logging setting.

        Returns:
            Boolean value (default: False)
        """
        value = self.get('verbose', cli_override)

        if value is None:
            return False

        # Handle various boolean representations
        if isinstance(value, bool):
            return value

        # Handle string representations
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif value_lower in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                print(f"WARNING: Invalid verbose value '{value}'. Using default (False).")
                return False

        # Handle numeric (0 = False, anything else = True)
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            print(f"WARNING: Invalid verbose value '{value}'. Using default (False).")
            return False

    def has_config_file(self) -> bool:
        """Check if a configuration file exists and was loaded."""
        return self.config_path.exists() and bool(self.config_data)
    
    def display_active_config(self):
        """Display active configuration settings."""
        print("\nActive Configuration:")
        print("-" * 50)
        if self.has_config_file():
            print(f"Config file: {self.config_path}")
            for key, value in self.config_data.items():
                print(f"  {key}: {value}")
        else:
            print("Config file: None (using defaults)")
        print("-" * 50)


def create_default_config_file(path: Optional[Path] = None) -> Path:
    """
    Create a default configuration file with example settings.

    Args:
        path: Where to create the config file (defaults to .file_organizer.yaml in CWD)

    Returns:
        Path to created config file
    """
    if path is None:
        path = Path.cwd() / '.file_organizer.yaml'

    default_config = """# ============================================================================
# File Organizer Configuration File
# ============================================================================
# Place this file as .file_organizer.yaml in your execution directory
# CLI flags override these settings (highest priority)
#
# Precedence: CLI flags > Config file > Built-in defaults
# ============================================================================

# ============================================================================
# EXECUTION MODE
# ============================================================================

# Default execution mode when --execute flag is not specified
default_mode: dry-run
# Alternatives:
# default_mode: execute     # WARNING: Will make actual changes without confirmation

# ============================================================================
# STAGE 2: FOLDER STRUCTURE OPTIMIZATION
# ============================================================================

# Folder flattening threshold (number of items)
# Folders with this many items or fewer will be flattened into parent
flatten_threshold: 5
# Alternatives:
# flatten_threshold: 0      # Disable flattening
# flatten_threshold: 3      # More aggressive flattening
# flatten_threshold: 10     # Less aggressive flattening

# ============================================================================
# STAGE 3: DUPLICATE DETECTION
# ============================================================================

# Duplicate detection settings
duplicate_detection:
  # Skip image files during duplicate detection
  # Images are numerous (~60-70% by count) but small (~10% by size)
  # Often intentionally duplicated (thumbnails, resizes, etc.)
  skip_images: true
  # Alternatives:
  # skip_images: false      # Include images in duplicate detection

  # Minimum file size to process in duplicate detection (bytes)
  # Files smaller than this are skipped (usually not worth deduplicating)
  min_file_size: 10240      # 10 KB (default)
  # Alternatives:
  # min_file_size: 0        # Process all files regardless of size
  # min_file_size: 1024     # 1 KB minimum
  # min_file_size: 51200    # 50 KB minimum
  # min_file_size: 1048576  # 1 MB minimum

# ============================================================================
# FILE OPERATIONS
# ============================================================================

# Preserve original file timestamps during rename/move operations
preserve_timestamps: true
# Alternatives:
# preserve_timestamps: false  # Use current timestamp for modified files

# ============================================================================
# LOGGING & OUTPUT
# ============================================================================

# Verbose output (detailed logging to console)
verbose: false
# Alternatives:
# verbose: true             # Show detailed progress and debug information

# Log file location
log_location: cwd
# Alternatives:
# log_location: /path/to/logs  # Absolute path to log directory

# Maximum number of detailed errors to log (prevents log file explosion)
max_errors_logged: 1000
# Alternatives:
# max_errors_logged: 0      # Don't log detailed errors
# max_errors_logged: 100    # Less detailed error logging
# max_errors_logged: 10000  # More detailed error logging

# ============================================================================
# PERFORMANCE TUNING (Large Scale Operations)
# ============================================================================

# Progress update interval for main operations
progress_update_interval: auto
# Alternatives:
# progress_update_interval: 100   # Update every 100 files
# progress_update_interval: 1000  # Update every 1000 files

# Number of files between scan progress updates
scan_progress_interval: 10000
# Alternatives:
# scan_progress_interval: 1000   # More frequent updates (noisier)
# scan_progress_interval: 50000  # Less frequent updates (quieter)

# ============================================================================
# FUTURE OPTIONS (Not Yet Implemented)
# ============================================================================

# The following options are planned for future releases:
#
# parallel_processing: false     # Enable parallel processing
# worker_threads: 8              # Number of worker threads
# checksum_algorithm: xxhash     # Hash algorithm (xxhash, sha256, etc.)
# cache_expiry_days: 30          # Days before cache entries expire
"""

    with open(path, 'w') as f:
        f.write(default_config)

    print(f"Created default configuration file: {path}")
    return path


if __name__ == "__main__":
    # Test configuration loading
    config = Config()
    
    print("\nConfiguration Test:")
    print(f"Flatten threshold: {config.get_flatten_threshold()}")
    print(f"Default mode: {config.get_default_mode()}")
    print(f"Preserve timestamps: {config.should_preserve_timestamps()}")
    print(f"Max errors logged: {config.get_max_errors_logged()}")
    
    # Test CLI override
    print(f"\nWith CLI override (threshold=10): {config.get_flatten_threshold(cli_override=10)}")
