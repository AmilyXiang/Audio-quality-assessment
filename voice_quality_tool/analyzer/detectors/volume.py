"""Volume fluctuation detection: abnormal loudness changes (AGC issues)."""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class VolumeDetector(BaseDetector):
    """Detects abnormal volume fluctuations (AGC pumping, inconsistent levels)."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.rms_change_threshold = self.config.get("rms_change_threshold", 0.4)
        self.min_history_frames = 3
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect volume fluctuation issues.
        
        Detects:
        1. Sudden loud spikes
        2. Rapid RMS changes (AGC pumping effect)
        """
        self.add_to_history(features, frame)
        
        if len(self.history) < self.min_history_frames:
            return None
        
        rms = features.get("rms", 0)
        
        # Compute RMS variance over recent history
        recent_rms = [h["features"]["rms"] for h in self.history[-3:]]
        
        if not recent_rms or max(recent_rms) == 0:
            return None
        
        rms_ratio = max(recent_rms) / (min(recent_rms) + 1e-6)
        
        # If RMS varies wildly in short time, it's a fluctuation
        if rms_ratio > (1.0 + self.rms_change_threshold):
            confidence = min((rms_ratio - 1.0) / self.rms_change_threshold * 0.8, 1.0)
            
            return DetectionEvent(
                event_type="volume_fluctuation",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "rapid_rms_change",
                    "rms_ratio": rms_ratio,
                    "current_rms": rms
                }
            )
        
        return None
