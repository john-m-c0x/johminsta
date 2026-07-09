"""instagram.py - post song to instagram via graph api"""

import os
import webbrowser
import requests

from spotify import Song
from display import caption


def _graph(endpoint: str, **kwargs) -> dict:
    token   = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    base    = f"https://graph.instagram.com/{user_id}/{endpoint}"
    result  = requests.post(base, params={"access_token": token}, **kwargs).json()
    if "error" in result:
        raise RuntimeError(f"graph api error on {endpoint}: {result['error']}")
    return result


def post_song(song: Song, dry_run: bool = False) -> None:
    container = _graph(
        "media",
        data={
            "image_url": song["image_url"],
            "caption":   caption(song),
        },
    )
    if dry_run:
        print(f"[dry-run] media container created: {container['id']}")
        print(f"[dry-run] caption:\n{caption(song)}")
        print(f"[dry-run] opening image in browser: {song['image_url']}")
        webbrowser.open(song["image_url"])
        print("[dry-run] skipping media_publish - nothing was posted")
        return
    _graph("media_publish", data={"creation_id": container["id"]})
