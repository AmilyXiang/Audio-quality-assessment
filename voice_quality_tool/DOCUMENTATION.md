# Voice Quality Analyzer - 完整文档

## 📋 目录

1. [功能概述](#功能概述)
2. [快速开始](#快速开始)
3. [核心功能](#核心功能)
4. [配置说明](#配置说明)
5. [API参考](#api参考)
6. [故障排查](#故障排查)

---

## 🎯 功能概述

语音质量诊断工具，专注通话体验问题的检测和定位。

### 检测能力

| 问题类型 | 检测方法 | 输出 |
|---------|---------|------|
| **噪声** | 零交叉率(ZCR) + RMS能量 + Spectral Rolloff | 噪声段时间/强度 |
| **卡顿** | 极低能量帧检测 | 静音/丢包时间点 |
| **音量波动** | 短时RMS剧烈变化 | 异常波动段 |
| **变声/失真** | 频谱中心/带宽/流量 + Peak-to-Peak | 音色突变点 |
| **对比分析** | Cross-Correlation + DTW对齐 + 差分 | 逐帧质量差 |

---

## 🚀 快速开始

### 1. 安装

```bash
cd voice_quality_tool
pip install -r requirements.txt
```

**核心依赖：**
- numpy >= 1.21.0（数组计算）
- scipy >= 1.7.0（信号处理）
- matplotlib >= 3.3.0（可视化）
- librosa >= 0.9.0（MFCC提取，可选）
- dtw-python >= 1.3.0（动态时间规整，可选）

### 2. 基础分析

```bash
# 分析单个文件
python analyze_file.py audio.wav -o report.json

# 实时麦克风分析
python analyze_mic.py 30  # 录音30秒

# 对比分析（测试音 vs 基准音）
python analyze_comparison.py test.wav baseline.wav -o comparison.json
```

### 3. 设备校准

```bash
# 生成设备专用配置
python calibrate.py clean_speech.wav -o device.json

# 使用设备配置分析
python analyze_file.py noisy_audio.wav -p device.json
```

---

## 🔧 核心功能

### 功能1：离线分析

**命令：**
```bash
python analyze_file.py <audio_file> [options]
```

**选项：**
- `-p, --profile <file>` - 使用设备配置文件
- `-o, --output <file>` - 保存JSON报告
- `--plot <file>` - 生成可视化图表
- `-v, --verbose` - 详细输出

**示例输出：**
```json
{
  "metadata": {
    "duration": 15.5,
    "sample_rate": 48000,
    "n_frames": 1550
  },
  "events": {
    "noise": [
      {"start": 2.3, "end": 3.7, "severity": "high"}
    ],
    "dropout": [
      {"start": 8.1, "end": 8.3, "severity": "medium"}
    ],
    "volume_fluctuation": [],
    "voice_distortion": [
      {"start": 12.5, "end": 13.0, "severity": "high"}
    ]
  }
}
```

### 功能2：实时监测

**命令：**
```bash
python analyze_mic.py [duration]
```

**适用场景：**
- 通话质量实时监控
- 设备性能测试
- 现场问题诊断

### 功能3：对比分析（NEW）

**流程：**
1. **粗对齐** - Cross-Correlation检测时间偏移
2. **精对齐** - MFCC + DTW处理语速差异（可选）
3. **差分计算** - 逐帧"测试值 - 基准值"
4. **异常检测** - 识别超过阈值(均值±2σ)的帧

**命令：**
```bash
python analyze_comparison.py test.wav baseline.wav -o result.json --plot
```

**输出结构：**
```json
{
  "metadata": {...},
  "alignment": {
    "coarse_offset_sec": -0.5,
    "coarse_confidence": 0.85
  },
  "differential_statistics": {
    "rms_diff": {"mean": -0.002, "std": 0.015, ...},
    "zero_crossing_rate_diff": {...},
    "spectral_centroid_diff": {...}
  },
  "anomaly_detection": {
    "rms_diff": {
      "anomaly_count": 45,
      "anomaly_ratio": 0.03,
      "anomaly_segments": [...]
    }
  }
}
```

### 功能4：设备校准

**目的：** 为特定录音设备生成自适应阈值

**命令：**
```bash
python calibrate.py baseline.wav -o device.json
```

**生成参数：**
- 噪声基线（RMS, ZCR）
- 语音特征范围（Spectral Centroid/Bandwidth）
- 动态阈值（P95, 标准差）

**使用校准配置：**
```bash
python analyze_file.py test.wav -p device.json
```

---

## ⚙️ 配置说明

### 预设配置

**1. CLEAN_SPEECH_CONFIG（清晰语音）**
```python
{
    'noise': {
        'zcr_threshold': 0.2,
        'rms_threshold': 0.02
    },
    'dropout': {
        'energy_threshold': 0.001,
        'min_duration': 0.1
    },
    'volume_fluctuation': {
        'rms_std_threshold': 0.15
    },
    'voice_distortion': {
        'spectral_centroid_change_threshold': 500,
        'spectral_flux_threshold': 0.5
    }
}
```

**2. NOISY_ENV_CONFIG（噪声环境）**
- 噪声阈值放宽（ZCR: 0.35, RMS: 0.05）
- 卡顿检测更敏感（能量: 0.002）

**3. MOBILE_CALL_CONFIG（移动通话）**
- 适配8kHz采样率
- 检测网络丢包（卡顿: 0.05s）

### 手动调整阈值

```python
from analyzer.analyzer import Analyzer

custom_config = {
    'noise': {'zcr_threshold': 0.25},  # 降低噪声敏感度
    'dropout': {'energy_threshold': 0.0005}  # 提高卡顿敏感度
}

analyzer = Analyzer(config=custom_config)
result = analyzer.analyze_file('audio.wav')
```

---

## 📊 检测原理

### 音频特征（9项）

| 特征 | 计算公式 | 物理意义 | 典型范围 |
|------|---------|---------|---------|
| **RMS** | √(Σx²/N) | 能量/音量 | 0.01-0.5 |
| **Zero Crossing Rate** | 符号变化/总样本 | 噪声/高频成分 | 0.05-0.3 |
| **Spectral Centroid** | Σ(f·A)/ΣA | 频谱重心/音色 | 500-3000 Hz |
| **Spectral Bandwidth** | √(Σ(f-fc)²·A/ΣA) | 频谱分散度 | 500-2000 Hz |
| **Spectral Flux** | Σ\|(S[t]-S[t-1])\| | 频谱变化率/抖动 | 0.01-0.5 |
| **Peak-to-Peak** | max(x) - min(x) | 削波/峰值 | 0-2.0 |
| **Spectral Rolloff** | 85%能量点频率 | 风噪/高频能量 | 2000-8000 Hz |
| **RMS P95** | RMS的95分位数 | 瞬态检测 | 0.05-0.8 |
| **MFCC** | Mel倒谱系数 | 音色指纹（13/20维） | - |

### 检测逻辑

**噪声检测：**
```
IF (ZCR > 阈值 OR RMS变化率 > 阈值 OR Spectral Rolloff > 3000 Hz)
   → 标记为噪声段
```

**卡顿检测：**
```
IF (RMS < 能量阈值 AND 持续时间 > 最小持续时长)
   → 标记为卡顿
```

**音量波动：**
```
IF (RMS标准差 > 阈值 AND 短时变化 > 2倍标准差)
   → 标记为异常波动
```

**变声/失真：**
```
IF (|Spectral Centroid变化| > 500 Hz 
    OR Peak-to-Peak > 1.8 
    OR Spectral Flux > 0.5)
   → 标记为失真
```

---

## 🔌 API参考

### Python集成

```python
from analyzer.analyzer import Analyzer
from analyzer.features import extract_features
from analyzer.frame import split_into_frames

# 1. 基础分析
analyzer = Analyzer()
result = analyzer.analyze_file('audio.wav')

for event in result.events['noise']:
    print(f"噪声: {event['start']:.2f}s - {event['end']:.2f}s")

# 2. 自定义配置
config = {
    'frame_length': 2048,
    'hop_length': 512,
    'noise': {'zcr_threshold': 0.3}
}
analyzer = Analyzer(config=config)

# 3. 对比分析
from analyze_comparison import analyze_comparison

result = analyze_comparison(
    test_path='test.wav',
    baseline_path='baseline.wav',
    enable_alignment=True
)

# 查看差分统计
stats = result['differential_statistics']
print(f"平均RMS差: {stats['rms_diff']['mean']:.6f}")

# 查看异常段
anomalies = result['anomaly_detection']['rms_diff']
print(f"异常帧数: {anomalies['anomaly_count']}")
```

### 命令行集成

```bash
# Shell脚本批量分析
for file in *.wav; do
    python analyze_file.py "$file" -o "${file%.wav}_report.json"
done

# 使用返回码判断质量
python analyze_file.py audio.wav && echo "质量正常" || echo "检测到问题"
```

---

## 🛠️ 故障排查

### 常见问题

**1. 误报噪声（安静环境被标记为噪声）**
- **原因：** 设备底噪高于默认阈值
- **解决：** 
  ```bash
  python calibrate.py clean_baseline.wav -o device.json
  python analyze_file.py test.wav -p device.json
  ```

**2. 漏检卡顿（明显断音未检测）**
- **原因：** 能量阈值过低
- **解决：** 调高 `dropout.energy_threshold` 或减小 `min_duration`
  ```python
  config = {'dropout': {'energy_threshold': 0.002, 'min_duration': 0.05}}
  ```

**3. 对齐失败（偏移检测不准）**
- **原因：** 音频内容差异大或信噪比低
- **解决：** 
  - 启用DTW精对齐: 安装 `librosa` 和 `dtw-python`
  - 手动指定偏移: 修改 `alignment.py` 中的 `max_shift` 参数

**4. 内存溢出（长音频分析）**
- **原因：** 一次性加载全部音频
- **解决：** 分段处理或调整帧参数
  ```python
  config = {'frame_length': 1024, 'hop_length': 256}  # 减少帧数
  ```

**5. librosa/dtw未安装警告**
- **影响：** 无法使用MFCC和DTW精对齐
- **解决：** 
  ```bash
  pip install librosa dtw-python
  ```

### 调试技巧

**1. 查看中间特征：**
```python
from analyzer.features import extract_features
from analyzer.frame import Frame

frames = split_into_frames(audio_data, sr)
for i, frame in enumerate(frames[:5]):
    features = extract_features(frame)
    print(f"帧{i}: RMS={features.rms:.4f}, ZCR={features.zero_crossing_rate:.4f}")
```

**2. 可视化特征时间序列：**
```bash
python analyze_comparison.py test.wav baseline.wav --plot comparison.png
```

**3. 启用详细日志：**
```bash
python analyze_file.py audio.wav -v
```

---

## 📚 进阶主题

### 批量分析

```python
import glob
import json
from analyzer.analyzer import Analyzer

analyzer = Analyzer()
results = {}

for audio_path in glob.glob('audio_samples/*.wav'):
    result = analyzer.analyze_file(audio_path)
    results[audio_path] = {
        'noise_count': len(result.events['noise']),
        'dropout_count': len(result.events['dropout']),
        'quality_score': result.summary.get('quality_score', 0)
    }

with open('batch_report.json', 'w') as f:
    json.dump(results, f, indent=2)
```

### 实时流处理

```python
import pyaudio
from analyzer.analyzer import Analyzer
from analyzer.frame import Frame

analyzer = Analyzer()
p = pyaudio.PyAudio()

def callback(in_data, frame_count, time_info, status):
    audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
    frame = Frame(audio, 0, len(audio), 16000)
    
    features = extract_features(frame)
    if features.zero_crossing_rate > 0.3:
        print(f"[警告] 检测到噪声: ZCR={features.zero_crossing_rate:.3f}")
    
    return (in_data, pyaudio.paContinue)

stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                input=True, stream_callback=callback)
stream.start_stream()
```

### 自定义检测器

```python
from analyzer.detectors.base import BaseDetector

class CustomDetector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
        self.threshold = config.get('threshold', 0.5)
    
    def detect(self, features, frame_index, time):
        if features.rms > self.threshold:
            return {
                'start': time,
                'end': time + 0.01,
                'severity': 'high',
                'value': features.rms
            }
        return None
```

---

## 📖 参考资料

**核心文档：**
- `docs/DETECTION_PRINCIPLES.md` - 检测原理详解
- `docs/CLEAN_SPEECH_CONFIG.md` - 配置预设说明

**示例代码：**
- `examples/demo_dropout_detection.py` - 卡顿检测示例
- `examples/analyze_clean_speech.py` - 清晰语音分析

**架构设计：**
- 检测器位于 `analyzer/detectors/` 目录
- 特征提取 `analyzer/features.py`
- 帧处理 `analyzer/frame.py`

---

## 📞 支持

遇到问题请查阅：
1. 本文档的[故障排查](#故障排查)章节
2. `docs/DETECTION_PRINCIPLES.md` 中的原理说明
3. 运行 `python <script>.py --help` 查看命令帮助

---

**版本：** 2.0 (含对齐对比功能)  
**更新日期：** 2026-02-06
