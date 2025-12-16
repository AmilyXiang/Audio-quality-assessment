#!/usr/bin/env python3
"""
机器人语音失真检测对比测试

对比：
- 原始DistortionDetector（瞬态失真）
- EnhancedDistortionDetector（瞬态 + 持续失真）
"""

import sys
import json
from scipy.io import wavfile
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG
from analyzer.detectors.enhanced_distortion import EnhancedDistortionDetector, DistortionDetector
from analyzer.detectors.base import merge_adjacent_events, filter_short_events


def analyze_with_original(audio_path, profile_path=None, disable_vad=False):
    """使用原始检测器分析"""
    
    print("=" * 70)
    print("🔍 原始检测器 (Transient Distortion Only)")
    print("=" * 70)
    
    sample_rate, data = wavfile.read(audio_path)
    if len(data.shape) > 1:
        data = data[:, 0]
    
    data = data.astype(float) / 32768.0
    
    config = DEFAULT_CONFIG.copy()
    config['enable_vad'] = not disable_vad
    
    if profile_path:
        with open(profile_path, 'r') as f:
            profile = json.load(f)
            config.update(profile.get('recommended_config', {}))
    
    analyzer = Analyzer(config=config)
    frames = list(frame_generator(data, sample_rate, 1200, 480))  # 25ms frames @ 48kHz
    result = analyzer.analyze_frames(frames)
    
    print(f"Total frames: {len(frames)}")
    print(f"Distortion events: {result.count_by_type('voice_distortion')}")
    
    distortion_events = result.get_events('voice_distortion')
    if distortion_events:
        for event in distortion_events:
            print(f"  [{event.start_time:.2f}s - {event.end_time:.2f}s] (confidence: {event.confidence:.2f})")
    
    return result.get_events('voice_distortion')


def analyze_with_enhanced(audio_path, profile_path=None, disable_vad=False):
    """使用增强检测器分析"""
    
    print("\n" + "=" * 70)
    print("✨ 增强检测器 (Transient + Persistent Distortion)")
    print("=" * 70)
    
    sample_rate, data = wavfile.read(audio_path)
    if len(data.shape) > 1:
        data = data[:, 0]
    
    data = data.astype(float) / 32768.0
    
    config = DEFAULT_CONFIG.copy()
    config['enable_vad'] = not disable_vad
    
    if profile_path:
        with open(profile_path, 'r') as f:
            profile = json.load(f)
            config.update(profile.get('recommended_config', {}))
    
    # 创建自定义分析器，使用增强检测器
    analyzer = Analyzer(config=config)
    
    # 替换失真检测器
    analyzer.detectors['voice_distortion'] = EnhancedDistortionDetector(
        baseline=profile_path
    )
    
    frames = list(frame_generator(data, sample_rate, 1200, 480))
    result = analyzer.analyze_frames(frames)
    
    print(f"Total frames: {len(frames)}")
    print(f"Distortion events: {result.count_by_type('voice_distortion')}")
    
    distortion_events = result.get_events('voice_distortion')
    if distortion_events:
        for event in distortion_events:
            print(f"  [{event.start_time:.2f}s - {event.end_time:.2f}s] (confidence: {event.confidence:.2f})")
    
    return result.get_events('voice_distortion')


def print_comparison_summary(audio_file, original_events, enhanced_events):
    """打印对比总结"""
    
    print("\n" + "=" * 70)
    print("📊 对比分析")
    print("=" * 70)
    
    original_count = len(original_events)
    enhanced_count = len(enhanced_events)
    
    print(f"\n文件: {audio_file}")
    print(f"原始检测器:  {original_count} 个事件")
    print(f"增强检测器:  {enhanced_count} 个事件")
    print(f"增加检测:    {enhanced_count - original_count} 个事件")
    
    if enhanced_count > original_count:
        print(f"\n🎯 增强检测器新发现的事件:")
        
        # 简单比对：时间不重叠 = 新事件
        original_ranges = set()
        for e in original_events:
            original_ranges.add((round(e.start_time, 1), round(e.end_time, 1)))
        
        new_count = 0
        for e in enhanced_events:
            key = (round(e.start_time, 1), round(e.end_time, 1))
            if key not in original_ranges:
                new_count += 1
                print(f"  [{e.start_time:.2f}s - {e.end_time:.2f}s] (类型: 持续失真, 置信度: {e.confidence:.2f})")
        
        print(f"\n📈 检测率提升: {(enhanced_count / max(1, original_count)) * 100 - 100:.1f}%")
    
    print("\n" + "=" * 70)


def main():
    """主函数"""
    
    import os
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    robotic_dir = os.path.join(os.path.dirname(base_dir), 'robotic')
    
    audio_file = os.path.join(robotic_dir, '1010bt161057-robot.wav')
    profile_file = os.path.join(base_dir, 'robot_device_profile.json')
    
    if not os.path.exists(audio_file):
        print(f"❌ 文件不存在: {audio_file}")
        print(f"\n请确保以下文件存在:")
        print(f"  - {audio_file}")
        print(f"  - {profile_file}")
        return
    
    if not os.path.exists(profile_file):
        print(f"❌ 配置文件不存在: {profile_file}")
        print(f"\n请先运行: python calibrate.py ../robotic/1010baseline.wav -o robot_device_profile.json")
        return
    
    print(f"\n🎙️  测试文件: {audio_file}")
    print(f"📋 设备配置: {profile_file}\n")
    
    # 模式1: VAD启用 + 使用设备配置
    print("\n📍 测试模式1: VAD启用 + 设备配置")
    print("-" * 70)
    
    original_events = analyze_with_original(audio_file, profile_file, disable_vad=False)
    enhanced_events = analyze_with_enhanced(audio_file, profile_file, disable_vad=False)
    
    print_comparison_summary(audio_file, original_events, enhanced_events)
    
    # 模式2: VAD禁用 + 使用设备配置
    print("\n\n📍 测试模式2: VAD禁用 + 设备配置")
    print("-" * 70)
    print("(用于调试，检测所有可能的失真，包括背景)")
    
    original_events_no_vad = analyze_with_original(audio_file, profile_file, disable_vad=True)
    enhanced_events_no_vad = analyze_with_enhanced(audio_file, profile_file, disable_vad=True)
    
    print_comparison_summary(audio_file, original_events_no_vad, enhanced_events_no_vad)
    
    # 总结与建议
    print("\n\n" + "🎓 技术总结".center(70, "="))
    print("""
原始检测器局限:
  - 仅检测瞬态失真（点击、爆裂）
  - 对合成/机器人语音无法检测
  - 持续性异常频谱被忽略

增强检测器改进:
  + 检测瞬态失真（保留原有）
  + 新增持续失真检测
  + 使用多维特征分析（频谱、共鸣峰、Mel）
  + 对合成语音更敏感

应用场景:
  ✓ 需要检测合成/机器人语音 → 使用增强检测器
  ✓ 生产环境（真实人声）→ 使用原始检测器
  ✓ 研究/质量评估 → 使用增强检测器（VAD禁用）
""".strip())
    
    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    main()
