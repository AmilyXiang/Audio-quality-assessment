"""Feature extraction: RMS, spectral properties for quality analysis."""
import numpy as np
from typing import Dict


def rms(samples) -> float:
    """Compute RMS energy level."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(arr ** 2)))


def rms_to_db(rms_value: float, reference: float = 1.0) -> float:
    """Convert RMS to dB (decibels).
    
    Args:
        rms_value: RMS energy value
        reference: Reference level (default 1.0 for normalized audio)
    
    Returns:
        dB value. Returns -100 dB for very small values to avoid -inf.
    """
    if rms_value < 1e-6:
        return -100.0
    return 20.0 * np.log10(rms_value / reference)


def spectral_centroid(samples, sample_rate) -> float:
    """Compute spectral centroid (center of mass in frequency domain)."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size < 2:
        return 0.0
    
    # Apply Hann window
    window = np.hanning(len(arr))
    windowed = arr * window
    
    # Compute FFT
    fft = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(arr), 1 / sample_rate)
    
    # Avoid division by zero
    if np.sum(fft) == 0:
        return 0.0
    
    centroid = np.sum(freqs * fft) / np.sum(fft)
    return float(centroid)


def spectral_bandwidth(samples, sample_rate) -> float:
    """Compute spectral bandwidth (spread around centroid)."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size < 2:
        return 0.0
    
    window = np.hanning(len(arr))
    windowed = arr * window
    fft = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(arr), 1 / sample_rate)
    
    if np.sum(fft) == 0:
        return 0.0
    
    centroid = np.sum(freqs * fft) / np.sum(fft)
    bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * fft) / np.sum(fft))
    return float(bandwidth)


def zero_crossing_rate(samples) -> float:
    """Compute zero crossing rate (indicator of noise vs voice)."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size < 2:
        return 0.0
    zero_crossings = np.sum(np.abs(np.diff(np.sign(arr)))) / 2
    return float(zero_crossings / len(arr))


def spectral_flux(samples_current, samples_prev, sample_rate) -> float:
    """Compute spectral flux (change in spectrum frame-to-frame)."""
    arr_curr = np.asarray(samples_current, dtype=np.float32)
    arr_prev = np.asarray(samples_prev, dtype=np.float32)
    
    if arr_curr.size < 2 or arr_prev.size < 2:
        return 0.0
    
    # Ensure same size for comparison
    min_len = min(len(arr_curr), len(arr_prev))
    arr_curr = arr_curr[:min_len]
    arr_prev = arr_prev[:min_len]
    
    window = np.hanning(len(arr_curr))
    
    fft_curr = np.abs(np.fft.rfft(arr_curr * window))
    fft_prev = np.abs(np.fft.rfft(arr_prev * window))
    
    # Normalize
    if np.sum(fft_prev) > 0:
        fft_prev_norm = fft_prev / np.sum(fft_prev)
    else:
        fft_prev_norm = fft_prev
    
    if np.sum(fft_curr) > 0:
        fft_curr_norm = fft_curr / np.sum(fft_curr)
    else:
        fft_curr_norm = fft_curr
    
    # Pad to same length
    max_len = max(len(fft_curr_norm), len(fft_prev_norm))
    fft_curr_norm = np.pad(fft_curr_norm, (0, max_len - len(fft_curr_norm)))
    fft_prev_norm = np.pad(fft_prev_norm, (0, max_len - len(fft_prev_norm)))
    
    flux = np.sqrt(np.sum((fft_curr_norm - fft_prev_norm) ** 2))
    return float(flux)


def extract_features(frame, prev_frame=None) -> Dict:
    """Extract comprehensive features from audio frame.
    
    Args:
        frame: Frame object with samples, sample_rate, start_time, end_time
        prev_frame: Previous frame for computing temporal features (optional)
    
    Returns:
        Dictionary with extracted features
    """
    samples = frame.samples
    sample_rate = frame.sample_rate
    prev_samples = prev_frame.samples if prev_frame is not None else None
    
    feats = {
        "rms": rms(samples),
        "spectral_centroid": spectral_centroid(samples, sample_rate),
        "spectral_bandwidth": spectral_bandwidth(samples, sample_rate),
        "zero_crossing_rate": zero_crossing_rate(samples),
        "spectral_flux": spectral_flux(samples, prev_samples, sample_rate) if prev_samples is not None else 0.0,
    }
    return feats
