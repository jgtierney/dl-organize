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
    
    default_config = """# File Organizer Configuration
# Optional configuration file for file-organizer tool
# CLI flags override these settings

# Default execution mode: 'dry-run' or 'execute'
default_mode: dry-run

# Folder flattening threshold (number of items)
# Folders with fewer than this many items will be flattened
flatten_threshold: 5

# Preserve original file timestamps during operations
preserve_timestamps: true

# Log file location: 'cwd' (current directory) or absolute path
log_location: cwd

# Large scale performance tuning
# Progress update interval: 'auto' (adaptive) or specific number
progress_update_interval: auto

# Maximum number of detailed errors to log (prevents log explosion)
max_errors_logged: 1000

# Number of files between scan progress updates
scan_progress_interval: 10000

# Future options (not yet implemented):
# parallel_processing: false
# worker_threads: 8
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
