#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制音频质量分析报告图表
"""

import matplotlib
matplotlib.use('Agg')  # 无界面后端
import matplotlib.pyplot as plt
import numpy as np

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_analysis_report(result_dict, output_path='report.png'):
    """
    根据分析结果生成可视化报告
    
    Args:
        result_dict: 分析结果字典（从JSON加载）
        output_path: 输出PNG文件路径
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('音频质量分析报告', fontsize=16, fontweight='bold')
    
    # 1. 事件统计
    ax1 = axes[0, 0]
    event_types = ['噪声', '卡顿', '音量波动', '失真']
    event_counts = [
        len(result_dict.get('noise', {}).get('events', [])),
        len(result_dict.get('dropout', {}).get('events', [])),
        len(result_dict.get('volume_fluctuation', {}).get('events', [])),
        len(result_dict.get('voice_distortion', {}).get('events', []))
    ]
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24']
    ax1.bar(event_types, event_counts, color=colors, alpha=0.7)
    ax1.set_title('检测到的问题事件数量', fontsize=12, fontweight='bold')
    ax1.set_ylabel('事件数量')
    ax1.grid(axis='y', alpha=0.3)
    
    # 2. 全局特征
    ax2 = axes[0, 1]
    global_data = result_dict.get('global', {})
    features = ['RMS均值', '过零率', '频谱质心', '频谱通量']
    values = [
        global_data.get('rms_mean', 0),
        global_data.get('zcr_mean', 0) * 10,  # 放大显示
        global_data.get('spectral_centroid_mean', 0) / 1000,  # 转为kHz
        global_data.get('spectral_flux_mean', 0) * 10
    ]
    ax2.barh(features, values, color='steelblue', alpha=0.7)
    ax2.set_title('全局音频特征', fontsize=12, fontweight='bold')
    ax2.set_xlabel('特征值（归一化）')
    ax2.grid(axis='x', alpha=0.3)
    
    # 3. 事件时间线
    ax3 = axes[1, 0]
    for i, (event_type, color) in enumerate(zip(['noise', 'dropout', 'volume_fluctuation', 'voice_distortion'], colors)):
        events = result_dict.get(event_type, {}).get('events', [])
        if events:
            times = [e.get('start', 0) for e in events]
            y_values = [i + 1] * len(times)
            ax3.scatter(times, y_values, c=color, s=50, alpha=0.6, label=event_types[i])
    
    ax3.set_yticks([1, 2, 3, 4])
    ax3.set_yticklabels(event_types)
    ax3.set_xlabel('时间 (秒)')
    ax3.set_title('问题事件时间分布', fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)
    ax3.legend(loc='upper right', fontsize=8)
    
    # 4. 质量评分
    ax4 = axes[1, 1]
    # 简单评分：100 - (各类事件数 * 权重)
    score = max(0, 100 - (
        event_counts[0] * 5 +  # 噪声
        event_counts[1] * 10 +  # 卡顿
        event_counts[2] * 3 +  # 音量波动
        event_counts[3] * 8    # 失真
    ))
    
    wedges, texts, autotexts = ax4.pie(
        [score, 100 - score],
        labels=['质量评分', '扣分'],
        autopct='%1.0f%%',
        colors=['#2ecc71', '#e74c3c'],
        startangle=90
    )
    ax4.set_title(f'综合质量评分: {score:.0f}/100', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ 报告图表已保存: {output_path}")


if __name__ == '__main__':
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='生成音频质量分析报告图表')
    parser.add_argument('result_json', help='分析结果JSON文件')
    parser.add_argument('-o', '--output', default='report.png', help='输出PNG文件路径')
    
    args = parser.parse_args()
    
    with open(args.result_json, 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    plot_analysis_report(result, args.output)
