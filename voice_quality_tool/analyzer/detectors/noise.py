"""Noise detection: background noise and sudden noise bursts."""
from typing import Optional
from .base import BaseDetector, DetectionEvent
import numpy as np


class NoiseDetector(BaseDetector):
    """Detects persistent background noise and sudden noise bursts."""
    
    def __init__(self, config=None):
        super().__init__(config)
        # Thresholds for noise detection
        self.detect_background_noise = self.config.get("detect_background_noise", False)  # 默认不检测背景噪声
        self.high_noise_rms = self.config.get("high_noise_rms_threshold", 0.15)
        self.noise_zcr_threshold = self.config.get("noise_zcr_threshold", 0.15)
        self.burst_spike_threshold = self.config.get("burst_spike_threshold", 0.3)
        
        # 第1阶段特征阈值
        self.spectral_rolloff_threshold = self.config.get("spectral_rolloff_threshold", 3000)  # Hz，>3kHz为风噪
        self.rms_percentile_threshold = self.config.get("rms_percentile_threshold", 0.3)
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect noise issues.
        
        Three types:
        1. Persistent background noise (high RMS + high zero-crossing rate)
        2. Sudden noise bursts (sudden RMS spike using RMS percentile)
        3. High-frequency noise (wind noise, spectral roll-off check)
        """
        self.add_to_history(features, frame)
        
        rms = features.get("rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        spectral_rolloff = features.get("spectral_rolloff", 0)
        rms_p95 = features.get("rms_percentile_95", 0)
        
        # 方法1: 持久性背景噪声检测（基于ZCR）
        if self.detect_background_noise and zcr > self.noise_zcr_threshold:
            return DetectionEvent(
                event_type="noise",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=min(zcr / self.noise_zcr_threshold * 0.7, 1.0),
                details={"reason": "high_zero_crossing_rate", "zcr": zcr}
            )
        
        # 方法2: 突发噪声检测（基于RMS增幅或RMS_P95）
        if prev_features and len(self.history) >= 2:
            prev_rms = prev_features.get("rms", 0)
            rms_increase = (rms - prev_rms) / (prev_rms + 1e-6)
            
            # 使用RMS_P95提高对瞬态爆音的敏感性
            if rms_increase > self.burst_spike_threshold or rms_p95 > rms * 1.5:
                return DetectionEvent(
                    event_type="noise",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=min(max(rms_increase, rms_p95 / rms) / self.burst_spike_threshold * 0.5, 1.0),
                    details={
                        "reason": "noise_burst_with_transient",
                        "rms_increase_ratio": rms_increase,
                        "rms_p95": rms_p95
                    }
                )
        
        # 方法3: 高频噪声检测（风噪）- 第1阶段特征
        if spectral_rolloff > self.spectral_rolloff_threshold:
            return DetectionEvent(
                event_type="noise",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=min((spectral_rolloff / self.spectral_rolloff_threshold - 1.0) * 0.5, 1.0),
                details={
                    "reason": "high_frequency_noise_windnoise",
                    "spectral_rolloff": spectral_rolloff
                }
            )
        
        return None
