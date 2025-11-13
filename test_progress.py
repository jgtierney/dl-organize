#!/usr/bin/env python
"""Test progress bar implementation."""

import time
from src.file_organizer.progress_bar import ProgressBar, SimpleProgress

print("Testing ProgressBar functionality")
print("=" * 70)

# Test 1: Simple progress bar without stats (non-verbose)
print("\nTest 1: Non-verbose progress bar (no stats)")
print("-" * 70)
progress = ProgressBar(
    total=100,
    description="Processing items",
    verbose=False,
    min_duration=0.0  # Force showing progress
)

for i in range(1, 101):
    progress.update(i)
    time.sleep(0.01)  # Simulate work

progress.finish()

# Test 2: Verbose progress bar with stats
print("\nTest 2: Verbose progress bar (with stats)")
print("-" * 70)
progress = ProgressBar(
    total=100,
    description="Processing files",
    verbose=True,
    min_duration=0.0  # Force showing progress
)

for i in range(1, 101):
    stats = {
        "Renamed": i // 2,
        "Deleted": i // 5,
        "Collisions": i // 10
    }
    progress.update(i, stats)
    time.sleep(0.01)  # Simulate work

final_stats = {
    "Renamed": 50,
    "Deleted": 20,
    "Collisions": 10
}
progress.finish(final_stats)

# Test 3: SimpleProgress counter
print("\nTest 3: SimpleProgress counter")
print("-" * 70)
simple = SimpleProgress("Scanning files", verbose=True)

for i in range(1, 51):
    simple.update(i)
    time.sleep(0.02)  # Simulate work

simple.finish()

# Test 4: Fast operation (< 5 seconds, should not show progress bar)
print("\nTest 4: Fast operation (should skip progress bar)")
print("-" * 70)
progress = ProgressBar(
    total=10,
    description="Quick task",
    verbose=True,
    min_duration=5.0  # Default setting
)

for i in range(1, 11):
    progress.update(i, {"Processed": i})
    time.sleep(0.01)  # Very fast

progress.finish({"Processed": 10})

print("\n" + "=" * 70)
print("✓ All tests completed successfully")
print("=" * 70)
