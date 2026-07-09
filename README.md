# random liked song

pulls a random song from your spotify liked library, downloads it as an mp3, and posts it to instagram daily.

## setup

```powershell
pip install -r requirements.txt
cp .env.example .env
```

fill in `.env` with your credentials (see below).

## usage

```powershell
python main.py       # run silently
python main.py -v    # verbose - shows spotdl progress and retry attempts
python main.py -d    # dry run - builds the ig media container but skips publish
```

first run opens a browser tab for spotify oauth. approving it writes a local `.spotify_cache` file so subsequent runs are silent.

## credentials

**spotify** - [developer.spotify.com](https://developer.spotify.com)
- create an app, grab client id + secret
- add `http://127.0.0.1:8888/callback` as redirect uri

**instagram** - meta graph api
- requires a business or creator account
- set `INSTAGRAM_ACCOUNT_TOKEN` and `INSTAGRAM_USER_ID` in `.env`

## github actions

`.github/workflows/post.yml` runs the poster on a daily cron, headless.

repo secrets needed:
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` - same as local
- `SPOTIFY_REFRESH_TOKEN` - the `refresh_token` field from your local `.spotify_cache` (spotify's oauth needs one interactive browser login; the refresh token from that login doesn't expire and lets CI skip the browser step entirely)
- `INSTAGRAM_ACCOUNT_TOKEN`, `INSTAGRAM_USER_ID` - same as local
- `GH_PAT` - a personal access token with `repo` scope (or fine-grained "Secrets: write" on this repo), used by `scripts/refresh_ig_token.py` to write the refreshed instagram token back as a secret each run so it never hits its 60-day expiry unattended. optional - without it the workflow still refreshes and uses the token for that run, it just won't persist for next time.

## structure

```
main.py                          entry point, -v/-d flags
spotify.py                       spotify auth, random track pick, spotdl download
display.py                       rich terminal output
instagram.py                     graph api post
scripts/refresh_ig_token.py      extends the instagram token, used by the workflow
```

## dependencies

- [spotipy](https://github.com/spotipy-dev/spotipy) - spotify api client
- [spotdl](https://github.com/spotDL/spotify-downloader) - mp3 download + metadata
- [rich](https://github.com/Textualize/rich) - terminal formatting
- ffmpeg - required by spotdl (`winget install ffmpeg`)
