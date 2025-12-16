"""Event aggregation and result reporting."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .detectors.base import DetectionEvent


@dataclass
class AnalysisResult:
    """Aggregated result of voice quality analysis."""
    events: List[DetectionEvent] = field(default_factory=list)
    frames_processed: int = 0
    total_duration: float = 0.0
    
    def add_event(self, event: DetectionEvent):
        """Add a detected event."""
        self.events.append(event)
    
    def finalize(self, min_duration_dict=None):
        """Post-process: merge nearby events and filter short ones.
        
        Args:
            min_duration_dict: 按问题类型的最小持续时间字典
                              例如: {"noise": 0.15, "dropout": 0.05, ...}
                              如果为None，使用默认0.3秒
        """
        from .detectors.base import merge_adjacent_events, filter_short_events
        
        # 默认阈值
        if min_duration_dict is None:
            min_duration_dict = {
                "noise": 0.3,
                "dropout": 0.3,
                "volume_fluctuation": 0.3,
                "voice_distortion": 0.3,
            }
        
        # Merge events by type
        event_types = set(e.event_type for e in self.events)
        merged_all = []
        for event_type in event_types:
            type_events = [e for e in self.events if e.event_type == event_type]
            merged = merge_adjacent_events(type_events, gap_threshold=0.15)
            
            # 根据问题类型使用不同的最小持续时间
            type_min_duration = min_duration_dict.get(event_type, 0.3)
            filtered = filter_short_events(merged, min_duration=type_min_duration)
            merged_all.extend(filtered)
        
        self.events = sorted(merged_all, key=lambda e: e.start_time)
    
    def to_dict(self) -> Dict:
        """Export results as dictionary (format requested by user).
        
        Returns:
            {
                "noise": {"count": int, "events": [{"start": float, "end": float}, ...]},
                "dropout": {...},
                "volume_fluctuation": {...},
                "voice_distortion": {...}
            }
        """
        result = {
            "noise": {"count": 0, "events": []},
            "dropout": {"count": 0, "events": []},
            "volume_fluctuation": {"count": 0, "events": []},
            "voice_distortion": {"count": 0, "events": []}
        }
        
        for event in self.events:
            if event.event_type in result:
                result[event.event_type]["events"].append({
                    "start": round(event.start_time, 2),
                    "end": round(event.end_time, 2)
                })
        
        # Count events
        for key in result:
            result[key]["count"] = len(result[key]["events"])
        
        return result
    
    def to_json_string(self) -> str:
        """Export as JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)
    
    def print_summary(self):
        """Print human-readable summary."""
        data = self.to_dict()
        print("\n" + "="*60)
        print("VOICE QUALITY ANALYSIS REPORT")
        print("="*60)
        print(f"Total duration analyzed: {self.total_duration:.2f}s")
        print(f"Total frames: {self.frames_processed}")
        print()
        
        for issue_type in ["noise", "dropout", "volume_fluctuation", "voice_distortion"]:
            count = data[issue_type]["count"]
            events = data[issue_type]["events"]
            
            if count > 0:
                print(f"❌ {issue_type.upper()}: {count} issue(s)")
                for evt in events:
                    print(f"   [{evt['start']:.2f}s - {evt['end']:.2f}s]")
            else:
                print(f"✓ {issue_type.upper()}: OK")
        
        print("="*60 + "\n")
