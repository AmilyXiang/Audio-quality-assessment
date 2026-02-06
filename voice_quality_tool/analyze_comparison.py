#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比分析工具 - 基于对齐的逐帧差分

用法：
    python analyze_comparison.py test.wav baseline.wav -o comparison.json
    python analyze_comparison.py test.wav baseline.wav --plot
"""

import sys
import json
import argparse
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from typing import Dict, List

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.alignment import align_audio_precise
from analyzer.features import extract_features
from analyzer.frame import Frame


def load_audio(path: str) -> tuple:
    """加载音频文件并归一化"""
    sr, data = wavfile.read(path)
    if len(data.shape) > 1:
        data = data[:, 0]
    data = data.astype(float)
    if data.max() > 1.0 or data.min() < -1.0:
        data = data / (2 ** 15)
    return sr, data


def frame_generator_aligned(data: np.ndarray, sr: int, frame_size: int, hop_size: int):
    """生成帧序列（与analyzer.frame_generator兼容）"""
    from analyzer.frame import Frame
    num_frames = (len(data) - frame_size) // hop_size + 1
    for i in range(num_frames):
        start_idx = i * hop_size
        end_idx = start_idx + frame_size
        if end_idx <= len(data):
            samples = data[start_idx:end_idx]
            start_time = start_idx / sr
            end_time = end_idx / sr
            yield Frame(samples, sr, start_time, end_time)


def compute_frame_diff(test_features: Dict, baseline_features: Dict) -> Dict:
    """
    计算单帧的差分特征
    
    Args:
        test_features: 测试音频的帧特征
        baseline_features: 基准音频的帧特征
        
    Returns:
        差分特征字典（实际值 - baseline值）
    """
    diff = {}
    
    # 核心特征差分
    for key in ['rms', 'zero_crossing_rate', 'spectral_centroid', 'spectral_bandwidth', 'spectral_flux']:
        if key in test_features and key in baseline_features:
            test_val = test_features[key]
            base_val = baseline_features[key]
            diff[f'{key}_diff'] = test_val - base_val
            diff[f'{key}_ratio'] = test_val / (base_val + 1e-10)
            diff[f'{key}_test'] = test_val
            diff[f'{key}_baseline'] = base_val
    
    # 第1阶段特征差分
    for key in ['peak_to_peak', 'spectral_rolloff', 'rms_percentile_95']:
        if key in test_features and key in baseline_features:
            test_val = test_features[key]
            base_val = baseline_features[key]
            diff[f'{key}_diff'] = test_val - base_val
            diff[f'{key}_test'] = test_val
            diff[f'{key}_baseline'] = base_val
    
    return diff


def analyze_comparison(test_path: str, baseline_path: str, 
                       enable_alignment: bool = True,
                       frame_duration: float = 0.025,
                       hop_duration: float = 0.010) -> Dict:
    """
    对比分析两个音频文件
    
    Args:
        test_path: 测试音频路径
        baseline_path: 基准音频路径
        enable_alignment: 是否启用精确对齐
        frame_duration: 帧时长（秒）
        hop_duration: 跳跃时长（秒）
        
    Returns:
        对比分析结果字典
    """
    print("\n" + "=" * 70)
    print("对比分析 - 基于对齐的逐帧差分".center(70))
    print("=" * 70)
    
    # 1. 加载音频
    print(f"\n[*] 加载音频文件...")
    sr_test, data_test = load_audio(test_path)
    sr_base, data_base = load_audio(baseline_path)
    
    print(f"   测试: {Path(test_path).name} ({len(data_test)/sr_test:.2f}s @ {sr_test}Hz)")
    print(f"   基准: {Path(baseline_path).name} ({len(data_base)/sr_base:.2f}s @ {sr_base}Hz)")
    
    # 2. 对齐音频
    alignment_info = None
    if enable_alignment:
        print(f"\n[*] 音频对齐...")
        # 统一采样率
        target_sr = max(sr_test, sr_base)
        if sr_test != target_sr:
            from scipy import signal as scipy_signal
            data_test = scipy_signal.resample(data_test, int(len(data_test) * target_sr / sr_test))
            sr_test = target_sr
        if sr_base != target_sr:
            from scipy import signal as scipy_signal
            data_base = scipy_signal.resample(data_base, int(len(data_base) * target_sr / sr_base))
            sr_base = target_sr
        
        # 精确对齐
        result = align_audio_precise(data_base, data_test, sr_test, 
                                     enable_coarse=True, enable_fine=False)
        data_base = result['aligned_reference']
        data_test = result['aligned_test']
        alignment_info = {
            'coarse_offset_sec': result['coarse_offset'] / sr_test,
            'coarse_confidence': result['coarse_confidence'],
            'quality': result['alignment_quality']
        }
        print(f"   [OK] 对齐完成: 偏移={alignment_info['coarse_offset_sec']:.3f}s, 置信度={alignment_info['coarse_confidence']:.2%}")
    else:
        # 简单裁剪
        min_len = min(len(data_test), len(data_base))
        data_test = data_test[:min_len]
        data_base = data_base[:min_len]
    
    # 3. 逐帧特征提取和差分
    print(f"\n[*] 逐帧差分计算...")
    frame_size = int(sr_test * frame_duration)
    hop_size = int(sr_test * hop_duration)
    
    frames_test = list(frame_generator_aligned(data_test, sr_test, frame_size, hop_size))
    frames_base = list(frame_generator_aligned(data_base, sr_test, frame_size, hop_size))
    
    n_frames = min(len(frames_test), len(frames_base))
    print(f"   总帧数: {n_frames} 帧 ({n_frames * hop_duration:.2f}s)")
    
    frame_diffs = []
    prev_test_frame = None
    prev_base_frame = None
    
    for i in range(n_frames):
        # 提取特征
        test_features = extract_features(frames_test[i], prev_test_frame)
        base_features = extract_features(frames_base[i], prev_base_frame)
        
        # 计算差分
        diff = compute_frame_diff(test_features, base_features)
        diff['time'] = frames_test[i].start_time
        diff['frame_index'] = i
        
        frame_diffs.append(diff)
        
        prev_test_frame = frames_test[i]
        prev_base_frame = frames_base[i]
        
        if (i + 1) % 100 == 0:
            print(f"   处理进度: {i+1}/{n_frames} ({(i+1)/n_frames*100:.1f}%)", end='\r')
    
    print(f"\n   [OK] 完成 {len(frame_diffs)} 帧的差分计算")
    
    # 4. 统计汇总
    print(f"\n[*] 差分统计...")
    stats = compute_diff_statistics(frame_diffs)
    
    # 5. 异常检测
    print(f"\n[*] 异常检测...")
    anomalies = detect_anomalies(frame_diffs, stats)
    
    # 6. 输出结果（结构化报告）
    result = {
        'metadata': {
            'test_file': Path(test_path).name,
            'baseline_file': Path(baseline_path).name,
            'test_duration': len(data_test) / sr_test,
            'baseline_duration': len(data_base) / sr_base,
            'aligned_duration': n_frames * hop_duration,
            'sample_rate': sr_test,
            'frame_length_ms': frame_duration * 1000,
            'frame_shift_ms': hop_duration * 1000,
            'n_frames': n_frames
        },
        'alignment': alignment_info if alignment_info else {'method': 'simple_trim'},
        'differential_statistics': stats,
        'anomaly_detection': anomalies,
        'frame_by_frame_diff': frame_diffs
    }
    
    print_summary(stats, anomalies)
    
    return result


def compute_diff_statistics(frame_diffs: List[Dict]) -> Dict:
    """计算差分统计量"""
    stats = {}
    
    # 提取差分序列
    diff_keys = [k for k in frame_diffs[0].keys() if k.endswith('_diff')]
    
    for key in diff_keys:
        values = [f[key] for f in frame_diffs if key in f]
        if values:
            values_arr = np.array(values)
            stats[key] = {
                'mean': float(np.mean(values_arr)),
                'std': float(np.std(values_arr)),
                'min': float(np.min(values_arr)),
                'max': float(np.max(values_arr)),
                'median': float(np.median(values_arr)),
                'p95': float(np.percentile(values_arr, 95))
            }
    
    return stats


def detect_anomalies(frame_diffs: List[Dict], stats: Dict, threshold_sigma: float = 2.0) -> Dict:
    """
    检测异常帧 - 差分超过阈值的帧
    
    Args:
        frame_diffs: 帧差分列表
        stats: 统计信息
        threshold_sigma: 阈值倍数（均值 ± threshold_sigma * 标准差）
    
    Returns:
        anomalies: {
            'feature_name': {
                'threshold': float,
                'anomaly_count': int,
                'anomaly_ratio': float,
                'anomaly_frames': [int],
                'anomaly_segments': [{'start_frame', 'end_frame', 'start_time', 'end_time', 'duration'}]
            }
        }
    """
    anomalies = {}
    
    # 对每个差分指标进行异常检测
    diff_keys = [k for k in stats.keys() if k.endswith('_diff')]
    
    for key in diff_keys:
        mean = stats[key]['mean']
        std = stats[key]['std']
        threshold = abs(mean) + threshold_sigma * std
        
        # 找出异常帧（绝对值超过阈值）
        anomaly_frames = []
        for i, frame in enumerate(frame_diffs):
            if key in frame:
                value = abs(frame[key])
                if value > threshold:
                    anomaly_frames.append(i)
        
        # 合并连续异常帧为段
        anomaly_segments = []
        if anomaly_frames:
            start = anomaly_frames[0]
            end = anomaly_frames[0]
            
            for frame_idx in anomaly_frames[1:]:
                if frame_idx == end + 1:
                    end = frame_idx
                else:
                    # 保存当前段
                    segment = {
                        'start_frame': int(start),
                        'end_frame': int(end),
                        'start_time': round(frame_diffs[start]['time'], 2),
                        'end_time': round(frame_diffs[end]['time'], 2),
                        'duration': round(frame_diffs[end]['time'] - frame_diffs[start]['time'], 2)
                    }
                    anomaly_segments.append(segment)
                    start = frame_idx
                    end = frame_idx
            
            # 最后一个段
            segment = {
                'start_frame': int(start),
                'end_frame': int(end),
                'start_time': round(frame_diffs[start]['time'], 2),
                'end_time': round(frame_diffs[end]['time'], 2),
                'duration': round(frame_diffs[end]['time'] - frame_diffs[start]['time'], 2)
            }
            anomaly_segments.append(segment)
        
        anomalies[key] = {
            'threshold': float(threshold),
            'anomaly_count': len(anomaly_frames),
            'anomaly_ratio': len(anomaly_frames) / len(frame_diffs) if frame_diffs else 0.0,
            'anomaly_frames': anomaly_frames[:100],  # 最多保存前100个
            'anomaly_segments': anomaly_segments
        }
    
    return anomalies


def print_summary(stats: Dict, anomalies: Dict):
    """打印统计摘要"""
    print("\n" + "=" * 70)
    print("差分统计摘要".center(70))
    print("=" * 70)
    
    # RMS差分
    if 'rms_diff' in stats:
        s = stats['rms_diff']
        print(f"\n[RMS能量差分]:")
        print(f"   平均差: {s['mean']:+.6f}  (正值=测试音量高于基准)")
        print(f"   标准差: {s['std']:.6f}")
        print(f"   范围: {s['min']:+.6f} ~ {s['max']:+.6f}")
        if 'rms_diff' in anomalies:
            print(f"   异常帧: {anomalies['rms_diff']['anomaly_count']} ({anomalies['rms_diff']['anomaly_ratio']:.1%})")
    
    # 噪声差分（过零率）
    if 'zero_crossing_rate_diff' in stats:
        s = stats['zero_crossing_rate_diff']
        print(f"\n[过零率差分] (噪声指标):")
        print(f"   平均差: {s['mean']:+.6f}  (正值=测试噪声高于基准)")
        print(f"   标准差: {s['std']:.6f}")
        print(f"   范围: {s['min']:+.6f} ~ {s['max']:+.6f}")
        if 'zero_crossing_rate_diff' in anomalies:
            print(f"   异常帧: {anomalies['zero_crossing_rate_diff']['anomaly_count']} ({anomalies['zero_crossing_rate_diff']['anomaly_ratio']:.1%})")
    
    # 频谱中心差分
    if 'spectral_centroid_diff' in stats:
        s = stats['spectral_centroid_diff']
        print(f"\n[频谱中心差分] (音色变化):")
        print(f"   平均差: {s['mean']:+.1f} Hz")
        print(f"   标准差: {s['std']:.1f} Hz")
        print(f"   范围: {s['min']:+.1f} ~ {s['max']:+.1f} Hz")
        if 'spectral_centroid_diff' in anomalies:
            print(f"   异常帧: {anomalies['spectral_centroid_diff']['anomaly_count']} ({anomalies['spectral_centroid_diff']['anomaly_ratio']:.1%})")
    
    # 频谱通量差分（抖动）
    if 'spectral_flux_diff' in stats:
        s = stats['spectral_flux_diff']
        print(f"\n[频谱通量差分] (抖动/不稳定性):")
        print(f"   平均差: {s['mean']:+.6f}  (正值=测试更抖)")
        print(f"   标准差: {s['std']:.6f}")
        print(f"   范围: {s['min']:+.6f} ~ {s['max']:+.6f}")
        if 'spectral_flux_diff' in anomalies:
            print(f"   异常帧: {anomalies['spectral_flux_diff']['anomaly_count']} ({anomalies['spectral_flux_diff']['anomaly_ratio']:.1%})")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='对比分析工具 - 基于对齐的逐帧差分',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_comparison.py test.wav baseline.wav -o result.json
  python analyze_comparison.py test.wav baseline.wav --no-align  # 不对齐
  python analyze_comparison.py test.wav baseline.wav --plot  # 生成差分图表
        """
    )
    
    parser.add_argument('test_audio', help='测试音频文件')
    parser.add_argument('baseline_audio', help='基准音频文件')
    parser.add_argument('-o', '--output', help='输出JSON文件路径')
    parser.add_argument('--no-align', action='store_true', help='禁用精确对齐')
    parser.add_argument('--plot', action='store_true', help='生成差分可视化图表')
    
    args = parser.parse_args()
    
    # 执行对比分析
    result = analyze_comparison(
        args.test_audio,
        args.baseline_audio,
        enable_alignment=not args.no_align
    )
    
    # 保存结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存: {args.output}")
    
    # 生成图表
    if args.plot:
        plot_path = args.output.replace('.json', '_plot.png') if args.output else 'comparison_plot.png'
        try:
            from generate_comparison_plot import plot_comparison_result
            plot_comparison_result(result, plot_path)
            print(f"📊 差分图表已保存: {plot_path}")
        except ImportError:
            print("⚠️  绘图模块未找到，跳过可视化")


if __name__ == '__main__':
    main()
