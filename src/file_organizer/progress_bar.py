"""
Progress bar utility for consistent progress reporting across all stages.

Features:
- 20-block visual progress bar (████░░░░)
- Updates every 5% increment
- In-place updates using carriage return (\r)
- Time tracking and estimation
- Verbose mode with statistics
- Auto-hides for fast operations (< 5 seconds)
"""

import time
from typing import Optional, Dict, Union


class ProgressBar:
    """
    Progress bar with visual indicators and time estimation.

    Example output (non-verbose):
        Stage 1/4: Filename Detoxification - Processing Files
          ████████░░░░░░░░░░░░ 40% (38,154/95,384 files) - 1.5s - ~2s remaining

    Example output (verbose):
        Stage 1/4: Filename Detoxification - Processing Files
          ████████░░░░░░░░░░░░ 40% (38,154/95,384 files) - 1.5s - ~2s | Renamed: 983, Deleted: 94
    """

    def __init__(
        self,
        total: int,
        description: str,
        verbose: bool = True,
        min_duration: float = 5.0,
        blocks: int = 20,
        update_interval: int = 5  # Update every 5%
    ):
        """
        Initialize progress bar.

        Args:
            total: Total number of items to process
            description: Activity description (e.g., "Processing Files")
            verbose: Whether to show verbose statistics
            min_duration: Minimum duration to show progress (seconds)
            blocks: Number of blocks in progress bar (default 20)
            update_interval: Percentage interval for updates (default 5%)
        """
        self.total = total
        self.description = description
        self.verbose = verbose
        self.min_duration = min_duration
        self.blocks = blocks
        self.update_interval = update_interval

        # Timing
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_percentage = 0

        # State
        self.current = 0
        self.finished = False
        self.show_progress = True  # Will be set to False if operation is too fast

    def should_update(self, current: int) -> bool:
        """
        Determine if progress bar should be updated.

        Args:
            current: Current item count

        Returns:
            True if should update, False otherwise
        """
        # Always update at the end
        if current >= self.total:
            return True

        # Calculate current percentage
        percentage = int((current / self.total) * 100)

        # Update every N%
        if percentage >= self.last_percentage + self.update_interval:
            return True

        return False

    def update(self, current: int, stats: Optional[Dict[str, Union[int, str]]] = None):
        """
        Update progress bar.

        Args:
            current: Current item count
            stats: Optional dict of statistics to show in verbose mode
                   e.g., {"Renamed": 123, "Deleted": 45, "Collisions": 8}
        """
        self.current = current

        # Check if we should update
        if not self.should_update(current):
            return

        # Calculate metrics
        elapsed = time.time() - self.start_time
        percentage = int((current / self.total) * 100)

        # Update last percentage
        self.last_percentage = percentage

        # Don't show progress for very fast operations
        if current < self.total and elapsed < 1.0:
            return  # Wait at least 1 second before showing progress

        # Build progress bar
        filled = int((current / self.total) * self.blocks)
        bar = '█' * filled + '░' * (self.blocks - filled)

        # Format counts with commas
        current_str = f"{current:,}"
        total_str = f"{self.total:,}"

        # Time remaining (only show for operations > 10 seconds)
        time_remaining_str = ""
        if elapsed > 10.0 and current > 0 and current < self.total:
            rate = current / elapsed
            remaining = (self.total - current) / rate
            time_remaining_str = f" - ~{int(remaining)}s remaining"

        # Build base progress line
        progress_line = f"  {bar} {percentage}% ({current_str}/{total_str}) - {elapsed:.1f}s{time_remaining_str}"

        # Add verbose statistics if provided
        if self.verbose and stats:
            stats_parts = []
            for k, v in stats.items():
                if isinstance(v, int):
                    stats_parts.append(f"{k}: {v:,}")
                else:
                    stats_parts.append(f"{k}: {v}")
            stats_str = ", ".join(stats_parts)
            progress_line += f" | {stats_str}"

        # Print with carriage return for in-place update
        print(progress_line, end='\r', flush=True)

    def finish(self, stats: Optional[Dict[str, Union[int, str]]] = None):
        """
        Mark progress as complete and print final line.

        Args:
            stats: Optional dict of statistics to show in verbose mode
        """
        if self.finished:
            return

        self.finished = True
        elapsed = time.time() - self.start_time

        # Check if operation was too fast to show progress
        if elapsed < self.min_duration:
            # Just print completion without progress bar
            if self.verbose and stats:
                stats_str = ", ".join(f"{k}: {v:,}" for k, v in stats.items())
                print(f"  ✓ {self.description} complete ({self.total:,} items, {elapsed:.1f}s) | {stats_str}")
            else:
                print(f"  ✓ {self.description} complete ({self.total:,} items, {elapsed:.1f}s)")
            return

        # Print final progress bar with 100% and newline
        bar = '█' * self.blocks
        total_str = f"{self.total:,}"

        progress_line = f"  {bar} 100% ({total_str}/{total_str}) - {elapsed:.1f}s"

        # Add verbose statistics if provided
        if self.verbose and stats:
            stats_parts = []
            for k, v in stats.items():
                if isinstance(v, int):
                    stats_parts.append(f"{k}: {v:,}")
                else:
                    stats_parts.append(f"{k}: {v}")
            stats_str = ", ".join(stats_parts)
            progress_line += f" | {stats_str}"

        # Print with newline to persist
        print(progress_line)

    def message(self, text: str):
        """
        Print a message that persists (doesn't get overwritten).

        Args:
            text: Message to print
        """
        print(f"  {text}")


class SimpleProgress:
    """
    Simple progress counter for operations without known total.

    Shows items processed and elapsed time, updates in place.
    """

    def __init__(self, description: str, verbose: bool = True):
        """
        Initialize simple progress counter.

        Args:
            description: Activity description
            verbose: Whether to show progress
        """
        self.description = description
        self.verbose = verbose
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.count = 0

    def update(self, count: int, force: bool = False):
        """
        Update progress counter.

        Args:
            count: Current count
            force: Force update even if too soon
        """
        if not self.verbose:
            return

        self.count = count
        current_time = time.time()

        # Time-based throttling (max 10 updates/sec)
        if not force and current_time - self.last_update_time < 0.1:
            return

        self.last_update_time = current_time
        elapsed = current_time - self.start_time

        print(f"  {self.description}: {count:,} items... ({elapsed:.1f}s)", end='\r', flush=True)

    def finish(self):
        """Mark as complete."""
        if not self.verbose:
            return

        elapsed = time.time() - self.start_time
        print(f"  ✓ {self.description}: {self.count:,} items ({elapsed:.1f}s)" + " " * 20)
