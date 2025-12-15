"""Distortion / voice change detection: spectral abnormalities.

This is the key component for detecting encoding issues, echo cancellation errors,
frequency response anomalies that degrade voice quality.
"""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class DistortionDetector(BaseDetector):
    """Detects voice distortion and spectral anomalies.
    
    Key signals:
    - Sudden spectral centroid shift (voice becomes tinny/muffled)
    - High spectral flux (spectrum changes abruptly, frame-to-frame)
    - Codec artifacts, echo cancellation misfire
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.spectral_flux_threshold = self.config.get("spectral_flux_threshold", 0.2)
        self.centroid_shift_threshold = self.config.get("centroid_shift_threshold", 500.0)  # Hz
        self.bandwidth_spike_threshold = self.config.get("bandwidth_spike_threshold", 1.5)
    
    def detect(self, features, frame, prev_features=None) -> Optional[DetectionEvent]:
        """Detect voice distortion via spectral analysis.
        
        Distortion signals:
        1. High spectral flux = rapid spectrum change (encoding artifact, echo cancellation gone wrong)
        2. Centroid shift = voice becomes tinny (high freq boost) or muffled (high freq cut)
        3. Bandwidth spike = sudden frequency spreading (codec breakage)
        """
        self.add_to_history(features, frame)
        
        spectral_flux = features.get("spectral_flux", 0)
        centroid = features.get("spectral_centroid", 0)
        bandwidth = features.get("spectral_bandwidth", 0)
        rms = features.get("rms", 0)
        
        # Skip if essentially silent
        if rms < 0.01:
            return None
        
        # Check for high spectral flux (sudden spectrum change)
        if spectral_flux > self.spectral_flux_threshold:
            confidence = min(spectral_flux / self.spectral_flux_threshold * 0.7, 1.0)
            return DetectionEvent(
                event_type="voice_distortion",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "high_spectral_flux",
                    "spectral_flux": spectral_flux,
                    "centroid": centroid
                }
            )
        
        # Check for centroid shift (frequency response anomaly)
        if prev_features:
            prev_centroid = prev_features.get("spectral_centroid", centroid)
            centroid_shift = abs(centroid - prev_centroid)
            
            if centroid_shift > self.centroid_shift_threshold:
                confidence = min(centroid_shift / self.centroid_shift_threshold * 0.6, 1.0)
                return DetectionEvent(
                    event_type="voice_distortion",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=confidence,
                    details={
                        "reason": "abrupt_centroid_shift",
                        "centroid_shift": centroid_shift,
                        "prev_centroid": prev_centroid,
                        "curr_centroid": centroid
                    }
                )
        
        # Check for bandwidth spike
        if prev_features:
            prev_bandwidth = prev_features.get("spectral_bandwidth", bandwidth)
            bandwidth_ratio = (bandwidth + 1.0) / (prev_bandwidth + 1.0)
            
            if bandwidth_ratio > self.bandwidth_spike_threshold:
                confidence = min((bandwidth_ratio - 1.0) / (self.bandwidth_spike_threshold - 1.0) * 0.5, 1.0)
                return DetectionEvent(
                    event_type="voice_distortion",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=confidence,
                    details={
                        "reason": "bandwidth_spike",
                        "bandwidth_ratio": bandwidth_ratio
                    }
                )
        
        return None
