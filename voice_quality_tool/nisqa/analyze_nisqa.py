#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用NISQA进行无参考音质评估
NISQA: Non-Intrusive Speech Quality Assessment
"""

import sys
import os
from pathlib import Path
import torch
from nisqa.NISQA_model import nisqaModel

def predict_quality(audio_path, model_path=None, get_frame_level=False):
    """
    使用NISQA评估音频质量
    
    Args:
        audio_path: 音频文件路径
        model_path: 模型权重路径（可选）
        get_frame_level: 是否获取帧级别分析
    
    Returns:
        dict: 包含MOS分数和其他指标
    """
    # 转为绝对路径
    audio_path = str(Path(audio_path).resolve())
    # 配置 - 使用MOS-only模型（当前pip版本的NISQA与完整模型不兼容）
    # 注意：完整的4维度评估需要使用GitHub仓库的代码，而不是pip安装的包
    weights_dir = Path(__file__).parent / 'weights'
    
    if model_path:
        selected_model = model_path
    elif (weights_dir / 'nisqa_mos_only.tar').exists():
        selected_model = str(weights_dir / 'nisqa_mos_only.tar')
    elif (weights_dir / 'nisqa_tts.tar').exists():
        selected_model = str(weights_dir / 'nisqa_tts.tar')
    elif (weights_dir / 'nisqa.tar').exists():
        selected_model = str(weights_dir / 'nisqa.tar')
    else:
        selected_model = None
    
    print(f"")
    print(f"【注意】当前使用MOS-only模型")
    print(f"  pip安装的NISQA库(v2.0)与完整4维度模型不兼容")
    print(f"  如需4维度评估，请使用nisqa_repo/run_predict.py脚本")
    print(f"")
    
    args = {
        'mode': 'predict_file',
        'pretrained_model': selected_model,
        'deg': audio_path,
        'output_dir': None,
        'ms_channel': None,
        'csv_file': None,
        'csv_mos_train': None,
        'csv_mos_val': None,
        'model': 'NISQA',
        'num_workers': 0,
        'bs': 1,
        'dim': 512,
        # 添加缺失的参数
        'ms_seg_length': 15,
        'ms_n_mels': 48,
        'double_ended': False,
        'data_dir': None,
        'output_name': None,
        'cnn_model': 'adapt',
        'pool': 'att',  # 注意力池化
        'tr_bs_val': 1,
        'tr_epochs': 100,
        'tr_lr': 0.0001,
        'tr_lr_patience': 5,
        'tr_checkpoint': None,
    }
    
    try:
        # 初始化模型
        print(f"\n[加载NISQA模型]")
        print(f"  模型类型: {args['pretrained_model']}")
        
        nisqa = nisqaModel(args)
        
        # 预测
        print(f"\n[分析音频]")
        print(f"  文件: {Path(audio_path).name}")
        
        df_result = nisqa.predict()
        
        # 转换DataFrame到字典
        if not df_result.empty:
            row = df_result.iloc[0]
            result = {
                'deg': row['deg'],
                'mos_pred': float(row['mos_pred']) if 'mos_pred' in row else None,
                'noi_pred': float(row['noi_pred']) if 'noi_pred' in row else None,
                'dis_pred': float(row['dis_pred']) if 'dis_pred' in row else None,
                'col_pred': float(row['col_pred']) if 'col_pred' in row else None,
                'loud_pred': float(row['loud_pred']) if 'loud_pred' in row else None,
            }
            
            # 如果需要帧级别分析
            if get_frame_level:
                print(f"\n[帧级别分析]")
                print(f"  正在提取帧级别特征...")
                
                # 尝试获取模型的中间输出
                try:
                    # 获取数据加载器
                    from nisqa.NISQA_lib import SpeechQualityDataset
                    import torch
                    
                    # 创建数据集
                    ds = SpeechQualityDataset(
                        df=df_result[['deg']],
                        df_con=None,
                        data_dir=None,
                        filename_column='deg',
                        mos_column=None,
                        seg_length=args['ms_seg_length'],
                        max_length=None,
                        to_memory=None,
                        to_memory_workers=None,
                        transform=None,
                        seg_hop_length=args['ms_seg_length']//2,  # 50%重叠
                    )
                    
                    # 获取音频的mel频谱
                    spec = ds[0][0].unsqueeze(0)
                    n_wins = torch.tensor([spec.shape[-1]])
                    
                    # 前向传播获取每帧的预测
                    with torch.no_grad():
                        # 获取每个池化层的输出
                        nisqa.model.eval()
                        x = nisqa.model.cnn(spec.to(nisqa.dev))
                        
                        # 获取帧级别的质量预测
                        if hasattr(nisqa.model, 'pool_layers'):
                            frame_scores = []
                            for pool_layer in nisqa.model.pool_layers:
                                frame_out = pool_layer(x, n_wins.to(nisqa.dev))
                                frame_scores.append(frame_out.cpu().numpy())
                            
                            result['frame_level'] = {
                                'num_frames': x.shape[-1],
                                'frame_scores': frame_scores
                            }
                            print(f"  ✓ 提取了 {x.shape[-1]} 帧数据")
                        else:
                            print(f"  ! 当前模型不支持帧级别输出")
                            result['frame_level'] = None
                            
                except Exception as e:
                    print(f"  ! 帧级别分析失败: {e}")
                    result['frame_level'] = None
            
            return result
        else:
            return None
        
    except Exception as e:
        print(f"\n[错误] 预测失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_result(result, filename):
    """打印结果"""
    if not result:
        return
    
    print("\n" + "=" * 70)
    print(" " * 20 + "NISQA 音质评估报告")
    print("=" * 70)
    
    print(f"\n【文件】{filename}")
    
    # MOS分数
    mos = result.get('mos_pred', result.get('mos', None))
    if mos is not None:
        print(f"\n【整体质量】")
        print(f"  MOS分数: {mos:.2f} / 5.0")
        
        # 质量等级
        if mos >= 4.0:
            level = "优秀"
            verdict = "音质优良"
        elif mos >= 3.5:
            level = "良好"
            verdict = "音质良好"
        elif mos >= 3.0:
            level = "一般"
            verdict = "音质可接受"
        elif mos >= 2.0:
            level = "较差"
            verdict = "音质较差"
        else:
            level = "很差"
            verdict = "音质很差"
        
        print(f"  质量等级: {level}")
        print(f"  判定: {verdict}")
    
    # 其他维度（如果有）
    dimensions = ['noi', 'dis', 'col', 'loud']
    dim_names = {
        'noi': '噪声',
        'dis': '失真',
        'col': '音色',
        'loud': '响度'
    }
    
    print(f"\n【质量维度】")
    has_dimensions = False
    for dim in dimensions:
        key = f'{dim}_pred'
        if key in result and result[key] is not None:
            print(f"  {dim_names[dim]}: {result[key]:.2f}")
            has_dimensions = True
    
    if not has_dimensions:
        print(f"  (此模型仅提供整体MOS分数)")
    
    print("\n" + "=" * 70)


def batch_analyze(directory, output_file=None):
    """批量分析目录中的所有音频"""
    directory = Path(directory)
    wav_files = sorted(directory.glob("*.wav"))
    
    if not wav_files:
        print(f"[错误] 未找到WAV文件: {directory}")
        return
    
    print("=" * 80)
    print(" " * 25 + "NISQA 批量评估")
    print("=" * 80)
    print(f"\n目录: {directory}")
    print(f"文件数: {len(wav_files)}\n")
    
    results = []
    
    for i, wav_file in enumerate(wav_files, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(wav_files)}] {wav_file.name}")
        print(f"{'='*80}")
        
        result = predict_quality(str(wav_file))
        
        if result:
            mos = result.get('mos_pred', result.get('mos', 0))
            results.append({
                'filename': wav_file.name,
                'mos': mos,
                'result': result
            })
            print_result(result, wav_file.name)
    
    # 汇总
    if results:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "汇总报告")
        print("=" * 80 + "\n")
        
        # 排序
        results_sorted = sorted(results, key=lambda x: x['mos'], reverse=True)
        
        print(f"{'排名':<6} {'文件名':<50} {'MOS分数':<10}")
        print("-" * 80)
        
        for i, r in enumerate(results_sorted, 1):
            print(f"{i:<6} {r['filename']:<50} {r['mos']:<10.2f}")
        
        # 统计
        avg_mos = sum(r['mos'] for r in results) / len(results)
        max_mos = max(r['mos'] for r in results)
        min_mos = min(r['mos'] for r in results)
        
        print("\n" + "=" * 80)
        print(f"统计信息:")
        print(f"  总文件数: {len(results)}")
        print(f"  平均MOS: {avg_mos:.2f}")
        print(f"  最高MOS: {max_mos:.2f}")
        print(f"  最低MOS: {min_mos:.2f}")
        print("=" * 80 + "\n")
        
        # 保存
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'directory': str(directory),
                    'total_files': len(results),
                    'average_mos': avg_mos,
                    'results': results
                }, f, indent=2, ensure_ascii=False)
            print(f"[✓] 结果已保存: {output_file}\n")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  单文件: python analyze_nisqa.py <audio.wav> [--frame-level]")
        print("  批量:   python analyze_nisqa.py <directory> [output.json]")
        print("\n选项:")
        print("  --frame-level  启用帧级别分析")
        print("\n示例:")
        print("  python analyze_nisqa.py test.wav")
        print("  python analyze_nisqa.py test.wav --frame-level")
        print("  python analyze_nisqa.py ../robotic nisqa_results.json")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    frame_level = '--frame-level' in sys.argv
    
    if path.is_file():
        # 单文件分析
        result = predict_quality(str(path), get_frame_level=frame_level)
        if result:
            print_result(result, path.name)
    elif path.is_dir():
        # 批量分析
        output_file = None
        for arg in sys.argv[2:]:
            if not arg.startswith('--'):
                output_file = arg
                break
        batch_analyze(path, output_file)
    else:
        print(f"[错误] 路径不存在: {path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
