#!/usr/bin/env python
"""
Production Render: STYLE_INTENSE_INTERACTION

Renders using PonyV6 with unfiltered explicit prompts.
Delivers .mp4 to /mnt/c/Users/craig/Downloads/synterra_production/
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.local.cinematic_director import CinematicDirector


def main():
    print("\n" + "═" * 70)
    print("  STYLE_INTENSE_INTERACTION PRODUCTION RENDER")
    print("═" * 70)

    # Base prompt - the style will inject explicit prefixes
    base_prompt = "two figures, intimate embrace, dramatic lighting, passionate expression"

    print(f"\n  Base Prompt: {base_prompt}")
    print(f"  Style: STYLE_INTENSE_INTERACTION")
    print(f"  Model: PonyV6 (STANDARD_ACTION)")
    print(f"  Output: /mnt/c/Users/craig/Downloads/synterra_production/")
    print("═" * 70)

    director = CinematicDirector()

    # Override Windows path for this render
    director.windows_downloads = Path("/mnt/c/Users/craig/Downloads/synterra_production")

    try:
        result = director.run(
            prompt=base_prompt,
            checkpoint="pony",  # PonyV6 for explicit content
            output_name="intense_interaction_60fps.mp4",
            motion_bucket_id=127,
            profile="portrait_full_body",
            skip_smoothing=False,
            skip_windows_copy=False,
            style="STYLE_INTENSE_INTERACTION"  # Inject unfiltered prompts
        )
    except Exception as e:
        print(f"\n❌ RENDER FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Results
    print("\n" + "═" * 70)
    print("  RENDER COMPLETE")
    print("═" * 70)
    print(f"  Image:       {result.get('image_path', 'N/A')}")
    print(f"  Raw Video:   {result['raw_video']}")
    print(f"  Smoothed:    {result['smoothed_video'] or 'SKIPPED'}")
    print(f"  Windows:     {result['windows_path'] or 'N/A'}")

    # VRAM Checkpoints
    print("\n" + "═" * 70)
    print("  VRAM CHECKPOINTS")
    print("═" * 70)
    for cp in result.get("vram_checkpoints", []):
        vram = cp["vram_gb"]
        status = "✓ PASS" if vram < 1.5 else "✗ FAIL"
        print(f"  {status}  {cp['stage']}: {vram}GB")

    print("═" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
