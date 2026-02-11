"""检查音频文件的时长和对齐情况"""
import librosa
import numpy as np
import json

# 基准文件和测试文件
baseline_wav = r"C:\Users\Amily\Downloads\BOXP_WHS_R.wav"
test_wav = r"C:\Users\Amily\Downloads\260206142707_30.1.65.182_BOXP_WHS_R\260206142602_30.1.65.182_BOXP_WHS_R.wav"

# 检查framewise JSON
baseline_json = r"d:\Audio quality assessment\Audio-quality-assessment\voice_quality_tool\nisqa\framewise_BOXP_WHS_R.json"
test_json = r"d:\Audio quality assessment\Audio-quality-assessment\voice_quality_tool\nisqa\framewise_260206142602_30.1.65.182_BOXP_WHS_R.json"

print("=" * 80)
print("音频文件时长检查")
print("=" * 80)

# 加载音频文件
y1, sr1 = librosa.load(baseline_wav, sr=None)
y2, sr2 = librosa.load(test_wav, sr=None)

duration1 = len(y1) / sr1
duration2 = len(y2) / sr2

print(f"\n基准文件: BOXP_WHS_R.wav")
print(f"  采样率: {sr1} Hz")
print(f"  样本数: {len(y1)}")
print(f"  时长: {duration1:.3f} 秒")

print(f"\n测试文件: 260206142602_30.1.65.182_BOXP_WHS_R.wav")
print(f"  采样率: {sr2} Hz")
print(f"  样本数: {len(y2)}")
print(f"  时长: {duration2:.3f} 秒")

print(f"\n时长差异: {abs(duration1 - duration2):.3f} 秒")

if abs(duration1 - duration2) > 0.1:
    print("⚠️  警告: 两个音频文件时长不同！帧级对比可能不准确！")
else:
    print("✓ 时长基本一致")

# 检查JSON文件中的帧数据
print("\n" + "=" * 80)
print("帧级数据检查")
print("=" * 80)

with open(baseline_json, 'r', encoding='utf-8') as f:
    baseline_data = json.load(f)

with open(test_json, 'r', encoding='utf-8') as f:
    test_data = json.load(f)

baseline_frames = baseline_data['frame_level']['frames']
test_frames = test_data['frame_level']['frames']

print(f"\n基准帧数: {len(baseline_frames)}")
print(f"测试帧数: {len(test_frames)}")

print(f"\n前5帧对比:")
print(f"{'Frame':<8} {'基准时间':<20} {'测试时间':<20} {'基准MOS':<12} {'测试MOS':<12}")
print("-" * 80)
for i in range(min(5, len(baseline_frames), len(test_frames))):
    bf = baseline_frames[i]
    tf = test_frames[i]
    print(f"{i:<8} {bf['time_start']:.1f}-{bf['time_end']:.1f}s{'':<8} {tf['time_start']:.1f}-{tf['time_end']:.1f}s{'':<8} {bf['mos']:<12.3f} {tf['mos']:<12.3f}")

# 检查VAD（语音活动检测）- 看看静音段分布
print("\n" + "=" * 80)
print("能量分布检查（检测静音段）")
print("=" * 80)

# 计算RMS能量
frame_length = 2048
hop_length = 512

rms1 = librosa.feature.rms(y=y1, frame_length=frame_length, hop_length=hop_length)[0]
rms2 = librosa.feature.rms(y=y2, frame_length=frame_length, hop_length=hop_length)[0]

# 找到语音起始点（能量超过阈值的第一个位置）
threshold = 0.02
speech_start1 = np.argmax(rms1 > threshold) * hop_length / sr1
speech_start2 = np.argmax(rms2 > threshold) * hop_length / sr2

print(f"\n基准文件语音起始: {speech_start1:.3f} 秒")
print(f"测试文件语音起始: {speech_start2:.3f} 秒")
print(f"起始点差异: {abs(speech_start1 - speech_start2):.3f} 秒")

if abs(speech_start1 - speech_start2) > 0.5:
    print("\n⚠️  警告: 两个音频的语音起始点相差较大！")
    print("   这意味着虽然时间窗口对齐，但实际语音内容没有对齐！")
    print("   帧级对比结果不可靠！")
else:
    print("\n✓ 语音起始点基本对齐")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)

if abs(duration1 - duration2) > 0.1 or abs(speech_start1 - speech_start2) > 0.5:
    print("\n❌ 音频文件未对齐！帧级对比结果不可信！")
    print("\n建议：")
    print("1. 使用DTW（动态时间规整）算法对齐音频")
    print("2. 或者只使用文件级对比（忽略帧级结果）")
    print("3. 或者检查音频是否确实是同一段语音的不同版本")
else:
    print("\n✓ 音频基本对齐，帧级对比可信")
    print("\n但是，帧级MOS差异很大的原因可能是：")
    print("1. NISQA模型对帧的评分波动较大")
    print("2. 每一帧（15秒窗口）内的语音内容真的质量不同")
    print("3. 需要检查是否是同一段语音的不同传输/编码版本")
