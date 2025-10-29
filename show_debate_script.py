#!/usr/bin/env python3
"""Show debate script content."""
import pickle
from pathlib import Path

# Load debate checkpoint
checkpoint = Path("data/work/episode_20251029/checkpoint_script.pkl")
with open(checkpoint, 'rb') as f:
    script = pickle.load(f)

print("=" * 70)
print(f"トピック: {script.title}")
print(f"概要: {script.topic_summary}")
print("=" * 70)
print()

for i, line in enumerate(script.lines, 1):
    print(f"{i:2}. [{line.speaker.upper()}]")
    print(f"    {line.text}")
    print()

print("=" * 70)
print(f"総発言数: {len(script.lines)}")
print(f"推定時間: {script.total_duration_sec:.1f}秒 ({script.total_duration_sec/60:.1f}分)")
print("=" * 70)
