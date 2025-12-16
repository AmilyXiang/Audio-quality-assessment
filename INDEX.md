# 📚 语音质量评估系统 - 完整文档索引

## 🎯 快速导航

### 🆘 我想...

| 我想... | 去看这个 |
|---------|----------|
| **快速上手** | [快速参考卡片](QUICK_REFERENCE.md) - 5分钟了解全部 |
| **完整学习** | [用户指南](voice_quality_tool/USER_GUIDE.md) - 详细所有功能 |
| **诊断问题** | [诊断完全指南](DIAGNOSIS_GUIDE.md) - 症状查询表 |
| **理解设计** | [问题解决方案](PROBLEM_SOLUTION.md) - 为什么这样设计 |
| **研究原理** | [技术实现细节](IMPLEMENTATION_SUMMARY.md) - 深度技术文档 |
| **特定案例** | [机器人语音分析](ROBOTIC_ANALYSIS_REPORT.md) - 实际数据分析 |
| **全局失真** | [全局分析文档](GLOBAL_DISTORTION_ANALYSIS.md) - 新功能说明 |

---

## 📖 文档全览

### 1️⃣ 快速参考卡片
**文件**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)  
**长度**: 6.7KB  
**目的**: 最快速的参考

**包含**:
- ⚡ 一行诊断
- 📊 诊断表
- 🎯 决策矩阵
- 📋 标准流程
- ⚙️ 参数调优
- 🆘 常见错误

**适合**: 已有基础、需要快速查询的人

**示例**:
```bash
python analyze_file.py audio.wav -p device.json
python analyzer/global_distortion_analyzer.py audio.wav baseline.wav
```

---

### 2️⃣ 用户指南
**文件**: [voice_quality_tool/USER_GUIDE.md](voice_quality_tool/USER_GUIDE.md)  
**长度**: 超长  
**目的**: 完整的使用手册

**包含**:
- 🚀 快速开始
- 📝 基础使用（离线、实时）
- 🔧 高级功能（校准、VAD）
- ⚙️ 配置调整（预设、自定义）
- 🎯 实际场景（5种场景）
- 💻 API集成
- 🐛 故障排查

**适合**: 新手用户、需要学习所有功能的人

**特色**:
- PowerShell/Bash 脚本示例
- REST API 封装示例
- Python 集成代码
- 批量处理方案

---

### 3️⃣ 诊断完全指南
**文件**: [DIAGNOSIS_GUIDE.md](DIAGNOSIS_GUIDE.md)  
**长度**: 11.4KB  
**目的**: 双系统的集成指南

**包含**:
- 🎯 核心理念（双层诊断）
- 📊 案例研究（机器人语音）
- 📋 使用流程
- 🛠️ 集成到应用
- 🎓 决策树
- ✅ 检查清单
- 📞 常见问题

**适合**: 需要集成系统、需要诊断指导的人

**亮点**:
- 离散 vs 全局对比
- 集成代码示例
- 决策流程图
- 应用场景矩阵

---

### 4️⃣ 问题解决方案
**文件**: [PROBLEM_SOLUTION.md](PROBLEM_SOLUTION.md)  
**长度**: 9.3KB  
**目的**: 解释"为什么原系统看不出变音"

**包含**:
- ❓ 问题陈述
- 🔬 根本原因分析
- ✅ 解决方案详解
- 📊 验证结果
- 💡 系统设计的智慧

**适合**: 想理解系统设计的人、需要技术论证的人

**核心内容**:
```
原系统：检测点的差异 (逐帧比对)
  ✓ 快、准、实用
  ✗ 无法检测全局失真

新系统：检测全局特征 (与基线对比)
  ✓ 检测整段变音
  ✓ 检测合成语音
  + 互补原系统
```

---

### 5️⃣ 全局失真分析
**文件**: [GLOBAL_DISTORTION_ANALYSIS.md](GLOBAL_DISTORTION_ANALYSIS.md)  
**长度**: 7.8KB  
**目的**: 新增功能的详细说明

**包含**:
- 📊 关键发现
- 🔬 测试数据对比表
- 🎯 核心问题解析
- 💡 改进方案
- 🚀 后续建议

**适合**: 想了解全局分析器的人

**数据亮点**:
```
基线 vs 机器人文件:
- Harmonic Clarity: +109% 异常
- Mel Flatness: +217% 异常
- 失真指数: 17.73%
```

---

### 6️⃣ 机器人语音分析
**文件**: [ROBOTIC_ANALYSIS_REPORT.md](ROBOTIC_ANALYSIS_REPORT.md)  
**长度**: 8.6KB  
**目的**: 实际案例分析

**包含**:
- 📊 分析摘要
- 🔍 分析结果对比
- 🔬 技术分析
- 📈 详细事件分析
- 💡 改进方案

**适合**: 想看实际案例、想理解数据的人

**案例**:
```
1010baseline.wav (基线)
1010bt161057-robot.wav (机器人语音)

发现: 用全局分析检测出17.73%失真
```

---

### 7️⃣ 技术实现细节
**文件**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)  
**长度**: 8.8KB  
**目的**: 代码实现细节

**包含**:
- 📁 项目结构
- 🔧 各组件功能
- 🎯 核心算法
- 🐛 问题修复历程
- 📊 验证结果

**适合**: 想研究代码、想修改系统的人

---

## 🎓 学习路径

### 路径A：快速上手（15分钟）
1. [快速参考卡片](QUICK_REFERENCE.md) - 了解基本操作
2. `python test_global_distortion.py` - 实际运行看效果
3. 开始使用

### 路径B：完整学习（1小时）
1. [快速参考卡片](QUICK_REFERENCE.md) - 快速概览
2. [用户指南](voice_quality_tool/USER_GUIDE.md) - 学习所有功能
3. [诊断完全指南](DIAGNOSIS_GUIDE.md) - 理解如何使用
4. 实验和测试

### 路径C：深度研究（2小时）
1. [问题解决方案](PROBLEM_SOLUTION.md) - 理解系统设计
2. [全局分析文档](GLOBAL_DISTORTION_ANALYSIS.md) - 新功能原理
3. [机器人语音分析](ROBOTIC_ANALYSIS_REPORT.md) - 实际案例
4. [技术实现细节](IMPLEMENTATION_SUMMARY.md) - 代码级别
5. 研究源代码

### 路径D：问题诊断（按症状查询）
1. 出现问题 → [快速参考卡片](QUICK_REFERENCE.md) 症状诊断表
2. 找到症状 → 查看解决方案
3. 需要更深入 → [诊断完全指南](DIAGNOSIS_GUIDE.md)

---

## 📁 项目结构

```
Audio-quality-assessment/
├─ README.md                          # 项目简介 (78B)
├─ QUICK_REFERENCE.md                 # ⭐ 快速参考卡片
├─ USER_GUIDE.md                      # (在voice_quality_tool/)
├─ DIAGNOSIS_GUIDE.md                 # 诊断完全指南
├─ PROBLEM_SOLUTION.md                # 问题解决方案
├─ GLOBAL_DISTORTION_ANALYSIS.md      # 全局分析说明
├─ ROBOTIC_ANALYSIS_REPORT.md         # 机器人语音分析
├─ IMPLEMENTATION_SUMMARY.md          # 技术实现细节
│
├─ voice_quality_tool/
│  ├─ analyze_file.py                 # 离线文件分析
│  ├─ analyze_mic.py                  # 实时麦克风分析
│  ├─ calibrate.py                    # 设备校准
│  ├─ test_analyzer.py                # 测试脚本
│  ├─ test_global_distortion.py       # 全局分析测试
│  ├─ test_enhanced_distortion.py     # 增强失真检测测试
│  ├─ requirements.txt
│  ├─ USER_GUIDE.md                   # 完整用户指南
│  │
│  └─ analyzer/
│     ├─ __init__.py
│     ├─ analyzer.py                  # 主分析器
│     ├─ frame.py                     # 帧分割
│     ├─ features.py                  # 特征提取
│     ├─ result.py                    # 结果聚合
│     ├─ vad.py                       # 语音活动检测
│     ├─ global_distortion_analyzer.py # ⭐ 全局分析器
│     │
│     └─ detectors/
│        ├─ base.py                   # 基类
│        ├─ noise.py                  # 噪声检测
│        ├─ dropout.py                # 卡顿检测
│        ├─ volume.py                 # 音量检测
│        ├─ distortion.py             # 失真检测
│        └─ enhanced_distortion.py    # 增强失真检测
│
└─ robotic/
   ├─ 1010baseline.wav                # 基线文件
   ├─ 1010bt161057-robot.wav          # 机器人语音
   └─ ... (其他测试文件)
```

---

## 🚀 快速命令

```bash
# 基础检测
python analyze_file.py audio.wav

# 校准设备
python calibrate.py baseline.wav -o device.json

# 完整诊断
python analyze_file.py audio.wav -p device.json -o events.json
python analyzer/global_distortion_analyzer.py audio.wav baseline.wav

# 运行测试
python test_analyzer.py
python test_global_distortion.py
```

---

## 📊 系统对比

| 功能 | 离散检测 | 全局分析 | 综合 |
|------|---------|---------|------|
| 检测点问题 | ✅ | ❌ | ✅ |
| 检测全局失真 | ❌ | ✅ | ✅ |
| 检测合成语音 | ❌ | ✅ | ✅ |
| 实时处理 | ✅ | ❌ | ✅* |
| 计算效率 | 高 | 中 | 中 |
| 准确性 | 高(点) | 高(全) | 高 |

*: 实时处理点问题，离线计算全局特征

---

## 🎓 核心概念

### 离散检测（Event-based）
```
工作原理：逐帧分析，发现异常帧
场景：正常语音 + 问题点
输出：事件列表 (时间+类型)
例子：[0.5-1.2s: NOISE, 3.2-3.5s: DROPOUT]
```

### 全局分析（File-level）
```
工作原理：计算全局特征，与基线对比
场景：整个文件的质量评估
输出：质量评分 + 失真指数
例子：失真指数 17.73%, 质量分数 0.45/1.00
```

### 双系统诊断
```
组合：离散事件 + 全局特征
结果：完整诊断
效果：
  • 检测局部问题 ✅
  • 检测全局失真 ✅
  • 识别异常模式 ✅
```

---

## 💾 关键文件位置

| 功能 | 文件 | 使用场景 |
|------|------|---------|
| 离散分析 | `analyze_file.py` | 日常使用 |
| 全局分析 | `analyzer/global_distortion_analyzer.py` | 质量评估 |
| 设备校准 | `calibrate.py` | 第一次设置 |
| 测试 | `test_analyzer.py`, `test_global_distortion.py` | 验证系统 |
| 增强失真 | `analyzer/detectors/enhanced_distortion.py` | 高级检测 |

---

## 📞 获取帮助

1. **快速问题** → [快速参考卡片](QUICK_REFERENCE.md) 常见错误章节
2. **怎么用** → [用户指南](voice_quality_tool/USER_GUIDE.md)
3. **有故障** → [诊断完全指南](DIAGNOSIS_GUIDE.md)
4. **想了解** → [问题解决方案](PROBLEM_SOLUTION.md)
5. **想研究** → [技术实现细节](IMPLEMENTATION_SUMMARY.md)

---

## ✅ 检查清单

部署前：
- [ ] 阅读 [快速参考卡片](QUICK_REFERENCE.md)
- [ ] 运行 `python test_analyzer.py`
- [ ] 运行 `python test_global_distortion.py`
- [ ] 校准设备：`python calibrate.py baseline.wav`

使用中：
- [ ] 理解离散 vs 全局分析的区别
- [ ] 知道如何诊断问题
- [ ] 掌握参数调优方法

---

## 📈 统计

```
文档总数：8个
总字数：约 60KB
代码行数：3000+ 行
测试用例：3个

覆盖范围：
✅ 基础使用
✅ 高级功能
✅ API集成
✅ 故障排查
✅ 案例分析
✅ 技术深度
```

---

## 🎯 一句话总结

```
原系统检测离散问题，新系统检测全局失真，
双系统互补，完整诊断。
```

---

**最后更新**：2025年12月16日  
**版本**：2.0  
**状态**：✅ 完整且可用
