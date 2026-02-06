#!/usr/bin/env python3
"""
全局失真检测 - 检测整段文件的系统性失真

解决问题：
原始系统只能检测离散事件（突发失真）
无法检测整段文件的持续系统性失真（如机器人语音、合成语音、编码失真等）

方案：计算整段文件的全局特征，与基线对比
"""

import numpy as np
from scipy.io import wavfile
from scipy import signal
import json
import os
from typing import Dict, Tuple
from .alignment import align_audio_precise


class GlobalDistortionAnalyzer:
    """全局失真分析器 - 检测整段文件的系统性失真"""
    
    def __init__(self):
        self.name = "GlobalDistortionAnalyzer"
    
    def analyze_file(self, audio_path: str, baseline_audio_path: str = None) -> Dict:
        """
        分析单个文件，可选与基线对比
        
        Args:
            audio_path: 待分析音频文件
            baseline_audio_path: 基线音频文件（用于对比）
        
        Returns:
            dict: 包含全局特征和失真判断
        """
        
        print(f"\n📊 全局失真分析")
        print("=" * 70)
        
        # 加载音频
        sample_rate, data = wavfile.read(audio_path)
        if len(data.shape) > 1:
            data = data[:, 0]
        data = data.astype(float) / 32768.0
        
        print(f"📁 分析文件: {os.path.basename(audio_path)}")
        print(f"   采样率: {sample_rate} Hz")
        print(f"   时长: {len(data) / sample_rate:.2f}s")
        print(f"   样本数: {len(data)}")
        
        # 计算全局特征
        global_features = self._compute_global_features(data, sample_rate)
        
        result = {
            "file": os.path.basename(audio_path),
            "duration": len(data) / sample_rate,
            "sample_rate": sample_rate,
            "global_features": global_features,
            "quality_assessment": None,
            "baseline_comparison": None
        }
        
        # 如果提供了基线，进行对比分析
        if baseline_audio_path and os.path.exists(baseline_audio_path):
            sr_base, data_base = wavfile.read(baseline_audio_path)
            if len(data_base.shape) > 1:
                data_base = data_base[:, 0]
            data_base = data_base.astype(float) / 32768.0
            
            print(f"\n📋 基线文件: {os.path.basename(baseline_audio_path)}")
            print(f"   采样率: {sr_base} Hz")
            print(f"   时长: {len(data_base) / sr_base:.2f}s")
            
            # 🔧 对齐音频：统一采样率 + 互相关粗对齐 + DTW精对齐（可选）
            print(f"\n🔧 音频对齐处理...")
            data, data_base, alignment_info = self._align_audio_v2(
                data, sample_rate, data_base, sr_base
            )
            print(f"   ✓ 对齐后长度: {len(data)} 样本 ({len(data)/sample_rate:.2f}s)")
            
            baseline_features = self._compute_global_features(data_base, sample_rate)
            comparison = self._compare_features(global_features, baseline_features)
            comparison['alignment_info'] = alignment_info
            
            result["baseline_comparison"] = comparison
            result["global_features"]["baseline"] = baseline_features
        
        # 质量评估（传入基线对比结果）
        result["quality_assessment"] = self._assess_quality(
            global_features, 
            baseline_comparison=result.get("baseline_comparison")
        )
        
        self._print_results(result)
        
        return result
    
    def _align_audio_v2(self, data1: np.ndarray, sr1: int, data2: np.ndarray, sr2: int) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        对齐两段音频：统一采样率 + 互相关粗对齐 + DTW精对齐
        
        Args:
            data1: 音频1数据（测试音频）
            sr1: 音频1采样率
            data2: 音频2数据（基准音频）
            sr2: 音频2采样率
            
        Returns:
            对齐后的 (data1, data2, alignment_info)
        """
        # 1. 统一采样率到较高的那个
        target_sr = max(sr1, sr2)
        
        if sr1 != target_sr:
            num_samples = int(len(data1) * target_sr / sr1)
            data1 = signal.resample(data1, num_samples)
            print(f"   重采样测试音频: {sr1}Hz -> {target_sr}Hz")
        
        if sr2 != target_sr:
            num_samples = int(len(data2) * target_sr / sr2)
            data2 = signal.resample(data2, num_samples)
            print(f"   重采样基准音频: {sr2}Hz -> {target_sr}Hz")
        
        # 2. 精确对齐（Cross-Correlation + DTW）
        try:
            alignment_result = align_audio_precise(
                reference=data2,  # 基准作为参考
                test=data1,       # 测试音频
                sr=target_sr,
                enable_coarse=True,
                enable_fine=False  # DTW可选，计算较慢
            )
            
            data1 = alignment_result['aligned_test']
            data2 = alignment_result['aligned_reference']
            
            alignment_info = {
                'method': alignment_result['alignment_quality'],
                'coarse_offset_sec': alignment_result['coarse_offset'] / target_sr,
                'coarse_confidence': alignment_result['coarse_confidence'],
                'fine_alignment': alignment_result.get('fine_alignment')
            }
            
        except Exception as e:
            print(f"   ⚠️  对齐失败，使用简单裁剪: {e}")
            # 降级到简单裁剪
            min_len = min(len(data1), len(data2))
            data1 = data1[:min_len]
            data2 = data2[:min_len]
            alignment_info = {'method': 'simple_trim', 'error': str(e)}
        
        return data1, data2, alignment_info
    
    def _align_audio(self, data1: np.ndarray, sr1: int, data2: np.ndarray, sr2: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        旧版对齐（向后兼容）：统一采样率，裁剪到相同长度
        """
        result = self._align_audio_v2(data1, sr1, data2, sr2)
        return result[0], result[1]  # 只返回音频，不返回alignment_info
    
    def _compute_global_features(self, data: np.ndarray, sample_rate: int) -> Dict:
        """计算音频文件的全局特征"""
        
        features = {}
        
        # 1. 能量特征
        rms = np.sqrt(np.mean(data ** 2))
        features['rms_energy'] = float(rms)
        features['rms_db'] = float(20 * np.log10(rms + 1e-10))
        features['dynamic_range'] = float(np.max(np.abs(data)) - np.min(np.abs(data)))
        
        # 2. 频谱特征
        fft = np.abs(np.fft.rfft(data))
        freqs = np.fft.rfftfreq(len(data), 1 / sample_rate)
        
        # 频谱中心和带宽
        power = fft ** 2
        centroid = np.sum(freqs * power) / (np.sum(power) + 1e-10)
        bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * power) / (np.sum(power) + 1e-10))
        
        features['spectral_centroid_mean'] = float(centroid)
        features['spectral_bandwidth_mean'] = float(bandwidth)
        
        # 频谱能量分布
        low_freq_energy = np.sum(power[(freqs < 1000)])
        mid_freq_energy = np.sum(power[(freqs >= 1000) & (freqs < 4000)])
        high_freq_energy = np.sum(power[(freqs >= 4000)])
        total_energy = low_freq_energy + mid_freq_energy + high_freq_energy
        
        features['low_freq_ratio'] = float(low_freq_energy / (total_energy + 1e-10))      # 0-1kHz
        features['mid_freq_ratio'] = float(mid_freq_energy / (total_energy + 1e-10))      # 1-4kHz
        features['high_freq_ratio'] = float(high_freq_energy / (total_energy + 1e-10))    # >4kHz
        
        # 3. 时域特征
        features['zcr_mean'] = float(np.mean(np.sum(np.abs(np.diff(np.sign(data))) / 2)) / len(data))
        
        # 4. 整体稳定性
        # 将信号分成10个段，计算每段的统计特性变化
        segment_length = len(data) // 10
        segment_rmss = []
        segment_centroids = []
        
        for i in range(10):
            segment = data[i * segment_length:(i + 1) * segment_length]
            if len(segment) > 0:
                seg_rms = np.sqrt(np.mean(segment ** 2))
                segment_rmss.append(seg_rms)
                
                seg_fft = np.abs(np.fft.rfft(segment))
                seg_freqs = np.fft.rfftfreq(len(segment), 1 / sample_rate)
                seg_power = seg_fft ** 2
                seg_centroid = np.sum(seg_freqs * seg_power) / (np.sum(seg_power) + 1e-10)
                segment_centroids.append(seg_centroid)
        
        # 稳定性 = 段间变异系数
        features['rms_stability'] = float(np.std(segment_rmss) / (np.mean(segment_rmss) + 1e-10))
        features['centroid_stability'] = float(np.std(segment_centroids) / (np.mean(segment_centroids) + 1e-10))
        
        # 5. 失真指标
        # 谐波失真：检查特定频率比例
        fundamental_range = (80, 300)  # 人声基频范围
        fundamental_power = np.sum(power[(freqs >= fundamental_range[0]) & (freqs <= fundamental_range[1])])
        features['harmonic_clarity'] = float(fundamental_power / (np.sum(power) + 1e-10))
        
        # Crest Factor (峰度) - 衡量冲击特性
        # CF = Peak / RMS, 正常语音 ~4-8, 失真语音 ~2-3
        crest_factor = (np.max(np.abs(data)) + 1e-10) / (rms + 1e-10)
        features['crest_factor'] = float(crest_factor)
        
        # 峰度（Kurtosis）- 衡量尾部尖锐度
        # 正常语音 ~3, 失真/合成 >5 或 <2
        kurtosis = float(self._compute_kurtosis(data))
        features['kurtosis'] = kurtosis
        
        # 6. Mel频谱特征（人耳感知）
        mel_spec = self._compute_mel_spectrogram(data, sample_rate)
        features['mel_entropy'] = float(self._compute_entropy(mel_spec))
        features['mel_flatness'] = float(self._compute_spectral_flatness(mel_spec))
        
        return features
    
    def _compute_kurtosis(self, data: np.ndarray) -> float:
        """计算峰度（Kurtosis）"""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 4)
    
    def _compute_mel_spectrogram(self, data: np.ndarray, sample_rate: int, n_mels: int = 13) -> np.ndarray:
        """计算Mel频谱（简化版）"""
        
        # 使用Mel滤波器近似
        n_fft = 2048
        hop_length = 512
        
        # 简单的时频分析
        num_frames = (len(data) - n_fft) // hop_length + 1
        mel_spec = np.zeros((num_frames, n_mels))
        
        for i in range(num_frames):
            frame = data[i * hop_length:i * hop_length + n_fft]
            if len(frame) < n_fft:
                frame = np.pad(frame, (0, n_fft - len(frame)))
            
            # 计算功率谱
            fft = np.abs(np.fft.rfft(frame))
            power = fft ** 2
            
            # 简化：将功率谱分成n_mels个梅尔频率段
            for j in range(n_mels):
                freq_start = int(j * len(power) / n_mels)
                freq_end = int((j + 1) * len(power) / n_mels)
                mel_spec[i, j] = np.mean(power[freq_start:freq_end])
        
        # 对整个频谱求平均
        return np.mean(mel_spec, axis=0)
    
    def _compute_entropy(self, spectrum: np.ndarray) -> float:
        """计算频谱熵（衡量分散度）"""
        spectrum = np.abs(spectrum)
        spectrum = spectrum / (np.sum(spectrum) + 1e-10)
        entropy = -np.sum(spectrum * np.log(spectrum + 1e-10))
        return entropy
    
    def _compute_spectral_flatness(self, spectrum: np.ndarray) -> float:
        """计算频谱平坦度（Wiener Entropy）"""
        spectrum = np.abs(spectrum) + 1e-10
        geometric_mean = np.exp(np.mean(np.log(spectrum)))
        arithmetic_mean = np.mean(spectrum)
        flatness = geometric_mean / (arithmetic_mean + 1e-10)
        return flatness
    
    def _compare_features(self, test_features: Dict, baseline_features: Dict) -> Dict:
        """比较测试特征与基线特征"""
        
        comparison = {
            "differences": {},
            "anomaly_scores": {},
            "overall_distortion_index": 0.0
        }
        
        # 关键特征对比
        key_features = [
            'rms_energy',
            'spectral_centroid_mean',
            'spectral_bandwidth_mean',
            'low_freq_ratio',
            'mid_freq_ratio',
            'high_freq_ratio',
            'rms_stability',
            'centroid_stability',
            'harmonic_clarity',
            'crest_factor',
            'kurtosis',
            'mel_entropy',
            'mel_flatness'
        ]
        
        anomaly_scores = []
        
        for feature in key_features:
            test_val = test_features.get(feature, 0)
            baseline_val = baseline_features.get(feature, 0)
            
            if baseline_val == 0:
                diff_ratio = 0
            else:
                diff_ratio = (test_val - baseline_val) / (abs(baseline_val) + 1e-10)
            
            comparison["differences"][feature] = {
                "test": test_val,
                "baseline": baseline_val,
                "diff_ratio": diff_ratio
            }
            
            # 异常度评分（基于偏离程度）
            anomaly = self._calculate_anomaly_score(feature, diff_ratio, test_val, baseline_val)
            comparison["anomaly_scores"][feature] = anomaly
            anomaly_scores.append(anomaly)
        
        # 综合异常指数
        comparison["overall_distortion_index"] = float(np.mean(anomaly_scores))
        
        return comparison
    
    def _calculate_anomaly_score(self, feature_name: str, diff_ratio: float, test_val: float, baseline_val: float) -> float:
        """
        计算特定特征的异常度 [0, 1]
        """
        
        # 不同特征有不同的正常偏差范围
        expected_ranges = {
            'rms_energy': 0.3,          # ±30% 正常
            'spectral_centroid_mean': 0.2,
            'spectral_bandwidth_mean': 0.25,
            'low_freq_ratio': 0.15,
            'mid_freq_ratio': 0.15,
            'high_freq_ratio': 0.20,
            'rms_stability': 0.5,       # 稳定性差异较大
            'centroid_stability': 0.4,
            'harmonic_clarity': 0.2,
            'crest_factor': 0.3,        # ±30%
            'kurtosis': 1.0,            # 峰度差异大
            'mel_entropy': 0.2,
            'mel_flatness': 0.3
        }
        
        expected_range = expected_ranges.get(feature_name, 0.2)
        
        # 异常度 = max(0, (实际偏差 - 预期偏差) / 预期偏差)
        if abs(diff_ratio) <= expected_range:
            return 0.0
        else:
            anomaly = min(1.0, (abs(diff_ratio) - expected_range) / expected_range)
            return anomaly
    
    def _assess_quality(self, features: Dict, baseline_comparison: Dict = None) -> Dict:
        """对整段文件进行质量评估
        
        Args:
            features: 测试音频的全局特征
            baseline_comparison: 基线对比结果（可选）
            
        Returns:
            包含质量评估的字典
        """
        
        # 如果有基线对比，优先使用相对评估
        if baseline_comparison:
            return self._assess_quality_relative(features, baseline_comparison)
        
        # 否则使用绝对评估（基于理论标准）
        assessment = {
            "overall_quality": "GOOD",
            "quality_score": 1.0,  # 0-1, 1=最好
            "issues": [],
            "details": {},
            "evaluation_method": "absolute"
        }
        
        score = 1.0
        
        # 1. 检查Crest Factor（峰度异常 = 失真迹象）
        cf = features.get('crest_factor', 5.0)
        if cf < 2.5 or cf > 8.0:  # 偏离正常范围
            assessment["issues"].append(f"异常Crest Factor: {cf:.2f} (预期: 4-8)")
            score -= 0.15
            assessment["details"]["crest_factor_issue"] = "可能存在严重失真或合成语音"
        
        # 2. 检查峰度（Kurtosis）
        kurtosis = features.get('kurtosis', 3.0)
        if kurtosis > 5.0 or kurtosis < 1.5:  # 偏离正常范围
            assessment["issues"].append(f"异常峰度: {kurtosis:.2f} (预期: 2-4)")
            score -= 0.15
            assessment["details"]["kurtosis_issue"] = "频谱分布异常，可能是合成或编码失真"
        
        # 3. 检查谐波清晰度
        harmonic_clarity = features.get('harmonic_clarity', 0.3)
        if harmonic_clarity < 0.15:
            assessment["issues"].append(f"谐波清晰度低: {harmonic_clarity:.3f}")
            score -= 0.15
            assessment["details"]["low_harmonic_clarity"] = "可能是广带噪声或失真"
        
        # 4. 检查频谱平坦度
        mel_flatness = features.get('mel_flatness', 0.5)
        if mel_flatness < 0.3:
            assessment["issues"].append(f"Mel频谱平坦度低: {mel_flatness:.3f}")
            score -= 0.1
            assessment["details"]["low_spectral_flatness"] = "频谱过于尖锐，可能存在编码失真"
        
        # 5. 检查稳定性
        rms_stability = features.get('rms_stability', 0.2)
        if rms_stability > 0.5:
            assessment["issues"].append(f"RMS稳定性差: {rms_stability:.3f}")
            score -= 0.1
            assessment["details"]["poor_rms_stability"] = "音量波动异常"
        
        centroid_stability = features.get('centroid_stability', 0.15)
        if centroid_stability > 0.4:
            assessment["issues"].append(f"中心频率稳定性差: {centroid_stability:.3f}")
            score -= 0.1
            assessment["details"]["poor_centroid_stability"] = "频谱特性波动异常"
        
        # 6. 频率分布检查
        low_freq = features.get('low_freq_ratio', 0.2)
        high_freq = features.get('high_freq_ratio', 0.2)
        
        if low_freq > 0.6 or high_freq > 0.5:
            assessment["issues"].append(f"频谱分布异常: 低频{low_freq:.1%}, 高频{high_freq:.1%}")
            score -= 0.1
            assessment["details"]["abnormal_freq_distribution"] = "可能是编码失真或特殊处理"
        
        score = max(0.0, score)
        assessment["quality_score"] = score
        
        # 判断质量等级
        if score >= 0.85:
            assessment["overall_quality"] = "✅ GOOD (正常)"
        elif score >= 0.70:
            assessment["overall_quality"] = "⚠️  FAIR (轻微问题)"
        elif score >= 0.50:
            assessment["overall_quality"] = "❌ POOR (显著问题)"
        else:
            assessment["overall_quality"] = "🚫 DISTORTED (严重失真)"
        
        return assessment
    
    def _assess_quality_relative(self, features: Dict, baseline_comparison: Dict) -> Dict:
        """基于基线的相对质量评估
        
        Args:
            features: 测试音频的全局特征
            baseline_comparison: 基线对比结果
            
        Returns:
            相对质量评估结果
        """
        distortion_index = baseline_comparison.get("overall_distortion_index", 0)
        anomaly_scores = baseline_comparison.get("anomaly_scores", {})
        differences = baseline_comparison.get("differences", {})
        
        # 基于失真指数计算分数
        score = max(0.0, 1.0 - distortion_index)
        
        # 根据失真度分级
        if distortion_index < 0.15:
            quality_label = "✅ EXCELLENT (与基线高度一致)"
        elif distortion_index < 0.30:
            quality_label = "✅ GOOD (与基线接近)"
        elif distortion_index < 0.50:
            quality_label = "⚠️  FAIR (与基线有差异)"
        else:
            quality_label = "❌ POOR (与基线差异显著)"
        
        assessment = {
            "overall_quality": quality_label,
            "quality_score": score,
            "evaluation_method": "relative",
            "baseline_distortion_index": distortion_index,
            "issues": [],
            "details": {}
        }
        
        # 列出主要异常项（异常度 >= 0.8）
        high_anomaly_features = []
        for feature, anomaly in anomaly_scores.items():
            if anomaly >= 0.8:
                diff_info = differences.get(feature, {})
                test_val = diff_info.get('test', 0)
                baseline_val = diff_info.get('baseline', 0)
                diff_ratio = diff_info.get('diff_ratio', 0)
                
                # 格式化特征名
                feature_name = feature.replace('_', ' ').title()
                
                if abs(diff_ratio) > 0.01:
                    assessment["issues"].append(
                        f"{feature_name}: {test_val:.4g} (基线: {baseline_val:.4g}, 偏差: {diff_ratio:+.1%})"
                    )
                    high_anomaly_features.append(feature_name)
        
        # 添加详细说明
        if distortion_index < 0.15:
            assessment["details"]["summary"] = "测试音频与基线高度一致，质量稳定"
        elif distortion_index < 0.30:
            assessment["details"]["summary"] = "测试音频与基线接近，有轻微差异"
        elif distortion_index < 0.50:
            assessment["details"]["summary"] = f"测试音频与基线存在明显差异，主要问题：{', '.join(high_anomaly_features[:3]) if high_anomaly_features else '多项指标偏离'}"
        else:
            assessment["details"]["summary"] = f"测试音频与基线差异显著，需要改善：{', '.join(high_anomaly_features[:3]) if high_anomaly_features else '多项指标严重偏离'}"
        
        return assessment
    
    def _print_results(self, result: Dict):
        """打印分析结果"""
        
        print("\n" + "=" * 70)
        print("📈 全局特征")
        print("=" * 70)
        
        features = result["global_features"]
        
        print(f"\n能量特征:")
        print(f"  RMS Energy: {features.get('rms_energy', 0):.6f} ({features.get('rms_db', 0):.2f} dB)")
        print(f"  Dynamic Range: {features.get('dynamic_range', 0):.6f}")
        
        print(f"\n频谱特征:")
        print(f"  Spectral Centroid: {features.get('spectral_centroid_mean', 0):.2f} Hz")
        print(f"  Spectral Bandwidth: {features.get('spectral_bandwidth_mean', 0):.2f} Hz")
        print(f"  Low Freq (<1kHz): {features.get('low_freq_ratio', 0):.1%}")
        print(f"  Mid Freq (1-4kHz): {features.get('mid_freq_ratio', 0):.1%}")
        print(f"  High Freq (>4kHz): {features.get('high_freq_ratio', 0):.1%}")
        
        print(f"\n稳定性指标:")
        print(f"  RMS Stability: {features.get('rms_stability', 0):.4f} (低=稳定)")
        print(f"  Centroid Stability: {features.get('centroid_stability', 0):.4f}")
        
        print(f"\n失真指标:")
        print(f"  Crest Factor: {features.get('crest_factor', 0):.2f} (正常: 4-8)")
        print(f"  Kurtosis: {features.get('kurtosis', 0):.2f} (正常: 2-4)")
        print(f"  Harmonic Clarity: {features.get('harmonic_clarity', 0):.3f}")
        print(f"  Mel Entropy: {features.get('mel_entropy', 0):.3f}")
        print(f"  Mel Flatness: {features.get('mel_flatness', 0):.3f}")
        
        # 质量评估
        qa = result["quality_assessment"]
        eval_method = qa.get("evaluation_method", "unknown")
        
        print("\n" + "=" * 70)
        print("🎯 质量评估")
        print("=" * 70)
        
        # 显示评估方法
        if eval_method == "relative":
            print("\n📊 评估模式: 相对评估（基于基线对比）")
            distortion_idx = qa.get("baseline_distortion_index", 0)
            print(f"与基线差异指数: {distortion_idx:.2%}")
        else:
            print("\n📊 评估模式: 绝对评估（基于理论标准）")
        
        print(f"\n整体质量: {qa['overall_quality']}")
        print(f"质量分数: {qa['quality_score']:.2f} / 1.00")
        
        # 显示摘要
        summary = qa.get("details", {}).get("summary")
        if summary:
            print(f"\n{summary}")
        
        if qa["issues"]:
            print(f"\n{'主要差异项' if eval_method == 'relative' else '检测到的问题'} ({len(qa['issues'])} 项):")
            for issue in qa["issues"]:
                print(f"  ⚠️  {issue}")
        else:
            if eval_method == "relative":
                print("\n✅ 各项指标与基线一致")
            else:
                print("\n✓ 未检测到明显问题")
        
        # 基线对比
        if result["baseline_comparison"]:
            comp = result["baseline_comparison"]
            print("\n" + "=" * 70)
            print("📊 与基线对比")
            print("=" * 70)
            print(f"\n整体失真指数: {comp['overall_distortion_index']:.2%}")
            
            if comp['overall_distortion_index'] > 0.15:
                print(f"⚠️  检测到显著失真 (偏差 > 15%)")
                print(f"\n主要差异特征:")
                
                # 显示异常度最高的特征
                top_anomalies = sorted(
                    comp['anomaly_scores'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                for feature, anomaly_score in top_anomalies:
                    if anomaly_score > 0:
                        diff_info = comp['differences'][feature]
                        print(f"  {feature}:")
                        print(f"    异常度: {anomaly_score:.1%}")
                        print(f"    测试值: {diff_info['test']:.4f}")
                        print(f"    基线值: {diff_info['baseline']:.4f}")
                        print(f"    偏离: {diff_info['diff_ratio']:+.1%}")
            else:
                print(f"✓ 与基线差异在正常范围内")


def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python global_distortion_analyzer.py <audio_file> [baseline_file]")
        print("\n示例:")
        print("  python global_distortion_analyzer.py test.wav")
        print("  python global_distortion_analyzer.py test.wav baseline.wav")
        return
    
    audio_file = sys.argv[1]
    baseline_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(audio_file):
        print(f"❌ 文件不存在: {audio_file}")
        return
    
    analyzer = GlobalDistortionAnalyzer()
    result = analyzer.analyze_file(audio_file, baseline_file)


if __name__ == '__main__':
    main()
