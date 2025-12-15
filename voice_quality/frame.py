"""Frame handling and timeline utilities."""
from dataclasses import dataclass


@dataclass
class Frame:
    samples: list
    sample_rate: int
    start_time: float
    end_time: float


def frame_generator(audio_samples, sample_rate: int, frame_size: int, hop_size: int):
    """Yield Frame objects from raw samples."""
    total = len(audio_samples)
    i = 0
    frame_idx = 0
    while i < total:
        end = min(i + frame_size, total)
        start_time = frame_idx * hop_size / sample_rate
        end_time = start_time + (end - i) / sample_rate
        yield Frame(samples=audio_samples[i:end], sample_rate=sample_rate, start_time=start_time, end_time=end_time)
        i += hop_size
        frame_idx += 1
