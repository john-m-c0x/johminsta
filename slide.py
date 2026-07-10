"""slide.py - render a track's audio analysis as a screenshot-style JSON panel
centered on a datamosh background (carousel slide 2).

layers, back to front:
  1. an abstract datamosh texture (procedural, not the album art)
  2. solid black at 80% opacity, so the texture only faintly bleeds through
  3. a square, Ubuntu-purple "terminal" panel showing audio_features.json

run standalone to preview:
    python slide.py            # writes ~/song/slide.png from sample data
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FRAME_SIZE   = 1080
BLACK_ALPHA  = int(255 * 0.55)   # black veil opacity over the datamosh
PANEL_FRAC   = 0.62              # square panel width as a fraction of the frame

# the flat audio-features fields worth showing, in the order they read best.
# everything else the source returns (id, href, isrc, ...) is plumbing, not
# analysis, so it's dropped before rendering. missing keys are simply skipped.
FEATURE_KEYS = [
    "danceability", "energy", "valence", "tempo", "time_signature",
    "key", "mode", "loudness", "acousticness", "instrumentalness",
    "liveness", "speechiness", "duration_ms",
]

# windows ships consolas; fall back to PIL's bundled font if it's missing.
_MONO      = "C:/Windows/Fonts/consola.ttf"
_MONO_BOLD = "C:/Windows/Fonts/consolab.ttf"

# ---- ubuntu purple ("aubergine") terminal palette ----
COL_PANEL  = (0x00, 0x00, 0x00)   # json box background - black
COL_TITLE  = (0x00, 0x00, 0x00)   # title bar - same black as the body
COL_BORDER = (0x77, 0x29, 0x53)   # ubuntu purple #772953
COL_PUNCT  = (0xEE, 0xEE, 0xEC)   # foreground text
COL_KEY    = (0xAD, 0x7F, 0xA8)   # bright purple - json keys
COL_NUM    = (0xE9, 0x54, 0x20)   # ubuntu orange - numbers
COL_STR    = (0x8A, 0xE2, 0x34)   # green - strings
COL_BOOL   = (0xAD, 0x7F, 0xA8)   # purple - true/false/null
COL_DIM    = (0xAE, 0xA7, 0x9F)   # ubuntu warm grey - filename

# near-black field the shards explode across.
_BG_DARK = (0x10, 0x10, 0x14)

# shard palette: deep, saturated mid-tones that pop against the near-black
# field for high contrast - no bright whites/pastels washing it out.
_SHARD_PALETTE = np.array([
    (0xC0, 0x2E, 0x86), (0x8E, 0x24, 0x6A),   # magenta / deep magenta
    (0x24, 0x86, 0x80), (0x2C, 0x9A, 0x9A),   # teal / cyan
    (0x5A, 0x30, 0x84), (0x74, 0x50, 0x9A),   # purple / muted violet
    (0x2E, 0x8C, 0x44), (0x5E, 0x6E, 0x2C),   # green / olive
    (0x9A, 0x7C, 0x2E), (0xA8, 0x30, 0x38),   # gold / red
    (0xB6, 0xB6, 0xC2),                       # light grey (sparing highlight)
    (0x20, 0x20, 0x28),                       # near-black speck
], dtype=np.float64)

# weights - saturated mid-tones common, the grey highlight and darks rarer.
_SHARD_W = np.array([
    0.13, 0.10,          # magentas
    0.11, 0.09,          # teal / cyan
    0.09, 0.07,          # purple / violet
    0.10, 0.06,          # green / olive
    0.05, 0.05,          # gold / red
    0.05,                # grey highlight
    0.05,                # dark
])
_SHARD_W = _SHARD_W / _SHARD_W.sum()


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_MONO_BOLD if bold else _MONO, size)
    except OSError:
        return ImageFont.load_default(size)


# ------------------------------------------------------------ background --

def _place(arr, rng, xs, ys, smin, smax, elong):
    """stamp chunky shards at the given positions; ~`elong` fraction elongated
    into bars. shards stay >= smin px so they read as blocks, not scratch."""
    f    = arr.shape[0]
    cols = _SHARD_PALETTE[rng.choice(len(_SHARD_W), len(xs), p=_SHARD_W)]
    for i in range(len(xs)):
        w = int(rng.integers(smin, smax))
        h = int(rng.integers(smin, smax))
        if rng.random() < elong:
            if rng.random() < 0.5:
                w *= int(rng.integers(3, 9))
            else:
                h *= int(rng.integers(3, 9))
        x = min(int(xs[i]), f - w)
        y = min(int(ys[i]), f - h)
        arr[y:y + h, x:x + w] = cols[i]


def _cluster(rng, n, cx, cy, s, f):
    """`n` positions gaussian-scattered around (cx, cy)."""
    return (np.clip(rng.normal(cx, s, n), 0, f - 2),
            np.clip(rng.normal(cy, s, n), 0, f - 2))


def _smear(arr, rng, count, src):
    """drag blocks along evolving paths - each smear starts with a random
    velocity, then curves (rotating direction), accelerates (parabolic drift)
    and jitters as it goes, for a random lifetime. so trails arc, spiral and
    meander instead of running dead straight, each with its own length."""
    f = arr.shape[0]
    for _ in range(count):
        bh, bw = int(rng.integers(2, 56)), int(rng.integers(2, 56))  # wide size spread
        sx, sy = src()
        sx = min(max(sx, 0), f - bw)
        sy = min(max(sy, 0), f - bh)
        block  = arr[sy:sy + bh, sx:sx + bw].copy()

        ang  = rng.uniform(0, 2 * np.pi)                # initial heading
        mag  = rng.uniform(2, 11)
        vx, vy = np.cos(ang) * mag, np.sin(ang) * mag
        curl = rng.uniform(-0.16, 0.16)                 # turn per step -> arcs/spirals
        ax   = rng.uniform(-0.5, 0.5)                   # constant pull -> parabola
        ay   = rng.uniform(-0.5, 0.5)
        jit  = rng.uniform(0.0, 1.3)                    # random wander
        ttl  = int(rng.integers(8, 130))                # varied lifetime
        # size trajectory along the trail: 0 const, 1 taper, 2 grow, 3 pulse.
        smode  = int(rng.integers(0, 4))
        pulses = rng.uniform(1.5, 4.0)

        fx, fy = float(sx), float(sy)
        cos_c, sin_c = np.cos(curl), np.sin(curl)
        for i in range(ttl):
            vx, vy = vx * cos_c - vy * sin_c, vx * sin_c + vy * cos_c   # rotate
            vx += ax + rng.normal(0, jit)
            vy += ay + rng.normal(0, jit)
            speed = np.hypot(vx, vy)
            if speed > 18:                              # clamp so it can't rip away
                vx, vy = vx * 18 / speed, vy * 18 / speed
            fx += vx
            fy += vy
            frac = (i + 1) / ttl
            if smode == 1:
                scale = 1.0 - 0.8 * frac                # taper down
            elif smode == 2:
                scale = 0.2 + 0.8 * frac                # grow
            elif smode == 3:
                scale = 0.35 + 0.65 * abs(np.sin(frac * np.pi * pulses))  # pulse
            else:
                scale = 1.0
            ch = max(1, min(bh, int(bh * scale)))       # never exceed the source block
            cw = max(1, min(bw, int(bw * scale)))
            dx = min(max(int(fx), 0), f - bw)
            dy = min(max(int(fy), 0), f - bh)
            arr[dy:dy + ch, dx:dx + cw] = block[:ch, :cw]


def _datamosh_texture(seed: int | None = None) -> Image.Image:
    """an exploded-shard datamosh on near-black: chunky pastel/white shards from
    a few random hotspots (so the composition varies), then dragged into long
    horizontal and vertical smear vectors."""
    rng = np.random.default_rng(seed)
    f   = FRAME_SIZE
    arr = np.full((f, f, 3), _BG_DARK, dtype=np.float64)
    arr += rng.normal(0, 3, (f, f, 1))                  # faint grain

    # 2-5 hotspots at random positions - varies per seed, no single centre blob.
    k     = int(rng.integers(2, 6))
    spots = [(f * rng.uniform(0.12, 0.88), f * rng.uniform(0.12, 0.88)) for _ in range(k)]
    for cx, cy in spots:
        s = f * rng.uniform(0.06, 0.22)
        _place(arr, rng, *_cluster(rng, int(rng.integers(220, 460)), cx, cy, s, f), 4, 22, 0.45)

    # a sparse layer across the whole frame so shards reach the edges too.
    n = int(rng.integers(500, 1000))
    _place(arr, rng, rng.integers(0, f, n), rng.integers(0, f, n), 3, 12, 0.5)

    # random-direction smears - sourced from hotspots most of the time, from
    # anywhere the rest, so drags criss-cross the whole frame.
    def src():
        if rng.random() < 0.35:
            return int(rng.integers(0, f)), int(rng.integers(0, f))
        cx, cy = spots[int(rng.integers(0, len(spots)))]
        return (int(np.clip(rng.normal(cx, f * 0.2), 0, f - 1)),
                int(np.clip(rng.normal(cy, f * 0.2), 0, f - 1)))

    _smear(arr, rng, int(rng.integers(320, 520)), src)

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------- panel --

def _spans(key: str, value, comma: bool) -> list[tuple[str, tuple]]:
    """colored (text, rgb) spans for one `"key": value,` json line. the comma
    is dropped on the final entry so the readout stays valid json."""
    if isinstance(value, bool):
        val, col = ("true" if value else "false"), COL_BOOL
    elif isinstance(value, (int, float)):
        val, col = (f"{value:g}" if isinstance(value, float) else str(value)), COL_NUM
    elif value is None:
        val, col = "null", COL_BOOL
    else:
        val, col = f'"{value}"', COL_STR
    tail = [(",", COL_PUNCT)] if comma else []
    return [
        ('  "', COL_PUNCT), (key, COL_KEY), ('"', COL_PUNCT),
        (": ", COL_PUNCT), (val, col),
    ] + tail


def _panel(data: dict, title: str) -> Image.Image:
    """a square code-editor panel showing `data` as pretty json under a title
    bar, its text block centered within the square."""
    keys  = list(data)
    lines = [[("{", COL_PUNCT)]]
    lines += [_spans(k, data[k], comma=i < len(keys) - 1) for i, k in enumerate(keys)]
    lines += [[("}", COL_PUNCT)]]

    size      = 30
    font      = _font(size)
    title_fnt = _font(24)
    char_w    = font.getlength("0")
    line_h    = int(size * 1.55)
    longest   = max(sum(len(t) for t, _ in ln) for ln in lines)

    pad, bar_h = 40, 56
    content_w  = int(longest * char_w)
    content_h  = len(lines) * line_h
    title_w    = int(title_fnt.getlength(title))
    # square: side is whichever of the content/title width or the stacked
    # height (plus padding and title bar) is larger.
    side = max(content_w + pad * 2, title_w + pad * 2, content_h + pad * 2 + bar_h)

    panel  = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(panel)
    radius = 22

    # rounded body + title bar + border
    draw.rounded_rectangle([0, 0, side - 1, side - 1], radius, fill=COL_PANEL + (255,))
    draw.rounded_rectangle([0, 0, side - 1, bar_h + radius], radius, fill=COL_TITLE + (255,))
    draw.rectangle([0, bar_h, side - 1, bar_h + 2], fill=COL_BORDER + (255,))
    draw.rounded_rectangle([0, 0, side - 1, side - 1], radius,
                           outline=COL_BORDER + (255,), width=2)

    # filename, centered in the title bar
    draw.text((side // 2, bar_h // 2), title,
              font=title_fnt, fill=COL_DIM + (255,), anchor="mm")

    # json body: left-aligned lines, the block centered in the square.
    x0 = (side - content_w) // 2
    y  = bar_h + (side - bar_h - content_h) // 2
    for ln in lines:
        x = x0
        for text, col in ln:
            draw.text((x, y), text, font=font, fill=col + (255,))
            x += font.getlength(text)
        y += line_h
    return panel


# ---------------------------------------------------------------- compose --

def _slug(name: str) -> str:
    """turn a song title into a filename-ish token: 'Blinding Lights' -> the
    'blinding_lights' in blinding_lights_features.json."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "audio"


def build_slide(features: dict, out_path: Path, name: str = "audio",
                seed: int | None = None, veil: int = BLACK_ALPHA) -> Path:
    """compose slide 2: datamosh texture, a black veil (0-255 alpha; 0 leaves the
    texture full-bright), then the centered square Ubuntu-purple json panel
    titled '<song>_features.json'."""
    data = {k: features[k] for k in FEATURE_KEYS if k in features} or dict(features)

    canvas = _datamosh_texture(seed).convert("RGBA")
    if veil > 0:
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, veil)))

    panel = _panel(data, f"{_slug(name)}_features.json")
    scale = (FRAME_SIZE * PANEL_FRAC) / panel.width
    panel = panel.resize((int(panel.width * scale), int(panel.height * scale)),
                         Image.LANCZOS)
    px = (FRAME_SIZE - panel.width) // 2
    py = (FRAME_SIZE - panel.height) // 2

    canvas.alpha_composite(panel, (px, py))
    canvas.convert("RGB").save(out_path)
    return out_path


if __name__ == "__main__":
    sample = {
        "danceability": 0.585, "energy": 0.842, "valence": 0.523,
        "tempo": 128.03, "time_signature": 4, "key": 9, "mode": 1,
        "loudness": -4.72, "acousticness": 0.012, "instrumentalness": 0.0,
        "liveness": 0.117, "speechiness": 0.043, "duration_ms": 215000,
    }
    home = Path.home() / "song"
    for s in range(1, 6):                              # 5 debug iterations
        _datamosh_texture(seed=s).save(home / f"texture_debug_{s}.png")
    build_slide(sample, home / "slide.png", name="Blinding Lights", seed=1)
    print("wrote texture_debug_1..5.png and slide.png")
