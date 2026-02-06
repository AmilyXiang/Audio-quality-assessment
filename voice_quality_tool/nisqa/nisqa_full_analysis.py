#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用NISQA官方仓库代码进行完整的4维度评估
包括：MOS总分 + 噪声(NOI) + 失真(DIS) + 音色(COL) + 响度(LOUD)
"""

import sys
import os
from pathlib import Path

# 添加NISQA仓库路径
nisqa_repo = Path(__file__).parent / 'nisqa_repo'
sys.path.insert(0, str(nisqa_repo))

try:
    from nisqa.NISQA_model import nisqaModel
except ImportError:
    print("[错误] 无法导入NISQA")
    print("  请确保nisqa_repo目录存在")
    sys.exit(1)


def predict_full_dimensions(audio_path):
    """使用NISQA仓库代码进行完整评估"""
    
    # 转为绝对路径
    audio_path = str(Path(audio_path).resolve())
    weights_dir = Path(__file__).parent / 'weights'
    
    # 使用完整模型
    model_path = weights_dir / 'nisqa.tar'
    if not model_path.exists():
        print(f"[错误] 模型不存在: {model_path}")
        return None
    
    print(f"\n[加载NISQA完整模型]")
    print(f"  模型: {model_path.name}")
    print(f"  文件: {Path(audio_path).name}")
    
    # 配置参数（与训练时一致）
    args = {
        'mode': 'predict_file',
        'pretrained_model': str(model_path),
        'deg': audio_path,
        'output_dir': None,
        'csv_file': None,
        'model': 'NISQA',
        'num_workers': 0,
        'bs': 1,
        'ms_channel': None,
        'dim': 512,
        'ms_seg_length': 15,
        'ms_n_mels': 48,
        'cnn_model': 'adapt',
        'pool': 'att', 
        'double_ended': False,
    }
    
    try:
        # 初始化模型
        nisqa = nisqaModel(args)
        
        # 预测
        print(f"\n[分析中...]")
        df_result = nisqa.predict()
        
        if df_result.empty:
            return None
        
        # 提取结果
        row = df_result.iloc[0]
        result = {
            'file': Path(audio_path).name,
            'mos': float(row['mos_pred']) if 'mos_pred' in row else None,
            'noi': float(row['noi_pred']) if 'noi_pred' in row else None,
            'dis': float(row['dis_pred']) if 'dis_pred' in row else None,
            'col': float(row['col_pred']) if 'col_pred' in row else None,
            'loud': float(row['loud_pred']) if 'loud_pred' in row else None,
        }
        
        return result
        
    except Exception as e:
        print(f"\n[错误] 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_result(result):
    """打印结果"""
    if not result:
        return
    
    print("\n" + "=" * 70)
    print(" " * 20 + "NISQA 完整评估报告")
    print("=" * 70)
    
    print(f"\n【文件】{result['file']}")
    
    # 整体MOS
    if result['mos']:
        print(f"\n【整体质量 MOS】")
        print(f"  分数: {result['mos']:.2f} / 5.0")
        
        if result['mos'] >= 4.0:
            print(f"  等级: 优秀 (Excellent)")
        elif result['mos'] >= 3.5:
            print(f"  等级: 良好 (Good)")
        elif result['mos'] >= 3.0:
            print(f"  等级: 一般 (Fair)")
        elif result['mos'] >= 2.0:
            print(f"  等级: 较差 (Poor)")
        else:
            print(f"  等级: 很差 (Bad)")
    
    # 4个维度
    print(f"\n【质量维度分析】")
    dimensions = [
        ('noi', '噪声 (Noisiness)', '越低越好'),
        ('dis', '失真 (Distortion)', '越低越好'),
        ('col', '音色 (Coloration)','越低越好'),
        ('loud', '响度 (Loudness)', '适中最好'),
    ]
    
    for key, name, note in dimensions:
        if result[key] is not None:
            print(f"  {name}: {result[key]:.2f} / 5.0  ({note})")
    
    print("\n" + "=" * 70 + "\n")


def batch_analyze(directory, output_file=None):
    """批量分析"""
    directory = Path(directory)
    wav_files = sorted(directory.glob("*.wav"))
    
    if not wav_files:
        print(f"[错误] 未找到WAV文件: {directory}")
        return
    
    print("=" * 80)
    print(" " * 25 + "NISQA 批量评估")
    print("=" * 80)
    print(f"\n目录: {directory}")
    print(f"  文件数: {len(wav_files)}\n")
    
    results = []
    
    for i, wav_file in enumerate(wav_files, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(wav_files)}]")
        
        result = predict_full_dimensions(str(wav_file))
        
        if result:
            results.append(result)
            print_result(result)
    
    # 汇总
    if results:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "汇总报告")
        print("=" * 80 + "\n")
        
        # 排序
        results_sorted = sorted(results, key=lambda x: x['mos'] if x['mos'] else 0, reverse=True)
        
        print(f"{'排名':<6} {'文件名':<40} {'MOS':<8} {'噪声':<8} {'失真':<8} {'音色':<8} {'响度':<8}")
        print("-" * 80)
        
        for i, r in enumerate(results_sorted, 1):
            mos_str = f"{r['mos']:.2f}" if r['mos'] else "N/A"
            noi_str = f"{r['noi']:.2f}" if r['noi'] else "N/A"
            dis_str = f"{r['dis']:.2f}" if r['dis'] else "N/A"
            col_str = f"{r['col']:.2f}" if r['col'] else "N/A"
            loud_str = f"{r['loud']:.2f}" if r['loud'] else "N/A"
            
            print(f"{i:<6} {r['file']:<40} {mos_str:<8} {noi_str:<8} {dis_str:<8} {col_str:<8} {loud_str:<8}")
        
        # 统计
        valid = [r for r in results if r['mos']]
        if valid:
            avg_mos = sum(r['mos'] for r in valid) / len(valid)
            avg_noi = sum(r['noi'] for r in valid if r['noi']) / len([r for r in valid if r['noi']]) if any(r['noi'] for r in valid) else None
            avg_dis = sum(r['dis'] for r in valid if r['dis']) / len([r for r in valid if r['dis']]) if any(r['dis'] for r in valid) else None
            avg_col = sum(r['col'] for r in valid if r['col']) / len([r for r in valid if r['col']]) if any(r['col'] for r in valid) else None
            avg_loud = sum(r['loud'] for r in valid if r['loud']) / len([r for r in valid if r['loud']]) if any(r['loud'] for r in valid) else None
            
            print("\n" + "=" * 80)
            print(f"统计信息:")
            print(f"  总文件数: {len(results)}")
            print(f"  平均MOS: {avg_mos:.2f}")
            if avg_noi: print(f"  平均噪声: {avg_noi:.2f}")
            if avg_dis: print(f"  平均失真: {avg_dis:.2f}")
            if avg_col: print(f"  平均音色偏移: {avg_col:.2f}")
            if avg_loud: print(f"  平均响度: {avg_loud:.2f}")
            print("=" * 80 + "\n")
        
        # 保存
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'directory': str(directory),
                    'total_files': len(results),
                    'results': results
                }, f, indent=2, ensure_ascii=False)
            print(f"[✓] 结果已保存: {output_file}\n")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  单文件: python nisqa_full_analysis.py <audio.wav>")
        print("  批量:   python nisqa_full_analysis.py <directory> [output.json]")
        print("\n说明:")
        print("  使用NISQA完整模型，提供MOS + 4维度评估")
        print("  维度: 噪声(NOI) / 失真(DIS) / 音色(COL) / 响度(LOUD)")
        print("\n示例:")
        print("  python nisqa_full_analysis.py test.wav")
        print("  python nisqa_full_analysis.py ../robotic nisqa_full_results.json")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    
    if path.is_file():
        # 单文件分析
        result = predict_full_dimensions(str(path))
        if result:
            print_result(result)
    elif path.is_dir():
        # 批量分析
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        batch_analyze(path, output_file)
    else:
        print(f"[错误] 路径不存在: {path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
