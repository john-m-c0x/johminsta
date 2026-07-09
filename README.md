# random liked song

pulls a random song from your spotify liked library, finds its musical hook, and posts it to instagram daily as a reel (album art + song info panel + a 30s audio clip).

## setup

```powershell
pip install -r requirements.txt
```

fill in `.env` with your credentials (see below).

## usage

```powershell
python main.py       # run silently
python main.py -v    # verbose - shows spotdl progress and retry attempts
```

first run opens a browser tab for spotify oauth. approving it writes a local `.spotify_cache` file so subsequent runs are silent.

## credentials

**spotify** - [developer.spotify.com](https://developer.spotify.com)
- create an app, grab client id + secret
- add `http://127.0.0.1:8888/callback` as redirect uri

**instagram** - meta graph api
- requires a business or creator account
- set `INSTAGRAM_ACCOUNT_TOKEN` and `INSTAGRAM_USER_ID` in `.env`

## structure

```
main.py                          entry point, -v flag
spotify.py                       spotify auth, random track pick, spotdl download
chorus.py                        finds the song's hook/hype moment (energy-based)
display.py                       rich terminal output, caption, panel screenshot export
video.py                         composes the reel (album art + panel screenshot + hook clip)
instagram.py                     graph api post (reels), hosts the clip as a github release
scripts/refresh_ig_token.py      extends the instagram token, used by the workflow
```

## dependencies

- [spotipy](https://github.com/spotipy-dev/spotipy) - spotify api client
- [spotdl](https://github.com/spotDL/spotify-downloader) - mp3 download + metadata
- [pydub](https://github.com/jiaaro/pydub) - energy-based hook/chorus clip detection
- [rich](https://github.com/Textualize/rich) - terminal formatting + panel screenshot
- [cairosvg](https://cairosvg.org/) - renders the panel screenshot (svg -> png)
- [Pillow](https://python-pillow.org/) - composes the reel frame
- ffmpeg - required by spotdl and for muxing the reel
- [gh cli](https://cli.github.com/) - used to upload the reel as a github release asset (preinstalled on github-hosted runners)

## github actions

`.github/workflows/post.yml` runs the bot daily (and via manual `workflow_dispatch`), headless. Instagram's Graph API needs a public URL to fetch the reel video from, so the workflow uploads each generated `.mp4` as a GitHub Release asset (the repo must be public) and passes that URL to the API - no third-party hosting needed.

**required repo secrets** (Settings -> Secrets and variables -> Actions):

- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` - same as local
- `SPOTIFY_REFRESH_TOKEN` - the `refresh_token` field from your local `.spotify_cache` (spotify's oauth needs one interactive browser login; the refresh token from that login doesn't expire and lets CI skip the browser step entirely - `spotify.py` picks it up directly via an in-memory cache handler, no file reconstruction needed)
- `INSTAGRAM_ACCOUNT_TOKEN`, `INSTAGRAM_USER_ID` - same as local
- `GH_PAT` - a personal access token with `repo` scope (or fine-grained "Secrets: write" on this repo), used by `scripts/refresh_ig_token.py` to write the refreshed instagram token back as a secret each run so it never hits its 60-day expiry unattended. optional - without it the workflow still refreshes and uses the token for that run, it just won't persist for next time.

### getting `SPOTIFY_REFRESH_TOKEN`

Run the bot locally once (`python main.py`) to complete the interactive oauth flow, then read the refresh token out of the generated cache file:

```powershell
python -c "import json; print(json.load(open('.spotify_cache'))['refresh_token'])"
```

Paste that value into the `SPOTIFY_REFRESH_TOKEN` secret.

### token refresh

- **Instagram**: the long-lived token expires roughly every 60 days. `scripts/refresh_ig_token.py` extends it and persists the new value back as the `INSTAGRAM_ACCOUNT_TOKEN` secret on every scheduled run (requires `GH_PAT`), so it never expires unattended.
- **Spotify**: the refresh token itself is long-lived and typically doesn't need rotating unless it's revoked (e.g. you changed your spotify password or revoked app access) - if runs start failing on the spotify step, redo the local oauth flow and update the secret.

### known caveat: spotdl on shared runners

`spotdl` resolves downloads via a YouTube/YouTube Music search, and GitHub-hosted runners share IPs across many users - YouTube occasionally rate-limits or blocks these IPs ("sign in to confirm you're not a bot"). The existing retry loop in `spotify.py` (`max_retries`, tries a different random song each time) is the only mitigation for now. If this becomes a persistent problem, a self-hosted runner would sidestep it.
