"""Noise detection detector (placeholder implementation)."""
from typing import Dict


def detect_noise(features: Dict, config) -> Dict:
    """Return event dict if noise is detected in frame features."""
    rms = features.get("rms", 0)
    if rms < config.get("noise_rms_threshold", 1e-4):
        return {"event": "noise_floor", "score": 1.0}
    return {}
