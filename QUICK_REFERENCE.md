# 快速参考卡片 - 语音质量检测

## 🎯 一行诊断

```bash
# 检测离散问题
python analyze_file.py audio.wav -p device.json

# 检测整体失真
python analyzer/global_distortion_analyzer.py audio.wav baseline.wav

# 两个都检测（推荐）
python analyze_file.py audio.wav -p device.json && python analyzer/global_distortion_analyzer.py audio.wav baseline.wav
```

---

## 📊 诊断表

| 现象 | 离散检测结果 | 全局分析结果 | 原因 | 解决方案 |
|------|-----------|-----------|------|--------|
| **短暂噪声** | ❌ 噪声:1 | ✓ 正常 | 环境干扰 | 忽略/增加阈值 |
| **持续低频** | ❌ 微弱检测 | ⚠️ 低频比例异常 | 设备特性 | 校准设备 |
| **整段合成** | ⚠️ 仅音量波动 | ❌ 失真指数>0.3 | 合成语音 | 标记为异常 |
| **编码问题** | ⚠️ 多个失真 | ❌ Crest Factor异常 | 有损压缩 | 重新编码 |
| **清晰人声** | ✓ 无问题 | ✓ 质量优 | 高质量 | 接受 |

---

## 💾 输出格式

### 离散检测 (analyze_file.py)
```json
{
  "noise": {"count": 2, "events": [{"start": 1.5, "end": 2.0}]},
  "dropout": {"count": 0, "events": []},
  "volume_fluctuation": {"count": 1, "events": [{"start": 5.0, "end": 6.0}]},
  "voice_distortion": {"count": 0, "events": []}
}
```

### 全局分析 (GlobalDistortionAnalyzer)
```
失真指数: 17.73%
主要问题:
  - Harmonic Clarity: +109% (异常)
  - Mel Flatness: +217% (异常)
  - Crest Factor: +29% (轻微异常)
质量评分: 0.45 / 1.00 (严重失真)
```

---

## 🎲 决策矩阵

```
事件数 ↓ / 失真指数 →    <0.1    0.1-0.2   0.2-0.3   >0.3
0 (~正常)            ✅好     ⚠️注意    ❌问题    🚫严重
1-3 (轻微)           ✅好     ⚠️注意    ⚠️问题    ❌严重
4-8 (中等)           ⚠️注意   ❌问题    ❌问题    🚫严重
>8 (严重)            ❌问题   ❌问题    🚫严重   🚫严重
```

---

## 📋 标准流程

### 第1次使用
```bash
# 1. 校准设备（一次性）
cd voice_quality_tool
python calibrate.py ../robotic/1010baseline.wav -o device.json

# 2. 测试系统
python test_analyzer.py
python test_global_distortion.py

# 3. 分析目标文件
python analyze_file.py ../robotic/1010bt161057-robot.wav -p device.json -o events.json
python analyzer/global_distortion_analyzer.py ../robotic/1010bt161057-robot.wav ../robotic/1010baseline.wav
```

### 日常使用
```bash
# 快速检查
python analyze_file.py new_file.wav -p device.json

# 详细检查
python analyze_file.py new_file.wav -p device.json -o report.json
python analyzer/global_distortion_analyzer.py new_file.wav baseline.wav
```

---

## 🔍 症状诊断表

### 症状1：听起来像机器人/合成

**检查**：
```
Step 1: 离散检测
  expect → VOLUME_FLUCTUATION 或 无问题 (因为机器人语音相对稳定)

Step 2: 全局分析
  expect → 失真指数 > 0.2, Harmonic Clarity <0.02, Mel Flatness <0.02
  
Action → 整段是合成/机器人语音，需要标记
```

### 症状2：有杂音/噪声

**检查**：
```
Step 1: 离散检测
  expect → NOISE: N (N>0)
  
Step 2: 全局分析
  expect → 高频比例异常
  
Action → 调查是环境噪声还是设备问题
```

### 症状3：声音忽大忽小

**检查**：
```
Step 1: 离散检测
  expect → VOLUME_FLUCTUATION: N
  
Step 2: 全局分析
  expect → RMS Stability 高 (>0.3)
  
Action → 音量需要归一化处理
```

### 症状4：听不清/爆音

**检查**：
```
Step 1: 离散检测
  expect → VOICE_DISTORTION: N 或 DROPOUT: N
  
Step 2: 全局分析
  expect → Crest Factor 极端值 (>15 或 <2)
  
Action → 检查编码/录制设备
```

---

## ⚡ 速查表

| 需求 | 命令 | 输出 |
|------|------|------|
| 检测离散问题 | `analyze_file.py audio.wav` | JSON |
| 检测合成语音 | `global_distortion_analyzer.py audio.wav baseline.wav` | 失真指数 |
| 完整诊断 | 两个命令都运行 | JSON + 失真指数 |
| 批量分析 | 见下面脚本 | 多个报告 |

### 批量分析脚本

**PowerShell**:
```powershell
$baseline = "device.json"
Get-ChildItem *.wav | ForEach-Object {
    python analyze_file.py $_.FullName -p $baseline -o "$($_.BaseName)_events.json"
    python analyzer/global_distortion_analyzer.py $_.FullName baseline.wav >> "$($_.BaseName)_global.txt"
}
```

**Bash**:
```bash
for f in *.wav; do
    python analyze_file.py "$f" -p device.json -o "${f%.wav}_events.json"
    python analyzer/global_distortion_analyzer.py "$f" baseline.wav > "${f%.wav}_global.txt"
done
```

---

## 🎓 参数调优

### 若误报过多（false positives）

```python
# 增加持续时间阈值
config = {
    "min_event_duration": {
        "noise": 0.30,           # 原:0.15
        "dropout": 0.10,         # 原:0.05
        "voice_distortion": 0.20, # 原:0.12
        "volume_fluctuation": 0.40, # 原:0.25
    }
}
```

### 若漏报（false negatives）

```python
# 减少持续时间阈值
config = {
    "min_event_duration": {
        "noise": 0.10,           # 原:0.15
        "dropout": 0.03,         # 原:0.05
        "voice_distortion": 0.08, # 原:0.12
        "volume_fluctuation": 0.15, # 原:0.25
    }
}
```

### 若全局分析灵敏度不对

```python
# 编辑 global_distortion_analyzer.py
analyzer = GlobalDistortionAnalyzer()

# 调整期望范围
analyzer.spectral_consistency_threshold = 0.30  # 原:0.35
analyzer.formant_stability_threshold = 0.25     # 原:0.30
analyzer.mel_distortion_threshold = 0.35        # 原:0.40
```

---

## 🆘 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: scipy` | 依赖未安装 | `pip install -r requirements.txt` |
| `Error opening audio stream` | 麦克风问题 | 检查设备/权限 |
| `File not found` | 路径错误 | 使用绝对路径或检查文件位置 |
| `All zeros distortion` | 基线文件无效 | 重新校准：`python calibrate.py` |
| 特别高的误报率 | VAD或阈值不对 | 尝试 `--disable-vad` 或调整参数 |

---

## 📞 获取帮助

查看完整文档：
- [USER_GUIDE.md](voice_quality_tool/USER_GUIDE.md) - 完整使用指南
- [DIAGNOSIS_GUIDE.md](DIAGNOSIS_GUIDE.md) - 诊断完全指南
- [GLOBAL_DISTORTION_ANALYSIS.md](GLOBAL_DISTORTION_ANALYSIS.md) - 全局分析原理
- [ROBOTIC_ANALYSIS_REPORT.md](ROBOTIC_ANALYSIS_REPORT.md) - 机器人语音分析案例

---

**最后更新**：2025年12月16日  
**版本**：2.0
