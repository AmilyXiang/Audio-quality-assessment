"""Distortion / voice change detection: spectral abnormalities.

This is the key component for detecting encoding issues, echo cancellation errors,
frequency response anomalies that degrade voice quality.
"""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class DistortionDetector(BaseDetector):
    """Detects voice distortion and spectral anomalies.
    
    Key signals:
    - Sudden spectral centroid shift (voice becomes tinny/muffled)
    - High spectral flux (spectrum changes abruptly, frame-to-frame)
    - Codec artifacts, echo cancellation misfire
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.spectral_flux_threshold = self.config.get("spectral_flux_threshold", 0.2)
        self.centroid_shift_threshold = self.config.get("centroid_shift_threshold", 500.0)  # Hz
        self.bandwidth_spike_threshold = self.config.get("bandwidth_spike_threshold", 1.5)
        # 第1阶段特征：削波检测
        self.peak_to_peak_threshold = self.config.get("peak_to_peak_threshold", 1.8)  # 接近1.9为削波
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect voice distortion via spectral analysis and clipping detection.
        
        基于标定基线对比（需要先调用 set_baseline）：
        1. 高频谱流量 = 相比基线频谱突变（编码失真、回声消除错误）
        2. 质心偏移 = 相比基线音色变化（变尖锐/低沉）
        3. 带宽激增 = 相比基线频率分布异常（编解码器崩溃）
        4. 削波检测 = Peak-to-Peak接近最大值（音频失真的直接证据）
        
        如果未设置 baseline，则使用相邻帧对比（兼容模式）
        """
        self.add_to_history(features, frame)
        
        spectral_flux = features.get("spectral_flux", 0)
        centroid = features.get("spectral_centroid", 0)
        bandwidth = features.get("spectral_bandwidth", 0)
        rms = features.get("rms", 0)
        peak_to_peak = features.get("peak_to_peak", 0)  # 第1阶段特征
        
        # 削波检测 - 第1阶段特征（优先检查，直接指标）
        if peak_to_peak > self.peak_to_peak_threshold:
            confidence = min((peak_to_peak / 2.0) ** 1.5, 1.0)  # 接近2.0时confidence接近1.0
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
        
        # 模式1：基于 baseline 对比（推荐）
        if self.baseline:
            baseline_flux = self.baseline.get("spectral_flux", 0)
            baseline_centroid = self.baseline.get("spectral_centroid", 0)
            baseline_bandwidth = self.baseline.get("spectral_bandwidth", 0)
            
            # 检测高频谱流量（相比基线）
            if baseline_flux > 0:
                flux_ratio = spectral_flux / baseline_flux
                if flux_ratio > 2.0:  # 超过基线2倍
                    confidence = min((flux_ratio - 1.0) / 2.0 * 0.7, 1.0)
                    return DetectionEvent(
                        event_type="voice_distortion",
                        start_time=frame.start_time,
                        end_time=frame.end_time,
                        confidence=confidence,
                        details={
                            "reason": "high_spectral_flux_vs_baseline",
                            "spectral_flux": spectral_flux,
                            "baseline_flux": baseline_flux,
                            "flux_ratio": flux_ratio
                        }
                    )
            
            # 检测质心偏移（相比基线）
            centroid_shift = abs(centroid - baseline_centroid)
            if centroid_shift > self.centroid_shift_threshold:
                confidence = min(centroid_shift / self.centroid_shift_threshold * 0.6, 1.0)
                return DetectionEvent(
                    event_type="voice_distortion",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=confidence,
                    details={
                        "reason": "centroid_shift_vs_baseline",
                        "centroid_shift": centroid_shift,
                        "baseline_centroid": baseline_centroid,
                        "curr_centroid": centroid
                    }
                )
            
            # 检测带宽激增（相比基线）
            if baseline_bandwidth > 0:
                bandwidth_ratio = bandwidth / baseline_bandwidth
                if bandwidth_ratio > self.bandwidth_spike_threshold:
                    confidence = min((bandwidth_ratio - 1.0) / (self.bandwidth_spike_threshold - 1.0) * 0.5, 1.0)
                    return DetectionEvent(
                        event_type="voice_distortion",
                        start_time=frame.start_time,
                        end_time=frame.end_time,
                        confidence=confidence,
                        details={
                            "reason": "bandwidth_spike_vs_baseline",
                            "bandwidth_ratio": bandwidth_ratio,
                            "baseline_bandwidth": baseline_bandwidth,
                            "curr_bandwidth": bandwidth
                        }
                    )
        
        # 模式2：相邻帧对比（兼容模式，未标定时使用）
        else:
            # Check for high spectral flux (sudden spectrum change)
            if spectral_flux > self.spectral_flux_threshold:
                confidence = min(spectral_flux / self.spectral_flux_threshold * 0.7, 1.0)
                return DetectionEvent(
                    event_type="voice_distortion",
                    start_time=frame.start_time,
                    end_time=frame.end_time,
                    confidence=confidence,
                    details={
                        "reason": "high_spectral_flux",
                        "spectral_flux": spectral_flux,
                        "centroid": centroid
                    }
                )
            
            # Check for centroid shift (frequency response anomaly)
            if prev_features:
                prev_centroid = prev_features.get("spectral_centroid", centroid)
                centroid_shift = abs(centroid - prev_centroid)
                
                if centroid_shift > self.centroid_shift_threshold:
                    confidence = min(centroid_shift / self.centroid_shift_threshold * 0.6, 1.0)
                    return DetectionEvent(
                        event_type="voice_distortion",
                        start_time=frame.start_time,
                        end_time=frame.end_time,
                        confidence=confidence,
                        details={
                            "reason": "abrupt_centroid_shift",
                            "centroid_shift": centroid_shift,
                            "prev_centroid": prev_centroid,
                            "curr_centroid": centroid
                        }
                    )
            
            # Check for bandwidth spike
            if prev_features:
                prev_bandwidth = prev_features.get("spectral_bandwidth", bandwidth)
                bandwidth_ratio = (bandwidth + 1.0) / (prev_bandwidth + 1.0)
                
                if bandwidth_ratio > self.bandwidth_spike_threshold:
                    confidence = min((bandwidth_ratio - 1.0) / (self.bandwidth_spike_threshold - 1.0) * 0.5, 1.0)
                    return DetectionEvent(
                        event_type="voice_distortion",
                        start_time=frame.start_time,
                        end_time=frame.end_time,
                        confidence=confidence,
                        details={
                            "reason": "bandwidth_spike",
                            "bandwidth_ratio": bandwidth_ratio
                        }
                    )
        
        return None
