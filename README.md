# random liked song

pulls a random song from your spotify liked library, downloads it as an mp3, renders it into a vertical reel (album art + audio), and posts it to instagram daily.

## setup

```powershell
pip install -r requirements.txt
cp .env.example .env
```

fill in `.env` with your credentials (see below).

## usage

```powershell
python main.py       # run silently
python main.py -v    # verbose - shows spotdl progress, ffmpeg output, and upload status
```

first run opens a browser tab for spotify oauth. approving it writes a local `.spotify_cache` file so subsequent runs are silent.

## credentials

**spotify** - [developer.spotify.com](https://developer.spotify.com)
- create an app, grab client id + secret
- add `http://127.0.0.1:8888/callback` as redirect uri

**instagram** - meta graph api
- requires a business or creator account, connected via instagram login (not facebook login)
- set `INSTAGRAM_TOKEN` and `INSTAGRAM_USER_ID` in `.env`

## how the reel gets posted

1. `video.py` downloads the album art and combines it with the mp3 into a 1080x1920 mp4 (blurred art fills the frame, full-res art centered on top), capped at 90s - the window instagram requires for a reel to be eligible for the reels tab.
2. `instagram.py` creates a `REELS` container with `upload_type=resumable`, uploads the video bytes directly to `rupload.facebook.com` (no public hosting needed), polls the container until instagram finishes processing it, then publishes.

## structure

```
main.py        entry point, -v flag
spotify.py     spotify auth, random track pick, spotdl download
display.py     rich terminal output, caption text
video.py       render album art + audio into a reel (ffmpeg)
instagram.py   graph api: resumable upload, poll, publish
```

## dependencies

- [spotipy](https://github.com/spotipy-dev/spotipy) - spotify api client
- [spotdl](https://github.com/spotDL/spotify-downloader) - mp3 download + metadata
- [rich](https://github.com/Textualize/rich) - terminal formatting
- ffmpeg - required by spotdl and by `video.py` (`winget install ffmpeg`)
