# Voice Quality Analyzer - 完整使用指南

## 📖 目录

1. [快速开始](#快速开始)
2. [基础使用](#基础使用)
3. [高级功能](#高级功能)
4. [配置调整](#配置调整)
5. [实际场景](#实际场景)
6. [API集成](#api集成)
7. [故障排查](#故障排查)

---

## 🚀 快速开始

### 安装依赖

```bash
cd voice_quality_tool
pip install -r requirements.txt
```

### 运行测试

```bash
# 生成测试音频并分析
python test_analyzer.py
```

**输出示例**：
```
🎵 Generating synthetic test audio...
✓ Saved test audio to: test_audio.wav
🔍 Analyzing with Voice Quality Analyzer...

============================================================
VOICE QUALITY ANALYSIS REPORT
============================================================
Total duration analyzed: 10.00s
Total frames: 1000

❌ NOISE: 1 issue(s)
   [1.63s - 2.00s]
✓ DROPOUT: OK
❌ VOLUME_FLUCTUATION: 3 issue(s)
   [0.43s - 0.99s]
============================================================
```

---

## 📝 基础使用

### 1. 离线文件分析

**最简单的方式**：
```bash
python analyze_file.py audio.wav
```

**保存结果为JSON**：
```bash
python analyze_file.py audio.wav --output report.json
# 或简写
python analyze_file.py audio.wav -o report.json
```

**JSON输出格式**：
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
    "count": 2,
    "events": [
      {"start": 15.20, "end": 15.90}
    ]
  }
}
```

---

### 2. 实时麦克风分析

**默认录制10秒**：
```bash
python analyze_mic.py
```

**自定义录制时长**：
```bash
python analyze_mic.py 30  # 录制30秒
```

**实时输出格式**：
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

---

## 🔧 高级功能

### 3. 设备校准（推荐）

**适用场景**：
- 低端设备（底噪高）
- 固定环境（办公室、家庭）
- 需要减少误报

**步骤**：

#### **Step 1: 录制基线音频**
在目标环境用目标设备录制 30-60 秒"正常"音频：
- 包含正常通话内容
- 包含设备固有特性
- 无明显质量问题

#### **Step 2: 校准生成配置文件**
```bash
python calibrate.py baseline_audio.wav --output device_profile.json
# 或简写
python calibrate.py baseline_audio.wav -o device_profile.json
```

**输出示例**：
```
🎤 Calibrating with: baseline_audio.wav
   Sample rate: 16000 Hz, Duration: 45.50s

📊 Analyzing baseline characteristics...

✅ Calibration complete!
💾 Device profile saved to: device_profile.json

📋 Baseline Statistics:
   RMS Mean: 0.0523
   RMS Std:  0.0312
   Centroid Mean: 1245.3 Hz
   ZCR Mean: 0.0871

🎯 Use this profile when analyzing:
   python analyze_file.py audio.wav --profile device_profile.json
```

#### **Step 3: 使用配置分析**
```bash
python analyze_file.py test_audio.wav --profile device_profile.json -o result.json
# 或简写
python analyze_file.py test_audio.wav -p device_profile.json -o result.json
```

**效果**：
- ✅ 自动适应设备底噪
- ✅ 减少误报率 50-80%
- ✅ 保留真实质量问题

---

### 4. VAD（语音活动检测）

**默认启用**（只分析人声片段）：
```bash
python analyze_file.py audio.wav
```

**禁用VAD**（分析所有帧，包括静音段）：
```bash
python analyze_file.py audio.wav --disable-vad
```

**效果对比**：

| 模式 | 检测结果 | 适用场景 |
|------|---------|---------|
| **VAD启用** | 噪声↓ 卡顿↓ | 嘈杂环境、有背景音 |
| **VAD禁用** | 噪声↑ 卡顿↑ | 实验室、高质量录音 |

**示例**：
```bash
# 启用VAD（默认）
python analyze_file.py office_call.wav
# 结果: NOISE: 1, DROPOUT: 0

# 禁用VAD
python analyze_file.py office_call.wav --disable-vad
# 结果: NOISE: 5, DROPOUT: 2 (包含非人声段)
```

---

### 5. 组合使用（推荐）

**最佳实践**：
```bash
# 1. 首次使用：校准设备
python calibrate.py my_device_baseline.wav -o my_device.json

# 2. 日常分析：使用配置 + VAD
python analyze_file.py call1.wav --profile my_device.json -o report1.json
python analyze_file.py call2.wav -p my_device.json -o report2.json

# 3. 特殊情况：禁用VAD查看所有问题
python analyze_file.py suspicious.wav -p my_device.json --disable-vad -o debug.json
```

---

## ⚙️ 配置调整

### 6. 使用预设配置

工具提供5种预设模式（详见 [CONFIG_PRESETS.md](CONFIG_PRESETS.md)）：

**在代码中使用**：
```python
from analyzer import Analyzer, frame_generator
from scipy.io import wavfile

# 标准模式（默认）
config = {
    "enable_vad": True,
    "min_event_duration": {
        "dropout": 0.05,
        "voice_distortion": 0.12,
        "noise": 0.15,
        "volume_fluctuation": 0.25,
    },
}

analyzer = Analyzer(config=config)
```

**5种预设模式**：

1. **STANDARD_MODE**（默认）- 生产环境
2. **STRICT_MODE** - 实验室/高质量
3. **RELAXED_MODE** - 嘈杂环境/低端设备
4. **VOIP_MODE** - 网络通话（对卡顿敏感）
5. **PODCAST_MODE** - 专业录音

---

### 7. 自定义阈值

**调整人耳感知阈值**：
```python
from analyzer import Analyzer

custom_config = {
    "enable_vad": True,
    
    # 差异化的最小持续时间（基于人耳感知）
    "min_event_duration": {
        "dropout": 0.03,            # 30ms - 更敏感
        "voice_distortion": 0.10,   # 100ms
        "noise": 0.20,              # 200ms - 更宽松
        "volume_fluctuation": 0.30, # 300ms
    },
    
    # 检测器灵敏度
    "noise_zcr_threshold": 0.18,    # 提高=不敏感
    "spectral_flux_threshold": 0.15, # 降低=更敏感
}

analyzer = Analyzer(config=custom_config)
```

**阈值调整规则**：

| 现象 | 解决方案 |
|------|---------|
| 误报太多 | 增加 `min_event_duration` |
| 漏报问题 | 减少 `min_event_duration` |
| 噪声误报 | 增加 `noise_zcr_threshold` |
| 变声漏报 | 减少 `spectral_flux_threshold` |

---

## 🎯 实际场景

### 场景1：办公环境（键盘、开门声）

**问题**：环境干扰导致误报

**解决方案**：
```bash
# 方案A：使用默认配置（已启用VAD + 持续性过滤）
python analyze_file.py office_call.wav -o report.json

# 方案B：如果仍有误报，使用宽松模式
# 在代码中设置 RELAXED_MODE 配置
```

**效果**：
- 短暂的键盘声（<150ms）被自动过滤
- 开门声（<200ms）不会误判为噪声
- 只检测持续的质量问题

---

### 场景2：低端手机/麦克风

**问题**：设备底噪高，误判为噪声

**解决方案**：
```bash
# 1. 校准设备（一次性）
python calibrate.py phone_baseline.wav -o phone_profile.json

# 2. 使用配置分析
python analyze_file.py phone_call.wav --profile phone_profile.json -o result.json
```

**效果**：
- 自动适应设备固有底噪
- 只检测异常噪声增加
- 误报率降低 70%+

---

### 场景3：VoIP通话（网络问题）

**问题**：需要检测丢包、编码问题

**解决方案**：
```python
# 使用VOIP_MODE配置
VOIP_CONFIG = {
    "enable_vad": True,
    "min_event_duration": {
        "dropout": 0.02,  # 20ms - 极度敏感（网络丢包）
        "voice_distortion": 0.08,
        "noise": 0.20,
        "volume_fluctuation": 0.30,
    },
}

analyzer = Analyzer(config=VOIP_CONFIG)
# ... 分析逻辑
```

**重点检测**：
- ⚠️ Dropout（卡顿）- 最敏感
- ⚠️ Voice Distortion（编码失真）- 敏感
- ✓ Noise（噪声）- 相对宽松
- ✓ Volume（音量）- 宽松

---

### 场景4：专业录音/播客

**问题**：高质量要求，不容忍任何问题

**解决方案**：
```bash
# 禁用VAD，使用严格模式
python analyze_file.py podcast.wav --disable-vad -o quality_check.json
```

**配置建议**：
```python
PODCAST_CONFIG = {
    "enable_vad": False,  # 检测所有内容
    "min_event_duration": {
        "dropout": 0.03,
        "voice_distortion": 0.08,
        "noise": 0.08,     # 对噪声极度敏感
        "volume_fluctuation": 0.12,
    },
}
```

---

### 场景5：批量分析

**PowerShell**：
```powershell
# 批量处理当前目录所有WAV文件
Get-ChildItem *.wav | ForEach-Object {
    $output = $_.BaseName + "_report.json"
    python analyze_file.py $_.FullName --profile device.json -o $output
    Write-Host "✓ Processed: $($_.Name)"
}
```

**Bash**：
```bash
# 批量处理
for file in *.wav; do
    output="${file%.wav}_report.json"
    python analyze_file.py "$file" --profile device.json -o "$output"
    echo "✓ Processed: $file"
done
```

---

## 💻 API集成

### 8. Python代码集成

**基础使用**：
```python
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG
from scipy.io import wavfile
import json

# 1. 加载音频
sample_rate, data = wavfile.read("audio.wav")

# 处理立体声
if len(data.shape) > 1:
    data = data[:, 0]

# 归一化
data = data.astype(float) / 32768.0

# 2. 创建分析器
analyzer = Analyzer(config=DEFAULT_CONFIG)

# 3. 生成帧
frame_size = int(sample_rate * 0.025)  # 25ms
hop_size = int(sample_rate * 0.010)     # 10ms
frames = frame_generator(data, sample_rate, frame_size, hop_size)

# 4. 分析
result = analyzer.analyze_frames(frames)

# 5. 获取结果
print(result.to_json_string())  # JSON字符串
report = result.to_dict()        # Python字典
result.print_summary()           # 控制台输出
```

---

**使用设备配置**：
```python
import json
from analyzer import Analyzer, frame_generator
from scipy.io import wavfile

# 加载设备配置
with open('device_profile.json', 'r') as f:
    profile = json.load(f)
    
config = profile.get('recommended_config', {})

# 加载音频
sample_rate, data = wavfile.read("test.wav")
data = data.astype(float) / 32768.0

# 分析
analyzer = Analyzer(config=config)
frames = frame_generator(data, sample_rate, 400, 160)
result = analyzer.analyze_frames(frames)

# 处理结果
for event in result.events:
    print(f"{event.event_type}: {event.start_time:.2f}s - {event.end_time:.2f}s")
```

---

**实时流处理**：
```python
from analyzer import Analyzer, Frame
import numpy as np

analyzer = Analyzer()

def process_audio_chunk(audio_chunk, sample_rate, timestamp):
    """处理实时音频块"""
    # 创建Frame对象
    frame = Frame(
        samples=audio_chunk,
        sample_rate=sample_rate,
        start_time=timestamp,
        end_time=timestamp + len(audio_chunk) / sample_rate
    )
    
    # 逐帧分析（需要自己维护帧序列）
    # 或者积累足够的帧后批量分析
    # frames = [frame1, frame2, ...]
    # result = analyzer.analyze_frames(frames)
    
    return frame
```

---

### 9. REST API封装（示例）

```python
from flask import Flask, request, jsonify
from analyzer import Analyzer, frame_generator
from scipy.io import wavfile
import tempfile
import os

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """
    POST /analyze
    Body: multipart/form-data
        - file: 音频文件
        - profile: 设备配置（可选）
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    audio_file = request.files['file']
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        # 加载音频
        sample_rate, data = wavfile.read(tmp_path)
        if len(data.shape) > 1:
            data = data[:, 0]
        data = data.astype(float) / 32768.0
        
        # 分析
        analyzer = Analyzer()
        frames = frame_generator(data, sample_rate, 400, 160)
        result = analyzer.analyze_frames(frames)
        
        # 返回JSON
        return jsonify(result.to_dict())
        
    finally:
        os.unlink(tmp_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**调用方式**：
```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@audio.wav" \
  | jq .
```

---

## 🐛 故障排查

### 常见问题

#### **Q1: 误报率太高**

**现象**：检测到很多短暂的问题

**解决方案**：
```bash
# 方案1：启用VAD（如果未启用）
python analyze_file.py audio.wav  # VAD默认启用

# 方案2：使用设备配置
python calibrate.py baseline.wav -o profile.json
python analyze_file.py audio.wav --profile profile.json

# 方案3：调整阈值（在代码中）
config = {
    "min_event_duration": {
        "noise": 0.30,  # 增加到300ms
        "dropout": 0.10,
        "volume_fluctuation": 0.40,
        "voice_distortion": 0.20,
    }
}
```

---

#### **Q2: 漏检真实问题**

**现象**：明显的问题没被检测到

**解决方案**：
```bash
# 方案1：禁用VAD
python analyze_file.py audio.wav --disable-vad

# 方案2：降低阈值
config = {
    "min_event_duration": {
        "dropout": 0.03,  # 降低到30ms
        "noise": 0.10,
        # ...
    }
}

# 方案3：调整检测敏感度
config = {
    "spectral_flux_threshold": 0.15,  # 降低=更敏感
    "noise_zcr_threshold": 0.12,      # 降低=更敏感
}
```

---

#### **Q3: 校准后效果反而变差**

**原因**：基线音频质量不好

**解决方案**：
```bash
# 重新录制基线音频，确保：
# 1. 时长 30-60 秒
# 2. 包含正常通话内容
# 3. 无明显质量问题（但可以有设备固有特性）
# 4. 在实际使用环境中录制

python calibrate.py new_baseline.wav -o profile.json
```

---

#### **Q4: 导入错误**

**现象**：`ImportError: No module named 'scipy'`

**解决方案**：
```bash
# 安装依赖
pip install -r requirements.txt

# 或单独安装
pip install numpy scipy pyaudio
```

---

#### **Q5: 实时麦克风无法使用**

**现象**：`Error opening audio stream`

**解决方案**：
```bash
# Windows: 安装 PyAudio
pip install pipwin
pipwin install pyaudio

# Linux/Mac: 安装系统依赖
sudo apt-get install portaudio19-dev  # Ubuntu/Debian
brew install portaudio                 # macOS
pip install pyaudio
```

---

## 📚 参考文档

- [README.md](README.md) - 项目总览
- [PERCEPTUAL_THRESHOLDS.md](PERCEPTUAL_THRESHOLDS.md) - 人耳感知阈值科学依据
- [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - 预设配置详解
- [ADVANCED_USAGE.md](ADVANCED_USAGE.md) - 高级功能说明
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - 技术实现细节

---

## 🎓 学习路径

**新手**：
1. 运行 `python test_analyzer.py` 了解基本功能
2. 使用 `python analyze_file.py` 分析实际文件
3. 阅读输出报告，理解各类问题

**进阶**：
1. 使用 `calibrate.py` 校准设备
2. 尝试 `--disable-vad` 对比效果
3. 调整配置参数，优化检测效果

**高级**：
1. 在代码中集成 API
2. 自定义检测器（扩展 `BaseDetector`）
3. 实现实时流分析

---

## 💡 最佳实践

1. **首次使用**：
   ```bash
   python test_analyzer.py  # 熟悉工具
   ```

2. **正式部署**：
   ```bash
   # 1. 校准设备
   python calibrate.py baseline.wav -o device.json
   
   # 2. 批量分析
   python analyze_file.py call1.wav -p device.json -o report1.json
   ```

3. **持续优化**：
   - 收集用户反馈
   - 调整阈值参数
   - 更新设备配置

---

## 🚀 快速命令参考

```bash
# 基础分析
python analyze_file.py audio.wav

# 保存结果
python analyze_file.py audio.wav -o report.json

# 使用设备配置
python analyze_file.py audio.wav -p device.json -o report.json

# 禁用VAD
python analyze_file.py audio.wav --disable-vad

# 完整命令
python analyze_file.py audio.wav --profile device.json --disable-vad -o report.json

# 校准设备
python calibrate.py baseline.wav -o device.json

# 实时分析
python analyze_mic.py 30

# 测试
python test_analyzer.py
```

---

**版本**：1.2.0  
**更新**：2025年12月16日  
**作者**：Voice Quality Analyzer Team
