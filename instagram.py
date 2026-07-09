"""instagram.py - post song video to instagram via graph api

the finished mp4 is hosted as a github release asset (the repo is public) so
the graph api has a url it can fetch the video from - there's no local-file
upload path via the simple content publishing flow.
"""

import os
import subprocess
import time
from pathlib import Path

import requests

from spotify import Song
from display import caption

POLL_INTERVAL = 5
POLL_TIMEOUT  = 300


def _upload_release_asset(video_path: Path) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]
    tag  = f"post-{int(time.time())}"

    subprocess.run(
        [
            "gh", "release", "create", tag, str(video_path),
            "--title", tag,
            "--notes", "auto-generated post",
        ],
        check=True,
    )
    return f"https://github.com/{repo}/releases/download/{tag}/{video_path.name}"


def _graph(endpoint: str, **kwargs) -> dict:
    token   = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    base    = f"https://graph.instagram.com/{user_id}/{endpoint}"
    result  = requests.post(base, params={"access_token": token}, **kwargs).json()
    if "error" in result:
        raise RuntimeError(f"graph api error on {endpoint}: {result['error']}")
    return result


def _wait_until_ready(container_id: str) -> None:
    token    = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
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
            raise RuntimeError(f"instagram failed to process video: {status}")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError("instagram media container did not finish processing in time")


def post_song(song: Song, video_path: Path) -> None:
    video_url = _upload_release_asset(video_path)

    container = _graph(
        "media",
        data={
            "media_type": "VIDEO",
            "video_url":  video_url,
            "caption":    caption(song),
        },
    )
    _wait_until_ready(container["id"])
    _graph("media_publish", data={"creation_id": container["id"]})
