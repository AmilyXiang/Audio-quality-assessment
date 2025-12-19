# Copilot Instructions for Voice Quality Assessment System

## 🏗️ 项目架构与核心组件
- 本项目分为两大检测体系：
  - **离散事件检测**（噪声、卡顿、音量波动、失真）：入口为 `voice_quality_tool/analyze_file.py`，核心逻辑在 `analyzer/` 和 `detectors/`。
  - **全局失真分析**：入口为 `voice_quality_tool/analyzer/global_distortion_analyzer.py`，需基线音频对比，适合合成/机器人音检测。
- 设备校准通过 `voice_quality_tool/calibrate.py`，生成设备特定参数（如 `device.json`）。
- 所有检测算法依赖 5 项音频特征（RMS, ZCR, Spectral Centroid, Bandwidth, Flux），详见 `docs/DETECTION_PRINCIPLES.md`。

## ⚡ 开发与运行流程
- 推荐 Python 3.8+，依赖见 `requirements.txt`。
- 离线分析：`python analyze_file.py <audio.wav> -p <device.json> -o <report.json>`
- 实时分析：`python analyze_mic.py [duration]`
- 全局分析：`python analyzer/global_distortion_analyzer.py <audio.wav> <baseline.wav>`
- 校准设备：`python calibrate.py <baseline.wav> -o <device.json>`
- 配置参数可在 `analyzer.py` 的 `DEFAULT_CONFIG` 或 `docs/DETECTION_PRINCIPLES.md` 查找和调整。

## 🧩 代码结构与约定
- 事件检测器均实现于 `detectors/`，继承自 `base.py`，统一接口，便于扩展。
- 特征提取逻辑集中于 `features.py`，帧切分在 `frame.py`。
- 检测结果通过 `result.py` 聚合，输出为 JSON（离线）或列表（实时）。
- 配置预设（如 CLEAN_SPEECH_CONFIG）可参考 `docs/DETECTION_PRINCIPLES.md`。
- 主要文档入口见根目录和 `voice_quality_tool/docs/`，如 `USER_GUIDE.md`、`QUICK_REFERENCE.md`。

## 🛠️ 调试与测试
- 推荐先运行校准流程，确保设备参数匹配。
- 支持自定义阈值，调优建议见 `docs/DETECTION_PRINCIPLES.md`。
- 常见问题与故障排查见 `README.md` 和 `PROBLEM_SOLUTION.md`。
- 典型输出格式和事件类型见 `voice_quality_tool/README.md`。

## 🔗 关键文件/目录参考
- `voice_quality_tool/analyze_file.py`：离线分析主入口
- `voice_quality_tool/analyze_mic.py`：实时分析主入口
- `voice_quality_tool/analyzer/`：核心分析与调度
- `voice_quality_tool/analyzer/detectors/`：各类检测器实现
- `voice_quality_tool/docs/DETECTION_PRINCIPLES.md`：检测原理与参数说明
- `voice_quality_tool/USER_GUIDE.md`：详细用户指南

## 📝 约定与风格
- 所有检测器参数均可配置，优先查阅文档和 `DEFAULT_CONFIG`。
- 事件时间单位为秒，输出为浮点数。
- 支持中英文文档，代码注释以英文为主。
- 诊断结果以 JSON 或列表结构输出，便于集成。

---
如遇不明确的结构或流程，优先查阅 `README.md`、`USER_GUIDE.md` 和 `docs/DETECTION_PRINCIPLES.md`，或参考示例命令。
