# 语音质量评估系统 - Voice Quality Assessment System

## 🎯 快速开始

```bash
# 1. 进入项目目录
cd voice_quality_tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 校准设备（第一次使用）
python calibrate.py ../robotic/1010baseline.wav -o device.json

# 4. 分析音频文件
python analyze_file.py ../robotic/1010bt161057-robot.wav -p device.json

# 5. 生成完整诊断
python analyze_file.py audio.wav -p device.json -o report.json
python analyzer/global_distortion_analyzer.py audio.wav ../robotic/1010baseline.wav
```

## 📚 完整文档索引

| 文档 | 说明 |
|------|------|
| [快速参考卡片](QUICK_REFERENCE.md) | ⭐ 5分钟快速上手 |
| [用户指南](voice_quality_tool/USER_GUIDE.md) | 详细使用说明 |
| [诊断完全指南](DIAGNOSIS_GUIDE.md) | 如何诊断问题 |
| [问题解决方案](PROBLEM_SOLUTION.md) | 整段变音检测原理 |
| [全局分析文档](GLOBAL_DISTORTION_ANALYSIS.md) | 新功能说明 |
| [文档总索引](INDEX.md) | 所有文档导航 |
| [工作总结](WORK_SUMMARY.md) | 项目完成情况 |

## 🔍 核心功能

### 1️⃣ 离散事件检测
- 检测噪声、卡顿、音量波动、失真
- 输出：事件列表（时间+类型）

### 2️⃣ 全局失真分析 ✨ 新增
- 检测整个文件的质量
- 检测合成/机器人语音
- 输出：失真指数 + 质量评分

### 3️⃣ 设备校准
- 自适应不同设备特性
- 减少误报率

## 💻 系统要求

- Python 3.8+
- numpy, scipy, pyaudio
- 操作系统：Windows/Linux/macOS

## 🚀 典型使用流程

```bash
# 步骤1：校准设备（一次性）
python calibrate.py your_baseline.wav -o device.json

# 步骤2：分析文件（检测离散问题）
python analyze_file.py test.wav -p device.json -o events.json

# 步骤3：全局分析（检测全局失真）
python analyzer/global_distortion_analyzer.py test.wav your_baseline.wav

# 步骤4：查看诊断结果
cat events.json                              # 离散事件
# （全局分析结果在控制台输出）
```

## 📊 系统架构

```
语音质量评估系统
├─ 离散事件检测（Event-based）
│  ├─ 噪声检测
│  ├─ 卡顿检测
│  ├─ 音量检测
│  └─ 失真检测
│
├─ 全局失真分析（File-level） ← 新增
│  ├─ 13维特征提取
│  ├─ 与基线对比
│  ├─ 失真指数计算
│  └─ 质量评估
│
└─ 双系统诊断
   └─ 完整问题诊断
```

## ✨ 亮点特性

✅ **双系统互补** - 检测离散问题和全局失真  
✅ **自适应校准** - 支持不同设备自动调整  
✅ **语音活动检测(VAD)** - 减少背景干扰误报  
✅ **人耳感知对齐** - 基于研究的检测阈值  
✅ **完整诊断** - 精确定位问题位置和类型  
✅ **易于集成** - 提供Python API和REST示例  

## 🎓 学习路径

### 🏃 快速入门（15分钟）
1. 读 [快速参考卡片](QUICK_REFERENCE.md)
2. 运行 `python test_analyzer.py`
3. 开始使用

### 📖 完整学习（1小时）
1. 读 [快速参考卡片](QUICK_REFERENCE.md)
2. 读 [用户指南](voice_quality_tool/USER_GUIDE.md)
3. 读 [诊断完全指南](DIAGNOSIS_GUIDE.md)
4. 实验和测试

### 🔬 深度研究（2小时+）
1. 所有学习路径的内容
2. 读 [问题解决方案](PROBLEM_SOLUTION.md)
3. 读 [技术实现细节](IMPLEMENTATION_SUMMARY.md)
4. 研究源代码

## 🆘 常见问题

**Q: 我应该使用哪个工具？**

A: 取决于你的需求：
- 只关心有没有问题 → 使用 `analyze_file.py`
- 需要完整诊断 → 两个都用
- 需要合成语音检测 → 必须用 `global_distortion_analyzer.py`

**Q: 为什么只检测到音量波动？**

A: 详见 [问题解决方案](PROBLEM_SOLUTION.md)，简单来说：
- 离散检测器检查"哪些帧不同"
- 整段机器人语音"所有帧都一样" → 检测不到
- 解决方案：使用全局分析器

**Q: 需要多少时间设置？**

A: 
- 首次安装：5分钟
- 校准设备：1分钟
- 分析文件：几秒钟

## 📞 获取帮助

1. **快速问题** → [快速参考卡片 - 常见错误](QUICK_REFERENCE.md)
2. **怎么用** → [用户指南](voice_quality_tool/USER_GUIDE.md)
3. **有故障** → [诊断完全指南](DIAGNOSIS_GUIDE.md)
4. **为什么** → [问题解决方案](PROBLEM_SOLUTION.md)
5. **深度** → [技术实现细节](IMPLEMENTATION_SUMMARY.md)

## 📈 项目统计

- 代码行数：3000+
- 文档：9份（70KB+）
- 测试用例：3个
- 支持语言：中文、英文
- 更新频率：持续维护

## ✅ 功能对标

| 功能 | 支持 | 说明 |
|------|------|------|
| 离散问题检测 | ✅ | 噪声、卡顿、音量、失真 |
| 全局失真检测 | ✅ | 新增功能 |
| 合成语音识别 | ✅ | 通过全局分析 |
| 设备校准 | ✅ | 自适应不同设备 |
| 实时处理 | ⚠️ | 支持点问题，离线计算全局 |
| 深度欺骗检测 | ❌ | 需要专门模型 |

## 📜 许可证

本项目为教学和研究之用。

## 🙏 致谢

- 基于ITU-T和学术研究的检测阈值
- 感谢所有用户的反馈和建议

---

**版本**: 2.0  
**最后更新**: 2025年12月16日  
**状态**: ✅ 稳定版本，可用于生产

👉 **立即开始**: [快速参考卡片](QUICK_REFERENCE.md)
