# random liked song

pulls a random song from your spotify liked library, finds its musical hook, and posts it to instagram daily as a reel (album art + song info + a 30s audio clip).

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

**instagram** - [instagrapi](https://github.com/subzeroid/instagrapi) (private/mobile api, not the graph api)
- no app/business account needed - just the account's own username + password
- set `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` in `.env`
- first run logs in and writes a local `.instagrapi_session.json` so subsequent runs reuse the same session instead of logging in fresh each time (see the github actions section for why this matters)

## structure

```
main.py        entry point, -v flag
spotify.py     spotify auth, random track pick, spotdl download
chorus.py      finds the song's hook via audio self-similarity (pychorus)
display.py     rich terminal output, caption, panel screenshot export
video.py       composes the reel (album art + panel screenshot + hook clip)
instagram.py   instagrapi post (reels)
```

## dependencies

- [spotipy](https://github.com/spotipy-dev/spotipy) - spotify api client
- [spotdl](https://github.com/spotDL/spotify-downloader) - mp3 download + metadata
- [pychorus](https://github.com/vivjay30/pychorus) - finds the chorus/hook of a track
- [rich](https://github.com/Textualize/rich) - terminal formatting + panel screenshot
- [cairosvg](https://cairosvg.org/) - renders the panel screenshot (svg -> png)
- [Pillow](https://python-pillow.org/) - composes the reel frame
- ffmpeg - required by spotdl and for muxing the reel
- [instagrapi](https://github.com/subzeroid/instagrapi) - posts the reel via instagram's private/mobile api

## running on github actions

`.github/workflows/post.yml` runs the bot daily (and via manual `workflow_dispatch`). Unlike the graph api, `instagrapi` uploads the local `.mp4` directly - no public hosting step needed.

**required repo secrets** (Settings -> Secrets and variables -> Actions):

- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` - same as local setup
- `SPOTIFY_REFRESH_TOKEN` - see below, needed since the runner can't do the interactive browser oauth flow
- `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` - same as local setup
- `INSTAGRAM_SESSION_B64` - see below, needed so the runner doesn't log in as a brand-new device every run

### getting `SPOTIFY_REFRESH_TOKEN`

Run the bot locally once (`python main.py`) to complete the interactive oauth flow, then read the refresh token out of the generated cache file:

```powershell
python -c "import json; print(json.load(open('.spotify_cache'))['refresh_token'])"
```

Paste that value into the `SPOTIFY_REFRESH_TOKEN` secret. The workflow reconstructs a minimal `.spotify_cache` from this secret before each run, with `expires_at` forced to `0` so spotipy refreshes it silently - no browser step ever runs on the runner.

### getting `INSTAGRAM_SESSION_B64`

Run the bot locally once from your own machine so the *first* login to this "device" happens from an ip/network instagram already associates with your account, rather than cold inside actions. This writes `.instagrapi_session.json`. Base64-encode it and paste the result into the `INSTAGRAM_SESSION_B64` secret:

```powershell
python -c "import base64; print(base64.b64encode(open('.instagrapi_session.json','rb').read()).decode())"
```

The workflow decodes this back to `.instagrapi_session.json` before each run so it reuses the same session/device fingerprint instead of looking like a new login every time.

### token/session refresh (manual)

Nothing here is auto-refreshed by the workflow:

- **Instagram session**: if a run ever fails with a challenge/checkpoint or login error, instagram has likely flagged the session - resolve the checkpoint manually in the app or website, then redo the local login and update `INSTAGRAM_SESSION_B64`.
- **Spotify**: the refresh token itself is long-lived and typically doesn't need rotating unless it's revoked (e.g. you changed your spotify password or revoked app access) - if runs start failing on the spotify step, redo the local oauth flow and update the secret.

### known caveat: spotdl on shared runners

`spotdl` resolves downloads via a YouTube/YouTube Music search, and GitHub-hosted runners share IPs across many users - YouTube occasionally rate-limits or blocks these IPs ("sign in to confirm you're not a bot"). The existing retry loop in `spotify.py` (`max_retries`, tries a different random song each time) is the only mitigation for now. If this becomes a persistent problem, a self-hosted runner would sidestep it.

### known caveat: instagrapi is unofficial

`instagrapi` emulates instagram's private mobile-app api rather than using the sanctioned graph api, which is against instagram's terms of service. Logging in or posting from an unfamiliar ip (like a github actions runner) can trip instagram's automated abuse detection and force a checkpoint/2fa challenge, which will block the automation until you resolve it manually in the app - there's no way to solve that from an unattended workflow run. Reusing the same persisted session every run (rather than logging in fresh) is the main mitigation, but this risk can't be fully eliminated. If reliability matters more than convenience here, the graph api path (see git history) doesn't carry this risk, at the cost of the business-account/app-review friction that motivated this switch.
