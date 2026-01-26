"""Voice Activity Detection (VAD) - 区分人声和非人声段落."""
import numpy as np
from typing import Dict


def is_voice_active(features: Dict, config: Dict) -> bool:
    """判断当前帧是否包含人声活动.
    
    基于以下启发式规则：
    - 人声RMS通常在0.02-0.8范围
    - 人声频谱中心在80-3000 Hz
    - 人声零交叉率适中（0.05-0.15）
    
    Args:
        features: 提取的特征字典
        config: 配置参数
    
    Returns:
        True if voice is detected, False otherwise
    """
    rms = features.get("rms", 0)
    centroid = features.get("spectral_centroid", 0)
    zcr = features.get("zero_crossing_rate", 0)
    
    # 能量门限
    min_rms = config.get("vad_min_rms", 0.02)
    max_rms = config.get("vad_max_rms", 1.0)
    
    # 频谱中心范围 (人声频段)
    min_centroid = config.get("vad_min_centroid", 80)
    max_centroid = config.get("vad_max_centroid", 3000)
    
    # 零交叉率范围
    min_zcr = config.get("vad_min_zcr", 0.03)
    max_zcr = config.get("vad_max_zcr", 0.18)
    
    # 综合判断
    rms_ok = min_rms < rms < max_rms
    centroid_ok = min_centroid < centroid < max_centroid
    zcr_ok = min_zcr < zcr < max_zcr
    
    # 至少满足2个条件
    vote_count = sum([rms_ok, centroid_ok, zcr_ok])
    return vote_count >= 2


def compute_baseline_stats(all_features: list) -> Dict:
    """计算音频的基线统计信息（用于自适应阈值）.
    
    包含核心特征 + 第1阶段特征
    
    Args:
        all_features: 所有帧的特征列表
    
    Returns:
        基线统计字典 (mean, std, percentiles)
    """
    if not all_features:
        return {}
    
    rms_values = [f.get("rms", 0) for f in all_features]
    centroid_values = [f.get("spectral_centroid", 0) for f in all_features]
    zcr_values = [f.get("zero_crossing_rate", 0) for f in all_features]
    flux_values = [f.get("spectral_flux", 0) for f in all_features]
    
    # 第1阶段特征（新增）
    peak_to_peak_values = [f.get("peak_to_peak", 0) for f in all_features]
    rolloff_values = [f.get("spectral_rolloff", 0) for f in all_features]
    rms_percentile_values = [f.get("rms_percentile_95", 0) for f in all_features]
    
    baseline = {
        # 核心特征
        "rms_mean": float(np.mean(rms_values)),
        "rms_std": float(np.std(rms_values)),
        "rms_p10": float(np.percentile(rms_values, 10)),
        "rms_p90": float(np.percentile(rms_values, 90)),
        
        "centroid_mean": float(np.mean(centroid_values)),
        "centroid_std": float(np.std(centroid_values)),
        
        "zcr_mean": float(np.mean(zcr_values)),
        "zcr_std": float(np.std(zcr_values)),
        
        "spectral_flux_mean": float(np.mean(flux_values)),
        "spectral_flux_std": float(np.std(flux_values)),
        
        # 第1阶段特征统计
        "peak_to_peak_mean": float(np.mean(peak_to_peak_values)),
        "peak_to_peak_std": float(np.std(peak_to_peak_values)),
        "peak_to_peak_max": float(np.max(peak_to_peak_values)),
        
        "spectral_rolloff_mean": float(np.mean(rolloff_values)),
        "spectral_rolloff_std": float(np.std(rolloff_values)),
        
        "rms_percentile_mean": float(np.mean(rms_percentile_values)),
        "rms_percentile_std": float(np.std(rms_percentile_values)),
    }
    
    return baseline


def adaptive_threshold(baseline: Dict, metric_name: str, default_value: float) -> float:
    """根据基线统计动态调整阈值.
    
    Args:
        baseline: 基线统计字典
        metric_name: 指标名称 (rms, centroid, zcr)
        default_value: 默认阈值
    
    Returns:
        调整后的阈值
    """
    if not baseline:
        return default_value
    
    mean_key = f"{metric_name}_mean"
    std_key = f"{metric_name}_std"
    
    if mean_key not in baseline or std_key not in baseline:
        return default_value
    
    mean = baseline[mean_key]
    std = baseline[std_key]
    
    # 动态阈值 = mean + 2*std (基于正态分布)
    adaptive = mean + 2 * std
    
    # 保证不会太极端
    return max(min(adaptive, default_value * 2), default_value * 0.5)
