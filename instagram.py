"""instagram.py - post song reel to instagram via graph api

the finished mp4 is hosted as a github release asset (the repo is public) so
the graph api has a url it can fetch the video from - there's no local-file
upload path for reels via the simple content publishing flow.
"""

import os
import subprocess
import time
import requests
from pathlib import Path

from spotify import Song
from display import caption

POLL_INTERVAL = 5
POLL_TIMEOUT  = 300


def _upload_release_asset(video_path: Path) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]
    tag  = f"reel-{int(time.time())}"

    subprocess.run(
        [
            "gh", "release", "create", tag, str(video_path),
            "--title", tag,
            "--notes", "auto-generated reel",
        ],
        check=True,
    )
    return f"https://github.com/{repo}/releases/download/{tag}/{video_path.name}"


def _graph(endpoint: str, **kwargs) -> dict:
    token   = os.getenv("INSTAGRAM_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    base    = f"https://graph.instagram.com/{user_id}/{endpoint}"
    return requests.post(base, params={"access_token": token}, **kwargs).json()


def _wait_until_ready(container_id: str) -> None:
    token    = os.getenv("INSTAGRAM_TOKEN")
    url      = f"https://graph.instagram.com/{container_id}"
    deadline = time.time() + POLL_TIMEOUT

    while time.time() < deadline:
        status = requests.get(
            url, params={"fields": "status_code", "access_token": token}
        ).json()
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"instagram failed to process reel: {status}")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError("instagram reel container did not finish processing in time")


def post_song(song: Song, video_path: Path) -> None:
    video_url = _upload_release_asset(video_path)

    container = _graph(
        "media",
        data={
            "media_type": "REELS",
            "video_url":  video_url,
            "caption":    caption(song),
        },
    )
    _wait_until_ready(container["id"])
    _graph("media_publish", data={"creation_id": container["id"]})
