"""分析baseline_compare数据，理解帧级矛盾"""
import json

compare_json = r"d:\Audio quality assessment\Audio-quality-assessment\voice_quality_tool\nisqa\baseline_compare_260206142602_30.1.65.182_BOXP_WHS_R.json"

with open(compare_json, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("文件级 vs 帧级对比分析")
print("=" * 80)

print("\n【文件级对比】")
print(f"基准文件级MOS: {data['file_level']['baseline']['mos']:.3f}")
print(f"测试文件级MOS: {data['file_level']['test']['mos']:.3f}")
print(f"文件级差值: {data['file_level']['diff']['mos']:+.3f}")

if data['file_level']['diff']['mos'] > 0:
    print("✓ 测试文件整体质量 优于 基准")
else:
    print("✗ 测试文件整体质量 劣于 基准")

print("\n【帧级对比 - 前10帧】")
print(f"{'帧ID':<6} {'时间窗口':<18} {'基准帧MOS':<12} {'测试帧MOS':<12} {'差值':<10} {'状态'}")
print("-" * 85)

frame_diffs = data['metrics']['mos']['frame_diffs']
for f in frame_diffs[:10]:
    status = "✓ 优于" if f['diff'] > 0 else "✗ 劣于"
    print(f"{f['frame_id']:<6} {f['time_start']:.1f}s-{f['time_end']:.1f}s{'':<8} {f['baseline_value']:<12.3f} {f['test_value']:<12.3f} {f['diff']:<+10.3f} {status}")

stats = data['metrics']['mos']['stats']
print(f"\n【帧级统计】")
print(f"总帧数: {len(frame_diffs)}")
print(f"劣于基准帧数: {stats['frames_below_baseline']} ({stats['percent_below_baseline']:.1f}%)")
print(f"帧级平均差值: {stats['mean_diff']:+.3f}")
print(f"帧级中位数差值: {stats['median_diff']:+.3f}")

print("\n" + "=" * 80)
print("矛盾分析")
print("=" * 80)

print(f"\n文件级差值: {data['file_level']['diff']['mos']:+.3f}")
print(f"帧级平均差值: {stats['mean_diff']:+.3f}")
print(f"差异: {abs(data['file_level']['diff']['mos'] - stats['mean_diff']):.3f}")

if abs(data['file_level']['diff']['mos'] - stats['mean_diff']) > 0.3:
    print("\n⚠️  发现严重矛盾！")
    print("   文件级显示测试优于基准")
    print("   但帧级显示测试严重劣于基准")
    print("\n可能的原因：")
    print("1. ❌ 框级对比错误：两个音频不是同一段内容")
    print("2. ❌ 基准选择错误：基准质量本身就很低")
    print("3. ❌ NISQA模型问题：文件级和帧级评分算法不一致")
    
print("\n让我检查基准文件的绝对质量：")
print(f"\n基准文件各维度得分：")
for dim in ['mos', 'noi', 'dis', 'col', 'loud']:
    score = data['file_level']['baseline'][dim]
    print(f"  {dim.upper()}: {score:.3f}", end="")
    if dim == 'mos':
        if score < 2.5:
            print(" ⚠️  极差质量")
        elif score < 3.0:
            print(" ⚠️  较差质量")  
        elif score < 3.5:
            print(" 中等质量")
        else:
            print(" ✓ 良好质量")
    else:
        if score < 3.0:
            print(" ⚠️  差")
        elif score < 4.0:
            print(" 中等")
        else:
            print(" ✓ 好")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)

baseline_mos = data['file_level']['baseline']['mos']
if baseline_mos < 3.0:
    print(f"\n❌ 核心问题：基准文件质量极差 (MOS={baseline_mos:.3f})")
    print("\n您选择的 BOXP_WHS_R.wav 作为基准是不合适的！")
    print("这个文件本身质量就很低，不适合作为参考标准。")
    print("\n建议：")
    print("1. 选择一个高质量音频（MOS > 3.5）作为基准")
    print("2. 或者使用 analyze_nisqa.py 直接评估每个文件的绝对质量")
    print("3. 不要使用帧级对比，只看文件级的绝对分数")
else:
    print("\n基准质量尚可，但仍存在帧级/文件级矛盾")
    print("建议进一步检查音频内容是否真的相同")
