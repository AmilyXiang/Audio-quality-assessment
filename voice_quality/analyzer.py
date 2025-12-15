"""Main analyzer for offline and real-time processing."""
from typing import Iterable, List
from .frame import Frame
from .features import extract_features
from .result import AnalysisResult
from .config import DEFAULT_CONFIG


class Analyzer:
    def __init__(self, config=DEFAULT_CONFIG):
        self.config = config

    def analyze_frames(self, frames: Iterable[Frame]) -> AnalysisResult:
        """Analyze an iterable of frames and return aggregated result."""
        result = AnalysisResult()
        for frame in frames:
            feats = extract_features(frame)
            result.add_frame_features(frame, feats)
        result.finalize()
        return result


def analyze_audio_stream(stream) -> AnalysisResult:
    """Example helper (placeholder). Accepts a stream or iterator of frames."""
    analyzer = Analyzer()
    return analyzer.analyze_frames(stream)
