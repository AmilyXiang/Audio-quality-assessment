"""Compact audio-derived summaries for LLM enrichment.

Route-1 approach: do not send raw audio; send compact, audit-friendly statistics.

All outputs are designed to be small and stable across platforms:
- per-second RMS dB and spectral centroid (lists)
- aggregate stats (mean/std/percentiles)
- coarse mel-band energies (13 bands, simplified)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


def _safe_percentiles(values: np.ndarray, ps: Tuple[int, ...] = (5, 50, 95)) -> Dict[str, float]:
    if values.size == 0:
        return {f"p{p}": 0.0 for p in ps}
    out = np.percentile(values, ps)
    return {f"p{p}": float(v) for p, v in zip(ps, out)}


def _rms_db(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(x))) + 1e-12)
    return float(20.0 * np.log10(rms))


def _spectral_centroid_hz(x: np.ndarray, sr: int) -> float:
    if x.size == 0:
        return 0.0
    fft = np.abs(np.fft.rfft(x))
    power = np.square(fft)
    freqs = np.fft.rfftfreq(x.size, 1.0 / sr)
    denom = float(np.sum(power) + 1e-12)
    return float(np.sum(freqs * power) / denom)


def _mel13_mean_power(x: np.ndarray, sr: int) -> List[float]:
    """Simplified 13-band 'mel-like' power by splitting FFT bins.

    Not a true mel filterbank; designed to be dependency-free and stable.
    """
    if x.size == 0:
        return [0.0] * 13
    n_fft = min(2048, x.size)
    frame = x[:n_fft]
    fft = np.abs(np.fft.rfft(frame))
    power = np.square(fft)
    n_bins = power.size
    bands = 13
    out = []
    for j in range(bands):
        start = int(j * n_bins / bands)
        end = int((j + 1) * n_bins / bands)
        band_val = float(np.mean(power[start:end])) if end > start else 0.0
        out.append(band_val)
    return out


def build_llm_audio_summary(
    data: np.ndarray,
    sample_rate: int,
    segment_sec: float = 1.0,
    max_segments: int = 120,
) -> Dict:
    """Build compact audio summary for LLM.

    Args:
        data: mono float waveform in [-1, 1]
        sample_rate: sampling rate
        segment_sec: segment duration for time series
        max_segments: cap number of segments to limit payload size

    Returns:
        dict with time series + aggregate stats
    """
    if data is None or len(data) == 0:
        return {
            "segment_sec": segment_sec,
            "segments": 0,
            "rms_db_series": [],
            "centroid_hz_series": [],
            "stats": {},
            "mel13_mean_power": [0.0] * 13,
        }

    seg_len = int(sample_rate * segment_sec)
    if seg_len <= 0:
        seg_len = sample_rate

    n_segments = int(np.ceil(len(data) / seg_len))
    n_segments = min(n_segments, max_segments)

    rms_db_series: List[float] = []
    centroid_series: List[float] = []

    for i in range(n_segments):
        start = i * seg_len
        end = min(len(data), (i + 1) * seg_len)
        seg = data[start:end]
        if seg.size == 0:
            continue
        rms_db_series.append(_rms_db(seg))
        centroid_series.append(_spectral_centroid_hz(seg, sample_rate))

    rms_arr = np.array(rms_db_series, dtype=float)
    cen_arr = np.array(centroid_series, dtype=float)

    stats = {
        "rms_db": {
            "mean": float(np.mean(rms_arr)) if rms_arr.size else 0.0,
            "std": float(np.std(rms_arr)) if rms_arr.size else 0.0,
            "min": float(np.min(rms_arr)) if rms_arr.size else 0.0,
            "max": float(np.max(rms_arr)) if rms_arr.size else 0.0,
            **_safe_percentiles(rms_arr),
        },
        "centroid_hz": {
            "mean": float(np.mean(cen_arr)) if cen_arr.size else 0.0,
            "std": float(np.std(cen_arr)) if cen_arr.size else 0.0,
            "min": float(np.min(cen_arr)) if cen_arr.size else 0.0,
            "max": float(np.max(cen_arr)) if cen_arr.size else 0.0,
            **_safe_percentiles(cen_arr),
        },
    }

    # Identify a few extreme segments for explainability
    extremes = {}
    if rms_arr.size:
        low_idx = int(np.argmin(rms_arr))
        high_idx = int(np.argmax(rms_arr))
        extremes["lowest_rms_db"] = {"segment": low_idx, "value": float(rms_arr[low_idx])}
        extremes["highest_rms_db"] = {"segment": high_idx, "value": float(rms_arr[high_idx])}
    if cen_arr.size:
        low_idx = int(np.argmin(cen_arr))
        high_idx = int(np.argmax(cen_arr))
        extremes["lowest_centroid_hz"] = {"segment": low_idx, "value": float(cen_arr[low_idx])}
        extremes["highest_centroid_hz"] = {"segment": high_idx, "value": float(cen_arr[high_idx])}

    mel13 = _mel13_mean_power(data, sample_rate)
    mel_sum = float(np.sum(mel13) + 1e-12)
    mel13_norm = [float(v / mel_sum) for v in mel13]

    return {
        "segment_sec": float(segment_sec),
        "segments": int(len(rms_db_series)),
        "rms_db_series": [float(round(v, 2)) for v in rms_db_series],
        "centroid_hz_series": [float(round(v, 1)) for v in centroid_series],
        "stats": stats,
        "extremes": extremes,
        "mel13_mean_power": [float(v) for v in mel13],
        "mel13_norm": mel13_norm,
    }
