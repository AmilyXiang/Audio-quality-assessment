"""
增强失真检测器 - 支持持续失真检测

支持检测：
1. 瞬态失真（原有）- 点击、爆裂、突发失真
2. 持续失真（新增）- 合成语音、机器人语音、音质劣化
"""

import numpy as np
from typing import Optional
from .base import DetectionEvent, BaseDetector


class EnhancedDistortionDetector(BaseDetector):
    """
    增强失真检测器
    
    结合瞬态失真和持续失真检测
    """
    
    def __init__(self, baseline=None):
        super().__init__(baseline)
        self.event_type = "voice_distortion"
        
        # 瞬态失真阈值（原有）
        self.spectral_flux_threshold = 0.2
        self.centroid_shift_threshold = 500  # Hz
        self.bandwidth_spike_threshold = 1.5
        
        # 持续失真阈值（新增）
        self.spectral_consistency_threshold = 0.35  # 异常度
        self.formant_stability_threshold = 0.30     # 异常度
        self.mel_distortion_threshold = 0.40        # 异常度
        
        # 历史记录用于持续失真检测
        self.history_size = 20  # 200ms @ 100 FPS
        self.spectral_consistency_history = []
        self.formant_stability_history = []
        self.mel_distortion_history = []
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True):
        """
        检测失真
        
        Args:
            features: 当前帧特征字典
            frame: Frame对象
            prev_features: 前一帧特征
            is_voice_active: 是否为活跃语音
        
        Returns:
            Optional[DetectionEvent]: 检测到失真事件或None
        """
        if not is_voice_active or prev_features is None:
            return None
        
        # 检测1：瞬态失真（原有）
        transient_event = self._detect_transient_distortion(features, prev_features)
        if transient_event:
            return transient_event
        
        # 检测2：持续失真（新增）
        persistent_event = self._detect_persistent_distortion(features, frame)
        
        return persistent_event
    
    def _detect_transient_distortion(self, features, prev_features):
        """检测瞬态失真（点击、爆裂）"""
        
        if features.get('spectral_flux', 0) > self.spectral_flux_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, features['spectral_flux'] / 0.5)
            )
        
        # 中心频率快速偏移
        centroid_shift = abs(
            features.get('spectral_centroid', 0) - 
            prev_features.get('spectral_centroid', 0)
        )
        if centroid_shift > self.centroid_shift_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, centroid_shift / 1000)
            )
        
        # 带宽突增
        bandwidth_ratio = (
            (features.get('spectral_bandwidth', 1) + 1e-6) / 
            (prev_features.get('spectral_bandwidth', 1) + 1e-6)
        )
        if bandwidth_ratio > self.bandwidth_spike_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, bandwidth_ratio / 2.0)
            )
        
        return None
    
    def _detect_persistent_distortion(self, features, frame):
        """
        检测持续失真（合成、机器人、音质劣化）
        
        原理：
        - 正常人声：频谱、共鸣峰、Mel频谱有自然变化
        - 失真/合成语音：这些特征异常稳定或异常波动
        """
        
        # 计算异常指标
        spectral_consistency = self._compute_spectral_consistency(features)
        formant_stability = self._compute_formant_stability(features)
        mel_distortion = self._compute_mel_distortion(features)
        
        # 保存历史
        self.spectral_consistency_history.append(spectral_consistency)
        self.formant_stability_history.append(formant_stability)
        self.mel_distortion_history.append(mel_distortion)
        
        # 只保留最近N帧
        if len(self.spectral_consistency_history) > self.history_size:
            self.spectral_consistency_history.pop(0)
            self.formant_stability_history.pop(0)
            self.mel_distortion_history.pop(0)
        
        # 需要至少5帧（50ms）才能判断
        if len(self.spectral_consistency_history) < 5:
            return None
        
        # 检查多指标都异常 = 持续失真
        consistent_abnormal = np.mean(self.spectral_consistency_history[-5:]) > self.spectral_consistency_threshold
        formant_abnormal = np.mean(self.formant_stability_history[-5:]) > self.formant_stability_threshold
        mel_abnormal = np.mean(self.mel_distortion_history[-5:]) > self.mel_distortion_threshold
        
        # 需要至少2个指标异常
        anomaly_count = sum([consistent_abnormal, formant_abnormal, mel_abnormal])
        
        if anomaly_count >= 2:
            confidence = min(
                1.0,
                (spectral_consistency + formant_stability + mel_distortion) / 3.0
            )
            
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'] - 0.05,  # 回溯50ms
                end_time=features['timestamp'] + 0.01,
                confidence=confidence
            )
        
        return None
    
    def _compute_spectral_consistency(self, features):
        """
        计算频谱稳定性异常度 [0, 1]
        
        正常语音：频谱持续变化（自然发音）
        失真语音：频谱过度稳定（合成/机器人）或过度波动（严重失真）
        """
        
        # 基于频谱中心、带宽、过零率的一致性
        centroid = features.get('spectral_centroid', 2000)
        bandwidth = features.get('spectral_bandwidth', 1000)
        zcr = features.get('zero_crossing_rate', 0.1)
        rms = features.get('rms_energy', 0.01)
        
        # 特征异常度 = 偏离正常范围的程度
        # 正常人声范围（基于研究）
        normal_centroid_range = (200, 4000)  # Hz
        normal_bandwidth_range = (500, 3000)  # Hz
        normal_zcr_range = (0.03, 0.25)
        normal_rms_range = (0.001, 0.1)
        
        centroid_abnormal = (
            1.0 if centroid < normal_centroid_range[0] or centroid > normal_centroid_range[1]
            else 0.0
        )
        
        bandwidth_abnormal = (
            1.0 if bandwidth < normal_bandwidth_range[0] or bandwidth > normal_bandwidth_range[1]
            else 0.0
        )
        
        zcr_abnormal = (
            1.0 if zcr < normal_zcr_range[0] or zcr > normal_zcr_range[1]
            else 0.0
        )
        
        # 不一致度 = 特征组合不匹配
        # 例如：高中心频率 + 低带宽 + 低ZCR = 异常组合
        inconsistency = 0.0
        
        if centroid > 3000 and bandwidth < 800:
            inconsistency += 0.3  # 高频+窄带 = 可能合成
        
        if centroid < 1000 and zcr > 0.15:
            inconsistency += 0.2  # 低频+高ZCR = 异常
        
        if bandwidth > 2500 and rms < 0.005:
            inconsistency += 0.2  # 宽带+弱信号 = 失真
        
        # 综合异常度
        abnormality = (centroid_abnormal + bandwidth_abnormal + zcr_abnormal) / 3.0
        abnormality = max(abnormality, inconsistency)
        
        return abnormality
    
    def _compute_formant_stability(self, features):
        """
        计算共鸣峰稳定性异常度 [0, 1]
        
        使用频谱峰值作为共鸣峰代理
        正常语音：共鸣峰随音素自然变化
        失真语音：共鸣峰过度稳定或消失
        """
        
        centroid = features.get('spectral_centroid', 2000)
        bandwidth = features.get('spectral_bandwidth', 1000)
        flux = features.get('spectral_flux', 0.1)
        
        # 共鸣峰特征
        # 正常语音：频谱通常有2-3个明显峰值
        # 失真语音：峰值消失或错位
        
        # 使用中心频率和带宽推断峰值分布
        peak_spread = centroid / (bandwidth + 1e-6)
        
        # 异常指标：
        # - 峰值分布异常 (spread > 10 或 < 0.5)
        # - 频谱变化太小 (flux < 0.05)
        # - 频谱变化太大 (flux > 0.5)
        
        abnormality = 0.0
        
        if peak_spread > 10 or peak_spread < 0.5:
            abnormality += 0.3
        
        if flux < 0.05:  # 频谱过度稳定 = 合成/机器人
            abnormality += 0.4
        elif flux > 0.5:  # 频谱过度波动 = 严重失真
            abnormality += 0.3
        
        return min(1.0, abnormality)
    
    def _compute_mel_distortion(self, features):
        """
        基于Mel尺度的失真检测 [0, 1]
        
        Mel尺度模拟人耳感知
        失真语音在Mel域显示异常特征
        """
        
        centroid = features.get('spectral_centroid', 2000)
        bandwidth = features.get('spectral_bandwidth', 1000)
        zcr = features.get('zero_crossing_rate', 0.1)
        rms = features.get('rms_energy', 0.01)
        
        # Mel相关特征
        # 在Mel尺度上，正常语音特征在特定范围内
        
        # 1. 中心频率在Mel尺度上的位置
        mel_centroid = 2595 * np.log10(1 + centroid / 700)
        normal_mel_centroid_range = (300, 3000)  # Mel
        
        # 2. 带宽与中心频率比例
        bandwidth_ratio = bandwidth / (centroid + 1e-6)
        normal_bandwidth_ratio_range = (0.3, 2.0)
        
        # 3. 能量-频率不匹配
        # 低RMS但高频率 = 失真迹象
        energy_freq_mismatch = 0.0
        if rms < 0.01 and centroid > 3000:
            energy_freq_mismatch = 0.3
        elif rms > 0.05 and centroid < 500:
            energy_freq_mismatch = 0.2
        
        # 综合Mel失真度
        abnormality = 0.0
        
        if (mel_centroid < normal_mel_centroid_range[0] or 
            mel_centroid > normal_mel_centroid_range[1]):
            abnormality += 0.25
        
        if (bandwidth_ratio < normal_bandwidth_ratio_range[0] or 
            bandwidth_ratio > normal_bandwidth_ratio_range[1]):
            abnormality += 0.25
        
        abnormality += energy_freq_mismatch
        
        return min(1.0, abnormality)


# 为了简化集成，也保留原始DistortionDetector
class DistortionDetector(BaseDetector):
    """
    原始失真检测器（仅检测瞬态失真）
    
    如需增强功能，改用 EnhancedDistortionDetector
    """
    
    def __init__(self, baseline=None):
        super().__init__(baseline)
        self.event_type = "voice_distortion"
        self.spectral_flux_threshold = 0.2
        self.centroid_shift_threshold = 500  # Hz
        self.bandwidth_spike_threshold = 1.5

    def detect(self, features, frame, prev_features=None, is_voice_active=True):
        """检测失真事件"""
        
        if not is_voice_active or prev_features is None:
            return None

        if features.get('spectral_flux', 0) > self.spectral_flux_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, features['spectral_flux'] / 0.5)
            )

        centroid_shift = abs(
            features.get('spectral_centroid', 0) - 
            prev_features.get('spectral_centroid', 0)
        )
        if centroid_shift > self.centroid_shift_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, centroid_shift / 1000)
            )

        bandwidth_ratio = (
            (features.get('spectral_bandwidth', 1) + 1e-6) / 
            (prev_features.get('spectral_bandwidth', 1) + 1e-6)
        )
        if bandwidth_ratio > self.bandwidth_spike_threshold:
            return DetectionEvent(
                event_type=self.event_type,
                start_time=features['timestamp'],
                end_time=features['timestamp'] + 0.01,
                confidence=min(1.0, bandwidth_ratio / 2.0)
            )

        return None
