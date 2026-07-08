"""instagram.py - post song to instagram via graph api"""

import os
import requests
from pathlib import Path

from spotify import Song
from display import caption


TMP_ART = Path.home() / "song" / "cover.jpg"


def _download_art(url: str) -> Path:
    TMP_ART.parent.mkdir(exist_ok=True)
    TMP_ART.write_bytes(requests.get(url, timeout=10).content)
    return TMP_ART


def _graph(endpoint: str, **kwargs) -> dict:
    token   = os.getenv("INSTAGRAM_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    base    = f"https://graph.instagram.com/{user_id}/{endpoint}"
    return requests.post(base, params={"access_token": token}, **kwargs).json()


def post_song(song: Song) -> None:
    container = _graph(
        "media",
        data={
            "image_url": song["image_url"],
            "caption":   caption(song),
        },
    )
    _graph("media_publish", data={"creation_id": container["id"]})
