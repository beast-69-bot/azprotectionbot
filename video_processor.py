"""
========================
VIDEO PROCESSING MODULE
========================
This module handles all video manipulation using FFmpeg.
It merges the protection clip with original videos.
"""

import subprocess
import os
import random
from typing import Tuple, Optional

# ========================
# HELPER FUNCTION: GET VIDEO DURATION
# ========================
def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds using FFprobe.
    
    FFprobe is part of FFmpeg and can read video metadata.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        float: Duration in seconds, or 0 if error
    """
    try:
        # FFprobe command to get duration
        # -v error: Only show errors
        # -show_entries format=duration: Get only duration field
        # -of default=noprint_wrappers=1:nokey=1: Output only the value
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        # Run the command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        
        print(f"✓ Video duration: {duration:.2f} seconds")
        return duration
        
    except Exception as e:
        print(f"✗ Error getting video duration: {e}")
        return 0


# ========================
# HELPER FUNCTION: VALIDATE VIDEO
# ========================
def validate_video(video_path: str, max_duration: float = None) -> Tuple[bool, str]:
    """
    Validate that a video file is usable.
    
    Args:
        video_path: Path to video file
        max_duration: Maximum allowed duration (None = no limit)
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    # Check if file exists
    if not os.path.exists(video_path):
        return False, "Video file not found"
    
    # Check file size (must be > 0)
    if os.path.getsize(video_path) == 0:
        return False, "Video file is empty"
    
    # Get duration
    duration = get_video_duration(video_path)
    if duration == 0:
        return False, "Could not read video duration (corrupted file?)"
    
    # Check max duration if specified
    if max_duration and duration > max_duration:
        return False, f"Video too long ({duration:.1f}s). Max: {max_duration}s"
    
    return True, f"Valid video ({duration:.1f}s)"


# ========================
# MAIN FUNCTION: PROCESS VIDEO
# ========================
def process_video(
    original_path: str,
    clip_path: str,
    output_path: str,
    position: str = "start",
    audio_mode: str = "mix"
) -> Tuple[bool, str]:
    """
    Process a video by inserting a protection clip.
    
    This is the main video processing function that:
    1. Validates input files
    2. Determines where to insert the clip
    3. Merges videos using FFmpeg
    4. Handles audio mixing
    
    Args:
        original_path: Path to original video
        clip_path: Path to protection clip
        output_path: Where to save processed video
        position: Where to insert clip (start/middle/end/random)
        audio_mode: How to handle audio (mix/clip/original)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    
    print("\n" + "="*50)
    print("STARTING VIDEO PROCESSING")
    print("="*50)
    
    # ========================
    # STEP 1: VALIDATE INPUTS
    # ========================
    print("\n[1/5] Validating input files...")
    
    # Check original video
    valid, msg = validate_video(original_path)
    if not valid:
        return False, f"Original video error: {msg}"
    print(f"  ✓ Original video: {msg}")
    
    # Check protection clip
    valid, msg = validate_video(clip_path, max_duration=10)
    if not valid:
        return False, f"Protection clip error: {msg}"
    print(f"  ✓ Protection clip: {msg}")
    
    # ========================
    # STEP 2: GET VIDEO INFO
    # ========================
    print("\n[2/5] Reading video information...")
    
    original_duration = get_video_duration(original_path)
    clip_duration = get_video_duration(clip_path)
    
    print(f"  Original: {original_duration:.2f}s")
    print(f"  Clip: {clip_duration:.2f}s")
    
    # ========================
    # STEP 3: DETERMINE POSITION
    # ========================
    print(f"\n[3/5] Determining insertion position (mode: {position})...")
    
    # Calculate where to insert the clip
    if position == "start":
        # Simple: clip first, then original
        insert_at = 0
        method = "concat"
        print(f"  → Inserting at START (0s)")
        
    elif position == "end":
        # Simple: original first, then clip
        insert_at = original_duration
        method = "concat"
        print(f"  → Inserting at END ({original_duration:.2f}s)")
        
    elif position == "middle":
        # Insert at the middle of the video
        insert_at = original_duration / 2
        method = "split"
        print(f"  → Inserting at MIDDLE ({insert_at:.2f}s)")
        
    elif position == "random":
        # Random position between 10% and 90% of video
        min_pos = original_duration * 0.1
        max_pos = original_duration * 0.9
        insert_at = random.uniform(min_pos, max_pos)
        method = "split"
        print(f"  → Inserting at RANDOM position ({insert_at:.2f}s)")
        
    else:
        return False, f"Invalid position: {position}"
    
    # ========================
    # STEP 4: BUILD FFMPEG COMMAND
    # ========================
    print(f"\n[4/5] Building FFmpeg command (method: {method})...")
    
    try:
        if method == "concat" and position == "start":
            # ========================
            # METHOD A: CLIP AT START
            # ========================
            # This is the simplest case: just concatenate clip + original
            
            # Create a temporary file list for FFmpeg concat demuxer
            concat_file = "concat_list.txt"
            with open(concat_file, 'w') as f:
                # FFmpeg concat format: file 'path'
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
                f.write(f"file '{os.path.abspath(original_path)}'\n")
            
            # FFmpeg command explanation:
            # -f concat: Use concat demuxer to join files
            # -safe 0: Allow absolute paths
            # -i concat_list.txt: Input is our file list
            # -c copy: Copy streams without re-encoding (fast!)
            # BUT: -c copy only works if videos have same codec/resolution
            # So we use re-encoding for compatibility:
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',           # Use concat demuxer
                '-safe', '0',             # Allow absolute paths
                '-i', concat_file,        # Input file list
                '-c:v', 'libx264',        # Video codec: H.264
                '-preset', 'medium',      # Encoding speed (medium = balanced)
                '-crf', '23',             # Quality (18-28, lower = better)
                '-c:a', 'aac',            # Audio codec: AAC
                '-b:a', '128k',           # Audio bitrate
                '-y',                     # Overwrite output file
                output_path
            ]
            
        elif method == "concat" and position == "end":
            # ========================
            # METHOD B: CLIP AT END
            # ========================
            # Same as start, but reversed order
            
            concat_file = "concat_list.txt"
            with open(concat_file, 'w') as f:
                f.write(f"file '{os.path.abspath(original_path)}'\n")
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                output_path
            ]
            
        else:
            # ========================
            # METHOD C: CLIP IN MIDDLE/RANDOM
            # ========================
            # This is more complex: we need to split the original video
            # and insert the clip in between
            
            # Split original into two parts
            part1_path = "temp_part1.mp4"
            part2_path = "temp_part2.mp4"
            
            # Extract first part (0 to insert_at)
            print(f"  → Extracting part 1 (0 to {insert_at:.2f}s)...")
            cmd_part1 = [
                'ffmpeg',
                '-i', original_path,
                '-t', str(insert_at),     # Duration of first part
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                part1_path
            ]
            subprocess.run(cmd_part1, check=True, capture_output=True)
            
            # Extract second part (insert_at to end)
            print(f"  → Extracting part 2 ({insert_at:.2f}s to end)...")
            cmd_part2 = [
                'ffmpeg',
                '-i', original_path,
                '-ss', str(insert_at),    # Start time
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                part2_path
            ]
            subprocess.run(cmd_part2, check=True, capture_output=True)
            
            # Now concatenate: part1 + clip + part2
            concat_file = "concat_list.txt"
            with open(concat_file, 'w') as f:
                f.write(f"file '{os.path.abspath(part1_path)}'\n")
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
                f.write(f"file '{os.path.abspath(part2_path)}'\n")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                output_path
            ]
        
        # ========================
        # STEP 5: EXECUTE FFMPEG
        # ========================
        print(f"\n[5/5] Processing video with FFmpeg...")
        print(f"  Command: {' '.join(cmd)}")
        
        # Run FFmpeg command
        # capture_output=True: Capture stdout/stderr
        # check=True: Raise exception if command fails
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        print("  ✓ FFmpeg processing completed!")
        
        # ========================
        # STEP 6: CLEANUP TEMP FILES
        # ========================
        print("\n[6/6] Cleaning up temporary files...")
        
        temp_files = ['concat_list.txt', 'temp_part1.mp4', 'temp_part2.mp4']
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"  ✓ Removed {temp_file}")
        
        # ========================
        # VERIFY OUTPUT
        # ========================
        if not os.path.exists(output_path):
            return False, "Output file was not created"
        
        output_size = os.path.getsize(output_path)
        if output_size == 0:
            return False, "Output file is empty"
        
        output_duration = get_video_duration(output_path)
        expected_duration = original_duration + clip_duration
        
        print(f"\n✓ SUCCESS!")
        print(f"  Output: {output_path}")
        print(f"  Size: {output_size / (1024*1024):.2f} MB")
        print(f"  Duration: {output_duration:.2f}s (expected: {expected_duration:.2f}s)")
        print("="*50 + "\n")
        
        return True, f"Video processed successfully ({output_duration:.1f}s)"
        
    except subprocess.CalledProcessError as e:
        # FFmpeg command failed
        error_msg = e.stderr if e.stderr else str(e)
        print(f"\n✗ FFmpeg error: {error_msg}")
        return False, f"FFmpeg error: {error_msg[:200]}"
        
    except Exception as e:
        # Other error
        print(f"\n✗ Processing error: {e}")
        return False, f"Processing error: {str(e)}"


# ========================
# FUNCTION: EXTRACT THUMBNAIL
# ========================
def extract_thumbnail(video_path: str, output_path: str, time: float = 1.0) -> bool:
    """
    Extract a frame from video as thumbnail.
    
    Args:
        video_path: Source video
        output_path: Where to save thumbnail
        time: Time in seconds to extract frame from
        
    Returns:
        bool: Success status
    """
    try:
        # FFmpeg command to extract a single frame
        # -ss: Seek to specific time
        # -i: Input video
        # -vframes 1: Extract only 1 frame
        # -q:v 2: Quality (2 = high quality)
        cmd = [
            'ffmpeg',
            '-ss', str(time),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Thumbnail extracted: {output_path}")
        return True
        
    except Exception as e:
        print(f"✗ Thumbnail extraction failed: {e}")
        return False
