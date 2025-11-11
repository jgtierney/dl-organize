"""
Video metadata extraction and comparison for Stage 3.

Provides fast video metadata extraction to avoid unnecessary hashing
when files can be determined as different based on duration, codec, etc.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

try:
    from pymediainfo import MediaInfo
    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False
    logging.warning("pymediainfo not available, video optimizations disabled")

logger = logging.getLogger(__name__)

# Video file extensions to check
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv', '.flv', '.webm',
    '.mpg', '.mpeg', '.m2ts', '.ts', '.vob', '.ogv', '.3gp', '.f4v'
}


class VideoMetadata:
    """Container for video metadata."""
    
    def __init__(self, duration: Optional[float] = None,
                 codec: Optional[str] = None,
                 resolution: Optional[str] = None,
                 bitrate: Optional[int] = None):
        self.duration = duration
        self.codec = codec
        self.resolution = resolution
        self.bitrate = bitrate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'duration': self.duration,
            'codec': self.codec,
            'resolution': self.resolution,
            'bitrate': self.bitrate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMetadata':
        """Create from dictionary."""
        return cls(
            duration=data.get('duration'),
            codec=data.get('codec'),
            resolution=data.get('resolution'),
            bitrate=data.get('bitrate')
        )
    
    def __repr__(self) -> str:
        parts = []
        if self.duration:
            parts.append(f"duration={self.duration:.1f}s")
        if self.codec:
            parts.append(f"codec={self.codec}")
        if self.resolution:
            parts.append(f"resolution={self.resolution}")
        return f"VideoMetadata({', '.join(parts)})"


def is_video_file(file_path: Path) -> bool:
    """
    Check if file is a video based on extension.
    
    Args:
        file_path: Path to file
    
    Returns:
        True if likely a video file
    """
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def extract_video_metadata(file_path: Path) -> Optional[VideoMetadata]:
    """
    Extract video metadata using pymediainfo.
    
    Args:
        file_path: Path to video file
    
    Returns:
        VideoMetadata object or None if extraction fails
    """
    if not PYMEDIAINFO_AVAILABLE:
        return None
    
    if not is_video_file(file_path):
        return None
    
    try:
        media_info = MediaInfo.parse(str(file_path))
        
        # Find video track
        for track in media_info.tracks:
            if track.track_type == 'Video':
                # Extract duration (in seconds)
                duration = None
                if track.duration:
                    duration = float(track.duration) / 1000.0  # Convert ms to seconds
                
                # Extract codec
                codec = track.codec_id or track.format
                
                # Extract resolution
                resolution = None
                if track.width and track.height:
                    resolution = f"{track.width}x{track.height}"
                
                # Extract bitrate
                bitrate = track.bit_rate
                
                logger.debug(f"Extracted metadata from {file_path}: "
                           f"duration={duration}, codec={codec}, resolution={resolution}")
                
                return VideoMetadata(
                    duration=duration,
                    codec=codec,
                    resolution=resolution,
                    bitrate=bitrate
                )
        
        # No video track found
        logger.warning(f"No video track found in {file_path}")
        return None
        
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        return None


def compare_durations(duration1: Optional[float], 
                     duration2: Optional[float],
                     tolerance: float = 1.0) -> bool:
    """
    Compare two video durations with tolerance.
    
    Args:
        duration1: First duration in seconds
        duration2: Second duration in seconds
        tolerance: Tolerance in seconds (default: 1.0)
    
    Returns:
        True if durations match within tolerance, False if different
        Returns True if either duration is None (can't determine)
    """
    if duration1 is None or duration2 is None:
        # Can't compare, assume they might match
        return True
    
    return abs(duration1 - duration2) <= tolerance


def videos_likely_different(file1_path: Path, file2_path: Path,
                           metadata1: Optional[VideoMetadata] = None,
                           metadata2: Optional[VideoMetadata] = None) -> bool:
    """
    Determine if two videos are likely different based on metadata.
    
    This is a fast pre-check to avoid expensive hashing when we can
    determine files are different based on metadata alone.
    
    Args:
        file1_path: Path to first file
        file2_path: Path to second file
        metadata1: Cached metadata for file1 (optional)
        metadata2: Cached metadata for file2 (optional)
    
    Returns:
        True if files are likely different (skip hashing)
        False if they might be the same (need to hash)
    """
    # If sizes are different, definitely different files
    try:
        size1 = file1_path.stat().st_size
        size2 = file2_path.stat().st_size
        if size1 != size2:
            logger.debug(f"Files have different sizes: {size1} vs {size2}")
            return True
    except OSError:
        # Can't get size, can't determine
        return False
    
    # Extract metadata if not provided
    if metadata1 is None:
        metadata1 = extract_video_metadata(file1_path)
    if metadata2 is None:
        metadata2 = extract_video_metadata(file2_path)
    
    # If we have durations for both, compare them
    if metadata1 and metadata2:
        if metadata1.duration and metadata2.duration:
            if not compare_durations(metadata1.duration, metadata2.duration):
                logger.debug(f"Videos have different durations: "
                           f"{metadata1.duration} vs {metadata2.duration}")
                return True
    
    # Can't determine they're different, might be same
    return False


def format_duration(seconds: Optional[float]) -> str:
    """
    Format duration in seconds as human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    if seconds is None:
        return "unknown"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

