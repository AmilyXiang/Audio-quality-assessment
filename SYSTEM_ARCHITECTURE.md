# 🏗️ 语音质量检测系统 - 完整工作逻辑

**版本**: v2.0  
**日期**: 2026年1月27日  
**作者**: Audio Quality Assessment System

---

## 📖 目录

1. [系统概览](#系统概览)
2. [核心架构](#核心架构)
3. [数据流详解](#数据流详解)
4. [特征提取机制](#特征提取机制)
5. [检测器详解](#检测器详解)
6. [配置系统](#配置系统)
7. [完整执行流程](#完整执行流程)

---

## 系统概览

### 设计思想

这是一个**基于声学特征的规则引擎**，专门检测通话/VoIP音频中的质量问题。采用**分层检测 + 后处理**架构：

```
音频输入 → 帧切分 → 特征提取 → VAD过滤 → 多检测器并行 → 事件聚合 → 持续性过滤 → 输出报告
```

### 核心能力

| 检测类型 | 原理 | 典型场景 |
|---------|------|---------|
| **噪声** (Noise) | ZCR、RMS波动、频谱滚降 | 风噪、爆音、底噪突增 |
| **卡顿** (Dropout) | RMS极低 + ZCR极低 | 网络丢包、缓冲区欠流 |
| **音量起伏** (Volume Fluctuation) | RMS方向反转 | AGC失效泵动 |
| **变声/失真** (Distortion) | 频谱突变、削波 | 编码失真、回声消除错误 |

---

## 核心架构

### 1. 模块划分

```
voice_quality_tool/
│
├── analyze_file.py          # 入口1：离线分析（文件）
├── analyze_mic.py           # 入口2：实时分析（麦克风）
├── calibrate.py             # 入口3：设备校准
│
├── analyzer/                # 核心分析引擎
│   ├── analyzer.py          # 主调度器（协调所有检测器）
│   ├── features.py          # 特征提取（8个声学特征）
│   ├── frame.py             # 帧切分与时间线管理
│   ├── vad.py               # 语音活动检测（过滤非人声）
│   ├── result.py            # 结果聚合与输出
│   │
│   └── detectors/           # 检测器集合（插件式）
│       ├── base.py          # 基类 + 工具函数
│       ├── noise.py         # 噪声检测器
│       ├── dropout.py       # 卡顿检测器
│       ├── volume.py        # 音量波动检测器
│       ├── distortion.py    # 失真检测器
│       └── enhanced_distortion.py  # 增强失真检测（可选）
│
└── docs/                    # 技术文档
    ├── DETECTION_PRINCIPLES.md    # 检测原理详解
    └── CLEAN_SPEECH_CONFIG.md     # 配置预设
```

### 2. 类关系图

```
Analyzer (主调度器)
    │
    ├── FrameGenerator (帧生成器)
    │       └── Frame (数据容器)
    │
    ├── FeatureExtractor (特征提取)
    │       └── Features Dict (8个特征)
    │
    ├── VAD (语音活动检测)
    │
    ├── NoiseDetector ────┐
    ├── DropoutDetector ───┤
    ├── VolumeDetector ────┼── 继承 BaseDetector
    └── DistortionDetector ┘
            │
            └── DetectionEvent (事件对象)
                    │
                    └── AnalysisResult (聚合结果)
```

---

## 数据流详解

### 完整处理流程

```
┌─────────────────┐
│  音频文件输入    │ (audio.wav, 16kHz/44.1kHz)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 1. 音频加载      │ scipy.io.wavfile.read()
│    - 转单声道    │ 如果是立体声 → 只取左声道
│    - 归一化      │ 转换为 [-1, 1] 浮点数
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 帧切分        │ frame_generator()
│    帧大小: 25ms  │ frame_size = sample_rate * 0.025
│    跳跃: 10ms    │ hop_size = sample_rate * 0.010
│                  │ → 帧重叠率 60%
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 特征提取      │ extract_features(frame)
│    每帧提取8个   │ → Features Dict
│    声学特征      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. VAD过滤      │ is_voice_active(features)
│    判断是否人声  │ 基于 RMS + Centroid + ZCR
│    (可选)        │ → True/False
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 并行检测      │ 4个检测器同时运行
│    每个检测器    │ detector.detect(features, frame)
│    独立判断      │ → DetectionEvent / None
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 事件聚合      │ result.add_event(event)
│    收集所有事件  │ → List[DetectionEvent]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. 后处理        │ result.finalize()
│    - 合并相邻    │ gap < 150ms → 合并
│    - 过滤短事件  │ duration < min_duration → 删除
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 8. 输出报告      │ result.to_json() / print_summary()
│    JSON格式      │ {noise: {...}, dropout: {...}, ...}
└─────────────────┘
```

### 关键时间参数

| 参数 | 值 | 说明 |
|------|----|----|
| **帧大小** | 25ms | 足够短以捕捉瞬态，足够长以计算频谱 |
| **帧跳跃** | 10ms | 60%重叠，提高时间分辨率 |
| **合并间隔** | 150ms | 两个事件间隔<150ms视为同一问题 |
| **最小持续时间** | 50-600ms | 按问题类型差异化（见下） |

**差异化持续性阈值**（基于人耳感知研究）：
```python
min_event_duration = {
    "dropout": 0.05,              # 50ms - 最敏感
    "voice_distortion": 0.12,     # 120ms
    "noise": 0.15,                # 150ms
    "volume_fluctuation": 0.25,   # 250ms - 最不敏感
}
```

---

## 特征提取机制

### 核心特征（5个）

每帧提取以下5个基础特征：

#### 1. **RMS (Root Mean Square) - 能量**
```python
rms = sqrt(mean(samples^2))
```
- **用途**: 音量检测、静音检测
- **范围**: 0.0 ~ 1.0（归一化音频）
- **人声典型值**: 0.05 ~ 0.3

#### 2. **Zero Crossing Rate (ZCR) - 零交叉率**
```python
zcr = count(sign_change) / len(samples)
```
- **用途**: 区分噪声（高ZCR）vs 人声（中等ZCR）
- **范围**: 0.0 ~ 0.5
- **人声典型值**: 0.05 ~ 0.15
- **噪声典型值**: > 0.15

#### 3. **Spectral Centroid - 频谱质心**
```python
centroid = sum(frequencies * fft_magnitudes) / sum(fft_magnitudes)
```
- **用途**: 音色检测（尖锐/低沉）
- **范围**: 0 ~ sample_rate/2 (Hz)
- **人声典型值**: 200 ~ 2000 Hz
- **机械声**: > 3000 Hz

#### 4. **Spectral Bandwidth - 频谱带宽**
```python
bandwidth = sqrt(sum((freqs - centroid)^2 * fft) / sum(fft))
```
- **用途**: 检测频率分布异常
- **编码失真**: 带宽突然变窄

#### 5. **Spectral Flux - 频谱流量**
```python
flux = sqrt(sum((fft_current - fft_previous)^2))
```
- **用途**: 检测频谱突变（帧间变化）
- **用于**: 变声、编码失真、回声消除错误

### 第1阶段扩展特征（3个）

用于提高瞬态检测准确性：

#### 6. **Peak-to-Peak - 峰峰值**
```python
p2p = max(samples) - min(samples)
```
- **用途**: 削波检测（audio clipping）
- **阈值**: > 1.8 视为削波（满幅为2.0）

#### 7. **Spectral Rolloff - 频谱滚降**
```python
rolloff_freq = freq where 95% energy is below
```
- **用途**: 检测风噪、高频噪声
- **阈值**: > 3000 Hz 视为高频噪声

#### 8. **RMS Percentile (P95) - RMS 95分位数**
```python
rms_p95 = percentile(sub_frame_rms_list, 95)
```
- **用途**: 捕捉瞬态爆音（比均值更敏感）
- **优势**: 不被平均值掩盖

### 第2阶段特征（可选）

#### 9. **MFCC (Mel-Frequency Cepstral Coefficients)**
```python
mfcc = librosa.feature.mfcc(samples, sr, n_mfcc=13)
```
- **用途**: 音色特征、麦克风响应差异
- **依赖**: 需要 `librosa` 库
- **默认**: 禁用（减少依赖）

---

## 检测器详解

### 1. NoiseDetector（噪声检测器）

#### 检测原理

**方法1: 持久性背景噪声**（默认禁用）
```python
if zcr > 0.15:  # 高零交叉率
    → 报告噪声
```

**方法2: 突发噪声（爆音）**
```python
if (rms_increase > 30%) or (rms_p95 > rms * 1.5):
    → 报告爆音
```

**方法3: 风噪检测**
```python
if spectral_rolloff > 3000 Hz:  # 高频能量过多
    → 报告风噪
```

#### 配置参数
```python
{
    "detect_background_noise": False,  # 默认只检测突发噪声
    "noise_zcr_threshold": 0.15,
    "burst_spike_threshold": 0.3,      # RMS增幅>30%
    "spectral_rolloff_threshold": 3000,
}
```

#### 典型输出
```json
{
  "event_type": "noise",
  "start_time": 12.35,
  "end_time": 13.10,
  "confidence": 0.85,
  "details": {
    "reason": "noise_burst_with_transient",
    "rms_increase_ratio": 0.45,
    "rms_p95": 0.12
  }
}
```

---

### 2. DropoutDetector（卡顿检测器）

#### 检测原理

检测"有声 → 无声 → 有声"的突变（状态机）：

```python
is_silence = (rms < 0.01) and (zcr < 0.05)

if is_silence and not prev_is_silence:
    → 报告卡顿（边界触发）
```

**为什么只检测边界？**
- 持续静音 ≠ 卡顿（可能是说话者停顿）
- 卡顿 = 突然的、非预期的静音
- 只在**进入静音时**报告一次

#### 特殊处理

**不受VAD过滤**：
```python
# Dropout检测即使VAD=False也运行
dropout_event = self.dropout_detector.detect(
    features, frame, is_voice_active=voice_active
)
```
**原因**: 卡顿本身就是异常静音，不应被VAD过滤掉

#### 配置参数
```python
{
    "silence_rms_threshold": 0.01,     # 极低能量
    "dropout_zcr_threshold": 0.05,     # 极低零交叉率
    "min_event_duration": {"dropout": 0.05}  # 50ms
}
```

#### 典型输出
```json
{
  "event_type": "dropout",
  "start_time": 45.80,
  "end_time": 46.40,
  "confidence": 0.9,
  "details": {
    "reason": "sudden_silence_dropout",
    "rms": 0.003,
    "threshold": 0.01
  }
}
```

---

### 3. VolumeDetector（音量波动检测器）

#### 检测原理

**区分两种场景**：

1. **❌ 不检测：说话者切换**（单向变化）
   ```
   小 → 大 → 大  (持续上升)
   大 → 小 → 小  (持续下降)
   ```

2. **✅ 检测：AGC泵动**（方向反转）
   ```
   大 → 小 → 大  (泵动)
   小 → 大 → 小  (泵动)
   ```

**实现（方向反转检测）**：
```python
direction_change = (curr_rms - last_rms) * (last_rms - prev_rms)

if direction_change < 0:  # 方向反转
    → 报告AGC泵动
```

#### 配置参数
```python
{
    "rms_change_threshold": 0.5,  # 50%变化
    "min_event_duration": {"volume_fluctuation": 0.25}  # 250ms
}
```

#### 典型输出
```json
{
  "event_type": "volume_fluctuation",
  "start_time": 28.02,
  "end_time": 28.60,
  "confidence": 0.75,
  "details": {
    "reason": "agc_pumping",
    "rms_ratio": 1.8,
    "pattern": "direction_reversal"
  }
}
```

---

### 4. DistortionDetector（失真检测器）

#### 检测原理

**两种工作模式**：

**模式1: 基于校准基线**（推荐）
```python
if baseline存在:
    flux_ratio = current_flux / baseline_flux
    if flux_ratio > 2.0:  # 超过基线2倍
        → 报告频谱突变
    
    centroid_shift = |current_centroid - baseline_centroid|
    if centroid_shift > 500 Hz:
        → 报告音色变化
```

**模式2: 相邻帧对比**（兼容模式）
```python
else:
    if spectral_flux > 0.2:
        → 报告频谱突变
    
    if |centroid - prev_centroid| > 500:
        → 报告音色变化
```

**削波检测**（优先级最高）：
```python
if peak_to_peak > 1.8:  # 接近满幅2.0
    → 报告音频削波
```

#### 配置参数
```python
{
    "spectral_flux_threshold": 0.2,
    "centroid_shift_threshold": 500.0,  # Hz
    "bandwidth_spike_threshold": 1.5,
    "peak_to_peak_threshold": 1.8,
    "min_event_duration": {"voice_distortion": 0.12}  # 120ms
}
```

#### 典型输出
```json
{
  "event_type": "voice_distortion",
  "start_time": 15.20,
  "end_time": 15.90,
  "confidence": 0.88,
  "details": {
    "reason": "high_spectral_flux_vs_baseline",
    "spectral_flux": 0.45,
    "baseline_flux": 0.18,
    "flux_ratio": 2.5
  }
}
```

---

## 配置系统

### 默认配置（DEFAULT_CONFIG）

适用于**电话/VoIP质量**检测：

```python
DEFAULT_CONFIG = {
    # VAD
    "enable_vad": True,
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # 持续性阈值（差异化）
    "min_event_duration": {
        "noise": 0.15,              # 150ms
        "dropout": 0.05,            # 50ms
        "volume_fluctuation": 0.25, # 250ms
        "voice_distortion": 0.12,   # 120ms
    },
    
    # 噪声检测
    "detect_background_noise": False,
    "noise_zcr_threshold": 0.15,
    "burst_spike_threshold": 0.3,
    "spectral_rolloff_threshold": 3000,
    
    # 卡顿检测
    "silence_rms_threshold": 0.01,
    "dropout_zcr_threshold": 0.05,
    
    # 音量波动
    "rms_change_threshold": 0.5,
    
    # 失真检测
    "spectral_flux_threshold": 0.2,
    "centroid_shift_threshold": 500.0,
    "bandwidth_spike_threshold": 1.5,
    "peak_to_peak_threshold": 1.8,
}
```

### 干净语音配置（CLEAN_SPEECH_CONFIG）

适用于**录音室/播客**高质量音频（放宽4倍）：

```python
CLEAN_SPEECH_CONFIG = {
    **DEFAULT_CONFIG,
    "min_event_duration": {
        "noise": 0.60,              # 600ms（4倍）
        "dropout": 0.20,            # 200ms（4倍）
        "volume_fluctuation": 1.00, # 1000ms（4倍）
        "voice_distortion": 0.50,   # 500ms（4倍）
    },
    "spectral_rolloff_threshold": 4000,  # 提高
    "peak_to_peak_threshold": 1.9,       # 更严格
}
```

### 设备校准配置

通过 `calibrate.py` 生成：

```json
// device_profile.json
{
  "device_name": "AirPods Pro",
  "calibration_date": "2026-01-27",
  "baseline_stats": {
    "rms_mean": 0.08,
    "centroid_mean": 850.5,
    "spectral_flux_mean": 0.12,
    ...
  },
  "recommended_config": {
    "silence_rms_threshold": 0.015,  // 基于设备底噪
    "noise_zcr_threshold": 0.18,     // 基于环境噪声
    ...
  }
}
```

---

## 完整执行流程

### 离线分析（analyze_file.py）

```bash
python analyze_file.py audio.wav --output report.json
```

**执行步骤**：

1. **加载音频**
   ```python
   sample_rate, data = wavfile.read("audio.wav")
   data = data / (2**15)  # 归一化
   ```

2. **选择配置**
   ```python
   if mode == 'clean-speech':
       config = CLEAN_SPEECH_CONFIG
   else:
       config = DEFAULT_CONFIG
   ```

3. **可选：加载设备配置**
   ```python
   if profile_path:
       profile = json.load(profile_path)
       config.update(profile["recommended_config"])
   ```

4. **创建分析器**
   ```python
   analyzer = Analyzer(config=config)
   ```

5. **生成帧流**
   ```python
   frame_size = sample_rate * 0.025  # 25ms
   hop_size = sample_rate * 0.010     # 10ms
   frames = frame_generator(data, sample_rate, frame_size, hop_size)
   ```

6. **执行分析**
   ```python
   result = analyzer.analyze_frames(frames)
   ```
   内部循环：
   ```python
   for frame in frames:
       # 1. 提取特征
       features = extract_features(frame, prev_frame)
       
       # 2. VAD过滤
       voice_active = is_voice_active(features, config)
       
       # 3. 检测器运行
       for detector in [noise, dropout, volume, distortion]:
           event = detector.detect(features, frame, prev_features)
           if event:
               result.add_event(event)
   ```

7. **后处理**
   ```python
   result.finalize(min_duration_dict={...})
   # - 合并相邻事件（gap < 150ms）
   # - 过滤短事件（按类型差异化阈值）
   ```

8. **输出结果**
   ```python
   result.print_summary()  # 控制台
   result.to_json_string() # JSON格式
   ```

### 实时分析（analyze_mic.py）

```bash
python analyze_mic.py 10  # 录制10秒
```

**执行步骤**：

1. **初始化PyAudio**
   ```python
   p = pyaudio.PyAudio()
   stream = p.open(format=pyaudio.paInt16, 
                   channels=1, 
                   rate=16000, 
                   input=True)
   ```

2. **实时录制 + 分析**
   ```python
   for i in range(num_chunks):
       # 读取音频块（例如100ms）
       chunk = stream.read(chunk_size)
       
       # 转换为帧
       frame = Frame(samples=chunk, ...)
       
       # 提取特征
       features = extract_features(frame, prev_frame)
       
       # 检测
       for detector in detectors:
           event = detector.detect(features, frame)
           if event:
               print(f"[{event.start_time:.2f}s] {event.event_type}")
   ```

3. **实时输出**
   ```
   [2.35s] noise (burst)
   [5.80s] dropout (silence)
   [8.02s] volume_fluctuation (agc_pumping)
   ```

### 设备校准（calibrate.py）

```bash
python calibrate.py baseline.wav --output device_profile.json
```

**执行步骤**：

1. **加载基线音频**（干净的人声样本）
   ```python
   baseline_audio = load_audio("baseline.wav")
   ```

2. **提取所有帧特征**
   ```python
   frames = frame_generator(baseline_audio, ...)
   all_features = [extract_features(f) for f in frames]
   ```

3. **计算统计信息**
   ```python
   baseline = compute_baseline_stats(all_features)
   # 包含：mean, std, percentiles for all features
   ```

4. **生成推荐阈值**
   ```python
   recommended_config = {
       "silence_rms_threshold": baseline["rms_p10"] * 0.5,
       "noise_zcr_threshold": baseline["zcr_mean"] + 2*baseline["zcr_std"],
       ...
   }
   ```

5. **保存配置**
   ```python
   json.dump({
       "baseline_stats": baseline,
       "recommended_config": recommended_config
   }, file)
   ```

---

## VAD（语音活动检测）详解

### 作用

过滤掉**非人声段落**（背景噪音、静音），避免误报。

### 判断逻辑

综合3个特征投票（至少满足2个）：

```python
def is_voice_active(features, config) -> bool:
    rms = features["rms"]
    centroid = features["spectral_centroid"]
    zcr = features["zero_crossing_rate"]
    
    # 条件1: 能量在合理范围
    rms_ok = 0.02 < rms < 1.0
    
    # 条件2: 频谱中心在人声频段
    centroid_ok = 80 < centroid < 3000  # Hz
    
    # 条件3: 零交叉率适中
    zcr_ok = 0.03 < zcr < 0.18
    
    # 投票：至少2个条件满足
    vote_count = sum([rms_ok, centroid_ok, zcr_ok])
    return vote_count >= 2
```

### 特殊处理

**Dropout检测器不受VAD限制**：
```python
# 即使VAD=False，也检测dropout
dropout_event = self.dropout_detector.detect(
    features, frame, is_voice_active=voice_active
)

# 其他检测器受VAD限制
if not voice_active:
    continue  # 跳过非人声段
```

**原因**: 卡顿本身就是异常的无声/静音，不应被VAD过滤。

---

## 后处理机制

### 1. 合并相邻事件

```python
def merge_adjacent_events(events, gap_threshold=0.15):
    """
    如果两个事件间隔 < 150ms，视为同一问题
    """
    merged = []
    for event in sorted(events, key=lambda e: e.start_time):
        if merged and event.start_time - merged[-1].end_time < 0.15:
            # 合并：扩展end_time
            merged[-1].end_time = max(merged[-1].end_time, event.end_time)
        else:
            merged.append(event)
    return merged
```

**示例**：
```
原始事件:
  [12.30s - 12.45s] noise
  [12.50s - 12.65s] noise  ← 间隔50ms

合并后:
  [12.30s - 12.65s] noise
```

### 2. 过滤短事件

```python
def filter_short_events(events, min_duration_dict):
    """
    根据问题类型使用不同的最小持续时间
    """
    filtered = []
    for event in events:
        min_dur = min_duration_dict.get(event.event_type, 0.3)
        if event.duration >= min_dur:
            filtered.append(event)
    return filtered
```

**示例**（dropout: 50ms阈值）：
```
原始事件:
  [5.20s - 5.24s] dropout  ← 40ms (太短)
  [5.80s - 5.92s] dropout  ← 120ms (保留)

过滤后:
  [5.80s - 5.92s] dropout
```

---

## 输出格式

### JSON输出

```json
{
  "noise": {
    "count": 2,
    "events": [
      {
        "start": 12.35,
        "end": 13.10,
        "confidence": 0.85,
        "details": {
          "reason": "noise_burst_with_transient",
          "rms_increase_ratio": 0.45
        }
      },
      {
        "start": 28.02,
        "end": 28.60,
        "confidence": 0.72,
        "details": {
          "reason": "high_frequency_noise_windnoise",
          "spectral_rolloff": 3500.5
        }
      }
    ]
  },
  "dropout": {
    "count": 1,
    "events": [
      {
        "start": 45.80,
        "end": 46.40,
        "confidence": 0.9,
        "details": {
          "reason": "sudden_silence_dropout",
          "rms": 0.003
        }
      }
    ]
  },
  "volume_fluctuation": {
    "count": 0,
    "events": []
  },
  "voice_distortion": {
    "count": 1,
    "events": [
      {
        "start": 15.20,
        "end": 15.90,
        "confidence": 0.88,
        "details": {
          "reason": "audio_clipping",
          "peak_to_peak": 1.92
        }
      }
    ]
  }
}
```

### 控制台输出

```
============================================================
VOICE QUALITY ANALYSIS REPORT
============================================================
Total duration analyzed: 60.00s
Total frames: 6000

❌ NOISE: 2 issue(s)
   [12.35s - 13.10s]
   [28.02s - 28.60s]

❌ DROPOUT: 1 issue(s)
   [45.80s - 46.40s]

✓ VOLUME_FLUCTUATION: OK

❌ VOICE_DISTORTION: 1 issue(s)
   [15.20s - 15.90s]

============================================================
```

---

## 性能指标

### 计算复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 帧切分 | O(N) | N = 样本数 |
| 特征提取（每帧） | O(F log F) | F = 帧大小（FFT） |
| 检测器（每帧） | O(1) | 简单阈值判断 |
| 后处理 | O(E log E) | E = 事件数（排序） |
| **总计** | **O(N log F)** | 线性复杂度 |

### 实测性能

- **离线分析**: ~0.1x 实时（10秒音频→1秒处理）
- **实时分析**: 延迟 < 50ms（满足实时需求）
- **内存占用**: < 50MB（不含音频数据）

---

## 扩展性设计

### 1. 插件式检测器

**添加新检测器**只需3步：

```python
# Step 1: 继承BaseDetector
from .base import BaseDetector, DetectionEvent

class MyNewDetector(BaseDetector):
    def __init__(self, config=None):
        super().__init__(config)
        self.my_threshold = config.get("my_threshold", 0.5)
    
    # Step 2: 实现detect方法
    def detect(self, features, frame, prev_features=None, is_voice_active=True):
        if features["rms"] > self.my_threshold:
            return DetectionEvent(
                event_type="my_new_problem",
                start_time=frame.start_time,
                end_time=frame.end_time,
                confidence=0.8
            )
        return None

# Step 3: 在Analyzer中注册
class Analyzer:
    def __init__(self, config=None):
        ...
        self.my_detector = MyNewDetector(config=self.config)
    
    def analyze_frames(self, frames):
        ...
        my_event = self.my_detector.detect(features, frame)
        if my_event:
            result.add_event(my_event)
```

### 2. 配置驱动

所有阈值都通过配置文件控制，无需修改代码：

```python
custom_config = {
    **DEFAULT_CONFIG,
    "my_threshold": 0.8,  # 自定义参数
}
analyzer = Analyzer(config=custom_config)
```

### 3. 多级检测

- **Level 1**: 声学特征（当前实现）
- **Level 2**: MFCC音色特征（可选）
- **Level 3**: 大模型推理（未来扩展）

---

## 技术债务与改进方向

### 当前限制

1. **规则死板**: 阈值固定，难以适应所有场景
2. **误报率**: 复杂场景（音乐、多人对话）误报较高
3. **无语义理解**: 无法区分"故意停顿"和"网络卡顿"

### 改进方向

1. **集成LLM**（下一阶段）:
   - 使用GPT-4o Audio API进行二次验证
   - 用Whisper提取语义embedding
   - 减少误报，提供更智能的分析

2. **机器学习**:
   - 训练分类器（Random Forest / XGBoost）
   - 基于标注数据集优化阈值
   - 自适应学习用户偏好

3. **多模态分析**:
   - 结合视频（唇形同步检测）
   - 结合网络指标（丢包率、延迟）

---

## 总结

这是一个**基于声学特征的规则引擎系统**，核心优势是：

✅ **快速**: 无需GPU，实时处理  
✅ **可解释**: 每个检测都有明确原因  
✅ **可配置**: 灵活的阈值和预设  
✅ **可扩展**: 插件式架构，易于添加新检测器  

适用场景：
- VoIP通话质量监控
- 音频录制质量检查
- 实时音频流分析

不适用场景：
- 语义分析（需要LLM）
- 音乐质量评估（需要专业指标）
- 极端复杂场景（需要深度学习）

---

**文档版本**: v1.0  
**最后更新**: 2026年1月27日  
**维护者**: Audio Quality Assessment Team
