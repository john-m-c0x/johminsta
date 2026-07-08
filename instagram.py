"""instagram.py - post song reel to instagram via instagrapi (private/mobile api)

instagrapi logs in as a real instagram client and uploads the local video
file directly - no public hosting needed. this is an unofficial, reverse
engineered api (not the graph api), so it carries a different risk: logging
in or posting from an unfamiliar ip (e.g. a github actions runner) can trip
instagram's automated abuse detection and force a checkpoint/2fa challenge
that blocks the session until resolved manually in the app. reusing the same
persisted session (SESSION_PATH) rather than logging in fresh every run is
the primary mitigation - see README for how that session is bootstrapped.
"""

import os
from pathlib import Path

from instagrapi import Client

from spotify import Song
from display import caption

SESSION_PATH = Path(os.getenv("INSTAGRAM_SESSION_PATH", ".instagrapi_session.json"))


def _client() -> Client:
    username = os.environ["INSTAGRAM_USERNAME"]
    password = os.environ["INSTAGRAM_PASSWORD"]

    cl = Client()
    if SESSION_PATH.exists():
        cl.load_settings(SESSION_PATH)

    try:
        cl.login(username, password)
        cl.get_timeline_feed()
    except Exception:
        cl = Client()
        cl.login(username, password)

    cl.dump_settings(SESSION_PATH)
    return cl


def post_song(song: Song, video_path: Path) -> None:
    cl = _client()
    cl.clip_upload(video_path, caption(song))
