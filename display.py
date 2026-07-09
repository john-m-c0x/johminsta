"""display.py - terminal output and caption"""

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


def caption(song: Song) -> str:
    return (
        f"\n{song['name']}\n"
        f"{song['artist']}\n"
        f"{song['album']}\n\n"
        f"date liked: {song['liked_at']}"
    )
