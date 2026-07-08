"""chorus.py - find the song's musical 'hook' via audio self-similarity (pychorus)"""

import subprocess
from pathlib import Path

from pychorus import find_and_output_chorus


def _ffmpeg_trim(mp3_path: Path, out_path: Path, start: float, clip_length: int) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(mp3_path),
            "-t", str(clip_length),
            str(out_path),
        ],
        capture_output=True, check=True,
    )


def find_hook_clip(mp3_path: Path, out_path: Path, clip_length: int = 30) -> Path:
    """
    locate the chorus via audio self-similarity and write a clip_length-second
    clip to out_path. falls back to the first clip_length seconds if no chorus
    is found (e.g. very short tracks) so one odd track can't break the run.
    """
    chorus_start = find_and_output_chorus(str(mp3_path), str(out_path), clip_length)
    if chorus_start is None:
        _ffmpeg_trim(mp3_path, out_path, start=0, clip_length=clip_length)
    return out_path
