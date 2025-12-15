#!/usr/bin/env python3
"""Offline audio file analysis entry point.

Analyzes a WAV/PCM file and produces a voice quality report.

Usage:
    python analyze_file.py <audio_file> [--output output.json]
"""
import sys
import os
import json
import argparse
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG


def analyze_file(audio_path, output_path=None):
    """Load and analyze a single audio file."""
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

    # Create analyzer with default config
    analyzer = Analyzer(config=DEFAULT_CONFIG)

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
        description="Analyze voice quality in audio files"
    )
    parser.add_argument("audio_file", help="Path to audio file (WAV/PCM)")
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path",
        default=None
    )
    
    args = parser.parse_args()
    
    success = analyze_file(args.audio_file, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
