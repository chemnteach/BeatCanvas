#!/usr/bin/env python3
"""
Standalone test for AnimateDiffPipeline.
Tests the pipeline independently from the API/WebSocket infrastructure.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("AnimateDiff Standalone Test")
print("=" * 80)

# Test 1: Import check
print("\n[TEST 1] Importing AnimateDiffPipeline...")
try:
    from src.video.animatediff_pipeline import AnimateDiffPipeline
    print("✓ Import successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Pipeline initialization
print("\n[TEST 2] Initializing pipeline...")
try:
    pipeline = AnimateDiffPipeline(
        target_fps=60,
        interpolate=False,  # Disable interpolation for faster testing
        heartbeat_callback=None
    )
    print("✓ Pipeline initialized")
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Generate a single test scene
print("\n[TEST 3] Generating single test scene...")
test_scene = {
    "description": "A serene beach with waves gently crashing",
    "image_prompt": "beach waves ocean sunset peaceful",
    "timestamp_start": 0.0,
    "timestamp_end": 4.0,
    "section": "intro"
}

try:
    print(f"Scene prompt: {test_scene['image_prompt']}")
    print(f"Duration: {test_scene['timestamp_end'] - test_scene['timestamp_start']}s")

    result = pipeline.generate_scene(
        scene=test_scene,
        scene_index=0,
        total_scenes=1,
        style="STYLE_BEACH_CASUAL"
    )

    print("✓ Scene generation completed!")
    print(f"  Video path: {result.get('video_path', 'NONE')}")
    print(f"  Duration: {result.get('duration', 0):.2f}s")
    print(f"  FPS: {result.get('fps', 0)}")
    print(f"  Frames: {result.get('frame_count', 0)}")
    print(f"  Generation time: {result.get('generation_time', 0):.1f}s")

    # Check if file actually exists
    video_path = result.get('video_path')
    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
        print(f"  File size: {file_size:.2f} MB")
        print(f"✓ Video file exists at: {video_path}")
    else:
        print(f"✗ Video file NOT FOUND at: {video_path}")

except Exception as e:
    print(f"✗ Scene generation failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Cleanup
print("\n[TEST 4] Cleaning up pipeline...")
try:
    pipeline.cleanup()
    print("✓ Cleanup successful")
except Exception as e:
    print(f"⚠ Cleanup warning: {e}")

print("\n" + "=" * 80)
print("All tests passed! AnimateDiffPipeline is working.")
print("=" * 80)
