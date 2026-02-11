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
    
    # OK/NOK分类
    ok_files = []
    nok_files = []
    
    # 问题维度统计
    nok_by_dimension = defaultdict(list)
    
    for comp in comparisons:
        filename = comp['filename']
        data = comp['data']
        
        # 获取状态（新的判定字段）
        status = data.get('status', 'UNKNOWN')
        nok_dimensions = data.get('nok_dimensions', [])
        nok_reasons = data.get('nok_reasons', {})
        
        # 文件级差值
        file_level = data.get('file_level', {})
        file_diff = file_level.get('diff', {})
        
        file_info = {
            'filename': filename,
            'status': status,
            'nok_dimensions': nok_dimensions,
            'nok_reasons': nok_reasons,
            'mos_diff': file_diff.get('mos', 0),
            'noi_diff': file_diff.get('noi', 0),
            'dis_diff': file_diff.get('dis', 0),
            'col_diff': file_diff.get('col', 0),
            'loud_diff': file_diff.get('loud', 0)
        }
        
        if status == 'OK':
            ok_files.append(file_info)
        else:  # NOK
            nok_files.append(file_info)
            # 统计各问题维度
            for dim in nok_dimensions:
                nok_by_dimension[dim].append(filename)
    
    return {
        'total': len(comparisons),
        'ok_files': ok_files,
        'nok_files': nok_files,
        'nok_by_dimension': dict(nok_by_dimension)
    }

def print_summary_report(analysis):
    """打印汇总报告"""
    print("=" * 100)
    print("NISQA 基准对比分析 - 质量问题汇总报告")
    print("=" * 100)
    
    total = analysis['total']
    ok_count = len(analysis['ok_files'])
    nok_count = len(analysis['nok_files'])
    
    print(f"\n📊 整体统计")
    print(f"  总文件数: {total}")
    print(f"  ✓ OK文件: {ok_count} ({ok_count/total*100:.1f}%) - 质量相当或优于基准")
    print(f"  ✗ NOK文件: {nok_count} ({nok_count/total*100:.1f}%) - 质量劣于基准")
    
    # NOK维度统计
    if analysis['nok_by_dimension']:
        print(f"\n📈 NOK文件问题维度分布")
        print(f"{'维度':<15} {'文件数':<10}")
        print("-" * 30)
        
        for dim, files in sorted(analysis['nok_by_dimension'].items()):
            print(f"{dim:<15} {len(files):<10}")
    
    # NOK文件详情
    if analysis['nok_files']:
        print(f"\n🚨 NOK文件详情")
        print("=" * 100)
        
        for item in analysis['nok_files']:
            print(f"\n【{item['filename']}】")
            print(f"  问题维度: {', '.join(item['nok_dimensions'])}")
            
            # 显示判定原因
            nok_reasons = item.get('nok_reasons', {})
            if nok_reasons:
                print(f"  判定依据:")
                for dim, reason in nok_reasons.items():
                    print(f"    - {dim}: {reason}")
            
            print(f"  文件级差值: MOS={item['mos_diff']:+.3f}, NOI={item['noi_diff']:+.3f}, "
                  f"DIS={item['dis_diff']:+.3f}, COL={item['col_diff']:+.3f}, LOUD={item['loud_diff']:+.3f}")
    
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
            'ok': len(analysis['ok_files']),
            'nok': len(analysis['nok_files'])
        },
        'nok_by_dimension': analysis['nok_by_dimension'],
        'ok_files': analysis['ok_files'],
        'nok_files': analysis['nok_files']
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
