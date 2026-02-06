#!/usr/bin/env python3
"""Offline audio file analysis entry point.

Analyzes a WAV/PCM file and produces a voice quality report.

Usage:
    python analyze_file.py <audio_file> [--output output.json]
    python analyze_file.py <audio_file> --profile device_profile.json
    python analyze_file.py <audio_file> --disable-vad  # 禁用VAD过滤
    python analyze_file.py <audio_file> --mode clean-speech  # 干净语音模式
"""
import sys
import os
import json
import argparse
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG, CLEAN_SPEECH_CONFIG


def analyze_file(
    audio_path,
    output_path=None,
    profile_path=None,
    disable_vad=False,
    mode='default',
    enable_llm=False,
    llm_model='deepseek-chat',
    llm_base_url=None,
    llm_api_key=None,
    llm_timeout=30,
):
    """Load and analyze a single audio file.
    
    Args:
        audio_path: 音频文件路径
        output_path: JSON输出路径（可选）
        profile_path: 设备配置文件路径（✅ 强制要求）
        disable_vad: 是否禁用VAD过滤
        mode: 分析模式 ('default'=电话质量 或 'clean-speech'=录音室质量)
    """
    # ✅ 强制要求profile
    if not profile_path:
        print("❌ Error: Device profile is required! Please run calibration first:")
        print("   python calibrate.py baseline_audio.wav --output device_profile.json")
        print("   python analyze_file.py audio.wav --profile device_profile.json")
        return False
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
    if mode == 'clean-speech':
        config = CLEAN_SPEECH_CONFIG.copy()
        print("🎙️  模式: 干净语音 (播客/录音室)")
    else:
        config = DEFAULT_CONFIG.copy()
        print("☎️  模式: 默认 (电话/VoIP质量)")

    baseline_global = None
    if profile_path:
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            recommended = profile.get("recommended_config", {})
            config.update(recommended)
            print(f"✅ Loaded device profile: {profile_path}")

            # 尝试加载语音基线特征
            baseline_global_path = os.path.splitext(profile_path)[0] + '_global.json'
            if os.path.exists(baseline_global_path):
                with open(baseline_global_path, 'r', encoding='utf-8') as f:
                    baseline_global = json.load(f)
                print(f"✅ Loaded global baseline: {baseline_global_path}")
            else:
                print(f"⚠️  No global baseline found: {baseline_global_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not load profile or baseline: {e}")

    # Apply CLI overrides
    if disable_vad:
        config["enable_vad"] = False
        print("⚠️  VAD disabled - analyzing all frames")

    # Create analyzer
    analyzer = Analyzer(config=config)
    
    # ✅ 加载baseline并设置到所有检测器
    try:
        baseline_stats = profile.get("baseline_stats", {})
        if not baseline_stats:
            print("❌ Error: Profile missing baseline_stats! Re-run calibration.")
            return False
        
        # 设置baseline到所有检测器
        for detector in [analyzer.noise_detector, analyzer.dropout_detector, 
                        analyzer.volume_detector, analyzer.distortion_detector]:
            detector.set_baseline(baseline_stats)
        
        print(f"✅ Baseline loaded and applied to all detectors")
    except Exception as e:
        print(f"❌ Error setting baseline: {e}")
        return False

    # Split into frames and analyze
    frame_size = int(sample_rate * 0.025)  # 25ms frames
    hop_size = int(sample_rate * 0.010)     # 10ms hop
    frames = frame_generator(data, sample_rate, frame_size, hop_size)

    print("🔍 Processing frames...")
    result = analyzer.analyze_frames(frames)

    # 全局失真分析
    try:
        from analyzer.global_distortion_analyzer import GlobalDistortionAnalyzer
        gda = GlobalDistortionAnalyzer()
        # 如果有基线，则对比
        if baseline_global:
            # 需要将当前音频的全局特征与基线对比
            # 先计算当前音频的全局特征
            sample_rate, data_temp = wavfile.read(audio_path)
            if len(data_temp.shape) > 1:
                data_temp = data_temp[:, 0]
            data_temp = data_temp.astype(float) / 32768.0
            
            current_features = gda._compute_global_features(data_temp, sample_rate)
            comparison = gda._compare_features(current_features, baseline_global)
            
            # 使用基线对比进行质量评估
            quality_assessment = gda._assess_quality(current_features, baseline_comparison=comparison)
            
            print("\n📊 Global Distortion Comparison:")
            print(json.dumps(comparison, indent=2, ensure_ascii=False))
            
            result.global_features = current_features
            result.global_comparison = comparison
            result.global_assessment = quality_assessment
        else:
            global_result = gda.analyze_file(audio_path)
            print("\n📊 Global Features:")
            print(json.dumps(global_result.get('global_features', {}), indent=2, ensure_ascii=False))
            result.global_features = global_result.get('global_features', {})
            result.global_assessment = global_result.get('quality_assessment')
    except Exception as e:
        print(f"⚠️  Global distortion analysis failed: {e}")

    # LLM 二次诊断（可选）
    if enable_llm:
        try:
            from llm_inference import query_llm
            resolved_base_url = llm_base_url or os.getenv('DEEPSEEK_API_BASE') or os.getenv('OPENAI_API_BASE')

            # Route-1: compact audio-derived summary for LLM (no raw audio upload)
            try:
                from audio_llm_features import build_llm_audio_summary
                llm_audio_summary = build_llm_audio_summary(
                    data,
                    sample_rate,
                    segment_sec=1.0,
                    max_segments=120,
                )
                result.llm_audio_summary = llm_audio_summary
            except Exception as e:
                llm_audio_summary = {"error": f"audio_summary_failed: {e}"}

            analysis_payload = result.to_dict()
            # Make sure the LLM can see the summary even if we don't persist it
            analysis_payload["llm_audio_summary"] = llm_audio_summary
            llm_text = query_llm(
                analysis_payload,
                api_key=llm_api_key,
                model=llm_model,
                base_url=resolved_base_url,
                timeout=llm_timeout,
            )
            result.llm_advice = llm_text
            result.llm_meta = {
                "model": llm_model,
                "base_url": resolved_base_url,
                "timeout": llm_timeout,
                "provider": "deepseek" if (resolved_base_url and 'deepseek' in resolved_base_url) else "openai",
            }
            print("\n🤖 LLM Advice (summary):")
            print(llm_text)
        except KeyboardInterrupt:
            print("⚠️  LLM request cancelled by user (skipped).")
        except Exception as e:
            print(f"⚠️  LLM analysis failed (skipped): {e}")

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
        description="Analyze voice quality in audio files (✅ Requires calibration profile)",
        epilog="Examples:\n"
               "  # Step 1: Calibrate first\n"
               "  python calibrate.py baseline.wav --output device_profile.json\n\n"
               "  # Step 2: Analyze with profile\n"
               "  python analyze_file.py audio.wav --profile device_profile.json\n"
               "  python analyze_file.py audio.wav -p device_profile.json --output report.json\n"
               "  python analyze_file.py audio.wav -p device_profile.json --disable-vad",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("audio_file", help="Path to audio file (WAV/PCM)")
    parser.add_argument(
        "--profile", "-p",
        required=True,  # ✅ 改为必需参数
        help="Device profile JSON (from calibrate.py) - REQUIRED"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path",
        default=None
    )
    parser.add_argument(
        "--disable-vad",
        action="store_true",
        help="Disable Voice Activity Detection (analyze all frames)"
    )
    parser.add_argument(
        "--mode",
        choices=['default', 'clean-speech'],
        default='default',
        help="Analysis mode: 'default' (telephone/VoIP) or 'clean-speech' (studio/podcast)"
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM second-opinion (DeepSeek/OpenAI compatible). Uses env DEEPSEEK_API_KEY/OPENAI_API_KEY by default."
    )
    parser.add_argument(
        "--llm-model",
        default="deepseek-chat",
        help="LLM model name (DeepSeek: deepseek-chat; OpenAI: gpt-4o)"
    )
    parser.add_argument(
        "--llm-base-url",
        default=None,
        help="LLM API base url (DeepSeek example: https://api.deepseek.com/v1). If omitted, auto-detect from env."
    )
    parser.add_argument(
        "--llm-api-key",
        default=None,
        help="LLM API key (optional). Prefer env vars DEEPSEEK_API_KEY or OPENAI_API_KEY."
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=30,
        help="LLM request timeout in seconds (default: 30)."
    )
    
    args = parser.parse_args()
    
    success = analyze_file(
        args.audio_file, 
        args.output, 
        args.profile,
        args.disable_vad,
        args.mode,
        args.llm,
        args.llm_model,
        args.llm_base_url,
        args.llm_api_key,
        args.llm_timeout,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
