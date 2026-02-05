#!/usr/bin/env python3
"""
Direct video generation without API - runs the complete pipeline synchronously
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append('backend')

from src.audio.analyzer import MusicAnalyzer
from src.storyboard.conceptor import ConceptGenerator
from src.storyboard.generator import StoryboardGenerator
from src.assets.generator import MultiProviderImageGenerator
from src.video.assembler import VideoAssembler

# Configuration
AUDIO_FILE = "data/uploads/WrapAroundMeVoxLoop-10Bar_keyC#min_88bpm.wav"
VISUAL_PROMPT = "Abstract colorful patterns flowing in rhythm with music, geometric shapes dancing"
QUALITY_TIER = "basic"  # 12 scenes
OUTPUT_FILE = "output/direct_test_video.mp4"

def main():
    """Run the complete video generation pipeline directly"""

    print("=== BeatCanvas Direct Video Generation ===")
    print(f"Audio: {Path(AUDIO_FILE).name}")
    print(f"Prompt: {VISUAL_PROMPT}")
    print(f"Quality: {QUALITY_TIER}")
    print()

    if not Path(AUDIO_FILE).exists():
        print(f"ERROR: Audio file not found: {AUDIO_FILE}")
        return False

    try:
        # Step 1: Audio Analysis
        print("1. Analyzing audio...")
        analyzer = MusicAnalyzer()
        music_data = analyzer.analyze_song(AUDIO_FILE)
        print(f"   Duration: {music_data['duration']:.2f}s")
        print(f"   Tempo: {music_data['tempo']} BPM")
        print(f"   Segments: {len(music_data['segments'])}")
        print("   [OK] Audio analysis complete")

        # Step 2: Concept Generation
        print("\n2. Generating visual concept...")
        conceptor = ConceptGenerator()
        concept = conceptor.generate_concept(music_data, VISUAL_PROMPT)
        print("   [OK] Visual concept generated")

        # Step 3: Storyboard Creation
        print("\n3. Creating storyboard...")
        storyboard_gen = StoryboardGenerator()

        # For basic quality, use fewer scenes (combine some segments)
        if QUALITY_TIER == "basic":
            # Use every segment (7 segments for this audio)
            scene_timings = [(seg['start_time'], seg['end_time']) for seg in music_data['segments']]
        else:
            # For higher quality, could split segments further
            scene_timings = None  # Will use default segments

        storyboard = storyboard_gen.create_storyboard(music_data, concept, scene_timings)
        print(f"   Scenes created: {len(storyboard)}")

        # Convert StoryboardScene objects to dictionaries for image generator
        storyboard_dicts = []
        for scene in storyboard:
            storyboard_dicts.append({
                'timestamp_start': scene.timestamp_start,
                'timestamp_end': scene.timestamp_end,
                'description': scene.description,
                'visual_style': scene.visual_style,
                'mood': scene.mood,
                'camera_direction': scene.camera_direction,
                'image_prompt': scene.image_prompt,
                'effects': scene.effects
            })

        print("   [OK] Storyboard complete")

        # Step 4: Image Generation (This is where it gets expensive)
        print("\n4. Generating images...")
        print("   WARNING: This will cost ~$1-2 for DALL-E API calls")
        print("   Press Ctrl+C within 5 seconds to cancel...")

        import time
        for i in range(5, 0, -1):
            print(f"   Starting in {i}...", end="\r")
            time.sleep(1)
        print("\n   Starting image generation...")

        image_gen = MultiProviderImageGenerator()

        async def generate_images():
            return await image_gen.generate_all_scenes(storyboard_dicts, "dalle")

        scene_assets = asyncio.run(generate_images())
        print(f"   Images generated: {len(scene_assets)} scenes")
        print("   [OK] Image generation complete")

        # Step 5: Video Assembly
        print("\n5. Assembling video...")
        assembler = VideoAssembler()
        video_path = assembler.create_video(
            audio_file=AUDIO_FILE,
            scene_assets=scene_assets,
            storyboard=storyboard_dicts,  # Use converted dictionaries
            task_id="direct_test"
        )
        print(f"   [OK] Video assembled: {video_path}")

        # Success!
        if Path(video_path).exists():
            file_size = Path(video_path).stat().st_size / (1024*1024)
            print(f"\n[SUCCESS] SUCCESS! Video generated:")
            print(f"   File: {video_path}")
            print(f"   Size: {file_size:.2f} MB")
            return True
        else:
            print("\n[ERROR] ERROR: Video file not created")
            return False

    except KeyboardInterrupt:
        print("\n\n[CANCELLED]  Generation cancelled by user")
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)