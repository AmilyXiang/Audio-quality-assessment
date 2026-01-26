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


def peak_to_peak(samples) -> float:
    """Compute peak-to-peak amplitude (detect clipping and bursts).
    
    用途：检测削波（audio clipping）、爆音
    
    Returns:
        Peak-to-peak value (0.0 ~ 2.0 for normalized audio)
    """
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size == 0:
        return 0.0
    return float(np.max(arr) - np.min(arr))


def spectral_rolloff(samples, sample_rate, threshold=0.95) -> float:
    """Compute spectral roll-off frequency (high-frequency energy cutoff).
    
    用途：检测风噪、高频噪声（>2kHz）
    
    Args:
        samples: Audio samples
        sample_rate: Sample rate in Hz
        threshold: Cumulative energy threshold (default 95%)
    
    Returns:
        Frequency (Hz) where 95% of energy is below
    """
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size < 2:
        return 0.0
    
    window = np.hanning(len(arr))
    windowed = arr * window
    fft = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(arr), 1 / sample_rate)
    
    if np.sum(fft) == 0:
        return sample_rate / 2
    
    # Cumulative sum of energy
    cumsum = np.cumsum(fft)
    cumsum_norm = cumsum / cumsum[-1]
    
    # Find frequency where cumsum crosses threshold
    rolloff_idx = np.where(cumsum_norm >= threshold)[0]
    if len(rolloff_idx) > 0:
        return float(freqs[rolloff_idx[0]])
    return float(freqs[-1])


def rms_percentile(samples, percentile=95, frame_size=256) -> float:
    """Compute RMS percentile (capture transient spikes).
    
    用途：捕捉瞬态事件（爆音、突增）- 比RMS均值更敏感
    
    Args:
        samples: Audio samples
        percentile: Percentile to compute (default 95th)
        frame_size: Sub-frame size for RMS computation
    
    Returns:
        RMS value at specified percentile
    """
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size == 0:
        return 0.0
    
    # Compute RMS for each sub-frame
    frame_rms_list = []
    for i in range(0, len(arr), frame_size):
        frame = arr[i:i+frame_size]
        if len(frame) > 0:
            frame_rms_list.append(rms(frame))
    
    if len(frame_rms_list) == 0:
        return 0.0
    
    return float(np.percentile(frame_rms_list, percentile))


def compute_mfcc(samples, sample_rate, n_mfcc=13, n_fft=512, hop_length=None) -> np.ndarray:
    """Compute Mel-Frequency Cepstral Coefficients (MFCC).
    
    用途：捕捉音色特征、麦克风响应差异、对标MOS/NISQA评分
    
    Args:
        samples: Audio samples
        sample_rate: Sample rate in Hz
        n_mfcc: Number of MFCC coefficients (default 13)
        n_fft: FFT size (default 512)
        hop_length: Hop length for STFT (default n_fft//4)
    
    Returns:
        MFCC vector of shape (n_mfcc,) - 平均值
        或 (n_mfcc, frames) - 完整时间序列
    """
    try:
        import librosa
    except ImportError:
        # Fallback: return zeros if librosa not installed
        print("⚠️  librosa not installed for MFCC. Install: pip install librosa")
        return np.zeros(n_mfcc)
    
    arr = np.asarray(samples, dtype=np.float32)
    if arr.size < n_fft:
        return np.zeros(n_mfcc)
    
    if hop_length is None:
        hop_length = n_fft // 4
    
    # Compute MFCC
    mfcc = librosa.feature.mfcc(
        y=arr,
        sr=sample_rate,
        n_mfcc=n_mfcc,
        n_fft=n_fft,
        hop_length=hop_length
    )
    
    # Return mean across time frames
    return np.mean(mfcc, axis=1)


def extract_features(frame, prev_frame=None) -> Dict:
    """Extract comprehensive features from audio frame.
    
    包含5个核心特征 + 3个第1阶段特征 + MFCC（可选）
    
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
        # 核心特征 (5个)
        "rms": rms(samples),
        "spectral_centroid": spectral_centroid(samples, sample_rate),
        "spectral_bandwidth": spectral_bandwidth(samples, sample_rate),
        "zero_crossing_rate": zero_crossing_rate(samples),
        "spectral_flux": spectral_flux(samples, prev_samples, sample_rate) if prev_samples is not None else 0.0,
        
        # 第1阶段特征 (3个) - 瞬态/爆音/噪声检测增强
        "peak_to_peak": peak_to_peak(samples),
        "spectral_rolloff": spectral_rolloff(samples, sample_rate),
        "rms_percentile_95": rms_percentile(samples, percentile=95),
        
        # 第2阶段特征 - MFCC（音色特征，可选）
        # "mfcc": compute_mfcc(samples, sample_rate)  # 默认注释，需要librosa
    }
    return feats
