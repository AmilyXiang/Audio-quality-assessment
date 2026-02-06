#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比分析可视化 - 绘制差分时间序列图
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_comparison_result(result_dict, output_path='comparison_plot.png'):
    """
    绘制对比分析差分图表
    
    Args:
        result_dict: analyze_comparison.py生成的结果字典
        output_path: 输出PNG路径
    """
    frame_diffs = result_dict['frame_diffs']
    meta = result_dict['meta']
    
    # 提取时间序列
    times = [f['time'] for f in frame_diffs]
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    fig.suptitle(f'音频对比分析 - 差分时间序列\n测试: {meta["test_file"]} vs 基准: {meta["baseline_file"]}', 
                 fontsize=14, fontweight='bold')
    
    # 1. RMS能量差分
    if 'rms_diff' in frame_diffs[0]:
        ax = axes[0]
        rms_diff = [f['rms_diff'] for f in frame_diffs]
        rms_test = [f.get('rms_test', 0) for f in frame_diffs]
        rms_baseline = [f.get('rms_baseline', 0) for f in frame_diffs]
        
        ax.plot(times, rms_test, label='测试音频', color='#e74c3c', alpha=0.7, linewidth=1)
        ax.plot(times, rms_baseline, label='基准音频', color='#3498db', alpha=0.7, linewidth=1)
        ax.fill_between(times, rms_baseline, rms_test, 
                        where=np.array(rms_diff)>0, color='red', alpha=0.2, label='高于基准')
        ax.fill_between(times, rms_baseline, rms_test,
                        where=np.array(rms_diff)<=0, color='blue', alpha=0.2, label='低于基准')
        
        ax.set_ylabel('RMS能量', fontsize=11)
        ax.set_title('能量对比（音量）', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)
    
    # 2. 过零率差分（噪声）
    if 'zero_crossing_rate_diff' in frame_diffs[0]:
        ax = axes[1]
        zcr_diff = [f['zero_crossing_rate_diff'] for f in frame_diffs]
        zcr_test = [f.get('zero_crossing_rate_test', 0) for f in frame_diffs]
        zcr_baseline = [f.get('zero_crossing_rate_baseline', 0) for f in frame_diffs]
        
        ax.plot(times, zcr_test, label='测试音频', color='#e74c3c', alpha=0.7, linewidth=1)
        ax.plot(times, zcr_baseline, label='基准音频', color='#3498db', alpha=0.7, linewidth=1)
        ax.fill_between(times, zcr_baseline, zcr_test,
                        where=np.array(zcr_diff)>0, color='red', alpha=0.2, label='噪声更高')
        ax.fill_between(times, zcr_baseline, zcr_test,
                        where=np.array(zcr_diff)<=0, color='blue', alpha=0.2, label='噪声更低')
        
        ax.set_ylabel('过零率', fontsize=11)
        ax.set_title('过零率对比（噪声水平）', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)
    
    # 3. 频谱中心差分（音色）
    if 'spectral_centroid_diff' in frame_diffs[0]:
        ax = axes[2]
        centroid_diff = [f['spectral_centroid_diff'] for f in frame_diffs]
        centroid_test = [f.get('spectral_centroid_test', 0) for f in frame_diffs]
        centroid_baseline = [f.get('spectral_centroid_baseline', 0) for f in frame_diffs]
        
        ax.plot(times, centroid_test, label='测试音频', color='#e74c3c', alpha=0.7, linewidth=1)
        ax.plot(times, centroid_baseline, label='基准音频', color='#3498db', alpha=0.7, linewidth=1)
        ax.fill_between(times, centroid_baseline, centroid_test,
                        where=np.array(centroid_diff)>0, color='red', alpha=0.2, label='更尖锐')
        ax.fill_between(times, centroid_baseline, centroid_test,
                        where=np.array(centroid_diff)<=0, color='blue', alpha=0.2, label='更低沉')
        
        ax.set_ylabel('频谱中心 (Hz)', fontsize=11)
        ax.set_title('频谱中心对比（音色变化）', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)
    
    # 4. 频谱通量差分（抖动）
    if 'spectral_flux_diff' in frame_diffs[0]:
        ax = axes[3]
        flux_diff = [f['spectral_flux_diff'] for f in frame_diffs]
        flux_test = [f.get('spectral_flux_test', 0) for f in frame_diffs]
        flux_baseline = [f.get('spectral_flux_baseline', 0) for f in frame_diffs]
        
        ax.plot(times, flux_test, label='测试音频', color='#e74c3c', alpha=0.7, linewidth=1)
        ax.plot(times, flux_baseline, label='基准音频', color='#3498db', alpha=0.7, linewidth=1)
        ax.fill_between(times, flux_baseline, flux_test,
                        where=np.array(flux_diff)>0, color='red', alpha=0.2, label='更抖动')
        ax.fill_between(times, flux_baseline, flux_test,
                        where=np.array(flux_diff)<=0, color='blue', alpha=0.2, label='更稳定')
        
        ax.set_ylabel('频谱通量', fontsize=11)
        ax.set_xlabel('时间 (秒)', fontsize=11)
        ax.set_title('频谱通量对比（抖动/稳定性）', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python generate_comparison_plot.py <result.json> [output.png]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'comparison_plot.png'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    plot_comparison_result(result, output_path)
    print(f"✓ 差分图表已保存: {output_path}")
