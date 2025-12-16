#!/usr/bin/env python3
"""
测试全局失真检测器
对比baseline和robot文件的整体特征
"""

import os
import sys
from analyzer.global_distortion_analyzer import GlobalDistortionAnalyzer


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    robotic_dir = os.path.join(os.path.dirname(base_dir), 'robotic')
    
    baseline_file = os.path.join(robotic_dir, '1010baseline.wav')
    robot_file = os.path.join(robotic_dir, '1010bt161057-robot.wav')
    
    if not os.path.exists(baseline_file):
        print(f"❌ 基线文件不存在: {baseline_file}")
        return
    
    if not os.path.exists(robot_file):
        print(f"❌ 机器人文件不存在: {robot_file}")
        return
    
    print("\n" + "=" * 70)
    print("🔬 全局失真检测 - 机器人语音分析")
    print("=" * 70)
    
    analyzer = GlobalDistortionAnalyzer()
    
    # 分析baseline（参考标准）
    print("\n" + "▶️  步骤1: 分析基线文件（参考标准）")
    baseline_result = analyzer.analyze_file(baseline_file)
    
    # 分析robot文件（与baseline对比）
    print("\n" + "▶️  步骤2: 分析机器人文件（与基线对比）")
    robot_result = analyzer.analyze_file(robot_file, baseline_file)
    
    # 总结
    print("\n" + "=" * 70)
    print("📋 分析总结")
    print("=" * 70)
    
    print(f"\n基线文件质量: {baseline_result['quality_assessment']['overall_quality']}")
    print(f"            分数: {baseline_result['quality_assessment']['quality_score']:.2f}")
    
    print(f"\n机器人文件质量: {robot_result['quality_assessment']['overall_quality']}")
    print(f"              分数: {robot_result['quality_assessment']['quality_score']:.2f}")
    
    if robot_result['baseline_comparison']:
        distortion_index = robot_result['baseline_comparison']['overall_distortion_index']
        print(f"\n失真指数: {distortion_index:.2%}")
        
        if distortion_index > 0.30:
            print(f"\n🚨 结论: 整段文件检测到严重系统性失真")
            print(f"\n这解释了为什么:")
            print(f"  • 离散事件检测器无法检测全程失真")
            print(f"  • 只有音量波动被检测到（相对变化）")
            print(f"  • 整体特征与基线不符")
            
            print(f"\n建议:")
            print(f"  1. 使用全局分析器检测系统性失真")
            print(f"  2. 组合使用事件检测（离散问题）和全局分析（整体质量）")
            print(f"  3. 区分: 局部问题 vs 全局失真")
        
        elif distortion_index > 0.15:
            print(f"\n⚠️  结论: 检测到中等程度的系统性失真")
        else:
            print(f"\n✓ 结论: 文件质量与基线相近")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
