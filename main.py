"""
random liked song

pulls one song at random from your spotify liked library, finds its hook,
and posts it to instagram as a reel (album art + song info + 30s audio clip).

  spotify.py     auth, fetch, download
  chorus.py      find the song's hook (pychorus)
  display.py     terminal output, caption, panel screenshot
  video.py       compose the reel
  instagram.py   graph api, post

usage:
  python main.py          # silent run
  python main.py -v       # verbose

"""

import sys
from pathlib import Path
from dotenv  import load_dotenv

from spotify   import get_random_liked_song
from chorus    import find_hook_clip
from display   import show_song, export_panel_image
from video     import build_reel
from instagram import post_song


def main(verbose: bool = False) -> None:
    load_dotenv()

    out_dir = Path.home() / "song"
    out_dir.mkdir(exist_ok=True)

    song = get_random_liked_song(out_dir=out_dir, verbose=verbose)
    show_song(song)

    hook_clip  = find_hook_clip(song["mp3_path"], out_dir / "hook.wav")
    panel_png  = export_panel_image(song, out_dir / "panel.png")
    video_path = build_reel(song, panel_png, hook_clip, out_dir)

    post_song(song, video_path)


if __name__ == "__main__":
    main(verbose="-v" in sys.argv)
