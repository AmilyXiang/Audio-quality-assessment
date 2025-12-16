"""Dropout / packet-loss detection: short silence and intermittent audio."""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class DropoutDetector(BaseDetector):
    """Detects audio dropouts (short silences, packet loss effects)."""
    
    def __init__(self, config=None):
        super().__init__(config)
        # Very low energy = silence
        self.silence_rms_threshold = self.config.get("silence_rms_threshold", 0.01)
        self.dropout_zcr_threshold = self.config.get("dropout_zcr_threshold", 0.05)
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect dropout events.
        
        Dropout = sudden drop to silence (very low RMS + very low ZCR)
        Indicates buffer underrun, network loss, or codec issue.
        """
        self.add_to_history(features, frame)
        
        rms = features.get("rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        
        # Dropout: both RMS and ZCR are very low
        if rms < self.silence_rms_threshold and zcr < self.dropout_zcr_threshold:
            confidence = 0.8 if rms < self.silence_rms_threshold * 0.5 else 0.5
            
            return DetectionEvent(
                event_type="dropout",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={"reason": "short_silence", "rms": rms, "zcr": zcr}
            )
        
        return None
