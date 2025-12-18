"""Main analyzer orchestrating all detectors."""
from typing import Iterable, Optional
from .frame import Frame
from .features import extract_features
from .result import AnalysisResult
from .detectors.noise import NoiseDetector
from .detectors.dropout import DropoutDetector
from .detectors.volume import VolumeDetector
from .detectors.distortion import DistortionDetector
from .vad import is_voice_active, compute_baseline_stats


# Default configuration for all detectors
DEFAULT_CONFIG = {
    # VAD (Voice Activity Detection)
    "enable_vad": True,               # 启用VAD过滤
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # Baseline calibration
    "enable_adaptive_threshold": False,  # 自适应阈值（需要先校准）
    
    # 人耳感知阈值（基于声学研究和ITU-T标准）
    # 不同问题类型的人耳敏感度不同，需要差异化处理
    "min_event_duration": {
        "noise": 0.15,                # 噪声：150ms（短暂噪音爆发通常被忽略）
        "dropout": 0.05,              # 卡顿：50ms（最敏感！>20ms就能察觉）
        "volume_fluctuation": 0.25,   # 音量起伏：250ms（人耳对音量变化相对迟钝）
        "voice_distortion": 0.12,     # 变声：120ms（对音色敏感，但瞬时变化不明显）
    },
    
    # Noise detection
    "detect_background_noise": False,  # 默认不检测背景噪声，只检测突发噪声
    "noise_zcr_threshold": 0.15,
    "burst_spike_threshold": 0.3,
    
    # Dropout detection (只检测静音卡顿)
    "silence_rms_threshold": 0.01,
    "dropout_zcr_threshold": 0.05,
    
    # Volume fluctuation detection
    "rms_change_threshold": 0.5,  # 音量波动阈值（50%变化，改为严格模式减少误报）
    
    # Distortion / voice change
    "spectral_flux_threshold": 0.2,
    "centroid_shift_threshold": 500.0,
    "bandwidth_spike_threshold": 1.5,
}

# 干净语音配置：适用于录音室、播客等高质量专业录音
# 参数值比默认配置放宽 4 倍，减少误报
CLEAN_SPEECH_CONFIG = {
    **DEFAULT_CONFIG,
    "min_event_duration": {
        "noise": 0.60,                # 默认150ms → 600ms
        "dropout": 0.20,              # 默认50ms → 200ms
        "volume_fluctuation": 1.00,   # 默认250ms → 1000ms
        "voice_distortion": 0.50,     # 默认120ms → 500ms
    },
}


class Analyzer:
    """Main voice quality analyzer.
    
    Combines multiple detectors to identify quality issues:
    - Noise (background + burst)
    - Dropout (short silence, packet loss)
    - Volume fluctuation (AGC issues)
    - Voice distortion (spectral anomalies)
    
    支持：
    - VAD（语音活动检测）过滤非人声段
    - 自适应阈值（基于音频基线统计）
    - 持续性过滤（忽略短暂干扰）
    """
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        
        # Initialize all detectors
        self.noise_detector = NoiseDetector(config=self.config)
        self.dropout_detector = DropoutDetector(config=self.config)
        self.volume_detector = VolumeDetector(config=self.config)
        self.distortion_detector = DistortionDetector(config=self.config)
        
        self.prev_features = None
        self.prev_frame = None
        self.all_features = []  # For baseline calibration
    
    def calibrate(self, frames: Iterable[Frame]) -> dict:
        """校准模式：分析音频以建立基线统计.
        
        用于：
        - 学习设备固有特性
        - 学习环境背景噪声水平
        - 生成自适应阈值
        
        Args:
            frames: 校准用的音频帧
        
        Returns:
            基线统计字典
        """
        calibration_features = []
        
        for frame in frames:
            features = extract_features(frame, self.prev_frame)
            calibration_features.append(features)
            self.prev_frame = frame
        
        baseline = compute_baseline_stats(calibration_features)
        
        # Set baseline to all detectors
        for detector in [self.noise_detector, self.dropout_detector, 
                        self.volume_detector, self.distortion_detector]:
            detector.set_baseline(baseline)
        
        return baseline
    
    def analyze_frames(self, frames: Iterable[Frame]) -> AnalysisResult:
        """Analyze an iterable of frames and return aggregated result.
        
        Args:
            frames: Iterator of Frame objects
        
        Returns:
            AnalysisResult with detected events
        """
        result = AnalysisResult()
        enable_vad = self.config.get("enable_vad", True)
        min_duration = self.config.get("min_event_duration", 0.3)
        
        # 支持字典类型的min_duration（按问题类型差异化）
        if isinstance(min_duration, dict):
            min_duration_dict = min_duration
        else:
            # 兼容旧版配置：统一阈值
            min_duration_dict = {
                "noise": min_duration,
                "dropout": min_duration,
                "volume_fluctuation": min_duration,
                "voice_distortion": min_duration,
            }
        
        for frame in frames:
            # Extract features from current frame
            features = extract_features(frame, self.prev_frame)
            self.all_features.append(features)
            
            result.frames_processed += 1
            if result.total_duration < frame.end_time:
                result.total_duration = frame.end_time
            
            # Voice Activity Detection
            voice_active = True
            if enable_vad:
                voice_active = is_voice_active(features, self.config)
            
            # 特别处理 Dropout 检测：即使 VAD 过滤掉，也要检测
            # 因为 Dropout 本身就是异常的无声/尖刺，不应该被 VAD 过滤
            dropout_event = self.dropout_detector.detect(
                features, frame,
                prev_features=self.prev_features,
                is_voice_active=voice_active
            )
            if dropout_event:
                result.add_event(dropout_event)
            
            # Skip other detections in non-voice segments
            if not voice_active:
                self.prev_features = features
                self.prev_frame = frame
                continue
            
            # Run remaining detectors (noise, volume, distortion)
            detectors = [
                self.noise_detector,
                self.volume_detector,
                self.distortion_detector,
            ]
            
            for detector in detectors:
                event = detector.detect(
                    features, frame, 
                    prev_features=self.prev_features,
                    is_voice_active=voice_active
                )
                if event:
                    result.add_event(event)
            
            # Update state for next iteration
            self.prev_features = features
            self.prev_frame = frame
        
        # Post-process: merge nearby events and filter short ones
        result.finalize(min_duration_dict=min_duration_dict)
        return result
