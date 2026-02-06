"""Dropout / packet-loss detection: short silence, packet loss, and sudden level changes."""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class DropoutDetector(BaseDetector):
    """Detects sudden/abrupt dropouts (short silence bursts).
    
    检测以下问题：
    - 短暂的、突然的无声段落（网络丢包、缓冲区欠流、编码器停顿）
    - 只检测"有声→无声→有声"的突变，而非持续静音
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        # Silence detection parameters
        self.silence_rms_threshold = self.config.get("silence_rms_threshold", 0.01)
        self.dropout_zcr_threshold = self.config.get("dropout_zcr_threshold", 0.05)
        # State tracking for detecting transitions
        self.prev_is_silence = False
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect sudden/abrupt dropout using baseline-relative silence threshold.
        
        只检测"短暂的、突然的"静音，不检测持续的静音：
        - 检测有声 → 无声的转换（dropout开始）
        - 静音定义：RMS < baseline_p10 * 0.5
        
        Requires baseline to be set via set_baseline() - raises error if missing.
        """
        # ✅ 强制要求baseline
        if not self.baseline:
            raise RuntimeError("❌ DropoutDetector requires baseline! Run calibrate.py first.")
        
        self.add_to_history(features, frame)
        
        rms = features.get("rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        
        # 从baseline计算自适应静音阈值
        # 静音 = RMS低于baseline的10%分位数的一半
        baseline_rms_p10 = self.baseline.get("rms_p10", 0.02)
        adaptive_silence_threshold = baseline_rms_p10 * 0.5
        
        baseline_zcr_mean = self.baseline.get("zcr_mean", 0.1)
        baseline_zcr_std = self.baseline.get("zcr_std", 0.03)
        adaptive_zcr_threshold = max(baseline_zcr_mean - 2 * baseline_zcr_std, 0.02)
        
        # 判断当前帧是否为静音（相对baseline）
        is_silence = rms < adaptive_silence_threshold and zcr < adaptive_zcr_threshold
        
        # 检测边界：从有声转为无声（dropout开始）
        if is_silence and not self.prev_is_silence:
            # 刚进入静音状态 - 报告卡顿事件
            confidence = 0.9 if rms < self.silence_rms_threshold / 2 else 0.7
            
            self.prev_is_silence = is_silence
            
            return DetectionEvent(
                event_type="dropout",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "sudden_silence_dropout_vs_baseline",
                    "rms": rms,
                    "threshold": adaptive_silence_threshold,
                    "baseline_rms_p10": baseline_rms_p10,
                    "zcr": zcr
                }
            )
        
        # 更新状态
        self.prev_is_silence = is_silence
        
        return None
