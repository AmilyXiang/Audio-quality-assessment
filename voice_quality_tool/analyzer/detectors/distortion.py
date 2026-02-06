"""Distortion / voice change detection: spectral abnormalities.

This is the key component for detecting encoding issues, echo cancellation errors,
frequency response anomalies that degrade voice quality.
"""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class DistortionDetector(BaseDetector):
    """Detects voice distortion and spectral anomalies using baseline-relative thresholds.
    
    Key signals:
    - Sudden spectral centroid shift (voice becomes tinny/muffled)
    - High spectral flux (spectrum changes abruptly, frame-to-frame)
    - Bandwidth anomalies (codec artifacts)
    - Audio clipping (peak-to-peak near maximum)
    
    Requires baseline calibration to operate.
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.spectral_flux_threshold = self.config.get("spectral_flux_threshold", 0.2)
        self.centroid_shift_threshold = self.config.get("centroid_shift_threshold", 500.0)  # Hz
        self.bandwidth_spike_threshold = self.config.get("bandwidth_spike_threshold", 1.5)
        self.peak_to_peak_threshold = self.config.get("peak_to_peak_threshold", 1.8)
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect voice distortion using baseline-relative thresholds.
        
        基于标定基线对比（强制要求 baseline）：
        1. 高频谱流量 = 相比基线频谱突变（编码失真、回声消除错误）
        2. 质心偏移 = 相比基线音色变化（变尖锐/低沉）
        3. 带宽激增 = 相比基线频率分布异常（编解码器崩溃）
        4. 削波检测 = Peak-to-Peak接近最大值（音频失真的直接证据）
        
        Requires baseline to be set via set_baseline() - raises error if missing.
        """
        # ✅ 强制要求baseline
        if not self.baseline:
            raise RuntimeError("❌ DistortionDetector requires baseline! Run calibrate.py first.")
        
        self.add_to_history(features, frame)
        
        spectral_flux = features.get("spectral_flux", 0)
        centroid = features.get("spectral_centroid", 0)
        bandwidth = features.get("spectral_bandwidth", 0)
        rms = features.get("rms", 0)
        peak_to_peak = features.get("peak_to_peak", 0)
        
        # 削波检测 - 第1阶段特征（优先检查，直接指标）
        if peak_to_peak > self.peak_to_peak_threshold:
            confidence = min((peak_to_peak / 2.0) ** 1.5, 1.0)
            return DetectionEvent(
                event_type="voice_distortion",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "audio_clipping",
                    "peak_to_peak": peak_to_peak,
                    "threshold": self.peak_to_peak_threshold
                }
            )
        
        # Skip if essentially silent
        if rms < 0.01:
            return None
        
        # 基于baseline的相对检测（强制模式）
        baseline_flux_mean = self.baseline.get("spectral_flux_mean", 0.1)
        baseline_flux_std = self.baseline.get("spectral_flux_std", 0.05)
        baseline_centroid_mean = self.baseline.get("centroid_mean", 1000)
        baseline_centroid_std = self.baseline.get("centroid_std", 200)
        baseline_bandwidth_mean = self.baseline.get("spectral_bandwidth_mean", 500)
        baseline_bandwidth_std = self.baseline.get("spectral_bandwidth_std", 100)
        
        # 检测高频谱流量（超过baseline + 3*std）
        adaptive_flux_threshold = baseline_flux_mean + 3.0 * baseline_flux_std
        if spectral_flux > adaptive_flux_threshold:
            confidence = min((spectral_flux / adaptive_flux_threshold - 1.0) * 0.7, 1.0)
            return DetectionEvent(
                event_type="voice_distortion",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "high_spectral_flux_vs_baseline",
                    "spectral_flux": spectral_flux,
                    "baseline_flux_mean": baseline_flux_mean,
                    "threshold": adaptive_flux_threshold
                }
            )
        
        # 检测质心偏移（超过baseline ± 3*std）
        centroid_deviation = abs(centroid - baseline_centroid_mean)
        adaptive_centroid_threshold = 3.0 * baseline_centroid_std
        if centroid_deviation > adaptive_centroid_threshold:
            confidence = min(centroid_deviation / adaptive_centroid_threshold * 0.6, 1.0)
            return DetectionEvent(
                event_type="voice_distortion",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "centroid_deviation_vs_baseline",
                    "centroid_deviation": centroid_deviation,
                    "baseline_centroid": baseline_centroid_mean,
                    "curr_centroid": centroid,
                    "threshold": adaptive_centroid_threshold
                }
            )
        
        # 检测带宽激增（超过baseline + 3*std）
        bandwidth_deviation = abs(bandwidth - baseline_bandwidth_mean)
        adaptive_bandwidth_threshold = 3.0 * baseline_bandwidth_std
        if bandwidth_deviation > adaptive_bandwidth_threshold:
            confidence = min(bandwidth_deviation / adaptive_bandwidth_threshold * 0.5, 1.0)
            return DetectionEvent(
                event_type="voice_distortion",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=confidence,
                details={
                    "reason": "bandwidth_deviation_vs_baseline",
                    "bandwidth_deviation": bandwidth_deviation,
                    "baseline_bandwidth": baseline_bandwidth_mean,
                    "curr_bandwidth": bandwidth,
                    "threshold": adaptive_bandwidth_threshold
                }
            )
        
        return None
