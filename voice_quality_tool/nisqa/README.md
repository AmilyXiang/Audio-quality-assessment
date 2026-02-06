# NISQA 感知质量分析工具

基于深度学习的语音质量评估，使用 [NISQA](https://github.com/gabrielmittag/NISQA) 模型进行帧级时序分析。

## 功能特点

- **MOS评分** (1-5分)：Mean Opinion Score，模拟人类主观感知
- **多维度分析**：
  - NOI (Noisiness): 噪声程度
  - DIS (Discontinuity): 不连续性/卡顿
  - COL (Coloration): 音色失真
  - LOUD (Loudness): 响度适中性
- **帧级时序分析**：0.5秒精度的质量变化追踪
- **可视化输出**：五维度时序曲线图

## 快速开始

### 1. 下载模型（首次使用）

```bash
# 自动下载NISQA预训练模型（~100MB）
python download_nisqa_model.py

# 或手动下载：
# https://github.com/gabrielmittag/NISQA/releases
# 将 nisqa.tar 放到 weights/ 目录
```

### 2. 帧级时序分析（推荐）

```bash
# 使用默认最优配置（15s窗口，0.5s跳跃）
python analyze_nisqa_framewise.py --audio ../path/to/audio.wav --model weights/nisqa.tar --plot
```

**输出**：
- `framewise_<filename>.png` - 五维度时序曲线图
- `framewise_<filename>.json` - 详细帧级数据

### 3. 标准文件级分析

```bash
# 仅获取整体质量评分
python analyze_nisqa.py --audio ../path/to/audio.wav --model weights/nisqa.tar
```

## 文件说明

| 文件 | 功能 | 推荐度 |
|------|------|--------|
| `analyze_nisqa_framewise.py` | 帧级时序分析，支持问题定位 | ⭐⭐⭐⭐⭐ |
| `analyze_nisqa.py` | 标准NISQA分析，仅文件级评分 | ⭐⭐⭐ |
| `nisqa_full_analysis.py` | 完整分析（包含所有模式） | ⭐⭐⭐⭐ |
| `download_nisqa_model.py` | 模型下载工具 | 🔧 |

## 配置参数

### 窗口长度 (seg_length)

| 配置 | 帧数 | 精度 | 推荐度 |
|------|------|------|--------|
| **15s** (默认) | 28 | 最高 | ⭐⭐⭐⭐⭐ |
| 13s | 32 | -1.6% | ⭐⭐⭐⭐ |
| 11s | 36 | -6.7% | ⭐⭐ |

**说明**：NISQA模型在15秒窗口上训练，偏离此窗口会降低准确性。

### 跳跃步长 (hop_length)

| 配置 | 时间分辨率 | 推荐场景 |
|------|-----------|---------|
| **0.5s** (默认) | 高分辨率 | 质量问题定位 |
| 1.0s | 标准分辨率 | 快速概览 |
| 0.25s | 极高分辨率 | 细粒度分析（计算量大） |

## 示例输出

### 控制台

```
File-Level Quality (Aggregated):
  MOS:        4.54  ← 总体质量优秀
  Noisiness:  4.30  ← 噪声低
  Distortion: 4.48  ← 几乎无失真
  Coloration: 4.33  ← 音色自然
  Loudness:   4.50  ← 响度适中

Frame-Level Quality (28 frames):
  Frame 1 [0.0s - 15.0s]: MOS: 4.64
  Frame 2 [0.5s - 15.5s]: MOS: 4.62
  ...
  Frame 27 [13.0s - 28.0s]: MOS: 1.85  ← 检测到质量下降
```

### JSON

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
    "frames": [...]
  }
}
```

## 质量评分参考

| MOS范围 | 质量等级 | 描述 |
|---------|---------|------|
| 4.5-5.0 | 优秀 (Excellent) | 几乎完美 |
| 4.0-4.5 | 良好 (Good) | 高质量 |
| 3.0-4.0 | 中等 (Fair) | 可接受 |
| 2.0-3.0 | 差 (Poor) | 明显问题 |
| 1.0-2.0 | 极差 (Bad) | 严重劣化 |

## 问题诊断

### 多维度指标解读

- **NOI < 3.0**: 背景噪声问题或录音设备干扰
- **DIS < 3.0**: 网络丢包、卡顿、断续
- **COL < 3.0**: 编解码失真、合成音特征、音色异常
- **LOUD < 3.0**: 音量过大/过小、增益设置不当

### 滑动窗口定位法

通过连续帧的MOS变化定位问题时间段：

```
Frame N   [t - t+15s]    MOS: 4.5
Frame N+1 [t+0.5 - t+15.5s]  MOS: 3.2  ← 下降
Frame N+2 [t+1.0 - t+16.0s]  MOS: 2.8  ← 继续下降

结论：新增段 [t+15s - t+16s] 质量恶化
```

每个帧有96.7%的内容与前一帧重叠，差异仅为0.5秒的新增段。MOS变化即可反映新增段的质量。

## 注意事项

1. **首次运行需下载模型**（~100MB）
2. **模型和第三方库不在Git仓库**，需本地下载
3. **输出文件（.png/.json）不应提交到版本控制**
4. 推荐使用默认15s/0.5s配置以获得最佳精度

## 技术细节

- 模型：NISQA (Non-Intrusive Speech Quality Assessment)
- 训练窗口：15秒
- 采样率支持：8kHz - 48kHz
- 输入格式：WAV（需librosa支持的格式）
- Mel频谱参数：n_fft=4096, n_mels=48, hop_length=0.01s

## 参考资料

- [NISQA GitHub](https://github.com/gabrielmittag/NISQA)
- [NISQA论文](https://arxiv.org/abs/2104.09494)
- [ITU-T P.863 (POLQA)](https://www.itu.int/rec/T-REC-P.863)
