#!/usr/bin/env python3

import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================

# Working directory
INPUT_DIR = r"C:\BR_Videos"
OUTPUT_DIR = r"C:\BR_Videos\Clipped"

# FFmpeg executables
FFMPEG_EXE = r"C:\ffmpeg\bin\ffmpeg.exe"

# Supported video extensions
VIDEO_EXTENSIONS = [".mp4", ".mov", ".mkv"]

# Segment duration (10 minutes)
SEGMENT_DURATION = 600

# Use NVIDIA NVENC encoder
USE_NVENC = False

# Enable segmentation
ENABLE_SEGMENTING = True

# Delete intermediate captioned video after segmentation
DELETE_INTERMEDIATE_FILE = False

# ============================================================
# Command Runner
# ============================================================

def run_command(command):

    print("\n====================================================")
    print("Running Command:")
    print("====================================================")
    print(" ".join(command))
    print()

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print("====================================================")
        print("ERROR")
        print("====================================================")
        print(result.stderr)

        return None

    return result


# ============================================================
# Rename Files to Safe Names
# ============================================================

def sanitize_and_rename_files(video_file):

    """
    Example:

    Original:
    Cockpit (May 08, 2026 - 21꞉50꞉29 GMT+0) #45a7850b.mp4

    Renamed:
    Cockpit_20260508_215029.mp4
    Cockpit_20260508_215029.ass
    """

    original_stem = video_file.stem

    ass_file = video_file.with_suffix(".ass")

    # Extract timestamp from parentheses
    match = re.search(r"\((.*?)\)", original_stem)

    if not match:

        print("Could not parse timestamp:")
        print(video_file.name)

        return None, None, None

    timestamp_text = match.group(1)

    # Replace Unicode colon
    timestamp_text = timestamp_text.replace("꞉", ":")

    # Remove timezone text
    timestamp_text = timestamp_text.replace(" GMT+0", "")

    try:

        dt = datetime.strptime(
            timestamp_text,
            "%b %d, %Y - %H:%M:%S"
        )

    except Exception as e:

        print("Failed to parse timestamp:")
        print(timestamp_text)
        print(e)

        return None, None, None

    timestamp_str = dt.strftime("%Y%m%d_%H%M%S")

    # Extract text before parentheses
    prefix = original_stem.split("(")[0].strip()

    safe_base_name = f"{prefix}_{timestamp_str}"

    new_video = video_file.with_name(
        safe_base_name + video_file.suffix
    )

    new_ass = ass_file.with_name(
        safe_base_name + ".ass"
    )

    # Rename video
    if video_file != new_video:

        print("\nRenaming video:")
        print(f"  {video_file.name}")
        print(f"  -> {new_video.name}")

        video_file.rename(new_video)

    # Rename subtitle
    if ass_file.exists() and ass_file != new_ass:

        print("\nRenaming subtitle:")
        print(f"  {ass_file.name}")
        print(f"  -> {new_ass.name}")

        ass_file.rename(new_ass)

    return new_video, new_ass, dt


# ============================================================
# Burn ASS Subtitles
# ============================================================

def burn_ass_subtitles(video_path, ass_path, output_path):

    video_codec = "h264_nvenc" if USE_NVENC else "libx264"

    # Convert Windows path for FFmpeg filter syntax
    safe_ass_path = (
        ass_path
        .as_posix()
        .replace(":", r"\:")
    )

    vf_filter = f"ass='{safe_ass_path}'"

    command = [
        FFMPEG_EXE,
        "-y",
        "-i", str(video_path),
        "-vf", vf_filter,
        "-c:v", video_codec,
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "copy",
        str(output_path)
    ]

    result = run_command(command)

    return result is not None


# ============================================================
# Segment Video
# ============================================================

def segment_video_with_timestamps(
    input_video,
    output_dir,
    base_name,
    start_datetime
):

    output_dir.mkdir(parents=True, exist_ok=True)

    temp_pattern = output_dir / "temp_%03d.mp4"

    command = [
        FFMPEG_EXE,
        "-y",
        "-i", str(input_video),
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(SEGMENT_DURATION),
        "-reset_timestamps", "1",
        str(temp_pattern)
    ]

    result = run_command(command)

    if result is None:
        return False

    segment_files = sorted(
        output_dir.glob("temp_*.mp4")
    )

    for index, segment_file in enumerate(segment_files):

        segment_start = start_datetime + timedelta(
            seconds=index * SEGMENT_DURATION
        )

        timestamp_str = segment_start.strftime(
            "%Y%m%d_%H%M%S"
        )

        new_name = f"{base_name.split('_')[0]}_{timestamp_str}.mp4"

        new_path = output_dir / new_name

        print("\nRenaming segment:")
        print(f"  {segment_file.name}")
        print(f"  -> {new_name}")

        segment_file.rename(new_path)

    return True


# ============================================================
# Main Processing Loop
# ============================================================

def process_videos():

    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for file in input_dir.iterdir():

        if file.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        print("\n====================================================")
        print(f"Processing: {file.name}")
        print("====================================================")

        # ----------------------------------------------------
        # Rename files safely
        # ----------------------------------------------------

        video_file, ass_file, creation_time = (
            sanitize_and_rename_files(file)
        )

        if video_file is None:
            continue

        if not ass_file.exists():

            print("\nMissing matching .ass file:")
            print(ass_file)

            continue

        base_name = video_file.stem

        # ----------------------------------------------------
        # Burn subtitles
        # ----------------------------------------------------

        captioned_output = (
            output_dir /
            f"{base_name}_captioned.mp4"
        )

        print("\nBurning subtitles...")

        success = burn_ass_subtitles(
            video_file,
            ass_file,
            captioned_output
        )

        if not success:

            print("Subtitle burn failed.")
            continue

        print("\nCaptioned video created:")
        print(captioned_output)

        # ----------------------------------------------------
        # Segment video
        # ----------------------------------------------------

        if ENABLE_SEGMENTING:

            segment_dir = output_dir 

            print("\nSegmenting video...")

            success = segment_video_with_timestamps(
                captioned_output,
                segment_dir,
                base_name,
                creation_time
            )

            if success:
                print("\nSegmenting complete.")
            else:
                print("\nSegmenting failed.")

        # ----------------------------------------------------
        # Cleanup
        # ----------------------------------------------------

        if (
            DELETE_INTERMEDIATE_FILE and
            captioned_output.exists()
        ):

            print("\nDeleting intermediate file:")
            print(captioned_output)

            captioned_output.unlink()

    print("\n====================================================")
    print("ALL PROCESSING COMPLETE")
    print("====================================================")


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    process_videos()

