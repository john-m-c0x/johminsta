"""analysis.py - local audio-features fallback when reccobeats lacks the track

computes a spotify-shaped features dict straight from the downloaded mp3 so
the analysis slide never goes missing on catalog gaps. tempo/key/mode/loudness
are real DSP; danceability/energy/acousticness are documented heuristics that
land in plausible spotify-like ranges, not the output of spotify's trained
models. only keys we can estimate credibly are included - the slide simply
renders fewer lines than a reccobeats hit.
"""

from pathlib import Path

import numpy as np
import librosa
from mutagen.mp3 import MP3

# analyze a window from the middle of the track: enough signal for stable
# tempo/key estimates at a fraction of the cost of decoding the whole song.
SAMPLE_RATE = 22050
WINDOW_S    = 120

# krumhansl-schmuckler key profiles: how strongly each pitch class sounds in a
# major/minor key. correlating the track's average chroma against all 24
# rotations picks the best-fitting key. index 0 = C, matching spotify's
# pitch-class convention.
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                   2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                   2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _key_mode(chroma_mean: np.ndarray) -> tuple[int, int]:
    """(key 0-11, mode 1=major/0=minor) with the best profile correlation."""
    best = (-2.0, 0, 1)
    for k in range(12):
        for mode, profile in ((1, _MAJOR), (0, _MINOR)):
            r = np.corrcoef(chroma_mean, np.roll(profile, k))[0, 1]
            if r > best[0]:
                best = (r, k, mode)
    return best[1], best[2]


def analyze_track(mp3_path: Path, verbose: bool = False) -> dict:
    """spotify-shaped audio features computed locally from the mp3."""
    total_s = MP3(mp3_path).info.length
    offset  = max(0.0, total_s / 2 - WINDOW_S / 2)
    y, sr   = librosa.load(str(mp3_path), sr=SAMPLE_RATE, mono=True,
                           offset=offset, duration=WINDOW_S)

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    key, mode = _key_mode(librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1))

    # loudness: overall RMS level in dBFS - tracks spotify's LUFS-ish number
    # closely enough for display.
    rms_db = 20 * np.log10(max(np.sqrt(np.mean(y ** 2)), 1e-6))

    # energy heuristic: map RMS level onto 0-1 (-60dB -> 0, 0dB -> 1).
    energy = float(np.clip((rms_db + 60) / 60, 0, 1))

    # danceability heuristic: steady beats near ~120bpm score high. regularity
    # is the inverse spread of beat-to-beat intervals; tempo_fit decays as the
    # tempo leaves the danceable range.
    beat_times = librosa.frames_to_time(beats, sr=sr)
    if len(beat_times) > 2:
        iv         = np.diff(beat_times)
        regularity = float(np.clip(1 - (np.std(iv) / max(np.mean(iv), 1e-6)), 0, 1))
    else:
        regularity = 0.0
    tempo_fit    = float(np.exp(-(((tempo - 120) / 80) ** 2)))
    danceability = float(np.clip(0.6 * regularity + 0.4 * tempo_fit, 0, 1))

    # acousticness heuristic: acoustic material concentrates spectral energy
    # low; a bright centroid means electric/produced.
    centroid     = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    acousticness = float(np.clip(1 - centroid / 4000, 0, 1))

    features = {
        "danceability": round(danceability, 3),
        "energy":       round(energy, 3),
        "tempo":        round(tempo, 3),
        "key":          key,
        "mode":         mode,
        "loudness":     round(float(rms_db), 3),
        "acousticness": round(acousticness, 3),
        "duration_ms":  int(total_s * 1000),
    }
    if verbose:
        print(f"  local analysis: {features}")
    return features
