"""
NISQA Frame-Level Quality Analysis
提取每一帧（时间段）的质量分数，而不是整个文件的聚合分数

Author: Modified from NISQA official code
"""

import os
import sys
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import librosa

# 添加NISQA模块路径
nisqa_path = os.path.join(os.path.dirname(__file__), 'nisqa_repo')
sys.path.insert(0, nisqa_path)

from nisqa import NISQA_lib as NL


def predict_dim_framewise(model, ds, bs, dev, audio_durations=None, num_workers=0):
    """
    修改自predict_dim，提取frame-level的质量预测
    
    Args:
        audio_durations: dict, {filename: duration_in_seconds}，用于计算真实帧数
    
    返回:
        frame_predictions: dict, 包含每个文件的帧级别预测
                          {filename: {'mos': [...], 'noi': [...], ...}}
        file_predictions: DataFrame, 文件级别的聚合预测（与原始predict_dim相同）
    """
    dl = DataLoader(ds,
                    batch_size=bs,
                    shuffle=False,
                    drop_last=False,
                    pin_memory=False,
                    num_workers=num_workers)
    
    model.to(dev)
    model.eval()
    
    frame_predictions = {}
    file_predictions_list = []
    
    with torch.no_grad():
        for xb, yb, (idx, n_wins) in dl:
            xb = xb.to(dev)
            n_wins_cpu = n_wins.clone()  # 保存真实的n_wins（未padding前）
            n_wins = n_wins.to(dev)
            
            # 前向传播到pooling之前
            x = model.cnn(xb, n_wins)
            x, n_wins_after_td = model.time_dependency(x, n_wins)
            x, n_wins_after_td2 = model.time_dependency_2(x, n_wins_after_td)
            
            # x shape: [batch_size, n_frames_padded, feature_dim]
            # 现在x包含了每一帧的特征（包括padding的零帧）
            
            # 对每个维度的pooling层，提取frame-level预测
            frame_outputs = []
            for i, pool_layer in enumerate(model.pool_layers):
                # pool_layer的结构:
                # - PoolAttFF: linear1 (d->h), linear2 (h->1, attention), linear3 (d->output)
                # - PoolAtt: linear1 (d->1, attention), linear2 (d->output)
                # - 其他: linear (d->output)
                
                # 我们需要直接对每一帧应用最终的预测层（跳过attention aggregation）
                if hasattr(pool_layer.model, 'linear3'):
                    # PoolAttFF: 使用linear3做预测
                    frame_pred = pool_layer.model.linear3(x)  # [batch, n_frames, 1]
                elif hasattr(pool_layer.model, 'linear2'):
                    # PoolAtt: 使用linear2做预测
                    frame_pred = pool_layer.model.linear2(x)  # [batch, n_frames, 1]
                elif hasattr(pool_layer.model, 'linear'):
                    # 其他pooling: 使用linear
                    frame_pred = pool_layer.model.linear(x)  # [batch, n_frames, 1]
                else:
                    raise ValueError("Unknown pooling layer structure")
                
                frame_outputs.append(frame_pred.squeeze(-1).cpu().numpy())  # [batch, n_frames]
            
            # frame_outputs: list of 5 arrays, each [batch, n_frames_padded]
            # 转置为 [batch, n_frames_padded, 5]
            frame_outputs = np.stack(frame_outputs, axis=-1)
            
            # 同时计算文件级别的聚合预测（使用完整的pooling）
            file_pred = model(xb, n_wins_cpu.to(dev)).cpu().numpy()  # [batch, 5]
            
            # 保存每个样本的结果
            for i in range(xb.shape[0]):
                sample_idx = idx[i].item()
                filename = ds.df.iloc[sample_idx]['deg']
                
                # 根据音频时长计算真实帧数（而不是使用NISQA的n_wins）
                if audio_durations and filename in audio_durations:
                    duration, seg_len, hop_len = audio_durations[filename]
                    # 帧数 = (总时长 - 窗口长度) / 跳跃长度 + 1
                    n_frames = max(1, int((duration - seg_len) / hop_len) + 1) if duration >= seg_len else 1
                else:
                    # 回退到NISQA的n_wins（可能不准确）
                    n_frames = n_wins_cpu[i].item()
                
                # 只保留有效帧（去除padding）
                valid_frame_pred = frame_outputs[i, :n_frames, :]  # [n_frames, 5]
                
                frame_predictions[filename] = {
                    'mos': valid_frame_pred[:, 0],
                    'noi': valid_frame_pred[:, 1],
                    'dis': valid_frame_pred[:, 2],
                    'col': valid_frame_pred[:, 3],
                    'loud': valid_frame_pred[:, 4],
                    'n_frames': n_frames,
                }
                
                file_predictions_list.append({
                    'filename': filename,
                    'mos_pred': file_pred[i, 0],
                    'noi_pred': file_pred[i, 1],
                    'dis_pred': file_pred[i, 2],
                    'col_pred': file_pred[i, 3],
                    'loud_pred': file_pred[i, 4],
                })
    
    file_predictions_df = pd.DataFrame(file_predictions_list)
    
    return frame_predictions, file_predictions_df


def plot_framewise_quality(frame_pred, filename, seg_length=15.0, hop_length=1.0, output_dir='.'):
    """
    可视化frame-level的质量分数
    """
    n_frames = frame_pred['n_frames']
    dims = ['mos', 'noi', 'dis', 'col', 'loud']
    dim_names = ['MOS (Overall)', 'Noisiness', 'Distortion', 'Coloration', 'Loudness']
    
    # Each frame with custom segment length and hop size
    # frame i covers time [i*hop_size, i*hop_size+seg_length]
    frame_times = np.arange(n_frames) * hop_length  # 起始时间（秒）
    
    fig, axes = plt.subplots(5, 1, figsize=(12, 10))
    fig.suptitle(f'Frame-Level Quality Analysis: {filename}', fontsize=14)
    
    for i, (dim, name) in enumerate(zip(dims, dim_names)):
        axes[i].plot(frame_times, frame_pred[dim], marker='o', linewidth=2)
        axes[i].set_ylabel(name, fontsize=10)
        axes[i].set_ylim([0, 5])
        axes[i].grid(True, alpha=0.3)
        axes[i].axhline(y=3.0, color='r', linestyle='--', alpha=0.5, label='Threshold')
        
        if i == len(dims) - 1:
            axes[i].set_xlabel('Time (seconds)', fontsize=10)
    
    plt.tight_layout()
    
    # 保存图像
    safe_filename = filename.replace('.wav', '').replace('/', '_').replace('\\', '_')
    output_path = os.path.join(output_dir, f'framewise_{safe_filename}.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Frame-level plot saved: {output_path}")


def main():
    """
    主函数：分析单个文件的frame-level质量
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='NISQA Frame-Level Quality Analysis')
    parser.add_argument('--audio', type=str, required=True, help='Path to audio file')
    parser.add_argument('--model', type=str, 
                       default='weights/nisqa.tar',
                       help='Path to NISQA model weights')
    parser.add_argument('--output_dir', type=str, default='.',
                       help='Output directory for results')
    parser.add_argument('--plot', action='store_true',
                       help='Generate frame-level quality plots')
    parser.add_argument('--seg_length', type=float, default=15.0,
                       help='Segment window length in seconds (default: 15.0)')
    parser.add_argument('--hop_length', type=float, default=0.5,
                       help='Hop size between frames in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.audio):
        print("[ERROR] Audio file not found:", args.audio)
        return
    
    if not os.path.exists(args.model):
        print("[ERROR] Model file not found:", args.model)
        return
    
    print("\n" + "="*60)
    print("Analyzing:", args.audio)
    print("Model:", args.model)
    print("="*60)
    
    # 加载模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print("Device:", device)
    
    # 创建dataset（单个文件）
    df = pd.DataFrame([{'deg': args.audio}])
    
    # 使用NISQA官方代码加载模型和数据
    from nisqa.NISQA_model import nisqaModel
    
    nisqa_args = {
        'mode': 'predict_file',
        'pretrained_model': args.model,
        'deg': args.audio,
        'output_dir': args.output_dir,
        'ms_channel': None,
        'csv_file': None,
        'csv_con': None,
        'csv_deg': None,
        'data_dir': None,
        'output_dir': args.output_dir,
        'num_workers': 0,
        'bs': 1,
        'ms_max_segments': None,
        'ms_seg_length': int(args.seg_length),  # 确保为整数
        'ms_seg_hop_length': args.hop_length,  # hop可以是浮点数
    }
    
    # 加载模型
    nisqa_model = nisqaModel(nisqa_args)
    
    # 获取音频时长（用于计算真实帧数）
    print("\n[Calculating audio duration...]")
    y, sr = librosa.load(args.audio, sr=None)
    duration = len(y) / sr
    print(f"  Audio duration: {duration:.2f} seconds")
    print(f"  Sample rate: {sr} Hz")
    
    # 计算预期帧数
    SEG_LENGTH = args.seg_length
    HOP_SIZE = args.hop_length
    expected_frames = max(1, int((duration - SEG_LENGTH) / HOP_SIZE) + 1) if duration >= SEG_LENGTH else 1
    print(f"  Expected frames ({SEG_LENGTH}s window, {HOP_SIZE}s hop): {expected_frames}")
    
    # 创建音频时长字典（使用basename作为key，以匹配NISQA的数据加载方式）
    # 存储 (duration, seg_length, hop_length) 元组
    audio_durations = {os.path.basename(args.audio): (duration, args.seg_length, args.hop_length)}
    
    # Frame-level预测
    print("\n[Running frame-level analysis...]")
    frame_preds, file_preds = predict_dim_framewise(
        nisqa_model.model,
        nisqa_model.ds_val,
        nisqa_args['bs'],
        device,
        audio_durations=audio_durations,
        num_workers=0
    )
    
    # 显示结果
    filename = os.path.basename(args.audio)
    
    # frame_preds的key是完整路径，需要找到对应的条目
    # 获取第一个（也是唯一一个）条目
    if len(frame_preds) == 0:
        print("[ERROR] No predictions generated!")
        return
    
    audio_key = list(frame_preds.keys())[0]
    frame_pred = frame_preds[audio_key]
    file_pred = file_preds.iloc[0]
    
    print("\n" + "="*60)
    print("File-Level Quality (Aggregated):")
    print("="*60)
    print(f"  MOS:        {file_pred['mos_pred']:.2f}")
    print(f"  Noisiness:  {file_pred['noi_pred']:.2f}")
    print(f"  Distortion: {file_pred['dis_pred']:.2f}")
    print(f"  Coloration: {file_pred['col_pred']:.2f}")
    print(f"  Loudness:   {file_pred['loud_pred']:.2f}")
    
    print("\n" + "="*60)
    print("Frame-Level Quality (Temporal Segments):")
    print("="*60)
    SEG_LENGTH = args.seg_length
    HOP_SIZE = args.hop_length
    print("  Total frames:", frame_pred['n_frames'])
    print(f"  Segment length: {SEG_LENGTH} seconds ({HOP_SIZE}s hop)")
    print(f"  Total duration: ~{(frame_pred['n_frames'] - 1) * HOP_SIZE + SEG_LENGTH:.1f} seconds")
    print()
    
    # 显示每一帧的详细数据
    for i in range(frame_pred['n_frames']):
        time_start = i * HOP_SIZE
        time_end = time_start + SEG_LENGTH
        print(f"  Frame {i+1} [{time_start:.1f}s - {time_end:.1f}s]:")
        print(f"    MOS: {frame_pred['mos'][i]:.2f}  |  "
              f"NOI: {frame_pred['noi'][i]:.2f}  |  "
              f"DIS: {frame_pred['dis'][i]:.2f}  |  "
              f"COL: {frame_pred['col'][i]:.2f}  |  "
              f"LOUD: {frame_pred['loud'][i]:.2f}")
    
    # 生成可视化
    if args.plot:
        print("\n[Generating frame-level quality plot...]")
        plot_framewise_quality(frame_pred, filename, 
                              seg_length=args.seg_length, 
                              hop_length=args.hop_length,
                              output_dir=args.output_dir)
    
    # 保存JSON结果
    import json
    output_json = os.path.join(args.output_dir, f'framewise_{filename}.json')
    
    # 转换numpy数组为列表（JSON序列化）
    json_data = {
        'filename': args.audio,
        'file_level': {
            'mos': float(file_pred['mos_pred']),
            'noi': float(file_pred['noi_pred']),
            'dis': float(file_pred['dis_pred']),
            'col': float(file_pred['col_pred']),
            'loud': float(file_pred['loud_pred']),
        },
        'frame_level': {
            'n_frames': int(frame_pred['n_frames']),
            'segment_duration': float(args.seg_length),
            'hop_duration': float(args.hop_length),
            'frames': [
                {
                    'frame_id': i,
                    'time_start': i * args.hop_length,
                    'time_end': i * args.hop_length + args.seg_length,
                    'mos': float(frame_pred['mos'][i]),
                    'noi': float(frame_pred['noi'][i]),
                    'dis': float(frame_pred['dis'][i]),
                    'col': float(frame_pred['col'][i]),
                    'loud': float(frame_pred['loud'][i]),
                }
                for i in range(frame_pred['n_frames'])
            ]
        }
    }
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Frame-level data saved: {output_json}")
    print("\n[Analysis complete!]")


if __name__ == '__main__':
    main()
