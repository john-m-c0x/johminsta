"""chorus.py - pick the song's hype moment: a window where energy peaks after a rise"""

import sys
from pathlib import Path

from pydub import AudioSegment

CHUNK_MS     = 1_000   # granularity (seconds) for the energy scan
LEAD_IN_S    = 5       # seconds of "before" context a window is compared against
LIFT_BIAS    = 1.5     # how much extra weight a rise in energy gets over raw loudness
FLOOR_DB     = -60.0   # clamp near-silence so it can't blow up the average with -inf
PRE_ROLL_S   = 5       # seconds of anticipation to include before the detected drop
CLIP_LENGTH  = 60      # length of the exported hook clip, in seconds
EXPORT_BITRATE = "320k"  # re-encode at mp3's max so the clip doesn't lose fidelity


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


def _select_clip(audio: AudioSegment, clip_length: int) -> AudioSegment:
    """
    return the clip_length-second slice of `audio` that best captures the hook.
    analysis runs on a mono downmix (loudness only), but the returned slice is
    cut from the original `audio` so channels/bitrate are preserved. falls back
    to the whole track when it's shorter than clip_length.
    """
    if len(audio) <= clip_length * 1000:
        return audio

    levels = _energy_profile(audio.set_channels(1))
    drop   = _best_start(levels, clip_length)
    start  = max(0, drop - PRE_ROLL_S)
    return audio[start * 1000: (start + clip_length) * 1000]


def find_hook_clip(mp3_path: Path, out_path: Path, clip_length: int = CLIP_LENGTH) -> Path:
    """
    scan the track in 1s slices for the loudest clip_length-second window that
    follows a rise in energy - the drop - and export a clip starting PRE_ROLL_S
    seconds before it, so the listener gets a moment of anticipation instead of
    landing right on the hit. the clip is cut from the original audio and
    re-encoded at EXPORT_BITRATE, keeping the source's channels and fidelity.
    """
    audio = AudioSegment.from_file(mp3_path)
    clip  = _select_clip(audio, clip_length)
    clip.export(
        out_path,
        format=out_path.suffix.lstrip(".") or "mp3",
        bitrate=EXPORT_BITRATE,
    )
    return out_path


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = src.with_name(f"{src.stem}_hook.mp3")
    find_hook_clip(src, dst)
    print(f"wrote {dst}")
