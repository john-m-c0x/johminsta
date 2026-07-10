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
from video   import Post

POLL_INTERVAL = 5
POLL_TIMEOUT  = 600


def _upload_release_assets(paths: list[Path]) -> list[str]:
    """host each file as an asset on one github release and return their public
    download urls (in the same order) - the graph api fetches media by url."""
    repo = os.environ["GITHUB_REPOSITORY"]
    tag  = f"post-{int(time.time())}"

    subprocess.run(
        [
            "gh", "release", "create", tag, *[str(p) for p in paths],
            "--title", tag,
            "--notes", "auto-generated post",
        ],
        check=True,
    )
    return [
        f"https://github.com/{repo}/releases/download/{tag}/{p.name}"
        for p in paths
    ]


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

    last_status = None
    while time.time() < deadline:
        last_status = requests.get(
            url, params={"fields": "status_code,status", "access_token": token}
        ).json()
        code = last_status.get("status_code")
        print(f"container {container_id} status: {last_status}", flush=True)
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"instagram failed to process video: {last_status}")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(
        f"instagram media container did not finish processing in "
        f"{POLL_TIMEOUT}s (last status: {last_status})"
    )


def _post_reel(song: Song, video_url: str) -> None:
    """single-slide fallback: a square reel that also shows in the feed grid.
    instagram deprecated the plain VIDEO media_type - all standalone video now
    goes through REELS, and share_to_feed keeps it in the main grid."""
    container = _graph(
        "media",
        data={
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       caption(song),
            "share_to_feed": "true",
        },
    )
    _wait_until_ready(container["id"])
    _graph("media_publish", data={"creation_id": container["id"]})


def _post_carousel(song: Song, video_url: str, image_url: str) -> None:
    """two-slide carousel: the album-art video, then the analysis image. each
    child is built with is_carousel_item, then bundled under a CAROUSEL parent.
    carousel video children use media_type VIDEO (REELS isn't allowed here)."""
    children = [
        _graph("media", data={
            "media_type": "VIDEO", "video_url": video_url,
            "is_carousel_item": "true",
        }),
        _graph("media", data={
            "image_url": image_url, "is_carousel_item": "true",
        }),
    ]
    for child in children:
        _wait_until_ready(child["id"])

    parent = _graph("media", data={
        "media_type": "CAROUSEL",
        "children":   ",".join(c["id"] for c in children),
        "caption":    caption(song),
    })
    _wait_until_ready(parent["id"])
    _graph("media_publish", data={"creation_id": parent["id"]})


def post_song(song: Song, post: Post) -> None:
    if post.slide is None:
        [video_url] = _upload_release_assets([post.video])
        _post_reel(song, video_url)
        return

    video_url, image_url = _upload_release_assets([post.video, post.slide])
    _post_carousel(song, video_url, image_url)
