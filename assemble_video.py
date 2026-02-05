#!/usr/bin/env python3
"""
Video assembly using existing generated images
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append('backend')

from src.video.assembler import VideoAssembler
from src.assets.generator import GeneratedImage

# Configuration
AUDIO_FILE = "data/uploads/WrapAroundMeVoxLoop-10Bar_keyC#min_88bpm.wav"
OUTPUT_FILE = "output/final_video.mp4"

def main():
    """Assemble video from existing images"""

    print("=== BeatCanvas Video Assembly ===")
    print(f"Audio: {Path(AUDIO_FILE).name}")

    # Check for generated images
    image_dir = Path("data/generated_images")
    image_files = list(image_dir.glob("*.png"))

    if not image_files:
        print("[ERROR] No generated images found!")
        return False

    print(f"Images found: {len(image_files)}")
    for img in sorted(image_files):
        print(f"   {img.name}")

    # Create simple scene assets mapping
    scene_assets = {}
    for img_path in image_files:
        # Extract timestamp from filename (e.g., scene_0.0_dalle_var_0_67f5fd02.png)
        filename = img_path.stem
        if 'scene_' in filename:
            try:
                # Parse timestamp
                timestamp_part = filename.split('_')[1]  # Get "0.0" from "scene_0.0_dalle_var_0_67f5fd02"
                timestamp = float(timestamp_part)

                if timestamp not in scene_assets:
                    scene_assets[timestamp] = []

                # Create GeneratedImage object
                generated_img = GeneratedImage(
                    scene_timestamp=timestamp,
                    image_path=str(img_path),
                    provider="dalle",
                    prompt="generated",
                    variation_index=0
                )
                scene_assets[timestamp].append(generated_img)
            except (ValueError, IndexError) as e:
                print(f"[WARNING] Could not parse timestamp from {filename}: {e}")

    print(f"Scene timestamps: {sorted(scene_assets.keys())}")

    # Create dummy storyboard with basic structure
    storyboard_dicts = []
    for timestamp in sorted(scene_assets.keys()):
        storyboard_dicts.append({
            'timestamp_start': timestamp,
            'timestamp_end': timestamp + 3.0,  # 3 second scenes
            'description': f'Scene at {timestamp}s',
            'visual_style': 'abstract',
            'mood': 'energetic',
            'camera_direction': 'static',
            'image_prompt': 'generated image',
            'effects': ['fade']
        })

    print(f"Created {len(storyboard_dicts)} scenes")

    # Assemble video
    print("\nAssembling video...")
    try:
        assembler = VideoAssembler()
        video_path = assembler.create_video(
            audio_file=AUDIO_FILE,
            scene_assets=scene_assets,
            storyboard=storyboard_dicts,
            task_id="final"
        )

        if Path(video_path).exists():
            file_size = Path(video_path).stat().st_size / (1024*1024)
            print(f"\n[SUCCESS] Video created!")
            print(f"   File: {video_path}")
            print(f"   Size: {file_size:.2f} MB")
            return True
        else:
            print("\n[ERROR] Video file not created")
            return False

    except Exception as e:
        print(f"\n[ERROR] Assembly failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)