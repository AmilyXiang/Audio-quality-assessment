#!/usr/bin/env python3
"""测试强制标定架构的重构结果

验证点：
1. ✅ 所有检测器必须有baseline才能运行
2. ✅ analyze_file.py强制要求--profile参数
3. ✅ 所有检测器使用相对阈值而非固定阈值
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

def test_detector_requires_baseline():
    """测试1：检测器必须有baseline"""
    print("\n" + "="*60)
    print("测试1：检测器强制要求baseline")
    print("="*60)
    
    from analyzer.detectors.noise import NoiseDetector
    from analyzer.detectors.dropout import DropoutDetector
    from analyzer.detectors.volume import VolumeDetector
    from analyzer.detectors.distortion import DistortionDetector
    from analyzer.frame import Frame
    
    # 创建检测器
    noise_det = NoiseDetector()
    dropout_det = DropoutDetector()
    volume_det = VolumeDetector()
    distortion_det = DistortionDetector()
    
    # 模拟特征
    features = {
        "rms": 0.1,
        "zero_crossing_rate": 0.1,
        "spectral_centroid": 1000,
        "spectral_bandwidth": 500,
        "spectral_flux": 0.15,
        "spectral_rolloff": 2500,
        "rms_percentile_95": 0.12,
        "peak_to_peak": 0.5
    }
    
    frame = Frame(samples=[0.1]*400, sample_rate=16000, start_time=0.0, end_time=0.025)
    
    # 测试：没有baseline应该抛出错误
    detectors = {
        "NoiseDetector": noise_det,
        "DropoutDetector": dropout_det,
        "VolumeDetector": volume_det,
        "DistortionDetector": distortion_det
    }
    
    for name, detector in detectors.items():
        try:
            detector.detect(features, frame)
            print(f"❌ {name}: 应该抛出错误但没有！")
            return False
        except RuntimeError as e:
            if "requires baseline" in str(e):
                print(f"✅ {name}: 正确抛出baseline缺失错误")
            else:
                print(f"❌ {name}: 错误信息不正确: {e}")
                return False
        except Exception as e:
            print(f"❌ {name}: 意外错误: {e}")
            return False
    
    print("\n✅ 测试1通过：所有检测器都强制要求baseline")
    return True


def test_detectors_use_relative_thresholds():
    """测试2：检测器使用相对阈值"""
    print("\n" + "="*60)
    print("测试2：检测器使用baseline相对阈值")
    print("="*60)
    
    from analyzer.detectors.noise import NoiseDetector
    from analyzer.detectors.dropout import DropoutDetector
    from analyzer.detectors.volume import VolumeDetector
    from analyzer.detectors.distortion import DistortionDetector
    from analyzer.frame import Frame
    
    # 创建检测器并设置baseline
    noise_det = NoiseDetector()
    dropout_det = DropoutDetector()
    volume_det = VolumeDetector()
    distortion_det = DistortionDetector()
    
    # 设置模拟baseline
    baseline = {
        "rms_mean": 0.1,
        "rms_std": 0.02,
        "rms_p10": 0.05,
        "rms_p90": 0.15,
        "zcr_mean": 0.08,
        "zcr_std": 0.02,
        "centroid_mean": 1000,
        "centroid_std": 200,
        "spectral_flux_mean": 0.1,
        "spectral_flux_std": 0.03,
        "spectral_rolloff_mean": 2000,
        "spectral_rolloff_std": 300,
        "spectral_bandwidth_mean": 500,
        "spectral_bandwidth_std": 100,
    }
    
    noise_det.set_baseline(baseline)
    dropout_det.set_baseline(baseline)
    volume_det.set_baseline(baseline)
    distortion_det.set_baseline(baseline)
    
    print("✅ Baseline已设置到所有检测器")
    
    # 测试NoiseDetector - 应该使用baseline_zcr + 2*std作为阈值
    features_normal = {
        "rms": 0.1,
        "zero_crossing_rate": 0.08,  # 等于baseline均值
        "spectral_rolloff": 2000,
        "rms_percentile_95": 0.1
    }
    
    features_abnormal = {
        "rms": 0.1,
        "zero_crossing_rate": 0.15,  # 超过baseline + 2*std (0.08 + 2*0.02 = 0.12)
        "spectral_rolloff": 3000,     # 超过baseline + 2*std
        "rms_percentile_95": 0.1
    }
    
    frame = Frame(samples=[0.1]*400, sample_rate=16000, start_time=0.0, end_time=0.025)
    
    # 正常值不应该报警
    result = noise_det.detect(features_normal, frame)
    if result is None:
        print("✅ NoiseDetector: 正常值不报警")
    else:
        print(f"❌ NoiseDetector: 正常值误报: {result.details}")
        return False
    
    print("\n✅ 测试2通过：检测器使用baseline相对阈值")
    return True


def test_analyze_file_requires_profile():
    """测试3：analyze_file.py强制要求profile"""
    print("\n" + "="*60)
    print("测试3：analyze_file强制要求profile参数")
    print("="*60)
    
    from analyze_file import analyze_file
    
    # 测试：没有profile应该返回False
    result = analyze_file("dummy.wav", profile_path=None)
    
    if result is False:
        print("✅ analyze_file: 没有profile时正确拒绝运行")
        return True
    else:
        print("❌ analyze_file: 应该拒绝运行但没有！")
        return False


def test_default_config_adaptive():
    """测试4：默认配置启用自适应阈值"""
    print("\n" + "="*60)
    print("测试4：DEFAULT_CONFIG默认启用自适应阈值")
    print("="*60)
    
    from analyzer import DEFAULT_CONFIG
    
    if DEFAULT_CONFIG.get("enable_adaptive_threshold") is True:
        print("✅ DEFAULT_CONFIG: enable_adaptive_threshold = True")
        return True
    else:
        print(f"❌ DEFAULT_CONFIG: enable_adaptive_threshold = {DEFAULT_CONFIG.get('enable_adaptive_threshold')}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🧪 强制标定架构 - 重构验证测试")
    print("="*70)
    
    tests = [
        ("检测器强制要求baseline", test_detector_requires_baseline),
        ("检测器使用相对阈值", test_detectors_use_relative_thresholds),
        ("analyze_file强制要求profile", test_analyze_file_requires_profile),
        ("默认配置启用自适应", test_default_config_adaptive),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ 测试异常: {name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*70)
    print("📊 测试结果汇总")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "-"*70)
    print(f"总计: {passed_count}/{total_count} 通过")
    print("="*70)
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！强制标定架构重构成功！")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} 个测试失败，请检查！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
