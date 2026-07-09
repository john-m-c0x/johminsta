"""
random liked song

pulls one song at random from your spotify
liked library and posts it to instagram.

  spotify.py     auth, fetch, download
  display.py     format, caption
  instagram.py   graph api, post

usage:
  python main.py          # silent run
  python main.py -v       # verbose
  python main.py -d       # dry run - builds the ig media container but skips publish

"""

import sys
from dotenv import load_dotenv

from spotify   import get_random_liked_song
from display   import show_song
from instagram import post_song


def main(verbose: bool = False, dry_run: bool = False) -> None:
    load_dotenv()

    song = get_random_liked_song(verbose=verbose)

    show_song(song)
    post_song(song, dry_run=dry_run)


if __name__ == "__main__":
    main(verbose="-v" in sys.argv, dry_run="-d" in sys.argv or "--dry-run" in sys.argv)
