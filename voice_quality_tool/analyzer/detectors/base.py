"""Base detector class and utilities."""
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class DetectionEvent:
    """Represents a detected quality issue."""
    event_type: str      # noise, dropout, volume_fluctuation, distortion
    start_time: float
    end_time: float
    confidence: float    # 0.0 - 1.0
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    @property
    def duration(self) -> float:
        """Event duration in seconds."""
        return self.end_time - self.start_time


class BaseDetector:
    """Base class for all quality detectors."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.history = []  # Store recent frames/features for context
        self.max_history = 10
        self.baseline = None  # Adaptive baseline statistics
    
    def add_to_history(self, features, frame):
        """Maintain a rolling history for temporal analysis."""
        self.history.append({"features": features, "frame": frame})
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def set_baseline(self, baseline: Dict):
        """Set adaptive baseline for relative thresholding."""
        self.baseline = baseline
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect an issue in the current frame.
        
        Args:
            features: Current frame features
            frame: Current frame object
            prev_features: Previous frame features (optional)
            is_voice_active: Whether voice is active in this frame (VAD result)
        
        Returns None if no issue detected, or a DetectionEvent.
        """
        raise NotImplementedError


def merge_adjacent_events(events: List[DetectionEvent], gap_threshold=0.1) -> List[DetectionEvent]:
    """Merge detection events that are close together."""
    if not events:
        return []
    
    # Sort by start time
    sorted_events = sorted(events, key=lambda e: e.start_time)
    merged = [sorted_events[0]]
    
    for current in sorted_events[1:]:
        last = merged[-1]
        # If gap is small, merge
        if current.start_time - last.end_time < gap_threshold:
            merged[-1] = DetectionEvent(
                event_type=last.event_type,
                start_time=last.start_time,
                end_time=max(last.end_time, current.end_time),
                confidence=max(last.confidence, current.confidence),
                details={**last.details, **current.details}
            )
        else:
            merged.append(current)
    
    return merged


def filter_short_events(events: List[DetectionEvent], min_duration=0.3) -> List[DetectionEvent]:
    """过滤掉持续时间过短的事件（可能是环境干扰）.
    
    Args:
        events: 事件列表
        min_duration: 最小持续时间（秒），默认0.3秒
    
    Returns:
        过滤后的事件列表
    """
    return [e for e in events if e.duration >= min_duration]
