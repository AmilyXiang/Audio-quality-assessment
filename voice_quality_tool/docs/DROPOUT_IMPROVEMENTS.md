# Dropout 检测改进说明

## 问题描述

之前的 Dropout 检测器只能检测**陡降到静音**（缓冲区欠流、网络丢包）。用户指出还应该检测**陡增**（音量突然增大、啸叫、反馈等不连续现象）。

## 改进内容

现在 DropoutDetector 检测三种不连续现象：

### 1. 陡降到静音（之前就有）
- **触发条件**：RMS < 0.01 AND ZCR < 0.05
- **含义**：突然无声，可能是缓冲区欠流、网络丢包、编码器问题
- **示例**：网络电话突然中断、视频会议掉线

```
音量:  ▄▄▄▄▃▁ ▁▁▁  ▄▄▄▄  
时间:  ─────  ↓↓↓  ─────
       正常   陡降   恢复
```

### 2. 陡增到过大（新增）
- **触发条件**：当前 RMS > 历史平均值 × 3.0，且历史平均值 > 0.05
- **含义**：音量突然增大，可能是尖刺、啸叫、反馈、突然的话筒碰撞
- **示例**：播客中的突然尖叫声、电话中的刺耳声音、麦克风反馈

```
音量:  ▄▄▄▃  ▇▇▇  ▃▄▄▄
时间:  ──── ↑↑↑ ────
       正常 陡增  恢复
```

### 3. 持续低能量段落（通过阈值检测）
- 检测无声或极低能量的连续段落
- 可能指示编码器问题或设备静音

## 代码改动

### 文件修改
1. **analyzer/detectors/dropout.py**
   - 新增 `spike_rms_threshold` 参数
   - 添加陡增检测逻辑
   - 改进事件详情信息

2. **analyzer/analyzer.py**
   - DEFAULT_CONFIG 中新增 `spike_rms_threshold: 0.8`
   - 添加参数注释

## 配置参数

### 默认配置
```python
# Dropout detection
"silence_rms_threshold": 0.01,      # 静音门槛
"dropout_zcr_threshold": 0.05,      # 零交叉率门槛
"spike_rms_threshold": 0.8,         # 突增倍数（3倍判断为突增）
```

### 干净语音配置
保持不变，因为 Dropout 通常更严格（不需要放宽）。

## 应用场景

### 什么时候会检测到陡增
- 📻 **播客/访谈**：突然大喊、尖叫、笑声
- 📞 **电话**：话筒啸叫、突然的背景噪声爆发
- 🎙️ **录音**：麦克风碰撞、风声、反馈
- 🎮 **游戏直播**：突然的系统声音、警报

### 不会检测为陡增的情况
- 正常的语调变化（检测器对比历史记录，允许3倍变化）
- 自然的情感表达（音量起伏）
- 重音强调（在正常范围内）

## 测试示例

### 分析默认模式（包括陡增检测）
```bash
python analyze_file.py audio.wav
```

### 检查dropout事件详情
```json
{
  "dropout": {
    "count": 2,
    "events": [
      {
        "start": 5.23,
        "end": 5.45,
        "reason": "sudden_dropout_silence",
        "details": {"rms": 0.003, "zcr": 0.02}
      },
      {
        "start": 12.10,
        "end": 12.35,
        "reason": "sudden_spike_loud",
        "details": {
          "current_rms": 0.92,
          "avg_rms": 0.25,
          "spike_ratio": 3.68
        }
      }
    ]
  }
}
```

## 事件原因标记

- `sudden_dropout_silence`: 音量陡降到静音
- `sudden_spike_loud`: 音量陡增（突然增大 3 倍以上）
- 其他future: 可扩展的事件类型

## 参数调优建议

### 如果误报过多
增大陡增的倍数阈值或对比帧数：
```python
# 不是 3 倍，改成 5 倍
if rms > avg_rms * 5.0:  # 更严格

# 或增加对比窗口
self.min_history_frames = 10  # 从5改成10
```

### 如果漏检
降低陡增的倍数阈值：
```python
if rms > avg_rms * 2.0:  # 更敏感
```

## 兼容性

- ✅ 与既有的 Noise、Volume、Distortion 检测器兼容
- ✅ 支持所有分析模式（default 和 clean-speech）
- ✅ JSON 输出格式不变，只是详情更详尽

## 总结

| 检测类型 | 原名称 | 新改进 | 示例 |
|---------|--------|--------|------|
| 陡降 | Dropout (silence) | ✓ 保留 | 网络掉线、缓冲欠流 |
| 陡增 | **Dropout (spike)** | ✅ 新增 | 突然尖叫、啸叫、反馈 |
| 波动 | Volume Fluctuation | - 不变 | AGC泵浦效应、自然起伏 |
