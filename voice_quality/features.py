"""Feature extraction: RMS, spectrum, MFCC placeholder implementations."""
import math
from typing import Dict


def rms(samples) -> float:
    if not samples:
        return 0.0
    mean_sq = sum(s * s for s in samples) / len(samples)
    return math.sqrt(mean_sq)


def spectrum_placeholder(samples, sample_rate):
    # Placeholder: in real code use numpy.fft
    return {"peak_freq": 0.0}


def mfcc_placeholder(samples, sample_rate):
    # Placeholder
    return [0.0] * 13


def extract_features(frame) -> Dict:
    feats = {
        "rms": rms(frame.samples),
        "spectrum": spectrum_placeholder(frame.samples, frame.sample_rate),
        "mfcc": mfcc_placeholder(frame.samples, frame.sample_rate),
    }
    return feats
