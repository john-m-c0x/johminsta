"""video.py - render a song into a vertical reel (album art + audio) via ffmpeg"""

import subprocess
import requests
from pathlib import Path

from spotify import Song


ART_PATH  = Path.home() / "song" / "cover.jpg"
REEL_PATH = Path.home() / "song" / "reel.mp4"

# instagram only surfaces reels in the reels tab between 5s-90s at 9:16
MAX_DURATION_SECONDS = 90
WIDTH, HEIGHT        = 1080, 1920


def _download_art(url: str) -> Path:
    ART_PATH.parent.mkdir(exist_ok=True)
    ART_PATH.write_bytes(requests.get(url, timeout=10).content)
    return ART_PATH


def build_reel(song: Song, verbose: bool = False) -> Path:
    """combine album art + mp3 into a 9:16 video: blurred art fills the
    frame, the full-resolution art is centered on top."""
    art = _download_art(song["image_url"])

    filter_complex = (
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},gblur=sigma=20[bg];"
        f"[0:v]scale={WIDTH}:{WIDTH}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(art),
            "-i",           str(song["mp3_path"]),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(MAX_DURATION_SECONDS),
            "-shortest",
            "-movflags", "+faststart",
            str(REEL_PATH),
        ],
        capture_output=True, text=True,
    )
    if verbose:
        print(result.stderr)
    if result.returncode != 0 or not REEL_PATH.exists():
        raise RuntimeError(f"ffmpeg failed to build reel:\n{result.stderr}")

    return REEL_PATH
