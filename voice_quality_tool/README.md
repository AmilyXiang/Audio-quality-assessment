# Voice Quality Analyzer Tool

一个**语音质量诊断工具**，专注于通话体验问题的检测和定位。

## 功能概述

### 检测能力

1. **噪声问题** (Noise)
   - 背景噪声持续偏高
   - 突发噪声（爆音、底噪突增）
   - 使用零交叉率(ZCR)和RMS能量变化检测

2. **卡顿/断续** (Dropout)
   - 短时静音（音频drop）
   - 网络丢包导致的断断续续
   - 检测极低能量帧

3. **音量起伏异常** (Volume Fluctuation)
   - 音量忽大忽小
   - 自动增益(AGC)异常导致的pumping
   - 检测短时RMS的剧烈波动

4. **变声** (Voice Distortion) ⭐ 重点
   - 声音突然变尖/变闷
   - 编码/丢包导致的频谱断裂
   - 回声消除异常
   - 使用频谱中心、频谱带宽、频谱流量检测

## 安装

### 依赖

- Python 3.7+
- numpy >= 1.21.0
- scipy >= 1.7.0
- pyaudio >= 0.2.11 (for real-time microphone)

### 快速安装

```bash
cd voice_quality_tool
pip install -r requirements.txt
```

## 使用

### 离线分析（文件）

分析单个音频文件并生成诊断报告：

```bash
python analyze_file.py path/to/audio.wav
```

保存结果为JSON：

```bash
python analyze_file.py path/to/audio.wav --output results.json
```

**输出格式（离线）：**
```json
{
  "noise": {
    "count": 2,
    "events": [
      {"start": 12.35, "end": 13.10},
      {"start": 28.02, "end": 28.60}
    ]
  },
  "dropout": {
    "count": 1,
    "events": [
      {"start": 45.80, "end": 46.40}
    ]
  },
  "volume_fluctuation": {
    "count": 0,
    "events": []
  },
  "voice_distortion": {
    "count": 1,
    "events": [
      {"start": 15.20, "end": 15.90}
    ]
  }
}
```

### 实时分析（麦克风）

从麦克风实时录制并分析（默认10秒）：

```bash
python analyze_mic.py
```

自定义时长（秒）：

```bash
python analyze_mic.py 30
```

**输出格式（实时）：**
```json
[
  {
    "type": "dropout",
    "start": 14.32,
    "end": 14.52,
    "confidence": 0.85
  },
  {
    "type": "noise",
    "start": 20.10,
    "end": 21.50,
    "confidence": 0.72
  }
]
```

## 项目结构

```
voice_quality_tool/
├── analyze_file.py          # 离线分析入口
├── analyze_mic.py           # 实时麦克风入口
├── requirements.txt         # Python依赖
└── analyzer/
    ├── __init__.py
    ├── analyzer.py          # 核心分析器（调度器）
    ├── frame.py             # 帧切分与时间轴管理
    ├── features.py          # 特征提取（RMS、频谱等）
    ├── result.py            # 事件聚合与报告生成
    └── detectors/
        ├── __init__.py
        ├── base.py          # 基础检测器类
        ├── noise.py         # 噪声检测
        ├── dropout.py       # 卡顿检测
        ├── volume.py        # 音量起伏检测
        └── distortion.py    # 变声检测
```

## 技术细节

### 特征提取

- **RMS**: 帧能量
- **Spectral Centroid**: 频谱中心（音色高低）
- **Spectral Bandwidth**: 频谱带宽（音色宽度）
- **Zero Crossing Rate (ZCR)**: 零交叉率（噪声指示）
- **Spectral Flux**: 帧间频谱变化（失真检测）

### 参数配置

在 `analyzer.py` 的 `DEFAULT_CONFIG` 中调整阈值：

```python
DEFAULT_CONFIG = {
    "noise_zcr_threshold": 0.15,           # ZCR阈值（越高越噪声）
    "burst_spike_threshold": 0.3,          # 爆音增长率
    "silence_rms_threshold": 0.01,         # 静音RMS阈值
    "rms_change_threshold": 0.4,           # RMS变化率（AGC检测）
    "spectral_flux_threshold": 0.2,        # 频谱变化幅度
    "centroid_shift_threshold": 500.0,     # Hz 频谱中心偏移
    "bandwidth_spike_threshold": 1.5,      # 带宽尖峰比例
}
```

## 常见问题

### Q: 为什么没有检测到噪声？
A: 调整 `noise_zcr_threshold` 和 `burst_spike_threshold`。背景噪声较低的环境需要更敏感的设置。

### Q: 可以分析实时流吗？
A: 支持麦克风输入。若要支持网络流（如VoIP），修改 `frame_generator()` 适配流协议。

### Q: 离线和实时模式的检测逻辑一样吗？
A: **完全相同**。只有时间参考不同（文件时间轴 vs 实时时间戳）。

## 许可证

MIT License

## 支持

问题或建议请提交 Issue。
