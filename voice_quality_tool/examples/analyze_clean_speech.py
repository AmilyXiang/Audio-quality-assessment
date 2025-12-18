#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
干净语音分析示例

展示如何使用超宽松配置分析高质量录音室录音、播客等干净语音。
这种配置可以显著减少误报，适合专业音频环境。
"""

import sys
import os

# 添加父目录到路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# 切换工作目录到项目根目录
os.chdir(parent_dir)

from analyzer.config import Config
from analyzer.audio_loader import load_audio_file
from analyzer.detector_pipeline import DetectorPipeline
from analyzer.result import AnalysisResult


def analyze_clean_speech(audio_path: str):
    """
    使用干净语音配置分析音频文件
    
    Args:
        audio_path: 音频文件路径
    """
    print(f"🎙️  分析文件: {audio_path}")
    print(f"{'=' * 70}\n")
    
    # ============================================================
    # 1. 创建干净语音配置
    # ============================================================
    clean_config = Config(
        # 最小持续时间：比默认值提高 3-4 倍
        min_dropout_duration=0.20,      # 默认: 0.05s
        min_distortion_duration=0.50,   # 默认: 0.12s
        min_noise_duration=0.60,        # 默认: 0.15s
        min_volume_duration=1.00,       # 默认: 0.25s
        
        # 阈值倍数
        dropout_threshold_multiplier=3.0,
        volume_threshold_multiplier=2.0,
        
        # VAD设置
        vad_enabled=True,
        vad_frame_duration_ms=20,
        vad_padding_duration_ms=200,
        vad_energy_threshold=0.02,
        
        # 采样率将从音频文件自动检测
        sample_rate=None
    )
    
    print("📋 配置详情:")
    print(f"  最小卡顿时长: {clean_config.min_dropout_duration}s")
    print(f"  最小失真时长: {clean_config.min_distortion_duration}s")
    print(f"  最小噪声时长: {clean_config.min_noise_duration}s")
    print(f"  最小音量波动时长: {clean_config.min_volume_duration}s")
    print(f"  VAD启用: {clean_config.vad_enabled}")
    print()
    
    # ============================================================
    # 2. 加载音频文件
    # ============================================================
    print("📂 加载音频文件...")
    try:
        frames, sample_rate, duration = load_audio_file(audio_path)
        print(f"  ✅ 加载成功")
        print(f"  采样率: {sample_rate} Hz")
        print(f"  时长: {duration:.2f} 秒")
        print(f"  总帧数: {len(frames)}")
        print()
    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        return
    
    # 更新配置中的采样率
    clean_config.sample_rate = sample_rate
    
    # ============================================================
    # 3. 运行检测
    # ============================================================
    print("🔍 开始分析...")
    pipeline = DetectorPipeline(clean_config)
    result = AnalysisResult()
    
    for event in pipeline.process(frames):
        result.add_event(event)
    
    result.finalize(duration)
    print("  ✅ 分析完成\n")
    
    # ============================================================
    # 4. 显示结果
    # ============================================================
    print(f"{'=' * 70}")
    print(f"📊 检测结果")
    print(f"{'=' * 70}\n")
    
    data = result.to_dict()
    
    print(f"噪声 (NOISE):           {data['noise']['count']} 个")
    print(f"卡顿 (DROPOUT):         {data['dropout']['count']} 个")
    print(f"音量波动 (VOLUME):       {data['volume_fluctuation']['count']} 个")
    print(f"失真 (DISTORTION):      {data['voice_distortion']['count']} 个")
    print(f"{'-' * 70}")
    
    total = (data['noise']['count'] + 
             data['dropout']['count'] + 
             data['volume_fluctuation']['count'] + 
             data['voice_distortion']['count'])
    print(f"总计:                   {total} 个\n")
    
    # ============================================================
    # 5. 质量评估
    # ============================================================
    if total == 0:
        quality = "优秀"
        emoji = "🎉"
    elif total <= 5:
        quality = "良好"
        emoji = "✅"
    elif total <= 15:
        quality = "一般"
        emoji = "⚠️"
    else:
        quality = "较差"
        emoji = "❌"
    
    print(f"{emoji} 音频质量: {quality}")
    print()
    
    # ============================================================
    # 6. 详细事件列表
    # ============================================================
    if total > 0:
        print(f"{'=' * 70}")
        print(f"📝 事件详情")
        print(f"{'=' * 70}\n")
        
        # 按类型分组显示
        for event_type in ['noise', 'dropout', 'volume_fluctuation', 'voice_distortion']:
            type_data = data[event_type]
            if type_data['count'] > 0:
                type_names = {
                    'noise': '噪声',
                    'dropout': '卡顿',
                    'volume_fluctuation': '音量波动',
                    'voice_distortion': '失真'
                }
                print(f"\n【{type_names[event_type]}】共 {type_data['count']} 个:")
                
                for i, event in enumerate(type_data['events'], 1):
                    print(f"  {i}. {event['start_time']:.2f}s - {event['end_time']:.2f}s "
                          f"(持续 {event['duration']:.3f}s)")
                    if 'metadata' in event and event['metadata']:
                        for key, value in event['metadata'].items():
                            if isinstance(value, float):
                                print(f"     {key}: {value:.4f}")
                            else:
                                print(f"     {key}: {value}")
        print()


def compare_configs(audio_path: str):
    """
    对比默认配置和干净语音配置的检测结果
    
    Args:
        audio_path: 音频文件路径
    """
    print(f"\n{'=' * 70}")
    print(f"📊 配置对比")
    print(f"{'=' * 70}\n")
    
    # 加载音频
    frames, sample_rate, duration = load_audio_file(audio_path)
    
    configs = [
        ("默认配置", Config(sample_rate=sample_rate)),
        ("干净语音配置", Config(
            sample_rate=sample_rate,
            min_dropout_duration=0.20,
            min_distortion_duration=0.50,
            min_noise_duration=0.60,
            min_volume_duration=1.00
        ))
    ]
    
    results = []
    for name, config in configs:
        pipeline = DetectorPipeline(config)
        result = AnalysisResult()
        
        for event in pipeline.process(frames):
            result.add_event(event)
        
        result.finalize(duration)
        data = result.to_dict()
        
        counts = {
            'noise': data['noise']['count'],
            'dropout': data['dropout']['count'],
            'volume': data['volume_fluctuation']['count'],
            'distortion': data['voice_distortion']['count']
        }
        counts['total'] = sum(counts.values())
        
        results.append((name, counts))
    
    # 显示对比表格
    print(f"{'配置':<15} {'噪声':>8} {'卡顿':>8} {'音量':>8} {'失真':>8} {'总计':>8}")
    print(f"{'-' * 70}")
    
    for name, counts in results:
        print(f"{name:<15} {counts['noise']:>8} {counts['dropout']:>8} "
              f"{counts['volume']:>8} {counts['distortion']:>8} {counts['total']:>8}")
    
    # 改善百分比
    if results[0][1]['total'] > 0:
        improvement = (1 - results[1][1]['total'] / results[0][1]['total']) * 100
        print(f"\n💡 使用干净语音配置减少了 {improvement:.1f}% 的检测问题\n")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python analyze_clean_speech.py <audio_file> [--compare]")
        print()
        print("示例:")
        print("  python analyze_clean_speech.py sample.wav")
        print("  python analyze_clean_speech.py sample.wav --compare")
        return
    
    audio_path = sys.argv[1]
    
    if not os.path.exists(audio_path):
        print(f"❌ 文件不存在: {audio_path}")
        return
    
    # 基本分析
    analyze_clean_speech(audio_path)
    
    # 对比模式
    if '--compare' in sys.argv:
        compare_configs(audio_path)


if __name__ == '__main__':
    main()
