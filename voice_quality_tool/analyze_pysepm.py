#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于pysepm的语音质量评估工具
Speech Quality Assessment using pysepm metrics

包含指标：
- PESQ: 感知语音质量评估（ITU-T P.862）
- STOI: 短时客观可懂度
- SNR: 信噪比相关指标
- LLR: 对数似然比
- WSS: 加权频谱斜率
- fwSNRseg: 频率加权分段信噪比
- CD: 倒谱距离
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
from scipy.io import wavfile
from scipy import signal


def load_and_preprocess(file_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    加载音频并预处理（重采样到16kHz，PESQ要求）
    
    Args:
        file_path: 音频文件路径
        target_sr: 目标采样率（PESQ支持8000或16000）
        
    Returns:
        (audio_data, sample_rate)
    """
    sr, data = wavfile.read(file_path)
    
    # 转换为浮点数
    if data.dtype == np.int16:
        data = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.float32:
        data = data.astype(np.float64)
    
    # 单声道
    if len(data.shape) > 1:
        data = np.mean(data, axis=1)
    
    # 重采样到目标采样率
    if sr != target_sr:
        num_samples = int(len(data) * target_sr / sr)
        data = signal.resample(data, num_samples)
        print(f"   重采样: {sr}Hz -> {target_sr}Hz")
    
    return data, target_sr


def calculate_pesq(ref: np.ndarray, deg: np.ndarray, sr: int) -> float:
    """计算PESQ分数 (ITU-T P.862)"""
    try:
        from pesq import pesq
        # PESQ范围：-0.5 到 4.5
        mode = 'wb' if sr == 16000 else 'nb'
        score = pesq(sr, ref, deg, mode)
        return float(score)
    except Exception as e:
        print(f"   ⚠️ PESQ计算失败: {e}")
        return None


def calculate_stoi(ref: np.ndarray, deg: np.ndarray, sr: int) -> float:
    """计算STOI可懂度 (Short-Time Objective Intelligibility)"""
    try:
        from pystoi import stoi
        # STOI范围：0 到 1
        score = stoi(ref, deg, sr, extended=False)
        return float(score)
    except Exception as e:
        print(f"   ⚠️ STOI计算失败: {e}")
        return None


def calculate_snr_metrics(ref: np.ndarray, deg: np.ndarray, sr: int) -> Dict:
    """计算SNR相关指标"""
    results = {}
    
    # 确保长度一致
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    
    # 计算噪声（差异信号）
    noise = deg - ref
    
    # 1. 全局SNR
    signal_power = np.sum(ref ** 2)
    noise_power = np.sum(noise ** 2)
    if noise_power > 0:
        snr_global = 10 * np.log10(signal_power / noise_power)
        results['snr_global'] = float(snr_global)
    
    # 2. 分段SNR (Segmental SNR)
    frame_length = int(0.03 * sr)  # 30ms帧
    hop_length = int(0.015 * sr)   # 15ms hop
    
    snr_segments = []
    for i in range(0, min_len - frame_length, hop_length):
        ref_frame = ref[i:i+frame_length]
        noise_frame = noise[i:i+frame_length]
        
        ref_power = np.sum(ref_frame ** 2)
        noise_power = np.sum(noise_frame ** 2)
        
        if noise_power > 0 and ref_power > 0:
            snr_seg = 10 * np.log10(ref_power / noise_power)
            # 限制范围 [-10, 35] dB
            snr_seg = np.clip(snr_seg, -10, 35)
            snr_segments.append(snr_seg)
    
    if snr_segments:
        results['snr_seg_mean'] = float(np.mean(snr_segments))
        results['snr_seg_std'] = float(np.std(snr_segments))
        results['snr_seg_min'] = float(np.min(snr_segments))
    
    return results


def calculate_llr(ref: np.ndarray, deg: np.ndarray, sr: int) -> float:
    """
    计算对数似然比 (Log-Likelihood Ratio)
    LLR越小越好，0表示完全匹配
    """
    # 帧参数
    frame_length = int(0.03 * sr)  # 30ms
    hop_length = int(0.015 * sr)   # 15ms
    order = 12  # LPC阶数
    
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    
    llr_values = []
    
    for i in range(0, min_len - frame_length, hop_length):
        ref_frame = ref[i:i+frame_length]
        deg_frame = deg[i:i+frame_length]
        
        # 跳过静音帧
        if np.sum(ref_frame ** 2) < 1e-6:
            continue
        
        try:
            # 计算LPC系数
            from scipy.linalg import toeplitz, solve_toeplitz
            
            # 自相关
            def autocorr(x, order):
                r = np.correlate(x, x, mode='full')
                r = r[len(r)//2:]
                return r[:order+1]
            
            r_ref = autocorr(ref_frame, order)
            r_deg = autocorr(deg_frame, order)
            
            if r_ref[0] > 0 and r_deg[0] > 0:
                # Levinson-Durbin求解LPC
                a_ref = solve_toeplitz(r_ref[:-1], r_ref[1:])
                a_deg = solve_toeplitz(r_deg[:-1], r_deg[1:])
                
                # 计算LLR
                a_ref_full = np.concatenate([[1], -a_ref])
                R = toeplitz(r_deg[:order+1])
                
                llr = np.log(np.dot(a_ref_full, np.dot(R, a_ref_full)) / r_deg[0] + 1e-10)
                llr = np.clip(llr, 0, 2)  # 限制范围
                llr_values.append(llr)
        except:
            continue
    
    if llr_values:
        return float(np.mean(llr_values))
    return None


def calculate_wss(ref: np.ndarray, deg: np.ndarray, sr: int) -> float:
    """
    计算加权频谱斜率距离 (Weighted Spectral Slope)
    WSS越小越好
    """
    frame_length = int(0.03 * sr)
    hop_length = int(0.015 * sr)
    n_fft = 512
    
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    
    wss_values = []
    
    # 临界频带权重（Bark scale近似）
    n_bands = 25
    
    for i in range(0, min_len - frame_length, hop_length):
        ref_frame = ref[i:i+frame_length] * np.hamming(frame_length)
        deg_frame = deg[i:i+frame_length] * np.hamming(frame_length)
        
        # 跳过静音
        if np.sum(ref_frame ** 2) < 1e-6:
            continue
        
        # FFT
        ref_spec = np.abs(np.fft.rfft(ref_frame, n_fft))
        deg_spec = np.abs(np.fft.rfft(deg_frame, n_fft))
        
        # 简化的频带划分
        band_size = len(ref_spec) // n_bands
        
        ref_bands = []
        deg_bands = []
        for b in range(n_bands):
            start = b * band_size
            end = start + band_size
            ref_bands.append(np.sum(ref_spec[start:end] ** 2))
            deg_bands.append(np.sum(deg_spec[start:end] ** 2))
        
        ref_bands = np.array(ref_bands) + 1e-10
        deg_bands = np.array(deg_bands) + 1e-10
        
        # 计算斜率
        ref_slope = np.diff(10 * np.log10(ref_bands))
        deg_slope = np.diff(10 * np.log10(deg_bands))
        
        # 加权差异
        weights = np.ones(len(ref_slope))  # 简化权重
        wss = np.sum(weights * (ref_slope - deg_slope) ** 2) / np.sum(weights)
        wss_values.append(wss)
    
    if wss_values:
        return float(np.mean(wss_values))
    return None


def calculate_cepstral_distance(ref: np.ndarray, deg: np.ndarray, sr: int) -> float:
    """
    计算倒谱距离 (Cepstral Distance)
    CD越小越好
    """
    frame_length = int(0.03 * sr)
    hop_length = int(0.015 * sr)
    n_mfcc = 13
    
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    
    cd_values = []
    
    for i in range(0, min_len - frame_length, hop_length):
        ref_frame = ref[i:i+frame_length]
        deg_frame = deg[i:i+frame_length]
        
        if np.sum(ref_frame ** 2) < 1e-6:
            continue
        
        try:
            # 简化的MFCC计算
            n_fft = 512
            ref_spec = np.abs(np.fft.rfft(ref_frame * np.hamming(frame_length), n_fft))
            deg_spec = np.abs(np.fft.rfft(deg_frame * np.hamming(frame_length), n_fft))
            
            # 对数能量
            ref_log = np.log(ref_spec + 1e-10)
            deg_log = np.log(deg_spec + 1e-10)
            
            # DCT获取倒谱系数
            from scipy.fftpack import dct
            ref_cep = dct(ref_log, type=2, norm='ortho')[:n_mfcc]
            deg_cep = dct(deg_log, type=2, norm='ortho')[:n_mfcc]
            
            # 欧氏距离
            cd = np.sqrt(2 * np.sum((ref_cep[1:] - deg_cep[1:]) ** 2))
            cd_values.append(cd)
        except:
            continue
    
    if cd_values:
        return float(np.mean(cd_values))
    return None


def analyze_quality(ref_path: str, deg_path: str, output_json: str = None) -> Dict:
    """
    执行完整的语音质量分析
    
    Args:
        ref_path: 参考音频路径（基准）
        deg_path: 退化音频路径（测试）
        output_json: 输出JSON路径
        
    Returns:
        分析结果字典
    """
    print("=" * 70)
    print("📊 pysepm 语音质量评估")
    print("=" * 70)
    
    # 加载音频
    print("\n🔊 加载音频...")
    ref, sr = load_and_preprocess(ref_path, target_sr=16000)
    deg, _ = load_and_preprocess(deg_path, target_sr=16000)
    
    print(f"✅ 参考音频: {ref_path}")
    print(f"   长度: {len(ref)/sr:.2f}s")
    print(f"✅ 测试音频: {deg_path}")
    print(f"   长度: {len(deg)/sr:.2f}s")
    
    # 对齐长度
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    print(f"📏 对齐后长度: {min_len/sr:.2f}s")
    
    results = {
        'metadata': {
            'reference_file': ref_path,
            'degraded_file': deg_path,
            'sample_rate': sr,
            'duration': float(min_len / sr)
        },
        'metrics': {}
    }
    
    # 1. PESQ
    print("\n📈 计算 PESQ (感知语音质量)...")
    pesq_score = calculate_pesq(ref, deg, sr)
    if pesq_score is not None:
        results['metrics']['pesq'] = {
            'value': pesq_score,
            'range': '[-0.5, 4.5]',
            'interpretation': interpret_pesq(pesq_score)
        }
        print(f"   PESQ = {pesq_score:.3f} ({interpret_pesq(pesq_score)})")
    
    # 2. STOI
    print("\n📈 计算 STOI (可懂度)...")
    stoi_score = calculate_stoi(ref, deg, sr)
    if stoi_score is not None:
        results['metrics']['stoi'] = {
            'value': stoi_score,
            'range': '[0, 1]',
            'interpretation': interpret_stoi(stoi_score)
        }
        print(f"   STOI = {stoi_score:.3f} ({interpret_stoi(stoi_score)})")
    
    # 3. SNR指标
    print("\n📈 计算 SNR 指标...")
    snr_results = calculate_snr_metrics(ref, deg, sr)
    if snr_results:
        results['metrics']['snr'] = snr_results
        if 'snr_global' in snr_results:
            print(f"   全局SNR = {snr_results['snr_global']:.2f} dB")
        if 'snr_seg_mean' in snr_results:
            print(f"   分段SNR = {snr_results['snr_seg_mean']:.2f} dB (mean)")
    
    # 4. LLR
    print("\n📈 计算 LLR (对数似然比)...")
    llr_score = calculate_llr(ref, deg, sr)
    if llr_score is not None:
        results['metrics']['llr'] = {
            'value': llr_score,
            'range': '[0, 2]',
            'interpretation': '越小越好，0为完美匹配'
        }
        print(f"   LLR = {llr_score:.3f}")
    
    # 5. WSS
    print("\n📈 计算 WSS (加权频谱斜率)...")
    wss_score = calculate_wss(ref, deg, sr)
    if wss_score is not None:
        results['metrics']['wss'] = {
            'value': wss_score,
            'range': '[0, ∞)',
            'interpretation': '越小越好'
        }
        print(f"   WSS = {wss_score:.3f}")
    
    # 6. Cepstral Distance
    print("\n📈 计算 CD (倒谱距离)...")
    cd_score = calculate_cepstral_distance(ref, deg, sr)
    if cd_score is not None:
        results['metrics']['cepstral_distance'] = {
            'value': cd_score,
            'range': '[0, ∞)',
            'interpretation': '越小越好'
        }
        print(f"   CD = {cd_score:.3f}")
    
    # 综合评估
    print("\n" + "=" * 70)
    print("📊 综合评估")
    print("=" * 70)
    
    overall = calculate_overall_quality(results['metrics'])
    results['overall'] = overall
    
    print(f"\n🏆 综合质量评级: {overall['grade']}")
    print(f"   {overall['description']}")
    
    # 保存结果
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存: {output_json}")
    
    print("\n" + "=" * 70)
    
    return results


def interpret_pesq(score: float) -> str:
    """解释PESQ分数"""
    if score >= 4.0:
        return "优秀 - 电信级质量"
    elif score >= 3.5:
        return "良好 - 可接受质量"
    elif score >= 3.0:
        return "中等 - 有轻微失真"
    elif score >= 2.5:
        return "较差 - 明显失真"
    else:
        return "差 - 严重失真"


def interpret_stoi(score: float) -> str:
    """解释STOI分数"""
    if score >= 0.9:
        return "优秀 - 高度可懂"
    elif score >= 0.75:
        return "良好 - 清晰可懂"
    elif score >= 0.6:
        return "中等 - 基本可懂"
    elif score >= 0.45:
        return "较差 - 部分可懂"
    else:
        return "差 - 难以理解"


def calculate_overall_quality(metrics: Dict) -> Dict:
    """计算综合质量评估"""
    score = 0
    count = 0
    
    # PESQ (权重最高)
    if 'pesq' in metrics:
        # 归一化到0-1
        pesq_norm = (metrics['pesq']['value'] + 0.5) / 5.0
        score += pesq_norm * 0.4
        count += 0.4
    
    # STOI
    if 'stoi' in metrics:
        score += metrics['stoi']['value'] * 0.3
        count += 0.3
    
    # SNR (归一化)
    if 'snr' in metrics and 'snr_seg_mean' in metrics['snr']:
        snr_norm = np.clip((metrics['snr']['snr_seg_mean'] + 10) / 45, 0, 1)
        score += snr_norm * 0.15
        count += 0.15
    
    # LLR (反向，越小越好)
    if 'llr' in metrics:
        llr_norm = 1 - np.clip(metrics['llr']['value'] / 2, 0, 1)
        score += llr_norm * 0.15
        count += 0.15
    
    if count > 0:
        overall_score = score / count
    else:
        overall_score = 0
    
    # 评级
    if overall_score >= 0.85:
        grade = "优秀"
        description = "音频质量非常好，失真极小"
    elif overall_score >= 0.7:
        grade = "良好"
        description = "音频质量较好，有轻微失真"
    elif overall_score >= 0.55:
        grade = "中等"
        description = "音频质量一般，存在明显失真"
    elif overall_score >= 0.4:
        grade = "较差"
        description = "音频质量较差，失真明显影响可懂度"
    else:
        grade = "差"
        description = "音频质量很差，严重失真"
    
    return {
        'score': float(overall_score),
        'grade': grade,
        'description': description
    }


def main():
    parser = argparse.ArgumentParser(
        description='基于pysepm的语音质量评估工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_pysepm.py reference.wav degraded.wav -o result.json
  
评估指标说明:
  PESQ  - 感知语音质量 (ITU-T P.862)，范围 -0.5 到 4.5，越高越好
  STOI  - 短时客观可懂度，范围 0 到 1，越高越好  
  SNR   - 信噪比，单位 dB，越高越好
  LLR   - 对数似然比，越小越好，0为完美
  WSS   - 加权频谱斜率，越小越好
  CD    - 倒谱距离，越小越好
        """
    )
    
    parser.add_argument('reference', help='参考音频文件路径（基准/干净音频）')
    parser.add_argument('degraded', help='待评估音频文件路径（测试/受损音频）')
    parser.add_argument('-o', '--output', help='JSON结果输出路径')
    
    args = parser.parse_args()
    
    # 检查文件
    if not Path(args.reference).exists():
        print(f"❌ 错误: 参考文件不存在: {args.reference}")
        sys.exit(1)
    
    if not Path(args.degraded).exists():
        print(f"❌ 错误: 测试文件不存在: {args.degraded}")
        sys.exit(1)
    
    # 执行分析
    analyze_quality(args.reference, args.degraded, args.output)


if __name__ == '__main__':
    main()
