#!/usr/bin/env python3
"""Test video generation functionality."""
from pathlib import Path
import yaml

from src.video.avatar_generator import AvatarGenerator

# Load characters
config_dir = Path("configs")
character_path = config_dir / "characters.yaml"

print("Loading character configurations...")
with open(character_path, 'r', encoding='utf-8') as f:
    characters = yaml.safe_load(f)

print(f"Loaded {len(characters)} characters: {list(characters.keys())}")

# Create avatar generator
output_dir = Path("data/work/test_avatars")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"\nGenerating avatars in {output_dir}...")
avatar_gen = AvatarGenerator(output_dir)

# Generate all avatars
avatars = avatar_gen.generate_all_avatars(characters)

print("\nGenerated avatars:")
for speaker, path in avatars.items():
    print(f"  {speaker}: {path}")
    print(f"    Exists: {path.exists()}")
    if path.exists():
        size = path.stat().st_size / 1024  # KB
        print(f"    Size: {size:.1f} KB")

print("\nAvatar generation test completed!")
