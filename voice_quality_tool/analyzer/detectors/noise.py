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
        """Detect noise issues using baseline-relative thresholds.
        
        Three types:
        1. Persistent background noise (ZCR exceeds baseline + 2*std)
        2. Sudden noise bursts (RMS spike or RMS_P95 anomaly)
        3. High-frequency noise (spectral rolloff exceeds baseline)
        
        Requires baseline to be set via set_baseline() - raises error if missing.
        """
        # ✅ 强制要求baseline
        if not self.baseline:
            raise RuntimeError("❌ NoiseDetector requires baseline! Run calibrate.py first.")
        
        self.add_to_history(features, frame)
        
        rms = features.get("rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        spectral_rolloff = features.get("spectral_rolloff", 0)
        rms_p95 = features.get("rms_percentile_95", 0)
        
        # 从baseline计算自适应阈值
        baseline_zcr_mean = self.baseline.get("zcr_mean", 0.1)
        baseline_zcr_std = self.baseline.get("zcr_std", 0.03)
        baseline_rolloff_mean = self.baseline.get("spectral_rolloff_mean", 2000)
        baseline_rolloff_std = self.baseline.get("spectral_rolloff_std", 500)
        baseline_rms_mean = self.baseline.get("rms_mean", 0.1)
        baseline_rms_std = self.baseline.get("rms_std", 0.05)
        
        # 方法1: 持久性背景噪声检测（基于ZCR相对baseline）
        adaptive_zcr_threshold = baseline_zcr_mean + 2.0 * baseline_zcr_std
        if self.detect_background_noise and zcr > adaptive_zcr_threshold:
            return DetectionEvent(
                event_type="noise",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=min(zcr / adaptive_zcr_threshold * 0.7, 1.0),
                details={
                    "reason": "high_zero_crossing_rate_vs_baseline",
                    "zcr": zcr,
                    "baseline_zcr": baseline_zcr_mean,
                    "threshold": adaptive_zcr_threshold
                }
            )
        
        # 方法2: 突发噪声检测（基于RMS增幅相对baseline）
        if prev_features and len(self.history) >= 2:
            prev_rms = prev_features.get("rms", 0)
            rms_increase = (rms - prev_rms) / (prev_rms + 1e-6)
            
            # 相对baseline判断是否为异常突增
            # 正常RMS波动 = baseline_std * 3，超过则为异常
            normal_rms_change = baseline_rms_std * 3
            rms_change_abs = abs(rms - baseline_rms_mean)
            
            if rms_change_abs > normal_rms_change or rms_p95 > baseline_rms_mean * 2:
                return DetectionEvent(
                    event_type="noise",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=min(rms_change_abs / normal_rms_change * 0.6, 1.0),
                    details={
                        "reason": "noise_burst_vs_baseline",
                        "rms_increase_ratio": rms_increase,
                        "rms_p95": rms_p95,
                        "baseline_rms": baseline_rms_mean,
                        "rms_change": rms_change_abs
                    }
                )
        
        # 方法3: 高频噪声检测（风噪）- 相对baseline
        adaptive_rolloff_threshold = baseline_rolloff_mean + 2.0 * baseline_rolloff_std
        if spectral_rolloff > adaptive_rolloff_threshold:
            return DetectionEvent(
                event_type="noise",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=min((spectral_rolloff / adaptive_rolloff_threshold - 1.0) * 0.5, 1.0),
                details={
                    "reason": "high_frequency_noise_vs_baseline",
                    "spectral_rolloff": spectral_rolloff,
                    "baseline_rolloff": baseline_rolloff_mean,
                    "threshold": adaptive_rolloff_threshold
                }
            )
        
        return None
