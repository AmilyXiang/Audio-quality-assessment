#!/usr/bin/env python3
"""Real-time microphone audio analysis.

Captures audio from microphone in real-time and performs streaming quality analysis.

Usage:
    python analyze_mic.py [duration_seconds] [--realtime]

Options:
    --realtime: Print events in real-time as they're detected
    duration_seconds: Recording duration (default: 10)
"""
import sys
import json
import time
from datetime import datetime
from analyzer import Analyzer, frame_generator, DEFAULT_CONFIG


def analyze_mic(duration=10, realtime=False):
    """Record from microphone and perform real-time analysis."""
    try:
        import pyaudio
        import numpy as np
    except ImportError:
        print("Error: pyaudio or numpy not installed. Run: pip install -r requirements.txt")
        return False

    SAMPLE_RATE = 16000
    CHUNK_SIZE = int(SAMPLE_RATE * 0.025)  # 25ms chunks (matches frame size)
    CHANNELS = 1

    print(f"🎤 Recording from microphone for {duration} seconds...")
    print("Press Ctrl+C to stop early\n")

    # Setup audio stream
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        return False

    try:
        # Create analyzer
        analyzer = Analyzer(config=DEFAULT_CONFIG)

        # Record and analyze chunks
        audio_data = []
        last_event_time = time.time()
        
        start_time = time.time()
        chunk_count = 0
        
        for i in range(int(duration * SAMPLE_RATE / CHUNK_SIZE)):
            try:
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(chunk, dtype=np.float32)
                audio_data.extend(audio_chunk)
                
                chunk_count += 1
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    break
                
                if chunk_count % 40 == 0:  # Every ~1 second
                    print(f"  Recording: {elapsed:.1f}s / {duration}s", end='\r')
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Recording stopped by user")
                break

        stream.stop_stream()
        stream.close()

        print(f"\n✓ Recording complete: {len(audio_data)} samples\n")

        # Analyze frames
        print("🔍 Processing and analyzing frames...")
        frame_size = int(SAMPLE_RATE * 0.025)
        hop_size = int(SAMPLE_RATE * 0.010)
        frames = frame_generator(audio_data, SAMPLE_RATE, frame_size, hop_size)
        
        result = analyzer.analyze_frames(frames)
        
        # Output results
        result.print_summary()
        
        # Print JSON
        print("JSON Output (realtime format):")
        events_list = []
        for event in result.events:
            events_list.append({
                "type": event.event_type,
                "start": round(event.start_time, 3),
                "end": round(event.end_time, 3),
                "confidence": round(event.confidence, 2)
            })
        print(json.dumps(events_list, indent=2))
        
        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  Recording interrupted")
        stream.stop_stream()
        stream.close()
        p.terminate()
        return False
    except Exception as e:
        print(f"Error during analysis: {e}")
        return False
    finally:
        p.terminate()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze voice quality from microphone")
    parser.add_argument("duration", nargs='?', type=int, default=10, help="Recording duration (seconds)")
    parser.add_argument("--realtime", action="store_true", help="Print events as they occur")
    
    args = parser.parse_args()
    
    success = analyze_mic(duration=args.duration, realtime=args.realtime)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
