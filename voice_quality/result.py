"""Event aggregation and analysis result."""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Event:
    event: str
    start_time: float
    end_time: float
    score: float
    details: Dict = field(default_factory=dict)


@dataclass
class AnalysisResult:
    events: List[Event] = field(default_factory=list)
    frames_processed: int = 0

    def add_frame_features(self, frame, features):
        self.frames_processed += 1
        # placeholder: detectors should add events via a plugin system

    def add_event(self, event: Event):
        self.events.append(event)

    def finalize(self):
        # post-process events, e.g., merge contiguous ones
        pass
