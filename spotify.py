"""spotify.py - pick a random liked song and download it via spotdl"""

import os
import random
import subprocess
import spotipy
from pathlib        import Path
from spotipy.oauth2 import SpotifyOAuth
from typing         import TypedDict


class Song(TypedDict):
    name:     str
    artist:   str
    album:    str
    uri:      str
    mp3_path: Path


def _client() -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-library-read",
        cache_path=".spotify_cache",
    ))


def _random_track(sp: spotipy.Spotify) -> dict:
    results = sp.current_user_saved_tracks(
        limit=50, offset=random.randint(0, 1000)
    )
    return random.choice(results["items"])["track"]


def _download(uri: str, out_dir: Path, verbose: bool) -> Path:
    url    = f"https://open.spotify.com/track/{uri.split(':')[-1]}"
    result = subprocess.run(
        [
            "spotdl", url,
            "--audio",            "youtube", "youtube-music",
            "--output",           str(out_dir),
            "--search-query",     "{title} {artists} official audio",
            "--dont-filter-results",
        ],
        capture_output=True, text=True,
    )
    if verbose:
        print(result.stdout)
    mp3s = list(out_dir.glob("*.mp3"))
    if not mp3s or "LookupError" in result.stdout + result.stderr:
        raise LookupError("spotdl could not find track")
    return mp3s[0]


def get_random_liked_song(
    out_dir: Path = Path.home() / "song",
    verbose: bool = False,
    max_retries: int = 5,
) -> Song:
    out_dir.mkdir(exist_ok=True)
    sp = _client()

    for attempt in range(1, max_retries + 1):
        track  = _random_track(sp)
        name   = track["name"]
        artist = track["artists"][0]["name"]
        if verbose:
            print(f"[{attempt}/{max_retries}] trying: {name} - {artist}")
        try:
            return Song(
                name=name,
                artist=artist,
                album=track["album"]["name"],
                uri=track["uri"],
                mp3_path=_download(track["uri"], out_dir, verbose),
            )
        except LookupError:
            if verbose:
                print(f"  ? not found, retrying...")

    raise RuntimeError(f"could not find a downloadable track after {max_retries} attempts")
