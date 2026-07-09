"""display.py - terminal output and panel screenshot export"""

import io
from pathlib      import Path
from rich.console import Console
from rich.panel   import Panel
from rich.align   import Align
from rich.text    import Text

from spotify import Song


def _render(song: Song) -> Text:
    text = Text(justify="center")
    text.append(f"\n{song['name']}\n",  style="bold cyan")
    text.append(f"{song['artist']}\n",  style="white")
    text.append(f"{song['album']}\n",   style="dim")
    text.append(f"\n{song['uri']}\n",   style="bright_black")
    return text


def _panel(song: Song) -> Panel:
    return Panel(
        Align.center(_render(song)),
        title="[cyan]\U0001f3a7 random liked song[/]",
        border_style="cyan",
        padding=(2, 6),
        expand=False,
    )


def show_song(song: Song) -> None:
    console = Console()
    console.print("\n")
    console.print(Align.center(_panel(song)))
    console.print("\n")


def export_panel_image(song: Song, out_path: Path, width: int = 80) -> Path:
    """render the panel to a png (via svg) for use as a reel frame. requires
    cairosvg and its system cairo/pango libs, only needed for this path."""
    import cairosvg

    console = Console(record=True, width=width, file=io.StringIO())
    console.print(Align.center(_panel(song)))
    svg = console.export_svg(title="")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_path), scale=2)
    return out_path


def caption(song: Song) -> str:
    return (
        f"\U0001f3b5 {song['name']}\n"
        f"\U0001f3a4 {song['artist']}\n"
        f"\U0001f4bf {song['album']}\n\n"
        f"#randomsong #spotify #likedsongs"
    )
