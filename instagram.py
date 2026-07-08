"""instagram.py - render a reel and publish it via the instagram graph api

reels are uploaded with the resumable upload protocol (rupload.facebook.com)
so the video never needs to be hosted anywhere public:

  1. create a REELS container (upload_type=resumable)
  2. upload the video bytes to rupload.facebook.com
  3. poll the container until instagram finishes processing it
  4. publish the container
"""

import os
import time
import requests
from pathlib import Path

from spotify import Song
from display import caption
from video   import build_reel


API_VERSION      = "v21.0"
POLL_INTERVAL_S  = 5
POLL_TIMEOUT_S   = 300


def _graph(method: str, path: str, **params) -> dict:
    token = os.getenv("INSTAGRAM_TOKEN")
    url   = f"https://graph.instagram.com/{path}"
    resp  = requests.request(
        method, url, params={**params, "access_token": token}, timeout=30
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"instagram api error on {path}: {data['error']}")
    return data


def _create_container(song: Song) -> str:
    user_id = os.getenv("INSTAGRAM_USER_ID")
    data = _graph(
        "POST", f"{user_id}/media",
        media_type="REELS",
        upload_type="resumable",
        caption=caption(song),
    )
    return data["id"]


def _upload_video(container_id: str, video_path: Path) -> None:
    token       = os.getenv("INSTAGRAM_TOKEN")
    video_bytes = video_path.read_bytes()
    resp = requests.post(
        f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}/{container_id}",
        headers={
            "Authorization": f"OAuth {token}",
            "offset":        "0",
            "file_size":     str(len(video_bytes)),
        },
        data=video_bytes,
        timeout=120,
    )
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"instagram upload failed: {data}")


def _wait_until_ready(container_id: str, verbose: bool) -> None:
    elapsed = 0
    while elapsed < POLL_TIMEOUT_S:
        status = _graph("GET", container_id, fields="status_code")["status_code"]
        if verbose:
            print(f"  container status: {status}")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"instagram failed to process reel: {status}")
        time.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
    raise TimeoutError("instagram reel processing timed out")


def _publish(container_id: str) -> None:
    user_id = os.getenv("INSTAGRAM_USER_ID")
    _graph("POST", f"{user_id}/media_publish", creation_id=container_id)


def post_song(song: Song, verbose: bool = False) -> None:
    video_path   = build_reel(song, verbose=verbose)
    container_id = _create_container(song)
    _upload_video(container_id, video_path)
    _wait_until_ready(container_id, verbose=verbose)
    _publish(container_id)
