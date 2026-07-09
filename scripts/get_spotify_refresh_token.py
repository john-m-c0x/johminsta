"""get_spotify_refresh_token.py - mint a fresh SPOTIFY_REFRESH_TOKEN

Run this locally (it opens a browser). The refresh token it prints is what CI
uses to authenticate without an interactive login. A refresh token is invalid
in CI ("invalid_grant: Invalid refresh token") when it was minted under a
different app than the SPOTIFY_CLIENT_ID/SECRET set in the GitHub secrets, when
it was revoked, or when a newer authorization rotated it out. Re-running this
with the *same* client id/secret you store in CI fixes all three.

usage:
  SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy python scripts/get_spotify_refresh_token.py

or put SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in a .env file first.

Then copy the printed token into the SPOTIFY_REFRESH_TOKEN GitHub secret, and
make sure SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET secrets match the values
used here.
"""

import os
import sys

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Must match spotify.py exactly - a token minted with a different redirect_uri
# or scope will not authenticate the CI client.
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-library-read"


def main() -> None:
    load_dotenv()

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET first "
            "(env vars or a .env file). These MUST be the same values you "
            "store in the GitHub secrets."
        )

    print(f"Using client id: {client_id[:6]}...")
    print(f"Redirect URI:    {REDIRECT_URI}")
    print(
        "\nMake sure this exact redirect URI is registered in your Spotify app "
        "at https://developer.spotify.com/dashboard -> your app -> Settings.\n"
    )

    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=True,
        cache_handler=None,  # don't write a cache file - we just want the token
    )

    # Runs the full interactive flow: opens a browser, you approve, paste the
    # redirected URL back if it can't auto-capture it.
    token_info = auth.get_access_token(as_dict=True)
    refresh_token = token_info["refresh_token"]

    print("\n" + "=" * 60)
    print("SPOTIFY_REFRESH_TOKEN (set this as a GitHub secret):\n")
    print(refresh_token)
    print("=" * 60)


if __name__ == "__main__":
    main()
