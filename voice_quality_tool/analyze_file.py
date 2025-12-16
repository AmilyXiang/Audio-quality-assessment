#!/usr/bin/env python3
"""Offline audio file analysis entry point.

Analyzes a WAV/PCM file and produces a voice quality report.

Usage:
    python analyze_file.py <audio_file> [--output output.json]
    python analyze_file.py <audio_file> --profile device_profile.json
    python analyze_file.py <audio_file> --disable-vad  # 禁用VAD过滤
"""
import sys
import os
import json
import argparse
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG


def analyze_file(audio_path, output_path=None, profile_path=None, disable_vad=False):
    """Load and analyze a single audio file.
    
    Args:
        audio_path: 音频文件路径
        output_path: JSON输出路径（可选）
        profile_path: 设备配置文件路径（可选）
        disable_vad: 是否禁用VAD过滤
    """
    # Load audio
    try:
        from scipy.io import wavfile
        sample_rate, data = wavfile.read(audio_path)
        
        # Handle stereo by converting to mono
        if len(data.shape) > 1:
            data = data[:, 0]
        
        # Normalize to [-1, 1] range
        data = data.astype(float)
        if data.max() > 1.0 or data.min() < -1.0:
            data = data / (2 ** 15)  # Assume 16-bit PCM
    
    except ImportError:
        print("Error: scipy not installed. Run: pip install -r requirements.txt")
        return False
    except FileNotFoundError:
        print(f"Error: File not found: {audio_path}")
        return False
    except Exception as e:
        print(f"Error loading audio: {e}")
        return False

    print(f"📁 Analyzing: {audio_path}")
    print(f"   Sample rate: {sample_rate} Hz, Duration: {len(data) / sample_rate:.2f}s")

    # Load config (from profile or default)
    config = DEFAULT_CONFIG.copy()
    
    if profile_path:
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            recommended = profile.get("recommended_config", {})
            config.update(recommended)
            print(f"✅ Loaded device profile: {profile_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not load profile: {e}")
    
    # Apply CLI overrides
    if disable_vad:
        config["enable_vad"] = False
        print("⚠️  VAD disabled - analyzing all frames")
    
    # Create analyzer
    analyzer = Analyzer(config=config)

    # Split into frames and analyze
    frame_size = int(sample_rate * 0.025)  # 25ms frames
    hop_size = int(sample_rate * 0.010)     # 10ms hop
    frames = frame_generator(data, sample_rate, frame_size, hop_size)
    
    print("🔍 Processing frames...")
    result = analyzer.analyze_frames(frames)
    
    # Output results
    result.print_summary()
    
    # Save JSON if requested
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.to_json_string())
        print(f"💾 Results saved to: {output_path}\n")
    else:
        # Print JSON to stdout
        print("JSON Output:")
        print(result.to_json_string())
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Analyze voice quality in audio files",
        epilog="Examples:\n"
               "  python analyze_file.py audio.wav\n"
               "  python analyze_file.py audio.wav --output report.json\n"
               "  python analyze_file.py audio.wav --profile device_profile.json\n"
               "  python analyze_file.py audio.wav --disable-vad",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("audio_file", help="Path to audio file (WAV/PCM)")
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path",
        default=None
    )
    parser.add_argument(
        "--profile", "-p",
        help="Device profile JSON (from calibrate.py)",
        default=None
    )
    parser.add_argument(
        "--disable-vad",
        action="store_true",
        help="Disable Voice Activity Detection (analyze all frames)"
    )
    
    args = parser.parse_args()
    
    success = analyze_file(
        args.audio_file, 
        args.output, 
        args.profile,
        args.disable_vad
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
