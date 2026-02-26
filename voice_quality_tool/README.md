# Voice Quality Analyzer Tool

一个**语音质量诊断工具**，专注于通话体验问题的检测和定位。

## 功能概述

### 检测能力

#### 1. 离散事件检测（基于音频特征）

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

#### 2. NISQA 感知质量评估（基于深度学习）⭐ 新增

使用 [NISQA](https://github.com/gabrielmittag/NISQA) 深度学习模型进行**帧级时序质量分析**：

**核心功能**：
- **MOS评分** (Mean Opinion Score 1-5)：整体质量
- **多维度分析**：
  - NOI (Noisiness): 噪声程度
  - DIS (Discontinuity): 不连续性/卡顿
  - COL (Coloration): 音色失真
  - LOUD (Loudness): 响度适中性

**分析模式**：
- **文件级评分**：整个音频的聚合质量
- **帧级时序分析**：每0.5秒一个采样点，定位问题时间段
- **可视化输出**：生成MOS/NOI/DIS/COL/LOUD时序曲线图

**默认配置（已优化）**：
- 窗口长度：15s（匹配NISQA训练数据）
- 跳跃步长：0.5s（高分辨率时间采样）
- 输出约28帧（对于30秒音频）

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

### NISQA 感知质量分析 ⭐

#### 1. 首次使用 - 下载模型

```bash
# 下载NISQA预训练模型（~100MB）
python nisqa/download_nisqa_model.py

# 或手动下载：
# 从 https://github.com/gabrielmittag/NISQA/releases 下载 nisqa.tar
# 放到 voice_quality_tool/nisqa/weights/ 目录
```

#### 2. 帧级时序分析（推荐）

```bash
# 使用默认配置（15s窗口，0.5s跳跃，最优配置）
python nisqa/analyze_nisqa_framewise.py --audio audio.wav --model nisqa/weights/nisqa.tar --plot

# 自定义窗口配置（不推荐修改）
python nisqa/analyze_nisqa_framewise.py --audio audio.wav --model nisqa/weights/nisqa.tar --seg_length 15 --hop_length 0.5 --plot
```

**输出文件**：
- `nisqa/framewise_<filename>.png`：五维度时序曲线图（MOS/NOI/DIS/COL/LOUD）
- `nisqa/framewise_<filename>.json`：详细帧级数据

**示例输出（控制台）**：
```
File-Level Quality (Aggregated):
  MOS:        4.54  ← 总体质量接近完美(5分制)
  Noisiness:  4.30  ← 几乎无噪声
  Distortion: 4.48  ← 几乎无不连续
  Coloration: 4.33  ← 音色自然
  Loudness:   4.50  ← 响度适中

Frame-Level Quality (Temporal Segments):
  Total frames: 28
  Segment length: 15.0 seconds (0.5s hop)
  
  Frame 1 [0.0s - 15.0s]:
    MOS: 4.64  |  NOI: 2.53  |  DIS: 4.54  |  COL: 4.47  |  LOUD: 4.56
  Frame 2 [0.5s - 15.5s]:
    MOS: 4.62  |  NOI: 2.39  |  DIS: 4.54  |  COL: 4.40  |  LOUD: 4.60
  ...
  Frame 27 [13.0s - 28.0s]:
    MOS: 1.85  |  NOI: 1.86  |  DIS: 3.11  |  COL: 2.02  |  LOUD: 2.71
    ↑ 检测到质量下降：最后3秒质量劣化
```

**JSON输出格式**：
```json
{
  "audio_file": "audio.wav",
  "file_level": {
    "mos": 4.541,
    "noi": 4.301,
    "dis": 4.481,
    "col": 4.331,
    "loud": 4.501
  },
  "frame_level": {
    "total_frames": 28,
    "seg_length": 15.0,
    "hop_length": 0.5,
    "frames": [
      {
        "frame_id": 0,
        "time_start": 0.0,
        "time_end": 15.0,
        "mos": 4.636,
        "noi": 2.53,
        "dis": 4.54,
        "col": 4.47,
        "loud": 4.56
      },
      ...
    ]
  }
}
```

#### 3. 标准NISQA分析（仅文件级）

```bash
# 快速获取整体质量评分
python nisqa/analyze_nisqa.py --audio audio.wav --model nisqa/weights/nisqa.tar
```

#### 4. 基准对比分析（推荐批量问题定位）

```bash
# 使用基准文件对目录内测试音频做逐帧对比，并自动清理临时结果
python nisqa/analyze_nisqa_baseline_compare.py \
  --baseline ../robotic/1010baseline.wav \
  --test-dir ../robotic/tst \
  --model nisqa/weights/nisqa.tar \
  --clean
```

说明：
- 默认输出目录为测试录音所在目录；可通过 `--output_dir` 覆盖。
- `--clean` 会删除 `baseline_compare_*.png/.json` 临时文件，仅保留 `baseline_compare_all.*` 和 `baseline_compare_heatmap.*`。
- 生成 Excel 时默认文件名为 `result.xlsx`（可通过 `--excel-output` 覆盖）。
- 如需保留帧级中间数据，可加 `--keep-framewise`。

#### 配置说明

**窗口长度 (seg_length)**：
- **默认15s**（推荐）：匹配NISQA训练数据，评分最准确
- 13s：+12.5%帧数，-1.6%精度（可接受）
- 11s：+28.6%帧数，-6.7%精度（不推荐）
- ⚠️ 短于11s会显著降低准确性

**跳跃步长 (hop_length)**：
- **默认0.5s**（推荐）：高时间分辨率，28帧
- 1.0s：标准分辨率，14帧
- 0.25s：极高分辨率（计算量大）

#### 4. 问题定位方法

通过**滑动窗口差异分析**定位质量问题：

```
Frame N   [t1 - t1+15s]  MOS: 4.5
Frame N+1 [t1+0.5 - t1+15.5s]  MOS: 3.2  ← 下降
Frame N+2 [t1+1.0 - t1+16.0s]  MOS: 2.8  ← 继续下降

结论：新增段[t1+15s - t1+16s]质量恶化
精度：可定位到0.5秒级时间段
```

**多维度诊断**：
- NOI < 3.0：背景噪声/录音设备问题
- DIS < 3.0：网络丢包/卡顿
- COL < 3.0：编解码失真/合成音特征
- LOUD < 3.0：音量设置/增益问题

## 项目结构

```
voice_quality_tool/
├── analyze_file.py          # 离线分析入口
├── analyze_mic.py           # 实时麦克风入口
├── requirements.txt         # Python依赖
├── nisqa/                   # NISQA感知质量分析
│   ├── analyze_nisqa_framewise.py  # 帧级时序分析（推荐）
│   ├── analyze_nisqa.py            # 标准NISQA分析
│   ├── download_nisqa_model.py     # 模型下载工具
│   ├── nisqa_full_analysis.py      # 完整分析
│   ├── weights/                    # 模型权重（需下载）
│   └── nisqa_repo/                 # NISQA官方库（需下载）
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
