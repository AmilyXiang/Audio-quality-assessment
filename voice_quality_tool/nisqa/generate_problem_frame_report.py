#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成问题帧详细报告

分析NOK文件，输出每个文件在哪些帧的哪些维度有问题
"""

import os
import json
import argparse
from pathlib import Path


def analyze_problem_frames(comparison_data, frame_diff_threshold=-0.3, severity_threshold=-0.5):
    """
    分析问题帧
    
    Args:
        comparison_data: 对比数据
        frame_diff_threshold: 帧差异阈值（默认-0.3）
        severity_threshold: 严重问题阈值（默认-0.5）
    
    Returns:
        问题帧详情
    """
    problems = {
        'file': comparison_data['test_file'].replace('framewise_', '').replace('.json', ''),
        'status': comparison_data['status'],
        'file_level': comparison_data['file_level']['diff'],
        'dimensions': {}
    }
    
    # 只分析NOK文件
    if comparison_data['status'] != 'NOK':
        return problems
    
    # 获取判定依据
    if 'nok_reasons' in comparison_data:
        problems['nok_reasons'] = comparison_data['nok_reasons']
    
    # 获取问题维度
    if 'problem_dimensions' in comparison_data:
        problems['problem_dimensions'] = comparison_data['problem_dimensions']
    
    # 分析每个维度的问题帧
    for dim in ['mos', 'noi', 'dis', 'col', 'loud']:
        dim_data = comparison_data['metrics'][dim]
        frame_diffs = dim_data['frame_diffs']
        
        problem_frames = []
        severe_frames = []
        
        for frame in frame_diffs:
            diff = frame['diff']
            
            # 严重问题帧
            if diff < severity_threshold:
                severe_frames.append({
                    'frame_id': frame['frame_id'],
                    'time': f"{frame['time_start']:.1f}s-{frame['time_end']:.1f}s",
                    'diff': diff,
                    'test_value': frame['test_value'],
                    'baseline_value': frame['baseline_value']
                })
            # 一般问题帧
            elif diff < frame_diff_threshold:
                problem_frames.append({
                    'frame_id': frame['frame_id'],
                    'time': f"{frame['time_start']:.1f}s-{frame['time_end']:.1f}s",
                    'diff': diff,
                    'test_value': frame['test_value'],
                    'baseline_value': frame['baseline_value']
                })
        
        if severe_frames or problem_frames:
            problems['dimensions'][dim] = {
                'severe_frames': severe_frames,
                'problem_frames': problem_frames,
                'total_problem_count': len(severe_frames) + len(problem_frames),
                'stats': dim_data['stats']
            }
    
    return problems


def generate_report(nok_files_data, output_path=None):
    """生成格式化报告"""
    
    if not nok_files_data:
        report = "=" * 80 + "\n"
        report += "质量分析报告 - 无问题文件\n"
        report += "=" * 80 + "\n\n"
        report += "所有文件质量良好，未发现NOK文件。\n"
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        print(report)
        return
    
    report = "=" * 80 + "\n"
    report += "问题文件帧级详细报告\n"
    report += "=" * 80 + "\n\n"
    
    for idx, file_data in enumerate(nok_files_data, 1):
        report += f"\n{'=' * 80}\n"
        report += f"问题文件 #{idx}: {file_data['file']}\n"
        report += f"{'=' * 80}\n\n"
        
        # 判定依据
        if 'nok_reasons' in file_data:
            report += "【判定依据】（决定NOK）\n"
            for dim, reason in file_data['nok_reasons'].items():
                report += f"  - {dim}: {reason}\n"
            report += "\n"
        
        # 问题维度概览
        if 'problem_dimensions' in file_data:
            report += "【问题维度】（仅供参考）\n"
            for dim, desc in file_data['problem_dimensions'].items():
                report += f"  - {dim}: {desc}\n"
            report += "\n"
        
        # 文件级差异
        report += "【文件级差异】\n"
        for dim, diff in file_data['file_level'].items():
            status = "✗ 劣化" if diff < -0.05 else "≈ 相当"
            report += f"  {dim.upper():<6} {diff:+.3f}  {status}\n"
        report += "\n"
        
        # 详细帧级问题
        report += "【问题帧详情】\n"
        report += "-" * 80 + "\n"
        
        for dim, dim_data in file_data['dimensions'].items():
            report += f"\n[{dim.upper()} 维度]\n"
            report += f"  问题帧总数: {dim_data['total_problem_count']}\n"
            report += f"  低于基准比例: {dim_data['stats']['percent_below_baseline']:.1f}%\n"
            report += f"  平均差值: {dim_data['stats']['mean_diff']:+.3f}\n"
            
            # 严重问题帧
            if dim_data['severe_frames']:
                report += f"\n  ⚠️  严重问题帧 (差值<-0.5):\n"
                for frame in dim_data['severe_frames'][:10]:  # 最多显示10个
                    report += f"    Frame {frame['frame_id']:2d} ({frame['time']:<13}) "
                    report += f"差值={frame['diff']:+.3f}  "
                    report += f"测试={frame['test_value']:.3f}  基准={frame['baseline_value']:.3f}\n"
                
                if len(dim_data['severe_frames']) > 10:
                    report += f"    ... 还有 {len(dim_data['severe_frames']) - 10} 个严重问题帧\n"
            
            # 一般问题帧（只显示前5个）
            if dim_data['problem_frames']:
                report += f"\n  问题帧 (差值<-0.3):\n"
                for frame in dim_data['problem_frames'][:5]:
                    report += f"    Frame {frame['frame_id']:2d} ({frame['time']:<13}) "
                    report += f"差值={frame['diff']:+.3f}  "
                    report += f"测试={frame['test_value']:.3f}  基准={frame['baseline_value']:.3f}\n"
                
                if len(dim_data['problem_frames']) > 5:
                    report += f"    ... 还有 {len(dim_data['problem_frames']) - 5} 个问题帧\n"
        
        report += "\n"
    
    # 输出报告
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"[报告已保存] {output_path}")
    
    print(report)


def main():
    parser = argparse.ArgumentParser(description='生成问题帧详细报告')
    parser.add_argument('input_dir', 
                       help='baseline_compare JSON文件所在目录')
    parser.add_argument('--output', '-o',
                       help='输出报告文件路径（可选）')
    parser.add_argument('--frame-threshold', type=float, default=-0.3,
                       help='问题帧差异阈值（默认-0.3）')
    parser.add_argument('--severity-threshold', type=float, default=-0.5,
                       help='严重问题帧差异阈值（默认-0.5）')
    parser.add_argument('--filter', '-f',
                       help='文件名过滤关键字（例如: NISQA 或 251212）')
    
    args = parser.parse_args()
    
    # 读取所有baseline_compare JSON文件
    input_dir = Path(args.input_dir)
    json_files = list(input_dir.glob('baseline_compare_*.json'))
    
    # 应用文件名过滤
    if args.filter:
        json_files = [f for f in json_files if args.filter in f.name]
        print(f"[信息] 应用过滤器 '{args.filter}'，剩余 {len(json_files)} 个文件")
    
    if not json_files:
        print(f"[错误] 在 {input_dir} 中未找到 baseline_compare_*.json 文件")
        return
    
    print(f"[信息] 找到 {len(json_files)} 个对比文件")
    
    # 分析所有文件
    nok_files_data = []
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            comparison_data = json.load(f)
        
        # 只分析NOK文件
        if comparison_data.get('status') == 'NOK':
            problems = analyze_problem_frames(
                comparison_data,
                args.frame_threshold,
                args.severity_threshold
            )
            nok_files_data.append(problems)
    
    print(f"[信息] 发现 {len(nok_files_data)} 个NOK文件\n")
    
    # 生成报告
    generate_report(nok_files_data, args.output)


if __name__ == '__main__':
    main()
