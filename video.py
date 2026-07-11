"""video.py - compose the album art into a square video post with the hook audio"""

import subprocess
from pathlib import Path
from typing import NamedTuple

import requests
from PIL import Image

from spotify import Song
from slide   import build_slide

FRAME_SIZE = 1080


class Post(NamedTuple):
    """the carousel's slides: the album-art video and the analysis video."""
    video: Path
    slide: Path | None  # None when the track has no audio-features to show


def _download_art(song: Song, out_path: Path) -> Path:
    out_path.write_bytes(requests.get(song["image_url"], timeout=10).content)
    return out_path


def _compose_frame(art_path: Path, out_path: Path) -> Path:
    """scale the (square) album art up/down to the post's frame size."""
    art = Image.open(art_path).convert("RGB").resize((FRAME_SIZE, FRAME_SIZE))
    art.save(out_path)
    return out_path


def _still_video(frame_path: Path, audio_clip: Path, out_path: Path) -> Path:
    """encode a still frame + audio clip into an mp4. -t caps the output at
    60s exactly: -shortest alone overshoots by a GOP or two on looped stills,
    and instagram rejects carousel video children longer than 60s."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_path),
            "-i", str(audio_clip),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest", "-t", "60",
            str(out_path),
        ],
        capture_output=True, check=True,
    )
    return out_path


def build_post(song: Song, audio_clip: Path, out_dir: Path,
               cont_clip: Path | None = None) -> Post:
    art_path   = _download_art(song, out_dir / "art.jpg")
    frame_path = _compose_frame(art_path, out_dir / "frame.png")
    video_path = _still_video(frame_path, audio_clip, out_dir / "post.mp4")

    # slide 2: the track's audio-features as a datamosh'd json screenshot,
    # rendered as a video so it carries audio - carousels have no shared
    # soundtrack, so each slide brings its own. its clip continues right where
    # slide 1's hook ends, so the song keeps playing across the swipe.
    slide_path = None
    if song["features"]:
        slide_png  = build_slide(song["features"], out_dir / "slide.png",
                                 name=song["name"])
        slide_path = _still_video(slide_png, cont_clip or audio_clip,
                                  out_dir / "slide.mp4")

    return Post(video=video_path, slide=slide_path)
