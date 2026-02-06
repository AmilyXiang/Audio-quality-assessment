#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matplotlib绘图配置 - 解决中文字体显示问题
Configure matplotlib for proper Chinese font display
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import sys
import platform


def configure_chinese_font():
    """
    配置matplotlib以正确显示中文字体
    解决中文显示为方块的问题
    
    Returns:
        FontProperties: 配置好的中文字体属性对象
    """
    system = platform.system()
    
    # 根据操作系统选择合适的中文字体
    if system == "Windows":
        # Windows系统常用中文字体
        chinese_fonts = [
            'Microsoft YaHei',  # 微软雅黑
            'SimHei',           # 黑体
            'SimSun',           # 宋体
            'KaiTi',            # 楷体
            'FangSong'          # 仿宋
        ]
    elif system == "Darwin":  # macOS
        chinese_fonts = [
            'PingFang SC',      # 苹方-简
            'Heiti SC',         # 黑体-简
            'STHeiti',          # 华文黑体
            'Arial Unicode MS'
        ]
    else:  # Linux
        chinese_fonts = [
            'WenQuanYi Micro Hei',  # 文泉驿微米黑
            'WenQuanYi Zen Hei',     # 文泉驿正黑
            'Noto Sans CJK SC',      # 思源黑体
            'Droid Sans Fallback'
        ]
    
    # 尝试找到可用的中文字体
    available_font = None
    from matplotlib.font_manager import findfont, FontProperties
    
    for font_name in chinese_fonts:
        try:
            fp = FontProperties(family=font_name)
            font_path = findfont(fp)
            # 如果找到的不是默认字体，说明该字体可用
            if font_name.lower() in font_path.lower() or 'sans' not in font_path.lower():
                available_font = font_name
                break
        except:
            continue
    
    # 如果没有找到，使用sans-serif作为后备
    if not available_font:
        if system == "Windows":
            available_font = 'SimHei'
        else:
            available_font = 'sans-serif'
        print(f"⚠️  警告: 未找到合适的中文字体，使用默认字体 '{available_font}'")
        print(f"   建议安装中文字体以获得更好的显示效果")
    
    # 配置matplotlib全局参数
    plt.rcParams['font.sans-serif'] = [available_font] + chinese_fonts + ['DejaVu Sans']
    plt.rcParams['font.family'] = 'sans-serif'
    
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False
    
    # 其他常用配置
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    
    print(f"✓ 已配置matplotlib中文字体: {available_font}")
    
    return FontProperties(family=available_font)


def get_chinese_font():
    """
    获取配置好的中文字体属性对象
    用于在特定文本中应用中文字体
    
    Returns:
        FontProperties: 中文字体属性对象
        
    Example:
        >>> font = get_chinese_font()
        >>> plt.title('中文标题', fontproperties=font)
    """
    return configure_chinese_font()


def test_chinese_display():
    """
    测试中文显示是否正常
    生成一个测试图表并保存
    """
    configure_chinese_font()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 测试各种中文文本
    test_texts = [
        "测试中文显示",
        "Test Chinese Characters 中英混合",
        "数字: 123456",
        "特殊符号: ！@#￥%……&*（）",
        "负数: -123.45"
    ]
    
    for i, text in enumerate(test_texts):
        ax.text(0.1, 0.8 - i * 0.15, text, 
                fontsize=12, 
                transform=ax.transAxes)
    
    ax.set_title('matplotlib中文字体测试', fontsize=16, pad=20)
    ax.set_xlabel('X轴标签', fontsize=12)
    ax.set_ylabel('Y轴标签', fontsize=12)
    ax.axis('off')
    
    # 保存图片
    output_path = 'chinese_font_test.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ 测试图片已保存: {output_path}")
    print("  请检查图片中的中文是否正常显示")
    
    plt.close()


def apply_report_style():
    """
    应用统一的报告图表样式
    为生成专业的分析报告图表提供一致的视觉风格
    """
    configure_chinese_font()
    
    # 专业报告样式配置
    plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
    
    plt.rcParams.update({
        # 字体大小
        'font.size': 10,
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        
        # 图形样式
        'axes.linewidth': 1.2,
        'grid.linewidth': 0.8,
        'lines.linewidth': 2.0,
        
        # 颜色
        'axes.prop_cycle': plt.cycler(color=[
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
        ]),
        
        # 网格
        'grid.alpha': 0.3,
        'axes.grid': True,
        'grid.linestyle': '--',
        
        # 图例
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.fancybox': True,
    })
    
    print("✓ 已应用报告图表样式")


if __name__ == '__main__':
    print("=" * 60)
    print("Matplotlib 中文字体配置工具")
    print("=" * 60)
    
    # 显示系统信息
    print(f"\n系统: {platform.system()}")
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"Matplotlib版本: {matplotlib.__version__}")
    
    # 配置并测试
    print("\n正在配置中文字体...")
    configure_chinese_font()
    
    print("\n生成测试图表...")
    test_chinese_display()
    
    print("\n" + "=" * 60)
    print("配置完成！")
    print("=" * 60)
