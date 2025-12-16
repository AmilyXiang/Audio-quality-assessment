#!/usr/bin/env python3
"""设备校准工具 - 学习设备和环境的基线特性.

用法：
    python calibrate.py baseline_audio.wav --output device_profile.json
    
然后在分析时使用：
    python analyze_file.py test.wav --profile device_profile.json
"""
import sys
import json
import argparse
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG, compute_baseline_stats


def calibrate_device(audio_path, output_path):
    """对设备进行校准，生成基线配置文件."""
    try:
        from scipy.io import wavfile
        sample_rate, data = wavfile.read(audio_path)
        
        if len(data.shape) > 1:
            data = data[:, 0]
        
        data = data.astype(float)
        if data.max() > 1.0 or data.min() < -1.0:
            data = data / (2 ** 15)
    
    except ImportError:
        print("❌ Error: scipy not installed. Run: pip install -r requirements.txt")
        return False
    except FileNotFoundError:
        print(f"❌ Error: File not found: {audio_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading audio: {e}")
        return False

    print(f"🎤 Calibrating with: {audio_path}")
    print(f"   Sample rate: {sample_rate} Hz, Duration: {len(data) / sample_rate:.2f}s")
    print("\n📊 Analyzing baseline characteristics...")
    
    # Create analyzer
    analyzer = Analyzer(config=DEFAULT_CONFIG)
    
    # Generate frames
    frame_size = int(sample_rate * 0.025)
    hop_size = int(sample_rate * 0.010)
    frames = frame_generator(data, sample_rate, frame_size, hop_size)
    
    # Calibrate
    baseline = analyzer.calibrate(frames)
    
    # Create device profile
    profile = {
        "baseline_stats": baseline,
        "sample_rate": sample_rate,
        "calibration_audio": audio_path,
        "recommended_config": {
            "enable_vad": True,
            "enable_adaptive_threshold": True,
            "min_event_duration": 0.3,
            
            # Adaptive thresholds based on baseline
            "silence_rms_threshold": max(baseline.get("rms_p10", 0.01) * 0.5, 0.005),
            "noise_zcr_threshold": baseline.get("zcr_mean", 0.15) + 2 * baseline.get("zcr_std", 0.05),
        }
    }
    
    # Save profile
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)
    
    print(f"\n✅ Calibration complete!")
    print(f"💾 Device profile saved to: {output_path}")
    print(f"\n📋 Baseline Statistics:")
    print(f"   RMS Mean: {baseline.get('rms_mean', 0):.4f}")
    print(f"   RMS Std:  {baseline.get('rms_std', 0):.4f}")
    print(f"   Centroid Mean: {baseline.get('centroid_mean', 0):.1f} Hz")
    print(f"   ZCR Mean: {baseline.get('zcr_mean', 0):.4f}")
    
    print(f"\n🎯 Use this profile when analyzing:")
    print(f"   python analyze_file.py audio.wav --profile {output_path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate device/environment baseline for adaptive quality analysis"
    )
    parser.add_argument(
        "baseline_audio",
        help="Reference audio file (clean recording from the device)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output profile JSON path",
        default="device_profile.json"
    )
    
    args = parser.parse_args()
    
    success = calibrate_device(args.baseline_audio, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
