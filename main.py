"""
random liked song

pulls one song at random from your spotify liked library, finds its hook,
and posts it to instagram as a video post (album art + a 60s audio clip).

  spotify.py     auth, fetch, download
  chorus.py      find the song's hook/hype moment (energy-based)
  display.py     terminal output, caption
  video.py       compose the post
  instagram.py   graph api, post

usage:
  python main.py               # silent run
  python main.py -v            # verbose
  python main.py --dry-run     # build the post but don't post it; leaves
                                # post.mp4 + caption.txt in the output dir
                                # for inspection (implies -v)

"""

import sys
from pathlib import Path
from dotenv  import load_dotenv

from spotify   import get_random_liked_song
from chorus    import find_hook_clip
from display   import show_song, caption
from video     import build_post
from instagram import post_song


def main(verbose: bool = False, dry_run: bool = False) -> None:
    load_dotenv()

    out_dir = Path.home() / "song"
    out_dir.mkdir(exist_ok=True)

    song = get_random_liked_song(out_dir=out_dir, verbose=verbose)
    show_song(song)

    hook_clip  = find_hook_clip(song["mp3_path"], out_dir / "hook.wav")
    video_path = build_post(song, hook_clip, out_dir)

    if dry_run:
        caption_path = out_dir / "caption.txt"
        caption_path.write_text(caption(song), encoding="utf-8")
        print(f"\ndry run - nothing posted. output in {out_dir}:")
        print(f"  video:   {video_path}")
        print(f"  caption: {caption_path}")
        return

    post_song(song, video_path)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    main(verbose=dry_run or "-v" in sys.argv, dry_run=dry_run)
