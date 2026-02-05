#!/usr/bin/env python
"""
Production Smoke Test - First 9:16 Vertical Action Shot

This script runs the full pipeline with VRAM checkpoints:
1. Generate 9:16 portrait image with Pony (STANDARD_ACTION)
2. Animate with SVD (8fps)
3. Smooth with RIFE (60fps)
4. Handoff to Windows Downloads

Expected VRAM checkpoints (all <1.5GB):
- After ImageGen kill
- After VideoGen kill
- After MotionSmoother cleanup

Usage:
    python production_smoke_test.py
    python production_smoke_test.py --skip-smoothing  # Skip RIFE (faster test)
    python production_smoke_test.py --skip-windows-copy  # Skip Windows handoff
"""

import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.local.cinematic_director import CinematicDirector


def print_banner(text: str):
    """Print a banner for visual separation."""
    print("\n" + "═" * 70)
    print(f"  {text}")
    print("═" * 70)


def main():
    parser = argparse.ArgumentParser(description="Production Smoke Test - 9:16 Action Shot")
    parser.add_argument("--prompt", type=str,
                        default="warrior princess, dynamic pose, dramatic lighting, full body portrait, studio lighting",
                        help="Generation prompt")
    parser.add_argument("--checkpoint", type=str, default="pony",
                        help="Model checkpoint (pony, base, cinematic)")
    parser.add_argument("--skip-smoothing", action="store_true",
                        help="Skip RIFE interpolation")
    parser.add_argument("--skip-windows-copy", action="store_true",
                        help="Skip Windows handoff")
    parser.add_argument("--motion", type=int, default=127,
                        help="Motion bucket ID (0-255)")
    args = parser.parse_args()

    print_banner("BEATCANVAS PRODUCTION SMOKE TEST")
    print(f"  Prompt: {args.prompt[:60]}...")
    print(f"  Model: {args.checkpoint}")
    print(f"  Profile: portrait_full_body (9:16)")
    print(f"  Motion: {args.motion}")
    print(f"  Smoothing: {'enabled' if not args.skip_smoothing else 'SKIPPED'}")
    print(f"  Windows: {'enabled' if not args.skip_windows_copy else 'SKIPPED'}")

    # Create director and run pipeline
    director = CinematicDirector()

    print_banner("STARTING PIPELINE")

    try:
        result = director.run(
            prompt=args.prompt,
            checkpoint=args.checkpoint,
            output_name="smoke_test_cinematic_60fps.mp4",
            motion_bucket_id=args.motion,
            profile="portrait_full_body",
            skip_smoothing=args.skip_smoothing,
            skip_windows_copy=args.skip_windows_copy
        )
    except Exception as e:
        print_banner("PIPELINE FAILED")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Results
    print_banner("PIPELINE COMPLETE - RESULTS")
    print(f"  Image:       {result.get('image_path', 'N/A')}")
    print(f"  Raw Video:   {result['raw_video']}")
    print(f"  Smoothed:    {result['smoothed_video'] or 'SKIPPED'}")
    print(f"  Final:       {result['final_output']}")
    print(f"  Windows:     {result['windows_path'] or 'SKIPPED'}")

    # VRAM Checkpoints
    print_banner("VRAM CHECKPOINTS")
    all_passed = True
    threshold = 1.5

    for cp in result.get("vram_checkpoints", []):
        vram = cp["vram_gb"]
        status = "✓ PASS" if vram < threshold else "✗ FAIL"
        if vram >= threshold:
            all_passed = False
        print(f"  {status}  {cp['stage']}: {vram}GB (threshold: <{threshold}GB)")

    # Summary
    print_banner("SUMMARY")
    if all_passed:
        print("  ✅ ALL VRAM CHECKPOINTS PASSED")
        print("  ✅ SMOKE TEST SUCCESSFUL")
    else:
        print("  ⚠️  SOME VRAM CHECKPOINTS FAILED")
        print("  ⚠️  VRAM leak detected - investigate before production")

    # File verification
    print_banner("FILE VERIFICATION")
    files_to_check = [
        ("Image", result.get("image_path")),
        ("Raw Video", result.get("raw_video")),
        ("Smoothed Video", result.get("smoothed_video")),
    ]

    for name, path in files_to_check:
        if path:
            p = Path(path)
            if p.exists():
                size_mb = p.stat().st_size / (1024 * 1024)
                print(f"  ✓ {name}: {p.name} ({size_mb:.2f} MB)")
            else:
                print(f"  ✗ {name}: NOT FOUND - {path}")
        else:
            print(f"  - {name}: SKIPPED")

    print("\n" + "═" * 70)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
