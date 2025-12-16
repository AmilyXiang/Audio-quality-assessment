# 语音质量评估 - 完整诊断指南

## 🎯 核心理念：双层诊断系统

你现在有两个互补的检测系统：

```
离散事件检测（Event Detection）
├─ 检测范围：突发问题、短暂异常
├─ 时间粒度：毫秒级
├─ 适用场景：正常语音中的问题点
└─ 工具：analyze_file.py

全局失真检测（Global Assessment）
├─ 检测范围：整体特征异常、系统性失真
├─ 时间粒度：整个文件
├─ 适用场景：合成语音、机器人语音、整体质量评估
└─ 工具：GlobalDistortionAnalyzer
```

---

## 🔍 案例研究：1010bt161057-robot.wav

### 问题描述

用户观察：**整段文件都是变音（机器人语音）**

### 为什么离散检测器看不出来？

```python
# 离散检测逻辑（原始系统）
for frame in frames:
    is_different = frame != baseline_pattern
    if is_different:
        report_issue()

# 对于整段机器人语音
# 所有帧都是机器人特征 → 彼此相似 → 不被认为是"异常"
# 只有相对音量波动 → 被检测为 VOLUME_FLUCTUATION
```

### 解决方案：全局分析

```python
# 全局分析逻辑（新系统）
test_features = compute_global_features(robot_file)
baseline_features = compute_global_features(baseline_file)

distortion_index = compare(test_features, baseline_features)
# distortion_index = 17.73% ← 检测到显著差异！

# 诊断结果
print("谐波清晰度异常: +109%")      # robot: 0.0367 vs baseline: 0.0176
print("Mel频谱异常: +217%")         # robot: 0.0214 vs baseline: 0.0068
print("Crest Factor异常: +29%")     # robot: 22.09 vs baseline: 17.12
```

### 分析结果

| 工具 | 发现 | 准确性 |
|-----|------|--------|
| **离散检测** | 2个音量波动事件 | ⚠️ 不完整 |
| **全局分析** | 17.73%失真指数 + 详细特征差异 | ✅ 准确 |
| **综合** | 整段变音 + 局部音量波动 | ✅✅ 完整 |

---

## 📊 使用流程

### 快速检查单个文件

```bash
# 同时运行两个检测器
python analyze_file.py unknown.wav -o events.json
python analyzer/global_distortion_analyzer.py unknown.wav baseline.wav
```

**输出解读**：

```json
// events.json - 离散问题
{
  "noise": 0,
  "dropout": 0,
  "volume_fluctuation": 2,        // ← 有局部音量波动
  "voice_distortion": 0
}

// 控制台 - 全局问题
"失真指数: 17.73%"                  // ← 整体有显著差异
"Harmonic Clarity: +109%"          // ← 缺乏谐波
"Mel Flatness: +217%"              // ← Mel频谱异常
"质量分数: 0.45 / 1.00"            // ← 文件质量差
```

**诊断**：
- 局部：有一些音量波动
- 整体：整段语音特征异常，可能是合成/机器人语音

---

## 🛠️ 集成到应用

### Python API 使用

```python
from scipy.io import wavfile
from analyzer import Analyzer, GlobalDistortionAnalyzer, frame_generator, DEFAULT_CONFIG
import json

def comprehensive_analysis(audio_path, baseline_path):
    """完整分析：离散 + 全局"""
    
    # ========== 离散事件检测 ==========
    sample_rate, data = wavfile.read(audio_path)
    if len(data.shape) > 1:
        data = data[:, 0]
    data = data.astype(float) / 32768.0
    
    analyzer = Analyzer(config=DEFAULT_CONFIG)
    frames = frame_generator(data, sample_rate, 1200, 480)
    event_result = analyzer.analyze_frames(frames)
    
    # ========== 全局失真检测 ==========
    global_analyzer = GlobalDistortionAnalyzer()
    global_result = global_analyzer.analyze_file(audio_path, baseline_path)
    
    # ========== 综合诊断 ==========
    diagnosis = {
        "file": audio_path,
        "local_events": {
            "noise": event_result.count_by_type("noise"),
            "dropout": event_result.count_by_type("dropout"),
            "volume_fluctuation": event_result.count_by_type("volume_fluctuation"),
            "voice_distortion": event_result.count_by_type("voice_distortion"),
        },
        "global_assessment": global_result["quality_assessment"],
        "distortion_index": global_result["baseline_comparison"]["overall_distortion_index"]
        if global_result["baseline_comparison"] else None,
        "recommendation": generate_recommendation(
            event_result,
            global_result
        )
    }
    
    return diagnosis


def generate_recommendation(event_result, global_result):
    """生成诊断建议"""
    
    local_issues = sum([
        event_result.count_by_type("noise"),
        event_result.count_by_type("dropout"),
        event_result.count_by_type("volume_fluctuation"),
        event_result.count_by_type("voice_distortion"),
    ])
    
    distortion_idx = global_result["baseline_comparison"]["overall_distortion_index"] \
        if global_result["baseline_comparison"] else 0
    
    quality_score = global_result["quality_assessment"]["quality_score"]
    
    if distortion_idx > 0.30:
        return "⚠️  整体失真严重，可能是合成/机器人语音或编码失真"
    elif distortion_idx > 0.15:
        return "⚠️  整体特征异常，质量有问题"
    elif local_issues > 3:
        return "⚠️  存在多个局部问题"
    elif local_issues > 0:
        return "✓ 基本可用，有少量问题"
    else:
        return "✅ 质量良好"
```

### REST API 封装

```python
from flask import Flask, request, jsonify
from analyzer import GlobalDistortionAnalyzer
import tempfile
import os

app = Flask(__name__)

@app.route('/analyze/comprehensive', methods=['POST'])
def comprehensive_analysis_api():
    """
    POST /analyze/comprehensive
    
    Form data:
        - test_file: 待分析音频
        - baseline_file: 基线音频
    
    Response:
        {
            "local_events": {...},
            "global_assessment": {...},
            "distortion_index": 0.177,
            "diagnosis": "..."
        }
    """
    
    test_file = request.files.get('test_file')
    baseline_file = request.files.get('baseline_file')
    
    if not test_file:
        return jsonify({"error": "No test_file provided"}), 400
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
        test_file.save(tf.name)
        test_path = tf.name
    
    baseline_path = None
    if baseline_file:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as bf:
            baseline_file.save(bf.name)
            baseline_path = bf.name
    
    try:
        # 调用综合分析
        result = comprehensive_analysis(test_path, baseline_path)
        return jsonify(result)
    finally:
        os.unlink(test_path)
        if baseline_path:
            os.unlink(baseline_path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## 📋 决策树：应该使用哪个工具？

```
是否需要了解整个文件的质量？
├─ NO (只关心有没有问题) 
│  └─ 使用 离散检测器
│     命令：python analyze_file.py audio.wav
│
├─ YES (需要完整诊断)
│  ├─ 有基线参考吗？
│  │  ├─ NO
│  │  │  └─ 使用 离散检测器 (无法做全局对比)
│  │  │
│  │  └─ YES (有baseline)
│  │     ├─ 想知道有没有合成/机器人语音？
│  │     │  ├─ YES
│  │     │  │  └─ 同时用两个！
│  │     │  │     1. analyze_file.py audio.wav -p baseline.json
│  │     │  │     2. global_distortion_analyzer.py audio.wav baseline.wav
│  │     │  │
│  │     │  └─ NO
│  │     │     └─ 先用全局分析看质量
│  │     │        global_distortion_analyzer.py audio.wav baseline.wav
│  │     │        如果有问题再用离散检测找具体位置
```

---

## 🎓 技术参数参考

### 离散检测器（Event-based）

| 参数 | 默认值 | 含义 |
|------|--------|------|
| **enable_vad** | True | 只分析人声片段 |
| **min_event_duration.dropout** | 50ms | 最小卡顿持续时间 |
| **min_event_duration.noise** | 150ms | 最小噪声持续时间 |
| **min_event_duration.volume_fluctuation** | 250ms | 最小音量波动持续时间 |
| **min_event_duration.voice_distortion** | 120ms | 最小失真持续时间 |

### 全局分析器（File-level）

| 参数 | 含义 | 异常阈值 |
|------|------|---------|
| **Crest Factor** | 峰值/RMS比 | >8 或 <2.5 |
| **Kurtosis** | 峰度 | >5 或 <1.5 |
| **Harmonic Clarity** | 基频能量比 | <0.15 |
| **Mel Flatness** | Mel频谱平坦度 | <0.3 |
| **Centroid Stability** | 频率稳定性 | >0.4 |
| **distortion_index** | 与基线差异 | >0.15 (中等) >0.30 (严重) |

---

## ✅ 检查清单

### 部署前确认

- [ ] 已安装所有依赖：`pip install -r requirements.txt`
- [ ] 已生成设备校准文件：`python calibrate.py baseline.wav -o device.json`
- [ ] 已测试离散检测：`python test_analyzer.py`
- [ ] 已测试全局分析：`python test_global_distortion.py`
- [ ] 理解两个系统的差异和互补性

### 日常使用

- [ ] 对每个新文件先运行全局分析
- [ ] 如果全局失真指数>0.15，手动检查
- [ ] 如果离散事件过多（>5），检查设备或基线
- [ ] 定期更新设备校准

---

## 📞 常见问题

**Q: 两个系统都要用吗？**

A: 不一定。根据应用场景：
- 生产环境（真实人声）→ 离散检测足够
- 研究/质量评估 → 需要全局分析
- 不确定输入（可能合成） → 两个都用

---

**Q: 为什么机器人文件只有17.73%差异，不是更大？**

A: 因为基线文件本身质量也不好（Crest Factor 17.12，远高于正常4-8）。
当两个都是"坏"的时候，相对差异反而不明显。

解决方法：使用更好的基线，或者使用绝对阈值而非相对对比。

---

**Q: 如何区分机器人语音 vs 失真人声？**

A: 看这两个特征：
- **Harmonic Clarity** 
  - 机器人：接近0（无谐波）
  - 失真人声：>0.1（仍有谐波，只是受损）
  
- **Mel Flatness**
  - 机器人：<0.02（完全非人类）
  - 失真人声：0.05-0.15（仍有人声特征）

---

**Q: 能检测到深度伪造/变声吗？**

A: 部分能。但更好的方法是用专门的反欺骗模型。
本系统可以作为第一层筛选：
```
如果 distortion_index > 0.3 且 harmonic_clarity < 0.02:
    flag_as_suspicious()  # 可能是合成/变声
```

但不能确定，需要用专门工具进一步验证。

---

## 🚀 下一步

1. **立即开始**
   ```bash
   python test_global_distortion.py
   ```

2. **集成到应用**
   - 修改 `analyze_file.py` 添加全局检测选项
   - 或直接调用 `GlobalDistortionAnalyzer` API

3. **优化参数**
   - 根据真实数据调整阈值
   - 收集正常/异常样本
   - 建立参考基准库

4. **未来增强**
   - 集成ML分类器
   - 支持更多语言
   - 实时流分析

---

**系统版本**：2.0 (含全局分析)  
**更新日期**：2025年12月16日  
**维护者**：Voice Quality Assessment Team
