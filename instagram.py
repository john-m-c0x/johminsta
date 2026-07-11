"""instagram.py - post song video to instagram via graph api

the finished mp4 is hosted as a github release asset (the repo is public) so
the graph api has a url it can fetch the video from - there's no local-file
upload path via the simple content publishing flow.
"""

import os
import re
import subprocess
import time
from pathlib import Path

import requests

from spotify import Song
from display import caption
from video   import Post

POLL_INTERVAL    = 5
POLL_TIMEOUT     = 600
POLL_BACKOFF_MAX = 120

# graph api error codes with a known meaning worth a targeted message
RATE_LIMIT_CODE    = 4        # app-level request limit (hourly window)
PUBLISH_QUOTA_CODE = 9        # content-publishing cap (25 posts / 24h)
PUBLISH_QUOTA_SUB  = 2207042


def _upload_release_assets(paths: list[Path], notes: str) -> list[str]:
    """host each file as an asset on one github release and return their public
    download urls (in the same order) - the graph api fetches media by url.
    `notes` should identify the song (name + spotify uri): the releases double
    as the posting history that recently_posted_uris() reads back."""
    repo = os.environ["GITHUB_REPOSITORY"]
    tag  = f"post-{int(time.time())}"

    subprocess.run(
        [
            "gh", "release", "create", tag, *[str(p) for p in paths],
            "--title", tag,
            "--notes", notes,
        ],
        check=True,
    )
    return [
        f"https://github.com/{repo}/releases/download/{tag}/{p.name}"
        for p in paths
    ]


def recently_posted_uris(limit: int = 50) -> set[str]:
    """spotify track uris from the last `limit` post releases - the picker
    excludes these so the same song can't post twice in quick succession.
    returns an empty set outside CI (no GITHUB_REPOSITORY) or on any failure:
    the exclusion is best-effort, never a reason not to post."""
    repo = os.getenv("GITHUB_REPOSITORY")
    if not repo:
        return set()
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/releases?per_page={limit}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return set()
    return set(re.findall(r"spotify:track:\w+", result.stdout))


def _graph(endpoint: str, **kwargs) -> dict:
    token   = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    base    = f"https://graph.instagram.com/{user_id}/{endpoint}"
    result  = requests.post(base, params={"access_token": token}, **kwargs).json()
    if "error" in result:
        _raise_graph_error(result["error"], f"on {endpoint}")
    return result


def _raise_graph_error(err: dict, context: str) -> None:
    """turn a graph api error payload into an exception with an actionable
    message for the failure modes we've actually hit (see the 2026-07-10
    quota and 2026-07-11 rate-limit incidents)."""
    # code 9 / subcode 2207042 is the hard content-publishing cap
    # (25 posts per rolling 24h). retrying cannot help - fail loudly
    # with an actionable message instead of a generic error.
    if err.get("code") == PUBLISH_QUOTA_CODE or err.get("error_subcode") == PUBLISH_QUOTA_SUB:
        raise RuntimeError(
            "instagram publish quota exhausted (25 posts per rolling 24h). "
            "do NOT retry - the window has to clear on its own. "
            f"full error: {err}"
        )
    # code 4 is the app-level request limit (calls per hour, not posts per
    # day). retrying immediately only sustains the limit.
    if err.get("code") == RATE_LIMIT_CODE:
        raise RuntimeError(
            "instagram app-level request limit reached (code 4). wait for the "
            "hourly window to clear before rerunning - retrying immediately "
            f"only sustains the limit. full error {context}: {err}"
        )
    raise RuntimeError(f"graph api error {context}: {err}")


def _publish_quota_remaining() -> int | None:
    """posts left in the rolling 24h content-publishing window, or None when
    the check itself fails (the endpoint isn't available on every account
    type - in that case just proceed and let the publish call decide)."""
    token   = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    try:
        resp = requests.get(
            f"https://graph.instagram.com/{user_id}/content_publishing_limit",
            params={"fields": "quota_usage,config", "access_token": token},
            timeout=10,
        ).json()
        entry = resp["data"][0]
        return entry["config"]["quota_total"] - entry["quota_usage"]
    except Exception:
        return None


def _wait_until_ready(container_id: str) -> None:
    token    = os.getenv("INSTAGRAM_ACCOUNT_TOKEN")
    url      = f"https://graph.instagram.com/{container_id}"
    deadline = time.time() + POLL_TIMEOUT
    delay    = POLL_INTERVAL

    last_status = None
    while time.time() < deadline:
        last_status = requests.get(
            url, params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        ).json()
        print(f"container {container_id} status: {last_status}", flush=True)

        err = last_status.get("error")
        if err:
            # each poll is itself an api call, so polling through a rate
            # limit at POLL_INTERVAL sustains the very limit we're hitting
            # (the 2026-07-11 incident). back off instead, and bail out on
            # anything that isn't a transient rate limit.
            if err.get("code") == RATE_LIMIT_CODE or err.get("is_transient"):
                delay = min(delay * 2, POLL_BACKOFF_MAX)
            else:
                _raise_graph_error(err, f"while polling container {container_id}")
        else:
            delay = POLL_INTERVAL
            code  = last_status.get("status_code")
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise RuntimeError(f"instagram failed to process video: {last_status}")

        # never sleep past the deadline - a backed-off delay could otherwise
        # overshoot it by minutes.
        time.sleep(max(0, min(delay, deadline - time.time())))

    if last_status and "error" in last_status:
        _raise_graph_error(
            last_status["error"],
            f"polling container {container_id} (gave up after {POLL_TIMEOUT}s)",
        )
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


def _post_carousel(song: Song, video_url: str, slide_url: str) -> None:
    """two-slide carousel: the album-art video, then the analysis slide (also a
    video - its audio picks up where slide 1's clip ends, since carousels have
    no shared soundtrack). each child is built with is_carousel_item, then
    bundled under a CAROUSEL parent. carousel video children use media_type
    VIDEO (REELS isn't allowed here)."""
    children = [
        _graph("media", data={
            "media_type": "VIDEO", "video_url": video_url,
            "is_carousel_item": "true",
        }),
        _graph("media", data={
            "media_type": "VIDEO", "video_url": slide_url,
            "is_carousel_item": "true",
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
    # pre-flight: skip the whole upload/publish dance when the 24h publishing
    # quota is already spent - the publish call would only fail at the end.
    remaining = _publish_quota_remaining()
    if remaining is not None:
        print(f"publish quota: {remaining} post(s) left in the 24h window")
        if remaining <= 0:
            raise RuntimeError(
                "instagram publish quota exhausted (25 posts per rolling 24h) - "
                "skipping publish. try again after the window clears."
            )

    notes = f"{song['name']} - {song['artist']}\n{song['uri']}"
    if post.slide is None:
        [video_url] = _upload_release_assets([post.video], notes)
        _post_reel(song, video_url)
        return

    video_url, slide_url = _upload_release_assets([post.video, post.slide], notes)
    _post_carousel(song, video_url, slide_url)
