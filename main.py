"""
random liked song

pulls one song at random from your spotify
liked library and posts it to instagram.

  spotify.py     auth, fetch, download
  display.py     format, caption
  video.py       render album art + audio into a reel
  instagram.py   graph api, resumable upload, publish

usage:
  python main.py          # silent run
  python main.py -v       # verbose

"""

import sys
from dotenv import load_dotenv

from spotify   import get_random_liked_song
from display   import show_song
from instagram import post_song


def main(verbose: bool = False) -> None:
    load_dotenv()

    song = get_random_liked_song(verbose=verbose)

    show_song(song)
    post_song(song, verbose=verbose)


if __name__ == "__main__":
    main(verbose="-v" in sys.argv)
