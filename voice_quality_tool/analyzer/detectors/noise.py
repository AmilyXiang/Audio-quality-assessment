"""Noise detection: background noise and sudden noise bursts."""
from typing import Optional
from .base import BaseDetector, DetectionEvent
import numpy as np


class NoiseDetector(BaseDetector):
    """Detects persistent background noise and sudden noise bursts."""
    
    def __init__(self, config=None):
        super().__init__(config)
        # Thresholds for noise detection
        self.high_noise_rms = self.config.get("high_noise_rms_threshold", 0.15)
        self.noise_zcr_threshold = self.config.get("noise_zcr_threshold", 0.15)
        self.burst_spike_threshold = self.config.get("burst_spike_threshold", 0.3)
    
    def detect(self, features, frame, prev_features=None) -> Optional[DetectionEvent]:
        """Detect noise issues.
        
        Two types:
        1. Persistent background noise (high RMS + high zero-crossing rate)
        2. Sudden noise bursts (sudden RMS spike)
        """
        self.add_to_history(features, frame)
        
        rms = features.get("rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        
        # Check for persistent background noise
        # Noise typically has higher zero-crossing rate and moderate-high RMS
        if zcr > self.noise_zcr_threshold:
            # Likely noise (not clear voice)
            return DetectionEvent(
                event_type="noise",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=min(zcr / self.noise_zcr_threshold * 0.7, 1.0),
                details={"reason": "high_zero_crossing_rate", "zcr": zcr}
            )
        
        # Check for noise bursts (sudden RMS increase)
        if prev_features and len(self.history) >= 2:
            prev_rms = prev_features.get("rms", 0)
            rms_increase = (rms - prev_rms) / (prev_rms + 1e-6)
            
            if rms_increase > self.burst_spike_threshold:
                # Sudden noise burst
                return DetectionEvent(
                    event_type="noise",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=min(rms_increase / self.burst_spike_threshold * 0.5, 1.0),
                    details={"reason": "noise_burst", "rms_increase_ratio": rms_increase}
                )
        
        return None
