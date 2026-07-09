"""video.py - compose album art + panel screenshot into a reel with the hook audio"""

import subprocess
from pathlib import Path

import requests
from PIL import Image

from spotify import Song

FRAME_W, FRAME_H = 1080, 1920
ART_H            = 1080


def _download_art(song: Song, out_path: Path) -> Path:
    out_path.write_bytes(requests.get(song["image_url"], timeout=10).content)
    return out_path


def _compose_frame(art_path: Path, panel_path: Path, out_path: Path) -> Path:
    frame = Image.new("RGB", (FRAME_W, FRAME_H), "black")

    art = Image.open(art_path).convert("RGB").resize((FRAME_W, ART_H))
    frame.paste(art, (0, 0))

    panel_h = FRAME_H - ART_H
    panel   = Image.open(panel_path).convert("RGB")
    scale   = min(FRAME_W / panel.width, panel_h / panel.height)
    panel   = panel.resize((int(panel.width * scale), int(panel.height * scale)))
    px = (FRAME_W - panel.width) // 2
    py = ART_H + (panel_h - panel.height) // 2
    frame.paste(panel, (px, py))

    frame.save(out_path)
    return out_path


def build_reel(song: Song, panel_png: Path, audio_clip: Path, out_dir: Path) -> Path:
    art_path   = _download_art(song, out_dir / "art.jpg")
    frame_path = _compose_frame(art_path, panel_png, out_dir / "frame.png")
    video_path = out_dir / "reel.mp4"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_path),
            "-i", str(audio_clip),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(video_path),
        ],
        capture_output=True, check=True,
    )
    return video_path
