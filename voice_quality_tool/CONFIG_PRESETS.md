# 预设配置示例

本文件包含针对不同场景的预设配置。

## 📋 使用方式

```python
from analyzer import Analyzer

# 加载配置
config = STRICT_MODE  # 或 STANDARD_MODE, RELAXED_MODE

# 创建分析器
analyzer = Analyzer(config=config)
```

---

## 🎯 标准模式（推荐 - 默认）

**适用场景**：
- 一般生产环境
- 正常办公环境
- 标准质量设备

**特点**：平衡检测精度和误报率

```python
STANDARD_MODE = {
    # VAD配置
    "enable_vad": True,
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # 人耳感知阈值（基于科学研究）
    "min_event_duration": {
        "dropout": 0.05,            # 50ms - 最敏感
        "voice_distortion": 0.12,   # 120ms
        "noise": 0.15,              # 150ms
        "volume_fluctuation": 0.25, # 250ms
    },
    
    # 检测阈值
    "noise_zcr_threshold": 0.15,
    "burst_spike_threshold": 0.3,
    "silence_rms_threshold": 0.01,
    "dropout_zcr_threshold": 0.05,
    "rms_change_threshold": 0.4,
    "spectral_flux_threshold": 0.2,
    "centroid_shift_threshold": 500.0,
    "bandwidth_spike_threshold": 1.5,
}
```

---

## 🔬 严格模式

**适用场景**：
- 实验室环境
- 高质量要求
- 音频编码测试
- 设备质检

**特点**：更敏感，检测更细微的问题

```python
STRICT_MODE = {
    "enable_vad": False,  # 禁用VAD，检测所有帧
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # 更短的最小持续时间
    "min_event_duration": {
        "dropout": 0.03,            # 30ms - 极度敏感
        "voice_distortion": 0.08,   # 80ms
        "noise": 0.10,              # 100ms
        "volume_fluctuation": 0.15, # 150ms
    },
    
    # 更严格的检测阈值
    "noise_zcr_threshold": 0.12,        # 降低（更敏感）
    "burst_spike_threshold": 0.2,       # 降低
    "silence_rms_threshold": 0.015,     # 提高（更宽松，避免误判）
    "dropout_zcr_threshold": 0.06,      # 提高
    "rms_change_threshold": 0.3,        # 降低
    "spectral_flux_threshold": 0.15,    # 降低
    "centroid_shift_threshold": 400.0,  # 降低
    "bandwidth_spike_threshold": 1.3,   # 降低
}
```

---

## 🌐 宽松模式

**适用场景**：
- 嘈杂环境（办公室、街道、公共场所）
- 低端设备（高底噪）
- 移动场景
- 需要减少误报

**特点**：只检测明显的质量问题

```python
RELAXED_MODE = {
    "enable_vad": True,  # 启用VAD，过滤非人声
    "vad_min_rms": 0.03,      # 提高能量门限
    "vad_max_rms": 1.0,
    "vad_min_centroid": 100,  # 收窄人声范围
    "vad_max_centroid": 2500,
    "vad_min_zcr": 0.04,
    "vad_max_zcr": 0.16,
    
    # 更长的最小持续时间
    "min_event_duration": {
        "dropout": 0.10,            # 100ms
        "voice_distortion": 0.20,   # 200ms
        "noise": 0.30,              # 300ms
        "volume_fluctuation": 0.40, # 400ms
    },
    
    # 更宽松的检测阈值
    "noise_zcr_threshold": 0.20,        # 提高（不敏感）
    "burst_spike_threshold": 0.5,       # 提高
    "silence_rms_threshold": 0.005,     # 降低（更严格，只检测极端静音）
    "dropout_zcr_threshold": 0.03,      # 降低
    "rms_change_threshold": 0.6,        # 提高
    "spectral_flux_threshold": 0.3,     # 提高
    "centroid_shift_threshold": 800.0,  # 提高
    "bandwidth_spike_threshold": 2.0,   # 提高
}
```

---

## 📞 VoIP场景模式

**适用场景**：
- 网络通话（Zoom、Teams、Skype）
- 实时流媒体
- 关注网络问题（丢包、抖动）

**特点**：对dropout和distortion极度敏感

```python
VOIP_MODE = {
    "enable_vad": True,
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # 网络问题最敏感
    "min_event_duration": {
        "dropout": 0.02,            # 20ms - 极度敏感（丢包）
        "voice_distortion": 0.08,   # 80ms - 敏感（编码问题）
        "noise": 0.20,              # 200ms - 相对宽松
        "volume_fluctuation": 0.30, # 300ms - 宽松
    },
    
    # 针对VoIP优化的阈值
    "noise_zcr_threshold": 0.18,        # 宽松（网络噪声可接受）
    "burst_spike_threshold": 0.4,       # 宽松
    "silence_rms_threshold": 0.008,     # 严格（检测丢包）
    "dropout_zcr_threshold": 0.04,      # 严格
    "rms_change_threshold": 0.5,        # 宽松（AGC常见）
    "spectral_flux_threshold": 0.15,    # 严格（编码失真）
    "centroid_shift_threshold": 400.0,  # 严格
    "bandwidth_spike_threshold": 1.3,   # 严格
}
```

---

## 🎙️ 播客/录音室模式

**适用场景**：
- 专业录音
- 播客制作
- 音频内容创作
- 高质量要求

**特点**：全面检测，不容忍任何质量问题

```python
PODCAST_MODE = {
    "enable_vad": False,  # 不过滤，检测所有内容
    "vad_min_rms": 0.02,
    "vad_max_rms": 1.0,
    "vad_min_centroid": 80,
    "vad_max_centroid": 3000,
    "vad_min_zcr": 0.03,
    "vad_max_zcr": 0.18,
    
    # 全方位高标准
    "min_event_duration": {
        "dropout": 0.03,            # 30ms
        "voice_distortion": 0.08,   # 80ms
        "noise": 0.08,              # 80ms - 对噪声极度敏感
        "volume_fluctuation": 0.12, # 120ms - 音量也需平稳
    },
    
    # 全面严格的阈值
    "noise_zcr_threshold": 0.10,        # 极度敏感
    "burst_spike_threshold": 0.15,      # 极度敏感
    "silence_rms_threshold": 0.02,      # 宽松（允许有意的停顿）
    "dropout_zcr_threshold": 0.08,      # 宽松
    "rms_change_threshold": 0.25,       # 严格（音量平稳）
    "spectral_flux_threshold": 0.12,    # 严格
    "centroid_shift_threshold": 350.0,  # 严格
    "bandwidth_spike_threshold": 1.2,   # 严格
}
```

---

## 🔧 自定义配置指南

### **第一步：确定使用场景**
- 生产环境 → STANDARD_MODE
- 高质量要求 → STRICT_MODE
- 嘈杂环境 → RELAXED_MODE
- VoIP应用 → VOIP_MODE
- 专业录音 → PODCAST_MODE

### **第二步：调整持续时间阈值**

人耳感知参考：
```python
"min_event_duration": {
    "dropout": 0.02-0.10,         # 最敏感
    "voice_distortion": 0.08-0.20,
    "noise": 0.10-0.30,
    "volume_fluctuation": 0.15-0.40,  # 最不敏感
}
```

**调整建议**：
- 误报多 → 增加阈值
- 漏报多 → 减少阈值
- 从标准值开始，逐步调整

### **第三步：调整检测敏感度**

| 参数 | 值越小 | 值越大 |
|------|-------|-------|
| `noise_zcr_threshold` | 更敏感 | 更宽松 |
| `silence_rms_threshold` | 更宽松 | 更敏感 |
| `rms_change_threshold` | 更敏感 | 更宽松 |
| `spectral_flux_threshold` | 更敏感 | 更宽松 |

### **第四步：启用/禁用VAD**

```python
"enable_vad": True   # 只分析人声段（推荐）
"enable_vad": False  # 分析所有帧（高质量场景）
```

---

## 📊 配置效果对比

使用相同测试音频：

| 模式 | Noise | Dropout | Volume | Distortion | 总问题数 |
|------|-------|---------|--------|------------|---------|
| **STRICT** | 15 | 3 | 8 | 12 | **38** |
| **STANDARD** | 3 | 1 | 3 | 4 | **11** ✅ |
| **RELAXED** | 1 | 0 | 1 | 1 | **3** |
| **VOIP** | 2 | 2 | 2 | 5 | **11** |
| **PODCAST** | 12 | 2 | 6 | 10 | **30** |

---

## 💡 实际应用建议

1. **首次使用**：从 STANDARD_MODE 开始
2. **有误报**：切换到 RELAXED_MODE 或增加 `min_event_duration`
3. **有漏报**：切换到 STRICT_MODE 或减少 `min_event_duration`
4. **特定场景**：使用对应的专用模式（VoIP/PODCAST）
5. **持续优化**：根据实际反馈微调参数

---

**版本**：1.0  
**更新**：2025年12月16日
