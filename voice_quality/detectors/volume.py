"""Volume fluctuation detection (placeholder)."""
from typing import Dict


def detect_volume(features: Dict, config) -> Dict:
    rms = features.get("rms", 0)
    if rms > config.get("loud_rms_threshold", 0.5):
        return {"event": "loud", "score": (rms - config.get("loud_rms_threshold", 0.5))}
    return {}
