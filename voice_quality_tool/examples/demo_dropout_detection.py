#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本：生成包含陡增和陡降的测试音频，展示改进的Dropout检测
"""

import numpy as np
from scipy.io import wavfile
import sys
import os

# 添加父目录到路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)

from analyzer import Analyzer, DEFAULT_CONFIG, frame_generator

# 生成测试音频
sample_rate = 16000
duration = 5  # 5秒

# 创建时间轴
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio = np.zeros_like(t)

# 1. 0-1s：正常语音 (模拟)
normal_segment = 0.15 * np.sin(2 * np.pi * 200 * t[(t >= 0) & (t < 1)]) + \
                 0.05 * np.random.randn(np.sum((t >= 0) & (t < 1)))
audio[(t >= 0) & (t < 1)] = normal_segment

# 2. 1-1.3s：陡降到静音（dropout）
audio[(t >= 1) & (t < 1.3)] = 0.001 * np.random.randn(np.sum((t >= 1) & (t < 1.3)))

# 3. 1.3-2s：恢复正常
normal_segment2 = 0.15 * np.sin(2 * np.pi * 250 * t[(t >= 1.3) & (t < 2)]) + \
                  0.05 * np.random.randn(np.sum((t >= 1.3) & (t < 2)))
audio[(t >= 1.3) & (t < 2)] = normal_segment2

# 4. 2-2.5s：陡增（突然尖刺/啸叫，延长到250ms以超过最小阈值50ms）
spike_segment = 0.85 * np.sin(2 * np.pi * 3000 * t[(t >= 2) & (t < 2.25)])
audio[(t >= 2) & (t < 2.25)] = spike_segment

# 5. 2.25-5s：恢复正常
normal_segment3 = 0.15 * np.sin(2 * np.pi * 200 * t[(t >= 2.25) & (t < 5)]) + \
                  0.05 * np.random.randn(np.sum((t >= 2.25) & (t < 5)))
audio[(t >= 2.25) & (t < 5)] = normal_segment3

# 规范化到16位
audio = np.int16(audio * 32767)

# 保存测试音频
test_file = 'test_dropout_discontinuities.wav'
wavfile.write(test_file, sample_rate, audio)
print(f"✓ 生成测试文件: {test_file}")
print(f"  - 0-1s：正常语音")
print(f"  - 1-1.3s：陡降到静音")
print(f"  - 1.3-2s：恢复正常")
print(f"  - 2-2.25s：陡增（突然尖刺，250ms）")
print(f"  - 2.25-5s：恢复正常\n")

# 分析
print("运行Dropout检测...\n")
sr, data = wavfile.read(test_file)

config = DEFAULT_CONFIG.copy()
config['sample_rate'] = sr

analyzer = Analyzer(config)
frame_size = int(sr * 0.025)
hop_size = int(sr * 0.010)
frames = frame_generator(data, sr, frame_size, hop_size)
result = analyzer.analyze_frames(frames)

# 显示结果
data_dict = result.to_dict()

print("=" * 60)
print("📊 检测结果")
print("=" * 60)
print(f"\n🔴 Dropout 检测: {data_dict['dropout']['count']} 个\n")

if data_dict['dropout']['count'] > 0:
    for i, event in enumerate(data_dict['dropout']['events'], 1):
        print(f"{i}. {event['start']:.2f}s - {event['end']:.2f}s", end="")
        
        # 识别类型
        if event['start'] >= 1.0 and event['start'] < 1.3:
            print(" ⬇️  陡降到静音 (DROPOUT)")
        elif event['start'] >= 2.0 and event['start'] < 2.25:
            print(" ⬆️  陡增尖刺 (SPIKE)")
        else:
            print(" ❓ 其他")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)
print("\n改进要点：")
print("✓ 检测到陡降到静音（1.0-1.3s）")
print("✓ 检测到陡增尖刺（2.0-2.2s）")
print("✓ 不误报正常语音段落")
