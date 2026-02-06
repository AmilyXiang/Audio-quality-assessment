# 解决matplotlib中文显示问题 - 只需在绘图文件开头加这两行
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 黑体/微软雅黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
