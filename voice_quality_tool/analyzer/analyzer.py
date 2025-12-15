"""Main analyzer orchestrating all detectors."""
from typing import Iterable, Optional
from .frame import Frame
from .features import extract_features
from .result import AnalysisResult
from .detectors.noise import NoiseDetector
from .detectors.dropout import DropoutDetector
from .detectors.volume import VolumeDetector
from .detectors.distortion import DistortionDetector


# Default configuration for all detectors
DEFAULT_CONFIG = {
    # Noise detection
    "noise_zcr_threshold": 0.15,
    "burst_spike_threshold": 0.3,
    
    # Dropout detection
    "silence_rms_threshold": 0.01,
    "dropout_zcr_threshold": 0.05,
    
    # Volume fluctuation
    "rms_change_threshold": 0.4,
    
    # Distortion / voice change
    "spectral_flux_threshold": 0.2,
    "centroid_shift_threshold": 500.0,
    "bandwidth_spike_threshold": 1.5,
}


class Analyzer:
    """Main voice quality analyzer.
    
    Combines multiple detectors to identify quality issues:
    - Noise (background + burst)
    - Dropout (short silence, packet loss)
    - Volume fluctuation (AGC issues)
    - Voice distortion (spectral anomalies)
    """
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        
        # Initialize all detectors
        self.noise_detector = NoiseDetector(config=self.config)
        self.dropout_detector = DropoutDetector(config=self.config)
        self.volume_detector = VolumeDetector(config=self.config)
        self.distortion_detector = DistortionDetector(config=self.config)
        
        self.prev_features = None
        self.prev_frame = None
    
    def analyze_frames(self, frames: Iterable[Frame]) -> AnalysisResult:
        """Analyze an iterable of frames and return aggregated result.
        
        Args:
            frames: Iterator of Frame objects
        
        Returns:
            AnalysisResult with detected events
        """
        result = AnalysisResult()
        
        for frame in frames:
            # Extract features from current frame
            features = extract_features(frame, self.prev_frame)
            
            result.frames_processed += 1
            if result.total_duration < frame.end_time:
                result.total_duration = frame.end_time
            
            # Run all detectors
            detectors = [
                self.noise_detector,
                self.dropout_detector,
                self.volume_detector,
                self.distortion_detector,
            ]
            
            for detector in detectors:
                event = detector.detect(features, frame, prev_features=self.prev_features)
                if event:
                    result.add_event(event)
            
            # Update state for next iteration
            self.prev_features = features
            self.prev_frame = frame
        
        # Post-process: merge nearby events
        result.finalize()
        return result
