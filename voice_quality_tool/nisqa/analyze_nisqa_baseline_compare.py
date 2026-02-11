#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NISQA 基准对比分析工具

流程：
1. 使用基准文件（高质量音频）进行帧级分析
2. 对所有测试文件进行帧级分析
3. 逐帧对比5个维度（MOS/NOI/DIS/COL/LOUD）
4. 统计低于基准的帧数，判断质量问题
5. 分析差值趋势，预判质量劣化方向
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 配置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 添加nisqa_repo到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nisqa_repo'))

from nisqa.NISQA_model import nisqaModel


class BaselineComparator:
    """基准对比分析器"""
    
    def __init__(self, baseline_json_path):
        """
        初始化对比器
        
        Args:
            baseline_json_path: 基准文件的framewise JSON结果路径
        """
        self.baseline_json_path = baseline_json_path
        self.baseline_data = self._load_json(baseline_json_path)
        self.baseline_frames = self.baseline_data['frame_level']['frames']
        
        print(f"[基准加载] {os.path.basename(baseline_json_path)}")
        print(f"  文件级MOS: {self.baseline_data['file_level']['mos']:.3f}")
        print(f"  总帧数: {len(self.baseline_frames)}")
        print(f"  窗口配置: {self.baseline_data['frame_level']['seg_length']}s / {self.baseline_data['frame_level']['hop_length']}s")
    
    def _load_json(self, path):
        """加载JSON文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _align_frames(self, baseline_frames, test_frames, metric='mos'):
        """
        使用互相关对齐两个帧序列
        
        Args:
            baseline_frames: 基准帧列表
            test_frames: 测试帧列表
            metric: 用于对齐的指标（默认MOS）
            
        Returns:
            tuple: (对齐后的基准帧, 对齐后的测试帧, 偏移量)
        """
        # 提取指标值序列
        baseline_values = np.array([f[metric] for f in baseline_frames])
        test_values = np.array([f[metric] for f in test_frames])
        
        # 计算互相关
        correlation = np.correlate(baseline_values, test_values, mode='full')
        
        # 找到最大相关位置
        lag = correlation.argmax() - (len(test_values) - 1)
        
        # 根据偏移量对齐
        if lag > 0:
            # 测试序列需要向右移动（基准从lag开始）
            aligned_baseline = baseline_frames[lag:]
            aligned_test = test_frames[:len(aligned_baseline)]
        elif lag < 0:
            # 测试序列需要向左移动（测试从-lag开始）
            aligned_test = test_frames[-lag:]
            aligned_baseline = baseline_frames[:len(aligned_test)]
        else:
            # 完美对齐
            min_len = min(len(baseline_frames), len(test_frames))
            aligned_baseline = baseline_frames[:min_len]
            aligned_test = test_frames[:min_len]
        
        return aligned_baseline, aligned_test, lag
    
    def compare_with_test(self, test_json_path):
        """
        对比测试文件与基准
        
        Args:
            test_json_path: 测试文件的framewise JSON结果路径
            
        Returns:
            dict: 对比结果
        """
        test_data = self._load_json(test_json_path)
        test_frames = test_data['frame_level']['frames']
        
        # 对齐帧序列
        baseline_frames, test_frames, lag = self._align_frames(self.baseline_frames, test_frames)
        
        if lag != 0:
            print(f"[对齐] 检测到时间偏移: {lag}帧 ({lag * 0.5:.1f}秒), 已自动对齐")
        
        if len(test_frames) != len(baseline_frames):
            print(f"[对齐后] 基准帧数={len(baseline_frames)}, 测试帧数={len(test_frames)}")
        
        # 计算逐帧差值
        metrics = ['mos', 'noi', 'dis', 'col', 'loud']
        frame_diffs = {m: [] for m in metrics}
        
        for i, (test_frame, base_frame) in enumerate(zip(test_frames, baseline_frames)):
            for metric in metrics:
                test_val = test_frame[metric]
                base_val = base_frame[metric]
                diff = test_val - base_val  # 正值=优于基准，负值=劣于基准
                frame_diffs[metric].append({
                    'frame_id': i,
                    'time_start': test_frame['time_start'],
                    'time_end': test_frame['time_end'],
                    'test_value': test_val,
                    'baseline_value': base_val,
                    'diff': diff
                })
        
        # 统计分析
        comparison = {
            'test_file': os.path.basename(test_json_path),
            'baseline_file': os.path.basename(self.baseline_json_path),
            'total_frames': len(test_frames),
            'file_level': {
                'test': test_data['file_level'],
                'baseline': self.baseline_data['file_level'],
                'diff': {}
            },
            'metrics': {}
        }
        
        # 文件级差异
        for metric in metrics:
            comparison['file_level']['diff'][metric] = (
                test_data['file_level'][metric] - self.baseline_data['file_level'][metric]
            )
        
        # 逐帧统计
        for metric in metrics:
            diffs = [f['diff'] for f in frame_diffs[metric]]
            below_baseline = [d for d in diffs if d < 0]
            
            comparison['metrics'][metric] = {
                'frame_diffs': frame_diffs[metric],
                'stats': {
                    'mean_diff': np.mean(diffs),
                    'median_diff': np.median(diffs),
                    'std_diff': np.std(diffs),
                    'min_diff': np.min(diffs),
                    'max_diff': np.max(diffs),
                    'frames_below_baseline': len(below_baseline),
                    'percent_below_baseline': len(below_baseline) / len(diffs) * 100,
                    'mean_degradation': np.mean(below_baseline) if below_baseline else 0.0
                },
                'trend': self._analyze_trend(diffs)
            }
        
        # 混合判定逻辑（方案3）：帧级为主 + 突变检测 + 文件级参考
        status_tags = []
        nok_reasons = {}  # 记录判定原因
        
        # 两阶段判定逻辑：
        # 阶段1: 仅看MOS维度判定OK/NOK（MOS是总体质量指标）
        # 阶段2: 对于NOK文件，分析各维度问题帧（问题定位，非判定依据）
        
        mos_metrics = comparison['metrics']['mos']
        mos_file_diff = comparison['file_level']['diff']['mos']
        mos_below_pct = mos_metrics['stats']['percent_below_baseline']
        mos_mean_diff = mos_metrics['stats']['mean_diff']
        mos_min_diff = mos_metrics['stats']['min_diff']
        
        # 阶段1: 仅用MOS判定OK/NOK
        is_nok = False
        if mos_below_pct > 50 and mos_file_diff < -0.05:
            # MOS帧劣化严重 且 文件级分数也差 → NOK
            nok_reasons['MOS'] = f'{mos_below_pct:.0f}%帧劣化 且 文件级劣化{mos_file_diff:.2f}'
            is_nok = True
        elif mos_min_diff < -0.5 and mos_file_diff < -0.05:
            # MOS存在严重突降 且 文件级分数差 → NOK
            nok_reasons['MOS'] = f'严重突降({mos_min_diff:.2f}) 且 文件级劣化{mos_file_diff:.2f}'
            is_nok = True
        
        # 阶段2: 对于NOK文件，记录各维度的问题帧（用于问题定位）
        problem_dimensions = {}  # 不参与OK/NOK判定，仅作问题分析参考
        if is_nok:
            for dim in ['noi', 'dis', 'col', 'loud']:
                dim_metrics = comparison['metrics'][dim]
                file_diff = comparison['file_level']['diff'][dim]
                below_pct = dim_metrics['stats']['percent_below_baseline']
                min_diff = dim_metrics['stats']['min_diff']
                
                # 记录该维度的问题情况（但不影响OK/NOK判定）
                if below_pct > 70 and file_diff < -0.1:
                    problem_dimensions[dim.upper()] = f'{below_pct:.0f}%帧劣化 且 文件级劣化{file_diff:.2f}'
                elif min_diff < -0.5 and file_diff < -0.1:
                    problem_dimensions[dim.upper()] = f'严重突降({min_diff:.2f}) 且 文件级劣化{file_diff:.2f}'
                elif below_pct > 50:
                    # 轻度问题也记录下来
                    problem_dimensions[dim.upper()] = f'{below_pct:.0f}%帧劣化（轻度）'
        
        # 设置判定结果
        if is_nok:
            status_tags.append('MOS_NOK')
            comparison['problem_dimensions'] = problem_dimensions  # 问题维度详情
        
        # 综合状态
        if status_tags:
            comparison['status'] = 'NOK'
            comparison['nok_dimensions'] = status_tags
            comparison['nok_reasons'] = nok_reasons
        else:
            comparison['status'] = 'OK'
            comparison['nok_dimensions'] = []
        
        return comparison
    
    def _analyze_trend(self, diffs):
        """
        分析差值趋势
        
        Args:
            diffs: 差值列表
            
        Returns:
            dict: 趋势分析结果
        """
        if len(diffs) < 3:
            return {
                'type': 'insufficient_data',
                'description': '数据不足（帧数<3）',
                'slope': 0.0,
                'sudden_drops': []
            }
        
        # 线性回归分析趋势
        x = np.arange(len(diffs))
        slope, intercept = np.polyfit(x, diffs, 1)
        
        # 判断趋势类型
        if abs(slope) < 0.001:
            trend_type = 'stable'
            description = '稳定（与基准差异保持恒定）'
        elif slope > 0.01:
            trend_type = 'improving'
            description = '改善趋势（质量逐渐接近或超越基准）'
        elif slope < -0.01:
            trend_type = 'degrading'
            description = '恶化趋势（质量逐渐远离基准）'
        else:
            trend_type = 'slight_fluctuation'
            description = '轻微波动'
        
        # 检测突变点
        sudden_drops = []
        for i in range(1, len(diffs)):
            if diffs[i] - diffs[i-1] < -0.5:  # 突然下降超过0.5
                sudden_drops.append({
                    'frame': i,
                    'drop': diffs[i] - diffs[i-1]
                })
        
        return {
            'type': trend_type,
            'description': description,
            'slope': slope,
            'intercept': intercept,
            'sudden_drops': sudden_drops
        }
    
    def print_comparison_report(self, comparison, detail_for_nok_only=True):
        """打印对比报告"""
        print("\n" + "="*80)
        print("NISQA 基准对比分析报告")
        print("="*80)
        
        print(f"\n【基准文件】 {comparison['baseline_file']}")
        print(f"【测试文件】 {comparison['test_file']}")
        print(f"【总帧数】   {comparison['total_frames']}")
        print(f"【质量判定】 {comparison['status']}", end="")
        if comparison['status'] == 'NOK':
            print(f" ({', '.join(comparison['nok_dimensions'])})")
            # 显示MOS判定依据
            nok_reasons = comparison.get('nok_reasons', {})
            if nok_reasons:
                print(f"【判定依据】")
                for dim, reason in nok_reasons.items():
                    print(f"  - {dim}: {reason}")
            # 显示其他维度的问题情况（仅作参考，不影响判定）
            problem_dims = comparison.get('problem_dimensions', {})
            if problem_dims:
                print(f"【问题维度】（仅供参考，不影响OK/NOK判定）")
                for dim, desc in problem_dims.items():
                    print(f"  - {dim}: {desc}")
        else:
            print(" ✓")
        
        # 文件级对比
        print("\n" + "-"*80)
        print("文件级质量对比")
        print("-"*80)
        print(f"{'维度':<12} {'基准':<10} {'测试':<10} {'差值':<10} {'状态'}")
        print("-"*80)
        
        for metric in ['mos', 'noi', 'dis', 'col', 'loud']:
            base_val = comparison['file_level']['baseline'][metric]
            test_val = comparison['file_level']['test'][metric]
            diff = comparison['file_level']['diff'][metric]
            
            if diff >= 0:
                status = '✓ 优于基准' if diff > 0.1 else '≈ 相当'
            else:
                status = '✗ 劣于基准' if diff < -0.1 else '≈ 相当'
            
            print(f"{metric.upper():<12} {base_val:<10.3f} {test_val:<10.3f} {diff:+.3f}     {status}")
        
        # 根据状态决定是否输出帧级详细分析
        if detail_for_nok_only and comparison['status'] == 'OK':
            print("\n[跳过帧级分析] 文件质量判定为OK，无需详细分析")
            return
        
        # 逐维度详细分析（仅NOK文件）
        print("\n" + "="*80)
        print("帧级详细分析 (NOK文件)")
        print("="*80)
        
        for metric in ['mos', 'noi', 'dis', 'col', 'loud']:
            stats = comparison['metrics'][metric]['stats']
            trend = comparison['metrics'][metric]['trend']
            
            print(f"\n【{metric.upper()} - {self._get_metric_name(metric)}】")
            print("-"*80)
            print(f"  平均差值:         {stats['mean_diff']:+.3f}")
            print(f"  中位数差值:       {stats['median_diff']:+.3f}")
            print(f"  标准差:           {stats['std_diff']:.3f}")
            print(f"  差值范围:         {stats['min_diff']:+.3f} ~ {stats['max_diff']:+.3f}")
            print(f"  低于基准帧数:     {stats['frames_below_baseline']} / {comparison['total_frames']} ({stats['percent_below_baseline']:.1f}%)")
            
            if stats['frames_below_baseline'] > 0:
                print(f"  平均劣化程度:     {stats['mean_degradation']:.3f}")
            
            print(f"\n  趋势分析:         {trend['description']}")
            if trend.get('sudden_drops'):
                print(f"  突变点检测:       发现 {len(trend['sudden_drops'])} 处突然下降")
                for drop in trend['sudden_drops'][:3]:  # 只显示前3个
                    print(f"    - Frame {drop['frame']}: 下降 {drop['drop']:.3f}")
            
            # 质量判定
            if stats['percent_below_baseline'] > 50:
                severity = "严重" if stats['mean_degradation'] < -0.5 else "中等"
                print(f"  ⚠️  质量问题: {severity}劣化（超过50%帧低于基准）")
            elif stats['percent_below_baseline'] > 20:
                print(f"  ⚠️  质量问题: 轻度劣化（20-50%帧低于基准）")
            elif stats['mean_diff'] < -0.1:
                print(f"  ⚠️  整体略低于基准，但波动较小")
            else:
                print(f"  ✓ 质量良好（与基准相当或优于基准）")
    
    def _get_metric_name(self, metric):
        """获取维度中文名"""
        names = {
            'mos': '总体质量',
            'noi': '噪声程度',
            'dis': '不连续性',
            'col': '音色失真',
            'loud': '响度适中性'
        }
        return names.get(metric, metric)
    
    def generate_comparison_plot(self, comparison, output_path):
        """生成对比可视化图表"""
        metrics = ['mos', 'noi', 'dis', 'col', 'loud']
        metric_names = ['MOS (总体)', 'NOI (噪声)', 'DIS (不连续)', 'COL (音色)', 'LOUD (响度)']
        
        fig, axes = plt.subplots(5, 1, figsize=(14, 16))
        fig.suptitle(f'基准对比分析\n基准: {comparison["baseline_file"]}\n测试: {comparison["test_file"]}', 
                     fontsize=14, fontweight='bold')
        
        for idx, (metric, name) in enumerate(zip(metrics, metric_names)):
            ax = axes[idx]
            frame_diffs = comparison['metrics'][metric]['frame_diffs']
            stats = comparison['metrics'][metric]['stats']
            
            frames = [f['frame_id'] for f in frame_diffs]
            times = [f['time_start'] for f in frame_diffs]
            baseline_vals = [f['baseline_value'] for f in frame_diffs]
            test_vals = [f['test_value'] for f in frame_diffs]
            diffs = [f['diff'] for f in frame_diffs]
            
            # 绘制基准和测试曲线
            ax.plot(times, baseline_vals, 'g-', linewidth=2, label='基准', alpha=0.8)
            ax.plot(times, test_vals, 'b-', linewidth=2, label='测试', alpha=0.8)
            
            # 填充差异区域
            ax.fill_between(times, baseline_vals, test_vals, 
                           where=np.array(test_vals) < np.array(baseline_vals),
                           alpha=0.3, color='red', label='劣于基准')
            ax.fill_between(times, baseline_vals, test_vals,
                           where=np.array(test_vals) >= np.array(baseline_vals),
                           alpha=0.3, color='green', label='优于基准')
            
            ax.set_xlabel('时间 (秒)', fontsize=10)
            ax.set_ylabel(name, fontsize=10)
            ax.legend(loc='best', fontsize=9)
            ax.grid(True, alpha=0.3)
            
            # 添加统计信息
            info_text = f"平均差值: {stats['mean_diff']:+.3f} | 低于基准: {stats['percent_below_baseline']:.1f}%"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n[可视化] 对比图表已保存: {output_path}")
        plt.close()
    
    def save_comparison_json(self, comparison, output_path):
        """保存对比结果为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"[数据] 对比结果已保存: {output_path}")
    
    def generate_multi_comparison_plot(self, comparisons, output_path):
        """
        生成多个测试文件的综合对比图表
        
        Args:
            comparisons: 对比结果列表
            output_path: 输出路径
        """
        metrics = ['mos', 'noi', 'dis', 'col', 'loud']
        metric_names = ['MOS (总体质量)', 'NOI (噪声程度)', 'DIS (不连续性)', 'COL (音色失真)', 'LOUD (响度适中性)']
        
        # 颜色方案
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        fig, axes = plt.subplots(5, 1, figsize=(16, 20))
        fig.suptitle(f'多文件基准对比分析\n基准: {comparisons[0]["baseline_file"]}', 
                     fontsize=16, fontweight='bold')
        
        for idx, (metric, name) in enumerate(zip(metrics, metric_names)):
            ax = axes[idx]
            
            # 绘制基准线（从第一个comparison获取）
            first_comp = comparisons[0]
            baseline_frame_diffs = first_comp['metrics'][metric]['frame_diffs']
            baseline_times = [f['time_start'] for f in baseline_frame_diffs]
            baseline_vals = [f['baseline_value'] for f in baseline_frame_diffs]
            
            ax.plot(baseline_times, baseline_vals, 'k--', linewidth=2.5, label='基准', alpha=0.9, zorder=100)
            
            # 绘制所有测试文件
            for comp_idx, comparison in enumerate(comparisons):
                color = colors[comp_idx % len(colors)]
                test_name = Path(comparison['test_file']).stem
                
                frame_diffs = comparison['metrics'][metric]['frame_diffs']
                # 每个测试文件使用自己的times（帧数可能不同）
                test_times = [f['time_start'] for f in frame_diffs]
                test_vals = [f['test_value'] for f in frame_diffs]
                stats = comparison['metrics'][metric]['stats']
                
                # 绘制测试线
                line_style = '-' if stats['percent_below_baseline'] > 50 else '--'
                line_width = 2.0 if stats['percent_below_baseline'] > 50 else 1.5
                
                ax.plot(test_times, test_vals, line_style, color=color, 
                       linewidth=line_width, label=test_name, alpha=0.8)
                
                # 标注严重问题段
                if stats['percent_below_baseline'] > 50:
                    # 找出最差的3帧
                    diffs = [f['diff'] for f in frame_diffs]
                    worst_frames = sorted(enumerate(diffs), key=lambda x: x[1])[:3]
                    for frame_idx, diff_val in worst_frames:
                        if diff_val < -0.5:  # 只标注显著劣化
                            ax.scatter(test_times[frame_idx], test_vals[frame_idx], 
                                     s=80, color=color, marker='x', zorder=50, alpha=0.7)
            
            ax.set_xlabel('时间 (秒)', fontsize=11)
            ax.set_ylabel(name, fontsize=11)
            ax.legend(loc='best', fontsize=9, ncol=2)
            ax.grid(True, alpha=0.3)
            
            # 设置y轴范围（收集所有数据）
            all_vals = baseline_vals.copy()
            for comp in comparisons:
                frame_diffs = comp['metrics'][metric]['frame_diffs']
                all_vals.extend([f['test_value'] for f in frame_diffs])
            y_min, y_max = min(all_vals), max(all_vals)
            y_range = y_max - y_min
            ax.set_ylim(y_min - 0.1*y_range, y_max + 0.1*y_range)
            
            # 添加统计摘要
            summary_lines = []
            for comp_idx, comparison in enumerate(comparisons):
                stats = comparison['metrics'][metric]['stats']
                test_name = Path(comparison['test_file']).stem[:20]  # 截断过长名称
                status = '[严重]' if stats['percent_below_baseline'] > 50 else \
                        '[轻度]' if stats['percent_below_baseline'] > 20 else '[良好]'
                summary_lines.append(f"{test_name}: {status} ({stats['percent_below_baseline']:.0f}%<基准)")
            
            summary_text = '\n'.join(summary_lines[:5])  # 最多显示5行
            if len(comparisons) > 5:
                summary_text += f"\n... 及其他{len(comparisons)-5}个文件"
            
            ax.text(0.02, 0.02, summary_text, transform=ax.transAxes,
                   verticalalignment='bottom', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n[综合对比图] 已保存: {output_path}")
        plt.close()
    
    def generate_summary_heatmap(self, comparisons, output_path):
        """
        生成质量对比热力图
        
        显示所有测试文件在各维度的质量状态（相比基准）
        """
        metrics = ['mos', 'noi', 'dis', 'col', 'loud']
        metric_names = ['MOS', 'NOI', 'DIS', 'COL', 'LOUD']
        
        # 准备数据矩阵
        test_names = [Path(comp['test_file']).stem for comp in comparisons]
        data_matrix = np.zeros((len(comparisons), len(metrics)))
        
        for i, comparison in enumerate(comparisons):
            for j, metric in enumerate(metrics):
                stats = comparison['metrics'][metric]['stats']
                # 使用低于基准的百分比作为热力图数据
                data_matrix[i, j] = stats['percent_below_baseline']
        
        # 绘制热力图
        fig, ax = plt.subplots(figsize=(10, max(6, len(comparisons) * 0.4)))
        
        im = ax.imshow(data_matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)
        
        # 设置坐标轴
        ax.set_xticks(np.arange(len(metrics)))
        ax.set_yticks(np.arange(len(comparisons)))
        ax.set_xticklabels(metric_names)
        ax.set_yticklabels(test_names)
        
        # 旋转x轴标签
        plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
        
        # 在每个格子中显示数值
        for i in range(len(comparisons)):
            for j in range(len(metrics)):
                value = data_matrix[i, j]
                color = 'white' if value > 50 else 'black'
                text = ax.text(j, i, f'{value:.0f}%',
                             ha="center", va="center", color=color, fontsize=9)
        
        ax.set_title(f'质量问题热力图 - 低于基准帧数百分比\n基准: {comparisons[0]["baseline_file"]}', 
                    fontsize=12, fontweight='bold', pad=20)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('低于基准的帧数百分比 (%)', rotation=270, labelpad=20)
        
        # 添加图例说明
        legend_text = '颜色说明:\n绿色: 良好 (<20%)\n黄色: 轻度问题 (20-50%)\n红色: 严重问题 (>50%)'
        fig.text(0.02, 0.02, legend_text, fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"[热力图] 已保存: {output_path}")
        plt.close()


def analyze_file_if_needed(audio_path, model_path, seg_length=15.0, hop_length=0.5):
    """如果JSON不存在，则运行帧级分析"""
    json_path = f"framewise_{Path(audio_path).stem}.json"
    
    if os.path.exists(json_path):
        print(f"[已存在] {json_path}")
        return json_path
    
    print(f"[分析中] {audio_path}")
    
    # 导入必要的模块
    import librosa
    import sys
    import pandas as pd
    
    # 导入 predict_dim_framewise 函数
    sys.path.insert(0, os.path.dirname(__file__))
    from analyze_nisqa_framewise import predict_dim_framewise
    from nisqa.NISQA_model import nisqaModel
    
    # 配置参数
    args_dict = {
        'mode': 'predict_file',
        'pretrained_model': model_path,
        'deg': audio_path,
        'output_dir': '.',
        'ms_channel': None,
        'csv_file': None,
        'csv_con': None,
        'csv_deg': None,
        'data_dir': None,
        'num_workers': 0,
        'bs': 1,
        'ms_max_segments': None,
        'ms_seg_length': int(seg_length),
        'ms_seg_hop_length': hop_length,
    }
    
    # 加载音频并计算帧数
    y, sr = librosa.load(audio_path, sr=None)
    duration = len(y) / sr
    expected_frames = max(1, int((duration - seg_length) / hop_length) + 1) if duration >= seg_length else 1
    
    audio_durations = {os.path.basename(audio_path): (duration, seg_length, hop_length)}
    
    # 加载模型
    model = nisqaModel(args_dict)
    
    # 运行帧级预测
    frame_preds, file_preds = predict_dim_framewise(
        model.model,
        model.ds_val,
        args_dict['bs'],
        'cpu',
        audio_durations=audio_durations,
        num_workers=0
    )
    
    # 获取结果
    audio_key = list(frame_preds.keys())[0]
    frame_pred = frame_preds[audio_key]
    file_pred = file_preds.iloc[0]
    
    # 保存结果
    result = {
        'audio_file': os.path.basename(audio_path),
        'file_level': {
            'mos': float(file_pred['mos_pred']),
            'noi': float(file_pred['noi_pred']),
            'dis': float(file_pred['dis_pred']),
            'col': float(file_pred['col_pred']),
            'loud': float(file_pred['loud_pred'])
        },
        'frame_level': {
            'total_frames': frame_pred['n_frames'],
            'seg_length': seg_length,
            'hop_length': hop_length,
            'frames': []
        }
    }
    
    for i in range(frame_pred['n_frames']):
        time_start = i * hop_length
        time_end = time_start + seg_length
        result['frame_level']['frames'].append({
            'frame_id': i,
            'time_start': time_start,
            'time_end': time_end,
            'mos': float(frame_pred['mos'][i]),
            'noi': float(frame_pred['noi'][i]),
            'dis': float(frame_pred['dis'][i]),
            'col': float(frame_pred['col'][i]),
            'loud': float(frame_pred['loud'][i])
        })
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"[完成] {json_path}")
    return json_path


def main():
    parser = argparse.ArgumentParser(description='NISQA基准对比分析工具')
    parser.add_argument('--baseline', required=True, 
                       help='基准音频文件路径（高质量参考）')
    parser.add_argument('--test', nargs='+',
                       help='测试音频文件路径（可多个）')
    parser.add_argument('--test-dir', 
                       help='测试音频文件所在目录（自动扫描所有.wav文件）')
    parser.add_argument('--model', required=True,
                       help='NISQA模型路径 (nisqa.tar)')
    parser.add_argument('--seg_length', type=float, default=15.0,
                       help='窗口长度（秒），默认15.0')
    parser.add_argument('--hop_length', type=float, default=0.5,
                       help='跳跃步长（秒），默认0.5')
    parser.add_argument('--output_dir', default='.',
                       help='输出目录，默认当前目录')
    parser.add_argument('--cleanup-framewise', action='store_true',
                       help='分析完成后自动删除framewise_*.json文件')
    
    args = parser.parse_args()
    
    # 验证参数：必须提供--test或--test-dir之一
    if not args.test and not args.test_dir:
        parser.error("必须提供--test或--test-dir参数之一")
    
    # 如果提供了--test-dir，自动扫描目录
    if args.test_dir:
        import glob
        baseline_path = os.path.abspath(args.baseline)
        test_dir = os.path.abspath(args.test_dir)
        
        # 扫描所有.wav文件
        all_wavs = sorted(glob.glob(os.path.join(test_dir, '*.wav')))
        
        # 排除基准文件
        test_files = [f for f in all_wavs if os.path.abspath(f) != baseline_path]
        
        if not test_files:
            print(f"[错误] 在目录 {test_dir} 中没有找到测试文件（排除基准文件后）")
            return
        
        print(f"[信息] 从目录 {test_dir} 中找到 {len(test_files)} 个测试文件")
        args.test = test_files
    
    # 1. 分析基准文件
    print("="*80)
    print("步骤1: 分析基准文件")
    print("="*80)
    baseline_json = analyze_file_if_needed(args.baseline, args.model, args.seg_length, args.hop_length)
    
    # 2. 初始化对比器
    comparator = BaselineComparator(baseline_json)
    
    # 3. 分析并对比所有测试文件
    print("\n" + "="*80)
    print("步骤2: 分析测试文件并对比")
    print("="*80)
    
    all_comparisons = []  # 收集所有对比结果
    
    for test_file in args.test:
        test_json = analyze_file_if_needed(test_file, args.model, args.seg_length, args.hop_length)
        
        # 对比
        comparison = comparator.compare_with_test(test_json)
        all_comparisons.append(comparison)
        
        # 打印报告
        comparator.print_comparison_report(comparison)
        
        # 生成单个文件的可视化
        test_basename = Path(test_file).stem
        plot_path = os.path.join(args.output_dir, f'baseline_compare_{test_basename}.png')
        comparator.generate_comparison_plot(comparison, plot_path)
        
        # 保存JSON
        json_path = os.path.join(args.output_dir, f'baseline_compare_{test_basename}.json')
        comparator.save_comparison_json(comparison, json_path)
        
        print("\n" + "="*80 + "\n")
    
    # 4. 生成综合对比图（如果有多个测试文件）
    if len(all_comparisons) > 1:
        print("="*80)
        print("步骤3: 生成综合对比可视化")
        print("="*80)
        
        # 综合对比图
        multi_plot_path = os.path.join(args.output_dir, 'baseline_compare_all.png')
        comparator.generate_multi_comparison_plot(all_comparisons, multi_plot_path)
        
        # 热力图
        heatmap_path = os.path.join(args.output_dir, 'baseline_compare_heatmap.png')
        comparator.generate_summary_heatmap(all_comparisons, heatmap_path)
        
        print("\n[完成] 所有对比分析完成！")
        print(f"  - 单文件对比图: {len(all_comparisons)} 张")
        print(f"  - 综合对比图: {multi_plot_path}")
        print(f"  - 质量热力图: {heatmap_path}")
    else:
        print("\n[完成] 仅一个测试文件，跳过综合对比图生成")
    
    # 清理framewise文件（如果启用）
    if args.cleanup_framewise:
        import glob
        print("\n" + "="*80)
        print("步骤4: 清理临时文件")
        print("="*80)
        
        # 在当前目录和output_dir中查找framewise文件
        search_dirs = ['.', args.output_dir]
        if os.path.dirname(baseline_json):
            search_dirs.append(os.path.dirname(baseline_json))
        
        # 去重
        search_dirs = list(set([os.path.abspath(d) for d in search_dirs]))
        
        deleted_count = 0
        for search_dir in search_dirs:
            framewise_files = glob.glob(os.path.join(search_dir, 'framewise_*.json'))
            for fpath in framewise_files:
                try:
                    os.remove(fpath)
                    print(f"[已删除] {os.path.relpath(fpath)}")
                    deleted_count += 1
                except Exception as e:
                    print(f"[删除失败] {os.path.relpath(fpath)}: {e}")
        
        if deleted_count > 0:
            print(f"\n[清理完成] 共删除 {deleted_count} 个framewise文件")
        else:
            print("\n[清理完成] 未找到framewise文件")


if __name__ == '__main__':
    main()
