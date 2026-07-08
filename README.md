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
```

first run opens a browser tab for spotify oauth. approving it writes a local `.spotify_cache` file so subsequent runs are silent.

## credentials

**spotify** - [developer.spotify.com](https://developer.spotify.com)
- create an app, grab client id + secret
- add `http://127.0.0.1:8888/callback` as redirect uri

**instagram** - meta graph api
- requires a business or creator account
- set `INSTAGRAM_TOKEN` and `INSTAGRAM_USER_ID` in `.env`

## structure

```
main.py        entry point, -v flag
spotify.py     spotify auth, random track pick, spotdl download
display.py     rich terminal output
instagram.py   graph api post (coming soon)
```

## dependencies

- [spotipy](https://github.com/spotipy-dev/spotipy) - spotify api client
- [spotdl](https://github.com/spotDL/spotify-downloader) - mp3 download + metadata
- [rich](https://github.com/Textualize/rich) - terminal formatting
- ffmpeg - required by spotdl (`winget install ffmpeg`)
