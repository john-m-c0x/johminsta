"""display.py - terminal output"""

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


def show_song(song: Song) -> None:
    console = Console()
    panel   = Panel(
        Align.center(_render(song)),
        title="[cyan]?? random liked song[/]",
        border_style="cyan",
        padding=(2, 6),
        expand=False,
    )
    console.print("\n")
    console.print(Align.center(panel))
    console.print("\n")


def caption(song: Song) -> str:
    return (
        f"?? {song['name']}\n"
        f"?? {song['artist']}\n"
        f"?? {song['album']}\n\n"
        f"#randomsong #spotify #likedsongs"
    )
