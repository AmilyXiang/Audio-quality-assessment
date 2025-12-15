"""Dropout / packet-loss detection (placeholder)."""
from typing import Dict


def detect_dropout(features: Dict, config) -> Dict:
    rms = features.get("rms", 0)
    if rms < config.get("dropout_rms_threshold", 1e-6):
        return {"event": "dropout", "score": 1.0}
    return {}
