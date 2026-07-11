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


def _select_start(audio: AudioSegment, clip_length: int) -> int:
    """
    start second of the clip_length-second slice that best captures the hook.
    analysis runs on a mono downmix (loudness only). returns 0 when the track
    is shorter than clip_length (the caller just takes the whole thing).
    """
    if len(audio) <= clip_length * 1000:
        return 0

    levels = _energy_profile(audio.set_channels(1))
    drop   = _best_start(levels, clip_length)
    return max(0, drop - PRE_ROLL_S)


def _export(clip: AudioSegment, out_path: Path) -> Path:
    clip.export(
        out_path,
        format=out_path.suffix.lstrip(".") or "mp3",
        bitrate=EXPORT_BITRATE,
    )
    return out_path


def find_hook_clip(
    mp3_path: Path,
    out_path: Path,
    clip_length: int = CLIP_LENGTH,
    continuation_out: Path | None = None,
) -> Path:
    """
    scan the track in 1s slices for the loudest clip_length-second window that
    follows a rise in energy - the drop - and export a clip starting PRE_ROLL_S
    seconds before it, so the listener gets a moment of anticipation instead of
    landing right on the hit. the clip is cut from the original audio and
    re-encoded at EXPORT_BITRATE, keeping the source's channels and fidelity.

    when continuation_out is given, also export the NEXT clip_length seconds
    (picking up exactly where the hook clip ends) - used as the audio for the
    carousel's second slide so the song carries on across the swipe. if the
    track ends less than 5s after the hook clip, the hook clip itself is
    reused rather than exporting a stub.
    """
    audio = AudioSegment.from_file(mp3_path)
    start = _select_start(audio, clip_length)
    clip  = audio[start * 1000: (start + clip_length) * 1000]
    _export(clip, out_path)

    if continuation_out is not None:
        cont_start = start + clip_length
        cont = audio[cont_start * 1000: (cont_start + clip_length) * 1000]
        _export(cont if len(cont) >= 5000 else clip, continuation_out)

    return out_path


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = src.with_name(f"{src.stem}_hook.mp3")
    find_hook_clip(src, dst)
    print(f"wrote {dst}")
