"""
深度数据分析 - 提取帧级详细数据、统计特征、时间序列等信息
用于LLM深度解读（不需要视觉功能）
"""

import json
import os
from pathlib import Path
import numpy as np
from collections import defaultdict

def load_detailed_analysis_data(summary_path, json_dir, num_worst=15, num_best=10):
    """加载详细分析数据"""
    
    # 读取汇总数据
    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # 获取文件列表
    worst_files = summary.get('worst_20_files', [])[:num_worst]
    best_files = summary.get('best_10_files', [])[:num_best]
    
    # 深度分析数据结构
    deep_analysis = {
        'worst_files_detail': [],
        'best_files_detail': [],
        'time_series_patterns': {},
        'correlation_analysis': {},
        'anomaly_detection': {},
        'statistical_summary': {}
    }
    
    # 分析最差文件
    print(f"正在深度分析最差的{num_worst}个文件...")
    for item in worst_files:
        filename = item['filename']
        json_path = Path(json_dir) / f"baseline_compare_{filename}.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 提取详细数据
                detail = analyze_single_file_deeply(filename, data, item)
                deep_analysis['worst_files_detail'].append(detail)
    
    # 分析最好文件
    print(f"正在深度分析最好的{num_best}个文件...")
    for item in best_files:
        filename = item['filename']
        json_path = Path(json_dir) / f"baseline_compare_{filename}.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                detail = analyze_single_file_deeply(filename, data, item)
                deep_analysis['best_files_detail'].append(detail)
    
    # 跨文件统计分析
    print("正在进行跨文件统计分析...")
    deep_analysis['statistical_summary'] = compute_cross_file_statistics(
        deep_analysis['worst_files_detail'],
        deep_analysis['best_files_detail']
    )
    
    # 时间模式分析
    print("正在分析时间模式...")
    deep_analysis['time_series_patterns'] = analyze_time_patterns(
        deep_analysis['worst_files_detail'] + deep_analysis['best_files_detail']
    )
    
    # 异常检测
    print("正在检测异常模式...")
    deep_analysis['anomaly_detection'] = detect_anomalies(
        deep_analysis['worst_files_detail']
    )
    
    return summary, deep_analysis

def analyze_single_file_deeply(filename, data, summary_item):
    """深度分析单个文件"""
    
    metrics = data.get('metrics', {})
    file_level = data.get('file_level', {})
    
    # 提取基本信息
    detail = {
        'filename': filename,
        'mos_diff': summary_item.get('mos_diff', 0),
        'mos_below_pct': summary_item.get('mos_below_pct', 0),
        'file_level_scores': file_level,
        'frame_analysis': {},
        'trend_info': {},
        'anomaly_frames': []
    }
    
    # 分析各维度的帧级数据
    for dim in ['mos', 'noi', 'dis', 'col', 'loud']:
        dim_data = metrics.get(dim, {})
        
        if 'frame_diffs' in dim_data:
            frame_diffs = dim_data['frame_diffs']
            diffs = [f['diff'] for f in frame_diffs]
            
            # 统计特征
            detail['frame_analysis'][dim.upper()] = {
                'mean': np.mean(diffs),
                'std': np.std(diffs),
                'min': np.min(diffs),
                'max': np.max(diffs),
                'median': np.median(diffs),
                'q25': np.percentile(diffs, 25),
                'q75': np.percentile(diffs, 75),
                'range': np.max(diffs) - np.min(diffs),
                'variability': np.std(diffs) / (np.mean(np.abs(diffs)) + 1e-6)
            }
            
            # 趋势信息
            trend = dim_data.get('trend', {})
            if trend:
                detail['trend_info'][dim.upper()] = {
                    'type': trend.get('type'),
                    'description': trend.get('description'),
                    'slope': trend.get('slope', 0)
                }
                
                # 突变点
                sudden_drops = trend.get('sudden_drops', [])
                for drop in sudden_drops:
                    detail['anomaly_frames'].append({
                        'dimension': dim.upper(),
                        'frame': drop.get('frame'),
                        'drop_value': drop.get('drop'),
                        'time': drop.get('frame', 0) * 0.5  # 假设0.5s步长
                    })
        
        # 统计信息
        stats = dim_data.get('stats', {})
        if stats:
            below_pct = stats.get('percent_below_baseline', 0)
            detail['frame_analysis'][dim.upper()]['below_baseline_pct'] = below_pct
    
    # 解析文件名元数据
    detail['metadata'] = parse_filename_metadata(filename)
    
    return detail

def parse_filename_metadata(filename):
    """解析文件名中的元数据"""
    
    metadata = {
        'timestamp': None,
        'ip_address': None,
        'device_code': None,
        'location_code': None
    }
    
    parts = filename.split('_')
    
    # 尝试提取时间戳（如260206125256）
    if len(parts) > 0 and parts[0].isdigit() and len(parts[0]) >= 12:
        timestamp = parts[0]
        metadata['timestamp'] = f"20{timestamp[:2]}-{timestamp[2:4]}-{timestamp[4:6]} {timestamp[6:8]}:{timestamp[8:10]}:{timestamp[10:12]}"
    
    # 尝试提取IP地址
    for part in parts:
        if '.' in part and all(x.isdigit() or x == '.' for x in part):
            metadata['ip_address'] = part
    
    # 提取设备代码（如BOXP, HF）
    for part in parts:
        if part in ['BOXP', 'BOXR', 'HF', 'BOX']:
            metadata['device_code'] = part
        if part in ['WHS', 'P']:
            metadata['location_code'] = part
    
    return metadata

def compute_cross_file_statistics(worst_files, best_files):
    """计算跨文件统计特征"""
    
    stats = {
        'worst_vs_best_comparison': {},
        'dimension_severity_ranking': [],
        'common_anomaly_times': []
    }
    
    # 对比最差和最好文件的统计特征
    for dim in ['MOS', 'NOI', 'DIS', 'COL', 'LOUD']:
        worst_means = [f['frame_analysis'].get(dim, {}).get('mean', 0) 
                      for f in worst_files if dim in f.get('frame_analysis', {})]
        best_means = [f['frame_analysis'].get(dim, {}).get('mean', 0) 
                     for f in best_files if dim in f.get('frame_analysis', {})]
        
        if worst_means and best_means:
            stats['worst_vs_best_comparison'][dim] = {
                'worst_avg': float(np.mean(worst_means)),
                'best_avg': float(np.mean(best_means)),
                'gap': float(np.mean(best_means) - np.mean(worst_means))
            }
    
    # 维度严重性排序
    dimension_severity = []
    for dim in ['MOS', 'NOI', 'DIS', 'COL', 'LOUD']:
        below_pcts = [f['frame_analysis'].get(dim, {}).get('below_baseline_pct', 0) 
                     for f in worst_files if dim in f.get('frame_analysis', {})]
        if below_pcts:
            avg_severity = np.mean(below_pcts)
            dimension_severity.append({
                'dimension': dim,
                'avg_severity': float(avg_severity)
            })
    
    stats['dimension_severity_ranking'] = sorted(
        dimension_severity, 
        key=lambda x: x['avg_severity'], 
        reverse=True
    )
    
    # 寻找共同的异常时间点
    anomaly_times = defaultdict(int)
    for file_detail in worst_files:
        for anomaly in file_detail.get('anomaly_frames', []):
            time_bucket = int(anomaly['time'] / 2) * 2  # 2秒时间桶
            anomaly_times[time_bucket] += 1
    
    # 找出出现频率高的异常时间点
    common_times = [{'time_range': f"{t}-{t+2}s", 'file_count': count} 
                   for t, count in anomaly_times.items() if count >= 3]
    stats['common_anomaly_times'] = sorted(common_times, key=lambda x: x['file_count'], reverse=True)[:5]
    
    return stats

def analyze_time_patterns(all_files):
    """分析时间模式"""
    
    patterns = {
        'by_timestamp': defaultdict(list),
        'by_ip': defaultdict(list),
        'by_device': defaultdict(list)
    }
    
    for file_detail in all_files:
        metadata = file_detail.get('metadata', {})
        mos_diff = file_detail.get('mos_diff', 0)
        
        # 按时间戳分组
        if metadata.get('timestamp'):
            date = metadata['timestamp'][:10]  # 提取日期部分
            patterns['by_timestamp'][date].append(mos_diff)
        
        # 按IP分组
        if metadata.get('ip_address'):
            patterns['by_ip'][metadata['ip_address']].append(mos_diff)
        
        # 按设备分组
        if metadata.get('device_code'):
            patterns['by_device'][metadata['device_code']].append(mos_diff)
    
    # 计算每组的平均质量
    result = {
        'timestamp_quality': {},
        'ip_quality': {},
        'device_quality': {}
    }
    
    for date, diffs in patterns['by_timestamp'].items():
        result['timestamp_quality'][date] = {
            'avg_mos_diff': float(np.mean(diffs)),
            'file_count': len(diffs),
            'quality_level': 'good' if np.mean(diffs) > 0 else 'poor'
        }
    
    for ip, diffs in patterns['by_ip'].items():
        result['ip_quality'][ip] = {
            'avg_mos_diff': float(np.mean(diffs)),
            'file_count': len(diffs),
            'quality_level': 'good' if np.mean(diffs) > 0 else 'poor'
        }
    
    for device, diffs in patterns['by_device'].items():
        result['device_quality'][device] = {
            'avg_mos_diff': float(np.mean(diffs)),
            'file_count': len(diffs),
            'quality_level': 'good' if np.mean(diffs) > 0 else 'poor'
        }
    
    return result

def detect_anomalies(worst_files):
    """检测异常模式"""
    
    anomalies = {
        'extreme_variability': [],
        'persistent_degradation': [],
        'multi_dimension_failure': []
    }
    
    for file_detail in worst_files:
        filename = file_detail['filename']
        frame_analysis = file_detail.get('frame_analysis', {})
        
        # 检测极端波动（高标准差）
        high_var_dims = []
        for dim, stats in frame_analysis.items():
            if stats.get('std', 0) > 0.3:  # 标准差阈值
                high_var_dims.append({
                    'dimension': dim,
                    'std': stats['std'],
                    'variability': stats.get('variability', 0)
                })
        
        if high_var_dims:
            anomalies['extreme_variability'].append({
                'filename': filename,
                'dimensions': high_var_dims
            })
        
        # 检测持续劣化（>70%帧低于基准）
        persistent_dims = []
        for dim, stats in frame_analysis.items():
            below_pct = stats.get('below_baseline_pct', 0)
            if below_pct > 70:
                persistent_dims.append({
                    'dimension': dim,
                    'below_pct': below_pct
                })
        
        if persistent_dims:
            anomalies['persistent_degradation'].append({
                'filename': filename,
                'dimensions': persistent_dims
            })
        
        # 检测多维度同时失败（>=3个维度>50%劣化）
        failed_dims = []
        for dim, stats in frame_analysis.items():
            below_pct = stats.get('below_baseline_pct', 0)
            if below_pct > 50:
                failed_dims.append(dim)
        
        if len(failed_dims) >= 3:
            anomalies['multi_dimension_failure'].append({
                'filename': filename,
                'failed_dimensions': failed_dims,
                'failure_count': len(failed_dims)
            })
    
    return anomalies

def format_deep_analysis_prompt(summary, deep_analysis):
    """格式化深度分析提示"""
    
    prompt = f"""# 音频质量深度数据分析任务

基于NISQA质量评估工具，我已提取了详尽的帧级数据、统计特征和时间模式，请您作为音频质量专家进行深度分析。

## 数据集概况

- **总文件数**: {summary['total_files']}
- **质量分布**: 良好{summary['quality_distribution']['good']}个, 中等劣化{summary['quality_distribution']['moderate']}个, 严重劣化{summary['quality_distribution']['severe']}个

---

## 第一部分：最差文件帧级详细分析

我提取了{len(deep_analysis['worst_files_detail'])}个质量最差文件的详细数据：

"""
    
    # 最差文件详情
    for i, file_detail in enumerate(deep_analysis['worst_files_detail'][:5], 1):
        prompt += f"""
### {i}. {file_detail['filename']}

**基本指标**:
- MOS文件级差值: {file_detail['mos_diff']:.3f}
- MOS低于基准帧占比: {file_detail['mos_below_pct']:.1f}%

**元数据解析**:
"""
        metadata = file_detail['metadata']
        if metadata.get('timestamp'):
            prompt += f"- 录制时间: {metadata['timestamp']}\n"
        if metadata.get('ip_address'):
            prompt += f"- 设备IP: {metadata['ip_address']}\n"
        if metadata.get('device_code'):
            prompt += f"- 设备代号: {metadata['device_code']}\n"
        
        prompt += "\n**帧级统计特征**:\n"
        for dim, stats in file_detail['frame_analysis'].items():
            prompt += f"- {dim}: 均值{stats['mean']:.3f}, 标准差{stats['std']:.3f}, 范围[{stats['min']:.3f}, {stats['max']:.3f}], 低于基准{stats.get('below_baseline_pct', 0):.1f}%\n"
        
        # 趋势
        if file_detail['trend_info']:
            prompt += "\n**质量趋势**:\n"
            for dim, trend in file_detail['trend_info'].items():
                prompt += f"- {dim}: {trend['description']} (斜率={trend['slope']:.4f})\n"
        
        # 异常帧
        if file_detail['anomaly_frames']:
            prompt += f"\n**检测到{len(file_detail['anomaly_frames'])}个质量突降点**:\n"
            for anomaly in file_detail['anomaly_frames'][:3]:
                prompt += f"- {anomaly['dimension']} 在 {anomaly['time']:.1f}秒处下降{anomaly['drop_value']:.3f}\n"
    
    # 跨文件统计
    prompt += f"""

---

## 第二部分：最差 vs 最好文件对比

维度平均差值对比（正值表示最好文件更优）:
"""
    
    comparison = deep_analysis['statistical_summary'].get('worst_vs_best_comparison', {})
    for dim, comp_data in comparison.items():
        prompt += f"- {dim}: 最差组={comp_data['worst_avg']:.3f}, 最好组={comp_data['best_avg']:.3f}, 差距={comp_data['gap']:.3f}\n"
    
    # 维度严重性排序
    prompt += "\n**维度问题严重性排序** (按平均劣化帧百分比):\n"
    for rank in deep_analysis['statistical_summary'].get('dimension_severity_ranking', []):
        prompt += f"{rank['dimension']}: {rank['avg_severity']:.1f}%  "
    
    # 共同异常时间
    common_anomalies = deep_analysis['statistical_summary'].get('common_anomaly_times', [])
    if common_anomalies:
        prompt += "\n\n**共同异常时间段** (多个文件在此时段同时质量下降):\n"
        for anomaly in common_anomalies:
            prompt += f"- {anomaly['time_range']}: {anomaly['file_count']}个文件出现异常\n"
    
    # 时间模式分析
    prompt += """

---

## 第三部分：时间、设备、网络模式分析

"""
    
    time_patterns = deep_analysis['time_series_patterns']
    
    # 按时间
    prompt += "**按录制日期统计**:\n"
    timestamp_quality = time_patterns.get('timestamp_quality', {})
    for date, info in sorted(timestamp_quality.items()):
        prompt += f"- {date}: {info['file_count']}个文件, 平均MOS差值={info['avg_mos_diff']:.3f}, 质量={info['quality_level']}\n"
    
    # 按IP
    prompt += "\n**按设备IP统计**:\n"
    ip_quality = time_patterns.get('ip_quality', {})
    for ip, info in sorted(ip_quality.items(), key=lambda x: x[1]['avg_mos_diff']):
        prompt += f"- {ip}: {info['file_count']}个文件, 平均MOS差值={info['avg_mos_diff']:.3f}, 质量={info['quality_level']}\n"
    
    # 按设备
    prompt += "\n**按设备类型统计**:\n"
    device_quality = time_patterns.get('device_quality', {})
    for device, info in sorted(device_quality.items(), key=lambda x: x[1]['avg_mos_diff']):
        prompt += f"- {device}: {info['file_count']}个文件, 平均MOS差值={info['avg_mos_diff']:.3f}, 质量={info['quality_level']}\n"
    
    # 异常模式检测
    prompt += """

---

## 第四部分：异常模式检测结果

"""
    
    anomalies = deep_analysis['anomaly_detection']
    
    # 极端波动
    extreme_var = anomalies.get('extreme_variability', [])
    if extreme_var:
        prompt += f"**极端波动文件** ({len(extreme_var)}个，标准差>0.3):\n"
        for item in extreme_var[:3]:
            dims = ', '.join([f"{d['dimension']}(std={d['std']:.3f})" for d in item['dimensions']])
            prompt += f"- {item['filename']}: {dims}\n"
    
    # 持续劣化
    persistent = anomalies.get('persistent_degradation', [])
    if persistent:
        prompt += f"\n**持续劣化文件** ({len(persistent)}个，>70%帧低于基准):\n"
        for item in persistent[:3]:
            dims = ', '.join([f"{d['dimension']}({d['below_pct']:.0f}%)" for d in item['dimensions']])
            prompt += f"- {item['filename']}: {dims}\n"
    
    # 多维度失败
    multi_fail = anomalies.get('multi_dimension_failure', [])
    if multi_fail:
        prompt += f"\n**多维度同时失败** ({len(multi_fail)}个，>=3维度>50%劣化):\n"
        for item in multi_fail[:3]:
            prompt += f"- {item['filename']}: {len(item['failed_dimensions'])}个维度失败 ({', '.join(item['failed_dimensions'])})\n"
    
    # 分析任务
    prompt += """

---

## 请您深度分析并回答：

### 1. 帧级数据洞察
- 从帧级统计特征（均值、标准差、范围、分位数）中，您发现了什么质量特征？
- 哪些文件的波动性（标准差/variability）最大？这反映了什么问题？
- 质量趋势分析中，"改善趋势"和"恶化趋势"分别意味着什么？

### 2. 维度相关性与优先级
- 五个维度（MOS/NOI/DIS/COL/LOUD）之间是否存在相关性？
- 哪个维度是"主导因素"（改善它对整体质量提升最大）？
- 为什么NOI（噪声）的问题最严重？

### 3. 时间、设备、网络模式深度解读
- 基于时间统计，哪个日期是"质量事故日"？可能发生了什么？
- 哪个IP地址的设备质量最差？应该如何排查？
- 不同设备代号（BOXP/BOXR/HF）之间的质量差异说明了什么？

### 4. 异常帧与突变点分析
- 多个文件在相同时间段出现异常，这是巧合还是系统性问题？
- 质量突降（sudden drops）最常发生在音频的哪个阶段（开头/中间/结尾）？
- 如何解释"持续劣化"与"极端波动"的区别和原因？

### 5. 根本原因假设与验证方案
- 基于所有数据，您对质量问题的根本原因有什么假设？
- 如何验证这些假设（需要收集哪些额外数据或日志）？
- 提出3-5个可立即执行的改进措施，按ROI排序。

### 6. 预测性维护建议
- 基于数据模式，如何预测下一次质量问题可能在何时何地发生？
- 应该建立哪些实时监控指标和告警阈值？

请提供专业、深入且基于数据的分析报告。
"""
    
    return prompt

def call_llm_for_deep_analysis(prompt, api_config):
    """调用LLM进行深度分析"""
    
    import requests
    
    api_key = api_config.get('api_key')
    model = api_config.get('model', 'deepseek-chat')
    base_url = api_config.get('base_url', 'https://api.deepseek.com/v1')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': '你是一位资深的音频质量分析专家，精通信号处理、统计分析和数据挖掘。你能够从复杂的帧级数据中发现深层模式，并提供可操作的技术洞察。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.7,
        'max_tokens': 8000  # 更长的输出
    }
    
    response = requests.post(
        f'{base_url}/chat/completions',
        headers=headers,
        json=data,
        timeout=180
    )
    
    response.raise_for_status()
    result = response.json()
    
    return result['choices'][0]['message']['content']

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='深度数据分析 - 使用LLM解读详细数据')
    parser.add_argument('--summary', default='quality_summary.json')
    parser.add_argument('--json-dir', default='.')
    parser.add_argument('--output', default='deep_data_analysis_report.md')
    parser.add_argument('--config', default='llm_config.json')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("NISQA质量深度数据分析 - LLM智能解读")
    print("=" * 80)
    
    # 加载和分析数据
    print("\n📊 正在加载并深度分析数据...")
    summary, deep_analysis = load_detailed_analysis_data(
        args.summary,
        args.json_dir,
        num_worst=15,
        num_best=10
    )
    
    # 格式化提示
    print("\n📝 正在准备深度分析提示...")
    prompt = format_deep_analysis_prompt(summary, deep_analysis)
    
    # 加载API配置
    print("\n🔧 正在加载LLM配置...")
    
    if not os.path.exists(args.config):
        print(f"\n❌ 错误: 配置文件不存在: {args.config}")
        return
    
    with open(args.config, 'r', encoding='utf-8') as f:
        api_config = json.load(f)
    
    print(f"  - 模型: {api_config.get('model')}")
    
    # 调用LLM
    print("\n🤖 正在调用LLM进行深度分析（这可能需要2-3分钟）...")
    
    try:
        analysis_report = call_llm_for_deep_analysis(prompt, api_config)
        
        # 组合完整报告
        full_report = f"""# NISQA音频质量深度数据分析报告

**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析工具**: NISQA + LLM深度数据分析
**分析模型**: {api_config.get('model')}
**数据集**: {summary['total_files']}个音频文件
**分析文件**: {len(deep_analysis['worst_files_detail'])}个最差 + {len(deep_analysis['best_files_detail'])}个最好

---

{analysis_report}

---

## 附录：数据来源说明

本报告基于以下详细数据：
1. **帧级统计**: 每个文件的5维度帧差值分布（均值、标准差、分位数、范围等）
2. **趋势分析**: 线性回归斜率、趋势类型（稳定/改善/恶化）
3. **异常检测**: 质量突降点、极端波动、持续劣化、多维度失败
4. **时间模式**: 按日期、IP地址、设备类型分组的质量统计
5. **跨文件对比**: 最差与最好文件的统计特征对比

### 数据文件
- 详细数据: baseline_compare_*.json (共{summary['total_files']}个)
- 可视化图表: baseline_compare_all.png, baseline_compare_heatmap.png
- 数据汇总: quality_summary.json

---
*本报告由NISQA质量评估工具结合大语言模型深度数据分析自动生成*
"""
        
        # 保存报告
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        print(f"\n✅ 深度分析报告已保存: {args.output}")
        
        print("\n" + "=" * 80)
        print("✅ 分析完成！")
        print(f"📄 完整报告: {args.output}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
