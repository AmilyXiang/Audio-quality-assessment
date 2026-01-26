#!/usr/bin/env python3
"""测试脚本：验证新特征提取和检测功能.

运行：
    python test_new_features.py <test_audio.wav>
"""
import sys
import json
import argparse
import numpy as np
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG
from analyzer.features import (
    extract_features, peak_to_peak, spectral_rolloff, 
    rms_percentile, compute_mfcc
)
from analyzer.frame import Frame


def test_feature_extraction(audio_path):
    """测试新特征提取"""
    try:
        from scipy.io import wavfile
    except ImportError:
        print("❌ scipy not installed")
        return False
    
    print("=" * 60)
    print("🧪 测试新特征提取")
    print("=" * 60)
    
    try:
        sample_rate, data = wavfile.read(audio_path)
        if len(data.shape) > 1:
            data = data[:, 0]
        
        data = data.astype(float)
        if data.max() > 1.0 or data.min() < -1.0:
            data = data / (2 ** 15)
    except Exception as e:
        print(f"❌ 加载音频失败: {e}")
        return False
    
    # 生成帧
    frame_size = int(sample_rate * 0.025)
    hop_size = int(sample_rate * 0.010)
    frames = frame_generator(data, sample_rate, frame_size, hop_size)
    
    feature_stats = {
        "rms": [], "peak_to_peak": [], "spectral_rolloff": [],
        "rms_percentile_95": [], "spectral_centroid": [], "spectral_flux": []
    }
    
    prev_frame = None
    for i, frame in enumerate(frames):
        features = extract_features(frame, prev_frame)
        
        # 收集统计数据
        for key in feature_stats.keys():
            if key in features:
                feature_stats[key].append(features[key])
        
        # 打印前3帧
        if i < 3:
            print(f"\n📊 帧 {i+1} 特征:")
            print(f"   RMS: {features.get('rms', 0):.4f}")
            print(f"   Peak-to-Peak: {features.get('peak_to_peak', 0):.4f} (削波检测)")
            print(f"   Spectral Rolloff: {features.get('spectral_rolloff', 0):.1f} Hz (风噪检测)")
            print(f"   RMS Percentile 95: {features.get('rms_percentile_95', 0):.4f} (瞬态检测)")
            print(f"   Spectral Centroid: {features.get('spectral_centroid', 0):.1f} Hz")
            print(f"   Spectral Flux: {features.get('spectral_flux', 0):.4f}")
        
        prev_frame = frame
        if i >= 10:  # 只处理前11帧用于演示
            break
    
    # 统计汇总
    print("\n" + "=" * 60)
    print("📈 特征统计汇总")
    print("=" * 60)
    
    for key, values in feature_stats.items():
        if values:
            print(f"\n{key}:")
            print(f"   Mean: {np.mean(values):.4f}")
            print(f"   Std:  {np.std(values):.4f}")
            print(f"   Min:  {np.min(values):.4f}")
            print(f"   Max:  {np.max(values):.4f}")
            
            # 异常检测提示
            if key == "peak_to_peak" and np.max(values) > 1.8:
                print(f"   ⚠️  检测到可能的削波信号！")
            elif key == "spectral_rolloff" and np.mean(values) > 3000:
                print(f"   ⚠️  检测到可能的高频噪声（风噪）！")
    
    return True


def test_mfcc_extraction(audio_path):
    """测试MFCC特征提取"""
    print("\n" + "=" * 60)
    print("🧪 测试MFCC特征提取（第2阶段）")
    print("=" * 60)
    
    try:
        from scipy.io import wavfile
        import librosa
    except ImportError as e:
        print(f"⚠️  缺少依赖: {e}")
        print("   运行: pip install librosa")
        return False
    
    try:
        sample_rate, data = wavfile.read(audio_path)
        if len(data.shape) > 1:
            data = data[:, 0]
        
        data = data.astype(float)
        if data.max() > 1.0 or data.min() < -1.0:
            data = data / (2 ** 15)
    except Exception as e:
        print(f"❌ 加载音频失败: {e}")
        return False
    
    # 计算MFCC
    try:
        mfcc = compute_mfcc(data, sample_rate, n_mfcc=13)
        print(f"\n✅ MFCC提取成功")
        print(f"   维度: {len(mfcc)}")
        print(f"   向量: {mfcc}")
        print(f"\n💡 MFCC用途: 捕捉音色特征，用于MOS/NISQA评分对标")
    except Exception as e:
        print(f"❌ MFCC计算失败: {e}")
        return False
    
    return True


def test_detector_enhancement(audio_path):
    """测试增强的检测器"""
    print("\n" + "=" * 60)
    print("🧪 测试检测器增强（利用新特征）")
    print("=" * 60)
    
    try:
        from scipy.io import wavfile
    except ImportError:
        print("❌ scipy not installed")
        return False
    
    try:
        sample_rate, data = wavfile.read(audio_path)
        if len(data.shape) > 1:
            data = data[:, 0]
        
        data = data.astype(float)
        if data.max() > 1.0 or data.min() < -1.0:
            data = data / (2 ** 15)
    except Exception as e:
        print(f"❌ 加载音频失败: {e}")
        return False
    
    # 创建分析器
    analyzer = Analyzer(config=DEFAULT_CONFIG)
    
    # 生成帧并分析
    frame_size = int(sample_rate * 0.025)
    hop_size = int(sample_rate * 0.010)
    frames = frame_generator(data, sample_rate, frame_size, hop_size)
    
    result = analyzer.analyze_frames(frames)
    
    print(f"\n✅ 分析完成")
    print(f"   处理帧数: {result.frames_processed}")
    print(f"   总时长: {result.total_duration:.2f}s")
    print(f"\n📋 检测事件:")
    
    for event_type, events in result.events.items():
        if events:
            print(f"   {event_type}: {len(events)} 个事件")
            for evt in events[:2]:  # 显示前2个事件
                details = evt.get("details", {})
                reason = details.get("reason", "unknown")
                print(f"      - {evt['start']:.2f}s ~ {evt['end']:.2f}s, 原因: {reason}")
    
    if not any(result.events.values()):
        print(f"   ℹ️  未检测到质量问题")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="测试新特征和检测器增强")
    parser.add_argument("audio_path", help="测试音频文件路径")
    args = parser.parse_args()
    
    print(f"\n🎤 测试音频: {args.audio_path}\n")
    
    # 测试1: 特征提取
    if not test_feature_extraction(args.audio_path):
        return False
    
    # 测试2: MFCC提取
    test_mfcc_extraction(args.audio_path)
    
    # 测试3: 检测器增强
    if not test_detector_enhancement(args.audio_path):
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    print("\n📚 特征说明:")
    print("   ✓ Peak-to-Peak: 检测削波和爆音")
    print("   ✓ Spectral Rolloff: 检测风噪和高频噪声")
    print("   ✓ RMS Percentile 95: 检测瞬态事件")
    print("   ✓ MFCC (第2阶段): 音色特征，用于MOS对标")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
