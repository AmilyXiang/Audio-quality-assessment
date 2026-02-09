"""
NISQA基准对比结果汇总分析工具
读取所有baseline_compare_*.json文件，生成质量问题汇总报告
"""

import json
import os
from pathlib import Path
import numpy as np
from collections import defaultdict

def load_all_comparisons(output_dir):
    """加载所有对比结果JSON文件"""
    comparisons = []
    json_files = sorted(Path(output_dir).glob('baseline_compare_*.json'))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                comparisons.append({
                    'filename': json_file.stem.replace('baseline_compare_', ''),
                    'data': data
                })
        except Exception as e:
            print(f"[警告] 无法读取 {json_file}: {e}")
    
    return comparisons

def analyze_quality_issues(comparisons):
    """分析质量问题"""
    
    # 分类统计
    severe_issues = []  # 严重问题（>50%帧低于基准）
    moderate_issues = []  # 中等问题（20-50%帧低于基准）
    good_quality = []  # 质量良好（<20%帧低于基准）
    
    # 各维度问题统计
    dimension_stats = {
        'MOS': {'severe': [], 'moderate': [], 'good': []},
        'NOI': {'severe': [], 'moderate': [], 'good': []},
        'DIS': {'severe': [], 'moderate': [], 'good': []},
        'COL': {'severe': [], 'moderate': [], 'good': []},
        'LOUD': {'severe': [], 'moderate': [], 'good': []}
    }
    
    # 文件级质量评分（基于MOS差值）
    mos_rankings = []
    
    for comp in comparisons:
        filename = comp['filename']
        data = comp['data']
        
        # 获取metrics（正确的JSON结构）
        metrics = data.get('metrics', {})
        
        # MOS维度评估
        mos_stats = metrics.get('mos', {}).get('stats', {})
        mos_below_pct = mos_stats.get('percent_below_baseline', 0)
        mos_mean_diff = mos_stats.get('mean_diff', 0)
        
        # 文件级MOS差值（使用正确的路径：file_level.diff.mos）
        file_level = data.get('file_level', {})
        file_diff = file_level.get('diff', {})
        mos_file_diff = file_diff.get('mos', 0)
        
        mos_rankings.append({
            'filename': filename,
            'mos_diff': mos_file_diff,
            'mos_below_pct': mos_below_pct
        })
        
        # 统计各维度问题（使用正确的维度名称映射）
        dim_mapping = {
            'MOS': 'mos',
            'NOI': 'noi',
            'DIS': 'dis',
            'COL': 'col',
            'LOUD': 'loud'
        }
        
        for dim_upper, dim_lower in dim_mapping.items():
            dim_stats = metrics.get(dim_lower, {}).get('stats', {})
            below_pct = dim_stats.get('percent_below_baseline', 0)
            
            if below_pct > 50:
                dimension_stats[dim_upper]['severe'].append(filename)
            elif below_pct > 20:
                dimension_stats[dim_upper]['moderate'].append(filename)
            else:
                dimension_stats[dim_upper]['good'].append(filename)
        
        # 判断整体质量（基于MOS）
        if mos_below_pct > 50:
            severe_issues.append({
                'filename': filename,
                'mos_below_pct': mos_below_pct,
                'mos_file_diff': mos_file_diff,
                'metrics': metrics
            })
        elif mos_below_pct > 20:
            moderate_issues.append({
                'filename': filename,
                'mos_below_pct': mos_below_pct,
                'mos_file_diff': mos_file_diff
            })
        else:
            good_quality.append({
                'filename': filename,
                'mos_below_pct': mos_below_pct,
                'mos_file_diff': mos_file_diff
            })
    
    # 按MOS文件级差值排序
    mos_rankings.sort(key=lambda x: x['mos_diff'])
    
    return {
        'total': len(comparisons),
        'severe_issues': severe_issues,
        'moderate_issues': moderate_issues,
        'good_quality': good_quality,
        'dimension_stats': dimension_stats,
        'mos_rankings': mos_rankings
    }

def print_summary_report(analysis):
    """打印汇总报告"""
    print("=" * 100)
    print("NISQA 基准对比分析 - 质量问题汇总报告")
    print("=" * 100)
    
    total = analysis['total']
    severe = len(analysis['severe_issues'])
    moderate = len(analysis['moderate_issues'])
    good = len(analysis['good_quality'])
    
    print(f"\n📊 整体统计（基于MOS总体质量）")
    print(f"  总文件数: {total}")
    print(f"  ✓ 质量良好: {good} ({good/total*100:.1f}%) - 低于基准帧数 <20%")
    print(f"  ⚠️  中等劣化: {moderate} ({moderate/total*100:.1f}%) - 低于基准帧数 20-50%")
    print(f"  ✗ 严重劣化: {severe} ({severe/total*100:.1f}%) - 低于基准帧数 >50%")
    
    # 各维度统计
    print(f"\n📈 各维度质量分布")
    print(f"{'维度':<10} {'质量良好':<15} {'中等劣化':<15} {'严重劣化':<15}")
    print("-" * 60)
    
    for dim_name in ['MOS', 'NOI', 'DIS', 'COL', 'LOUD']:
        stats = analysis['dimension_stats'][dim_name]
        good_count = len(stats['good'])
        mod_count = len(stats['moderate'])
        sev_count = len(stats['severe'])
        print(f"{dim_name:<10} {good_count:<15} {mod_count:<15} {sev_count:<15}")
    
    # 最差的20个文件（MOS）
    print(f"\n⚠️  MOS质量最差的20个文件")
    print(f"{'排名':<6} {'文件名':<60} {'MOS差值':<12} {'低于基准%':<12}")
    print("-" * 95)
    
    worst_20 = analysis['mos_rankings'][:20]
    for i, item in enumerate(worst_20, 1):
        print(f"{i:<6} {item['filename']:<60} {item['mos_diff']:>+8.3f}     {item['mos_below_pct']:>6.1f}%")
    
    # 最好的10个文件（MOS）
    print(f"\n✓ MOS质量最好的10个文件")
    print(f"{'排名':<6} {'文件名':<60} {'MOS差值':<12} {'低于基准%':<12}")
    print("-" * 95)
    
    best_10 = analysis['mos_rankings'][-10:][::-1]
    for i, item in enumerate(best_10, 1):
        print(f"{i:<6} {item['filename']:<60} {item['mos_diff']:>+8.3f}     {item['mos_below_pct']:>6.1f}%")
    
    # 严重问题详情
    if analysis['severe_issues']:
        print(f"\n🚨 严重质量问题文件详情（MOS低于基准帧数>50%）")
        print("=" * 100)
        
        for item in sorted(analysis['severe_issues'], key=lambda x: x['mos_below_pct'], reverse=True):
            print(f"\n【{item['filename']}】")
            print(f"  MOS低于基准帧数: {item['mos_below_pct']:.1f}%")
            print(f"  文件级MOS差值: {item['mos_file_diff']:+.3f}")
            
            # 显示各维度问题
            metrics = item['metrics']
            problem_dims = []
            dim_mapping = {'noi': 'NOI', 'dis': 'DIS', 'col': 'COL', 'loud': 'LOUD'}
            
            for dim_lower, dim_upper in dim_mapping.items():
                dim_stats = metrics.get(dim_lower, {}).get('stats', {})
                below_pct = dim_stats.get('percent_below_baseline', 0)
                if below_pct > 50:
                    problem_dims.append(f"{dim_upper}({below_pct:.1f}%)")
            
            if problem_dims:
                print(f"  其他问题维度: {', '.join(problem_dims)}")
    
    # NOI（噪声）问题突出的文件
    noi_severe = analysis['dimension_stats']['NOI']['severe']
    if len(noi_severe) > 20:
        print(f"\n🔊 NOI（噪声）问题严重文件: {len(noi_severe)} 个")
        print("  前20个噪声问题最严重的文件已在上面MOS最差列表中体现")
    
    print("\n" + "=" * 100)
    print("分析完成！")
    print(f"详细数据请查看: voice_quality_tool/nisqa/baseline_compare_*.json")
    print(f"可视化图表:")
    print(f"  - 综合对比图: voice_quality_tool/nisqa/baseline_compare_all.png")
    print(f"  - 质量热力图: voice_quality_tool/nisqa/baseline_compare_heatmap.png")
    print("=" * 100)

def save_summary_json(analysis, output_path):
    """保存汇总分析结果为JSON"""
    summary = {
        'total_files': analysis['total'],
        'quality_distribution': {
            'good': len(analysis['good_quality']),
            'moderate': len(analysis['moderate_issues']),
            'severe': len(analysis['severe_issues'])
        },
        'dimension_statistics': {
            dim: {
                'good': len(stats['good']),
                'moderate': len(stats['moderate']),
                'severe': len(stats['severe'])
            }
            for dim, stats in analysis['dimension_stats'].items()
        },
        'worst_20_files': analysis['mos_rankings'][:20],
        'best_10_files': analysis['mos_rankings'][-10:][::-1],
        'severe_issue_files': [
            {
                'filename': item['filename'],
                'mos_below_pct': item['mos_below_pct'],
                'mos_file_diff': item['mos_file_diff']
            }
            for item in analysis['severe_issues']
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n[已保存] 汇总分析结果: {output_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='NISQA基准对比结果汇总分析')
    parser.add_argument('--output-dir', default='.',
                       help='对比结果JSON文件所在目录')
    parser.add_argument('--save-json', 
                       help='保存汇总结果为JSON文件（可选）')
    
    args = parser.parse_args()
    
    print("正在加载对比结果...")
    comparisons = load_all_comparisons(args.output_dir)
    
    if not comparisons:
        print("[错误] 未找到任何baseline_compare_*.json文件")
        return
    
    print(f"已加载 {len(comparisons)} 个对比结果")
    
    print("\n正在分析质量问题...")
    analysis = analyze_quality_issues(comparisons)
    
    print_summary_report(analysis)
    
    if args.save_json:
        save_summary_json(analysis, args.save_json)

if __name__ == '__main__':
    main()
