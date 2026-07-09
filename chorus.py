"""chorus.py - pick the song's hype moment: a 30s window where energy peaks after a rise"""

import sys
from pathlib import Path

from pydub import AudioSegment

CHUNK_MS  = 1_000   # granularity (seconds) for the energy scan
LEAD_IN_S = 5       # seconds of "before" context a window is compared against
LIFT_BIAS = 1.5     # how much extra weight a rise in energy gets over raw loudness
FLOOR_DB  = -60.0   # clamp near-silence so it can't blow up the average with -inf


def _energy_profile(audio: AudioSegment) -> list[float]:
    """loudness (dBFS) of every CHUNK_MS slice across the track, floored to avoid -inf"""
    return [
        max(audio[i:i + CHUNK_MS].dBFS, FLOOR_DB)
        for i in range(0, len(audio), CHUNK_MS)
    ]


def _best_start(levels: list[float], clip_length: int) -> int:
    """
    score every possible clip_length-second window by how loud it is and how
    much louder it is than the few seconds right before it. a verse building
    into a chorus reads as a jump in energy into a sustained loud section -
    a decent proxy for "the hype moment" without needing real structural
    chorus detection. skips the very start/end of the track since intros and
    outros are rarely the hook.
    """
    margin = max(1, int(len(levels) * 0.1))
    lo, hi = margin, len(levels) - clip_length - margin

    if hi <= lo:
        return 0

    best_start, best_score = lo, float("-inf")
    for start in range(lo, hi):
        window     = levels[start:start + clip_length]
        window_avg = sum(window) / len(window)

        before     = levels[max(0, start - LEAD_IN_S):start]
        before_avg = sum(before) / len(before) if before else window_avg

        score = window_avg + LIFT_BIAS * (window_avg - before_avg)
        if score > best_score:
            best_start, best_score = start, score

    return best_start


def find_hook_clip(mp3_path: Path, out_path: Path, clip_length: int = 30) -> Path:
    """
    scan the track in 1s slices for the loudest clip_length-second window that
    follows a rise in energy, and export that window to out_path. falls back
    to the loudest window alone when nothing else stands out, and to the
    whole track when it's shorter than clip_length - so no track can fail to
    produce a clip.
    """
    audio  = AudioSegment.from_file(mp3_path).set_channels(1)
    levels = _energy_profile(audio)

    if len(levels) <= clip_length:
        clip = audio
    else:
        start = _best_start(levels, clip_length)
        clip  = audio[start * 1000: (start + clip_length) * 1000]

    clip.export(out_path, format=out_path.suffix.lstrip(".") or "mp3")
    return out_path


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = src.with_name(f"{src.stem}_hook.mp3")
    find_hook_clip(src, dst)
    print(f"wrote {dst}")
