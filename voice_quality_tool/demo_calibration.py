#!/usr/bin/env python3
"""标定和分析演示脚本"""
import sys
import json
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG, compute_baseline_stats
from scipy.io import wavfile

print("\n" + "="*70)
print("标定和分析Demo演示".center(70))
print("="*70)

# 标定音频
calibration_audio = "../test_db_dropout.wav"
print(f"\n📁 标定音频: {calibration_audio}")

try:
    sample_rate, data = wavfile.read(calibration_audio)
    if len(data.shape) > 1:
        data = data[:, 0]
    
    data = data.astype(float)
    if data.max() > 1.0 or data.min() < -1.0:
        data = data / (2 ** 15)
    
    print(f"   采样率: {sample_rate} Hz")
    print(f"   时长: {len(data) / sample_rate:.2f}s")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    sys.exit(1)

# 生成帧并标定
print("\n📊 执行标定...")
analyzer = Analyzer(config=DEFAULT_CONFIG)
frame_size = int(sample_rate * 0.025)
hop_size = int(sample_rate * 0.010)
frames = frame_generator(data, sample_rate, frame_size, hop_size)

baseline = analyzer.calibrate(frames)

print("\n✅ 标定完成！")
print("\n📋 基线统计 (Baseline Statistics):")
print("\n   === 核心特征 ===")
print(f"   RMS Mean:      {baseline.get('rms_mean', 0):.6f}")
print(f"   RMS Std:       {baseline.get('rms_std', 0):.6f}")
print(f"   ZCR Mean:      {baseline.get('zcr_mean', 0):.6f}")
print(f"   Centroid Mean: {baseline.get('centroid_mean', 0):.1f} Hz")
print(f"   Flux Mean:     {baseline.get('spectral_flux_mean', 0):.6f}")

print("\n   === 第1阶段特征（新增）===")
print(f"   Peak-to-Peak Mean:     {baseline.get('peak_to_peak_mean', 0):.6f}")
print(f"   Peak-to-Peak Max:      {baseline.get('peak_to_peak_max', 0):.6f}")
print(f"   Spectral Rolloff Mean: {baseline.get('spectral_rolloff_mean', 0):.1f} Hz")
print(f"   RMS Percentile 95:     {baseline.get('rms_percentile_mean', 0):.6f}")

# 现在分析另一个音频
print("\n" + "="*70)
print("第2步：分析音频文件".center(70))
print("="*70)

analysis_audio = "../test_dropout_debug.wav"
print(f"\n📁 分析音频: {analysis_audio}")

try:
    sample_rate, data = wavfile.read(analysis_audio)
    if len(data.shape) > 1:
        data = data[:, 0]
    
    data = data.astype(float)
    if data.max() > 1.0 or data.min() < -1.0:
        data = data / (2 ** 15)
    
    print(f"   采样率: {sample_rate} Hz")
    print(f"   时长: {len(data) / sample_rate:.2f}s")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    sys.exit(1)

# 分析
print("\n📊 执行分析...")
analyzer2 = Analyzer(config=DEFAULT_CONFIG)
# 先设置基线（使用上面的标定结果）
for detector in [analyzer2.noise_detector, analyzer2.dropout_detector, 
                 analyzer2.volume_detector, analyzer2.distortion_detector]:
    detector.set_baseline(baseline)

frames2 = frame_generator(data, sample_rate, frame_size, hop_size)
result = analyzer2.analyze_frames(frames2)

print("\n✅ 分析完成！")
print("\n📊 分析结果:")
print(f"   处理帧数: {result.frames_processed}")
print(f"   总时长: {result.total_duration:.2f}s")

print("\n📋 检测到的问题:")
# result.events 是一个列表而不是字典
if isinstance(result.events, list):
    events = result.events
else:
    events = result.events if hasattr(result, 'events') else []

if events:
    print(f"   共检测到 {len(events)} 个事件\n")
    for i, evt in enumerate(events[:5], 1):  # 显示前5个
        event_type = evt.get('event_type', 'unknown')
        start = evt.get('start', 0)
        end = evt.get('end', 0)
        reason = evt.get('details', {}).get('reason', 'unknown') if isinstance(evt.get('details'), dict) else 'unknown'
        confidence = evt.get('confidence', 0)
        print(f"      {i}. [{event_type}] {start:.2f}s ~ {end:.2f}s")
        print(f"         原因: {reason}")
        print(f"         置信度: {confidence:.2%}")
        
        # 显示详细指标
        details = evt.get('details', {})
        if isinstance(details, dict):
            for key, value in details.items():
                if key != 'reason':
                    if isinstance(value, float):
                        print(f"         {key}: {value:.4f}")
                    else:
                        print(f"         {key}: {value}")
        print()
else:
    print("   ✅ 未检测到质量问题！")

print("\n" + "="*70)
print("演示完成".center(70))
print("="*70)

print("\n💡 总结:")
print("   ✅ 标定过程：学习设备和环境的基线特性")
print("   ✅ 分析过程：基于基线检测音频质量问题")
print("   ✅ 新特征：Peak-to-Peak, Spectral Rolloff, RMS P95")
print("   ✅ 结果：JSON格式输出，便于集成")

print("\n🚀 下一步:")
print("   1. 使用生成的设备档案分析新音频")
print("   2. 调整阈值参数优化检测性能")
print("   3. 集成到您的应用系统")

print()
