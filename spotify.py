"""spotify.py - pick a random liked song and download it via spotdl"""

import os
import random
import subprocess
import spotipy
from mutagen.mp3    import MP3
from pathlib        import Path
from spotipy.oauth2 import SpotifyOAuth
from typing         import TypedDict

# reject a download whose length strays from the spotify track by more than
# this - catches spotdl grabbing an hour-long mix/compilation for a 3min song.
# generous enough to allow a different master or a few seconds of silence.
DURATION_TOLERANCE_S = 20
DURATION_TOLERANCE_PCT = 0.15


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


def _probe_duration(mp3_path: Path) -> float | None:
    """length of the mp3 in seconds, or None if the file is unreadable/corrupt."""
    try:
        length = MP3(mp3_path).info.length
    except Exception:
        return None
    return length if length and length > 0 else None


def _download(uri: str, out_dir: Path, expected_s: float, verbose: bool) -> Path:
    # clear stale mp3s so a prior (or rejected) download can't be mistaken for
    # this one when we glob for the result below.
    for stale in out_dir.glob("*.mp3"):
        stale.unlink()

    url    = f"https://open.spotify.com/track/{uri.split(':')[-1]}"
    result = subprocess.run(
        [
            "spotdl", url,
            "--audio",  "youtube", "youtube-music",
            "--output", str(out_dir),
            # no --dont-filter-results: let spotdl match candidates against the
            # spotify track's own title/artist/duration instead of grabbing the
            # first raw search hit, which can be an hour-long mix or - worse,
            # since it can share the right length - a completely different song.
        ],
        capture_output=True, text=True,
    )
    if verbose:
        print(result.stdout)
    mp3s = list(out_dir.glob("*.mp3"))
    if not mp3s or "LookupError" in result.stdout + result.stderr:
        raise LookupError("spotdl could not find track")

    # a single-track url should yield exactly one file; more than one means we
    # can't tell which is the intended track, so treat it as a failed download.
    if len(mp3s) > 1:
        for f in mp3s:
            f.unlink()
        raise LookupError(f"expected one mp3, got {len(mp3s)}")

    mp3      = mp3s[0]
    actual_s = _probe_duration(mp3)
    if actual_s is None:
        if verbose:
            print("  ! rejecting unreadable/corrupt download")
        mp3.unlink()
        raise LookupError("downloaded file is corrupt or unreadable")

    tolerance = max(DURATION_TOLERANCE_S, expected_s * DURATION_TOLERANCE_PCT)
    if abs(actual_s - expected_s) > tolerance:
        if verbose:
            print(f"  ! rejecting {actual_s:.0f}s file (expected ~{expected_s:.0f}s)")
        mp3.unlink()
        raise LookupError("downloaded audio length does not match spotify track")
    return mp3


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
                mp3_path=_download(
                    track["uri"], out_dir, track["duration_ms"] / 1000, verbose
                ),
            )
        except LookupError:
            if verbose:
                print(f"  ? not found, retrying...")

    raise RuntimeError(f"could not find a downloadable track after {max_retries} attempts")
