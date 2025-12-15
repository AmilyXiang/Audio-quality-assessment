"""Distortion / voice change detection (重点).

Placeholder uses simple spectral change heuristic. Replace with ML-based model or more advanced DSP in production.
"""
from typing import Dict


def detect_distortion(features: Dict, prev_features: Dict, config) -> Dict:
    """Detects abrupt spectral changes indicating distortion or voice change.

    Returns an event dict when change magnitude exceeds threshold.
    """
    spec = features.get("spectrum", {})
    prev_spec = prev_features.get("spectrum", {}) if prev_features else {}
    change = 0.0
    # Simple heuristic: compare peak_freq
    if spec and prev_spec:
        change = abs(spec.get("peak_freq", 0.0) - prev_spec.get("peak_freq", 0.0))
    if change > config.get("distortion_freq_change_threshold", 200.0):
        return {"event": "distortion", "score": change}
    return {}
