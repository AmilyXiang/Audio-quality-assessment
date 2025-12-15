#!/usr/bin/env python3
"""Test script: generate synthetic audio with known quality issues and analyze.

Demonstrates the analyzer's detection capabilities.
"""
import numpy as np
from scipy.io import wavfile
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG


def generate_test_audio():
    """Generate synthetic audio with various quality issues."""
    sample_rate = 16000
    duration = 10  # 10 seconds
    t = np.arange(int(sample_rate * duration)) / sample_rate
    
    audio = np.zeros_like(t)
    
    # 0-2s: Clean speech (simulated with filtered noise)
    segment1 = np.random.randn(int(sample_rate * 2)) * 0.1
    segment1 = np.convolve(segment1, np.ones(50)/50, mode='same')
    audio[:int(sample_rate * 2)] = segment1
    
    # 2-3s: Background noise
    audio[int(sample_rate * 2):int(sample_rate * 3)] = np.random.randn(sample_rate) * 0.2
    
    # 3-4s: Dropout (silence)
    audio[int(sample_rate * 3):int(sample_rate * 3.5)] = np.random.randn(int(sample_rate * 0.5)) * 0.002
    
    # 4-5s: Speech with normal volume
    segment2 = np.sin(2 * np.pi * 200 * t[int(sample_rate*4):int(sample_rate*5)]) * 0.15
    segment2 += np.sin(2 * np.pi * 300 * t[int(sample_rate*4):int(sample_rate*5)]) * 0.1
    audio[int(sample_rate * 4):int(sample_rate * 5)] = segment2
    
    # 5-6s: Volume fluctuation (rapid changes)
    for i in range(10):
        start = int(sample_rate * (5 + i * 0.1))
        end = int(sample_rate * (5 + (i + 1) * 0.1))
        volume = 0.05 + (0.2 if i % 2 == 0 else 0.05)
        audio[start:end] = np.sin(2 * np.pi * 250 * t[start:end]) * volume
    
    # 6-7s: Clean speech
    segment3 = np.sin(2 * np.pi * 220 * t[int(sample_rate*6):int(sample_rate*7)]) * 0.12
    audio[int(sample_rate * 6):int(sample_rate * 7)] = segment3
    
    # 7-8s: Spectral distortion (high frequency boost)
    freq_base = np.sin(2 * np.pi * 150 * t[int(sample_rate*7):int(sample_rate*8)]) * 0.1
    freq_noise = np.random.randn(sample_rate) * 0.15  # High freq noise
    audio[int(sample_rate * 7):int(sample_rate * 8)] = freq_base + freq_noise
    
    # 8-10s: Clean segment
    segment4 = np.sin(2 * np.pi * 180 * t[int(sample_rate*8):int(sample_rate*10)]) * 0.12
    audio[int(sample_rate * 8):int(sample_rate * 10)] = segment4
    
    # Normalize
    audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.9
    audio = (audio * 32767).astype(np.int16)
    
    return audio, sample_rate


def main():
    print("🎵 Generating synthetic test audio...\n")
    audio, sample_rate = generate_test_audio()
    
    # Save test audio
    test_file = "test_audio.wav"
    wavfile.write(test_file, sample_rate, audio)
    print(f"✓ Saved test audio to: {test_file}\n")
    
    print("🔍 Analyzing with Voice Quality Analyzer...\n")
    
    # Create analyzer
    analyzer = Analyzer(config=DEFAULT_CONFIG)
    
    # Create frames
    frame_size = int(sample_rate * 0.025)  # 25ms
    hop_size = int(sample_rate * 0.010)     # 10ms
    
    # Normalize audio to float [-1, 1]
    audio_float = audio.astype(float) / 32767.0
    
    frames = frame_generator(audio_float, sample_rate, frame_size, hop_size)
    
    # Analyze
    result = analyzer.analyze_frames(frames)
    
    # Display results
    result.print_summary()
    
    # Save JSON report
    output_file = "test_audio_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result.to_json_string())
    print(f"💾 Report saved to: {output_file}\n")
    
    print("📊 Expected detections:")
    print("  - Noise:     2-3s segment")
    print("  - Dropout:   3-3.5s segment (silence)")
    print("  - Volume:    5-6s segment (rapid RMS changes)")
    print("  - Distort:   7-8s segment (high frequency noise)")


if __name__ == "__main__":
    main()
