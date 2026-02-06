#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频对齐模块 - Cross-Correlation粗对齐 + DTW精对齐
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional
import warnings


def find_time_offset_cross_correlation(reference: np.ndarray, test: np.ndarray, 
                                       sr: int, max_offset_sec: float = 5.0) -> Tuple[int, float]:
    """
    使用互相关找到两段音频的时间偏移量（粗对齐）
    
    Args:
        reference: 参考音频（基准）
        test: 测试音频
        sr: 采样率
        max_offset_sec: 最大搜索偏移时间（秒）
        
    Returns:
        (offset_samples, confidence): 偏移量（样本数）和置信度(0-1)
    """
    max_offset_samples = int(max_offset_sec * sr)
    
    # 限制长度以提高计算效率（取前30秒）
    max_len = min(len(reference), len(test), int(30 * sr))
    ref_segment = reference[:max_len]
    test_segment = test[:max_len]
    
    # 计算互相关
    correlation = signal.correlate(test_segment, ref_segment, mode='valid')
    
    # 找到最大相关位置
    peak_idx = np.argmax(np.abs(correlation))
    offset = peak_idx - len(ref_segment) + 1
    
    # 限制在合理范围内
    if abs(offset) > max_offset_samples:
        offset = np.clip(offset, -max_offset_samples, max_offset_samples)
    
    # 计算置信度（归一化相关系数）
    max_corr = np.abs(correlation[peak_idx])
    ref_energy = np.sqrt(np.sum(ref_segment ** 2))
    test_energy = np.sqrt(np.sum(test_segment ** 2))
    confidence = max_corr / (ref_energy * test_energy + 1e-10)
    confidence = float(np.clip(confidence, 0, 1))
    
    return int(offset), confidence


def compute_mfcc_sequence(audio: np.ndarray, sr: int, n_mfcc: int = 13, 
                          frame_length: int = 512, hop_length: int = 256) -> Optional[np.ndarray]:
    """
    计算音频的MFCC时间序列（用于DTW对齐）
    
    Args:
        audio: 音频数据
        sr: 采样率
        n_mfcc: MFCC系数数量
        frame_length: 帧长度
        hop_length: 跳跃长度
        
    Returns:
        MFCC矩阵 (n_mfcc, n_frames) 或 None（如果librosa未安装）
    """
    try:
        import librosa
        mfcc = librosa.feature.mfcc(
            y=audio, 
            sr=sr, 
            n_mfcc=n_mfcc,
            n_fft=frame_length,
            hop_length=hop_length
        )
        return mfcc
    except ImportError:
        warnings.warn("librosa not installed, MFCC computation skipped")
        return None


def dtw_align(reference_mfcc: np.ndarray, test_mfcc: np.ndarray, 
              window_size: Optional[int] = None) -> Tuple[np.ndarray, float]:
    """
    使用动态时间规整(DTW)对齐两段MFCC序列
    
    Args:
        reference_mfcc: 参考MFCC (n_mfcc, n_frames_ref)
        test_mfcc: 测试MFCC (n_mfcc, n_frames_test)
        window_size: Sakoe-Chiba带宽约束（None=不约束）
        
    Returns:
        (path, distance): 对齐路径 (n_aligned, 2) 和DTW距离
    """
    try:
        from dtw import dtw as dtw_compute
        # 转置为 (n_frames, n_mfcc)
        ref = reference_mfcc.T
        test = test_mfcc.T
        
        # 计算DTW
        if window_size:
            alignment = dtw_compute(ref, test, window_type='sakoechiba', window_args={'window_size': window_size})
        else:
            alignment = dtw_compute(ref, test)
        
        return alignment.index1, alignment.index2, alignment.distance
        
    except ImportError:
        # 尝试使用fastdtw
        try:
            from fastdtw import fastdtw
            ref = reference_mfcc.T
            test = test_mfcc.T
            distance, path = fastdtw(ref, test, radius=window_size or 50)
            path = np.array(path)
            return path[:, 0], path[:, 1], distance
        except ImportError:
            warnings.warn("Neither dtw-python nor fastdtw is installed. DTW alignment skipped.")
            return None, None, None


def align_audio_precise(reference: np.ndarray, test: np.ndarray, sr: int,
                        enable_coarse: bool = True, enable_fine: bool = True) -> dict:
    """
    完整的音频对齐流程：粗对齐(xcorr) + 精对齐(DTW)
    
    Args:
        reference: 参考音频
        test: 测试音频
        sr: 采样率
        enable_coarse: 是否启用粗对齐
        enable_fine: 是否启用精对齐（需要librosa和dtw）
        
    Returns:
        对齐结果字典：{
            'coarse_offset': int,  # 粗对齐偏移量（样本）
            'coarse_confidence': float,  # 粗对齐置信度
            'fine_alignment': dict,  # 精对齐信息
            'aligned_reference': np.ndarray,  # 对齐后的参考音频
            'aligned_test': np.ndarray,  # 对齐后的测试音频
            'alignment_quality': str  # 对齐质量评估
        }
    """
    result = {
        'coarse_offset': 0,
        'coarse_confidence': 0.0,
        'fine_alignment': None,
        'aligned_reference': reference.copy(),
        'aligned_test': test.copy(),
        'alignment_quality': 'none'
    }
    
    # 1. 粗对齐（Cross-Correlation）
    if enable_coarse:
        offset, confidence = find_time_offset_cross_correlation(reference, test, sr)
        result['coarse_offset'] = offset
        result['coarse_confidence'] = confidence
        
        # 应用偏移
        if offset > 0:
            # test开始较晚，裁掉test的前面
            test = test[offset:]
        elif offset < 0:
            # reference开始较晚，裁掉reference的前面
            reference = reference[-offset:]
        
        result['alignment_quality'] = 'coarse'
        print(f"   粗对齐: 偏移={offset/sr:.3f}s ({offset}样本), 置信度={confidence:.2%}")
    
    # 2. 裁剪到相同长度
    min_len = min(len(reference), len(test))
    reference = reference[:min_len]
    test = test[:min_len]
    
    result['aligned_reference'] = reference
    result['aligned_test'] = test
    
    # 3. 精对齐（DTW）
    if enable_fine and min_len > sr:  # 至少1秒
        ref_mfcc = compute_mfcc_sequence(reference, sr)
        test_mfcc = compute_mfcc_sequence(test, sr)
        
        if ref_mfcc is not None and test_mfcc is not None:
            # 计算DTW（限制在前10秒以提高速度）
            max_frames = min(ref_mfcc.shape[1], test_mfcc.shape[1], 400)  # ~10秒@256hop
            ref_mfcc_short = ref_mfcc[:, :max_frames]
            test_mfcc_short = test_mfcc[:, :max_frames]
            
            idx_ref, idx_test, distance = dtw_align(ref_mfcc_short, test_mfcc_short, window_size=50)
            
            if idx_ref is not None:
                result['fine_alignment'] = {
                    'dtw_distance': float(distance),
                    'path_length': len(idx_ref) if hasattr(idx_ref, '__len__') else 0,
                    'compression_ratio': len(idx_ref) / max_frames if hasattr(idx_ref, '__len__') else 1.0
                }
                result['alignment_quality'] = 'fine'
                print(f"   精对齐: DTW距离={distance:.2f}, 路径长度={len(idx_ref) if hasattr(idx_ref, '__len__') else 0}")
    
    return result


def compute_frame_alignment_map(reference: np.ndarray, test: np.ndarray, sr: int,
                                frame_size: int, hop_size: int) -> np.ndarray:
    """
    计算帧级别的对齐映射（用于逐帧差分）
    
    Args:
        reference: 对齐后的参考音频
        test: 对齐后的测试音频
        sr: 采样率
        frame_size: 帧大小
        hop_size: 跳跃大小
        
    Returns:
        对齐映射数组: shape (n_frames, 2), 每行为 [ref_frame_idx, test_frame_idx]
    """
    n_frames = (min(len(reference), len(test)) - frame_size) // hop_size + 1
    
    # 简单的1:1映射（已经对齐的情况）
    alignment_map = np.column_stack([np.arange(n_frames), np.arange(n_frames)])
    
    return alignment_map


if __name__ == '__main__':
    # 测试代码
    print("音频对齐模块测试")
    print("=" * 60)
    
    # 生成测试信号
    sr = 16000
    t = np.linspace(0, 2, 2 * sr)
    reference = np.sin(2 * np.pi * 440 * t) * 0.5
    
    # 测试信号：延迟0.1秒
    test = np.zeros_like(reference)
    delay_samples = int(0.1 * sr)
    test[delay_samples:] = reference[:-delay_samples]
    
    print(f"\n测试1: 互相关粗对齐")
    offset, conf = find_time_offset_cross_correlation(reference, test, sr)
    print(f"检测到偏移: {offset}样本 ({offset/sr:.3f}秒)")
    print(f"置信度: {conf:.2%}")
    print(f"预期偏移: {delay_samples}样本 ({delay_samples/sr:.3f}秒)")
    
    print(f"\n测试2: 完整对齐流程")
    result = align_audio_precise(reference, test, sr, enable_coarse=True, enable_fine=False)
    print(f"对齐质量: {result['alignment_quality']}")
    print(f"对齐后长度: ref={len(result['aligned_reference'])}, test={len(result['aligned_test'])}")
    
    print("\n✓ 模块测试完成")
