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
    global_features: Optional[Dict] = None
    global_comparison: Optional[Dict] = None
    global_assessment: Optional[Dict] = None
    llm_advice: Optional[str] = None
    llm_meta: Optional[Dict] = None
    llm_audio_summary: Optional[Dict] = None
    
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
            "meta": {
                "frames_processed": self.frames_processed,
                "total_duration": round(self.total_duration, 2),
            },
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
            if key == "meta":
                continue
            result[key]["count"] = len(result[key]["events"])

        # Optional: global distortion analyzer outputs
        if self.global_features is not None or self.global_comparison is not None:
            result["global"] = {
                "features": self.global_features,
                "comparison": self.global_comparison,
                "assessment": self.global_assessment,
            }

        # Optional: LLM enrichment
        if self.llm_advice is not None:
            result["llm"] = {
                "advice": self.llm_advice,
                "meta": self.llm_meta or {},
            }

        # Optional: keep the compact audio summary used for LLM (route-1)
        if self.llm_audio_summary is not None:
            result.setdefault("llm", {"meta": self.llm_meta or {}})
            result["llm"]["audio_summary"] = self.llm_audio_summary
        
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

        # Global distortion summary (system-level / whole-file)
        global_block = data.get("global")
        if global_block and global_block.get("assessment"):
            qa = global_block["assessment"]
            overall = qa.get("overall_quality", "(unknown)")
            score = qa.get("quality_score", None)
            comp = global_block.get("comparison") or {}
            odi = comp.get("overall_distortion_index", None)

            is_ok = isinstance(score, (int, float)) and score >= 0.85
            prefix = "✓" if is_ok else "❌"

            extra = []
            if isinstance(score, (int, float)):
                extra.append(f"score={score:.2f}")
            if isinstance(odi, (int, float)):
                extra.append(f"baseline_diff={odi:.2%}")
            extra_text = (" (" + ", ".join(extra) + ")") if extra else ""

            print(f"{prefix} GLOBAL_DISTORTION: {overall}{extra_text}")
        else:
            print("- GLOBAL_DISTORTION: (not available)")
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
