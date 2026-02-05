#!/usr/bin/env python3
"""
E2E Test: CinematographyEngine + RealVisXL_V5.0

Renders a STYLE_HIGH_VELOCITY_ACTION scene using the full pipeline:
1. CinematographyEngine composes the prompt
2. LocalImageGenerator renders with RealVisXL_V5.0 (STANDARD_CINEMATIC)
3. Output saved to /mnt/c/Users/craig/Downloads/synterra_production/

Usage:
    cd backend
    python scripts/test_render_realvis.py

    # Or with custom output directory:
    python scripts/test_render_realvis.py --output /path/to/output

    # Dry run (prompt only, no render):
    python scripts/test_render_realvis.py --dry-run
"""

import argparse
import sys
import time
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def main():
    parser = argparse.ArgumentParser(description="E2E test: CinematographyEngine + RealVisXL")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="/mnt/c/Users/craig/Downloads/synterra_production",
        help="Output directory for rendered image",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only generate and print prompt, don't render",
    )
    parser.add_argument(
        "--style",
        type=str,
        default="STYLE_HIGH_VELOCITY_ACTION",
        choices=["STYLE_HIGH_VELOCITY_ACTION", "STYLE_URBAN_LUXURY", "STYLE_PHYSICAL_DRAMA"],
        help="Style to use for rendering",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default="muscular man throwing punch in underground fight club, sweat flying, crowd cheering",
        help="Subject description for the scene",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("E2E TEST: CinematographyEngine + RealVisXL_V5.0")
    print("=" * 70)

    # Step 1: Import and create CinematographyEngine
    print("\n[1/4] Initializing CinematographyEngine...")
    try:
        from src.cinematography import CinematographyEngine
        from src.cinematography.style_logic import (
            STYLE_HIGH_VELOCITY_ACTION,
            STYLE_URBAN_LUXURY,
            STYLE_PHYSICAL_DRAMA,
        )

        engine = CinematographyEngine()
        print("     OK - Engine initialized")
        print(f"     Available cameras: {len(engine.list_cameras())}")
        print(f"     Available film stocks: {len(engine.list_film_stocks())}")
        print(f"     Available styles: {engine.list_styles()}")
    except Exception as e:
        print(f"     FAILED: {e}")
        return 1

    # Step 2: Compose prompt using selected style
    print(f"\n[2/4] Composing prompt with {args.style}...")
    try:
        # Map style name to constant
        style_map = {
            "STYLE_HIGH_VELOCITY_ACTION": STYLE_HIGH_VELOCITY_ACTION,
            "STYLE_URBAN_LUXURY": STYLE_URBAN_LUXURY,
            "STYLE_PHYSICAL_DRAMA": STYLE_PHYSICAL_DRAMA,
        }
        style = style_map[args.style]

        composed = engine.compose(
            subject=args.subject,
            style=style,
        )

        print("     OK - Prompt composed")
        print(f"\n     DIRECTOR INJECT (FIRST): {composed.director_inject[:80]}..." if composed.director_inject else "\n     DIRECTOR INJECT: (none)")
        print(f"     SUBJECT: {composed.subject}")
        print(f"     STYLE PREFIX: {composed.style_prefix}")
        print(f"     CAMERA TOKENS: {composed.camera_tokens}")
        print(f"     FILM TOKENS: {composed.film_tokens}")
        print(f"     LIGHTING TOKENS: {composed.lighting_tokens}")
        print(f"     MOTION TOKENS: {composed.motion_tokens}")
        print(f"     QUALITY TOKENS: {composed.quality_tokens}")
        print(f"     ESTIMATED TOKENS: {composed.estimated_tokens} (CLIP limit: 77)")
        print(f"\n     FULL PROMPT:\n     {composed.full_prompt}")

        # Verify mandatory tokens
        assert "detailed skin" in composed.full_prompt, "CRITICAL: 'detailed skin' missing!"
        print("\n     VERIFICATION: 'detailed skin' present")

        # Get generation config
        gen_config = engine.get_generation_config(style=style)
        print(f"\n     GENERATION CONFIG:")
        print(f"       - CFG Scale: {gen_config['cfg_scale']}")
        print(f"       - Steps: {gen_config['steps']}")
        print(f"       - Recommended checkpoint: {gen_config['recommended_checkpoint']}")

        # Get negative prompt
        negative = engine.get_negative_prompt(style=style)
        print(f"\n     NEGATIVE PROMPT (first 100 chars):")
        print(f"       {negative[:100]}...")

        # Get aDetailer config
        adetailer = engine.get_adetailer_config()
        print(f"\n     ADETAILER CONFIG:")
        print(f"       - Face repair: {adetailer['face_repair']['enabled']} ({adetailer['face_repair']['model']})")
        print(f"       - Hand repair: {adetailer['hand_repair']['enabled']} ({adetailer['hand_repair']['model']})")

    except Exception as e:
        print(f"     FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Early exit for dry run
    if args.dry_run:
        print("\n[DRY RUN] Skipping render. Prompt generation successful.")
        return 0

    # Step 3: Render with LocalImageGenerator
    print(f"\n[3/4] Rendering with RealVisXL_V5.0 (STANDARD_CINEMATIC)...")
    try:
        from src.local.image_generator import LocalImageGenerator

        generator = LocalImageGenerator()

        # Get SDXL geometry from generation config
        target_size = gen_config.get("target_size", (576, 1024))
        crops_coords = gen_config.get("crops_coords_top_left", (0, 0))
        original_size = gen_config.get("original_size", (576, 1024))

        print(f"     SDXL Geometry: target={target_size}, crops={crops_coords}")

        # Generate image with SDXL geometry parameters to prevent distortion
        start_time = time.time()
        image = generator.generate(
            prompt=composed.full_prompt,
            checkpoint="STANDARD_CINEMATIC",  # RealVisXL_V5.0
            negative_prompt=negative,
            num_inference_steps=gen_config["steps"],
            guidance_scale=gen_config["cfg_scale"],
            width=target_size[0],
            height=target_size[1],
            # SDXL geometry to prevent aspect ratio distortion
            target_size=target_size,
            crops_coords_top_left=crops_coords,
            original_size=original_size,
        )
        render_time = time.time() - start_time

        print(f"     OK - Image rendered in {render_time:.1f}s")
        print(f"     Image size: {image.size}")

    except Exception as e:
        print(f"     FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 4: Save to output directory
    print(f"\n[4/4] Saving to {args.output}...")
    try:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        style_short = args.style.replace("STYLE_", "").lower()
        output_path = output_dir / f"cinematography_test_{style_short}_{timestamp}.png"

        generator.save_image(image, output_path)

        # Verify
        assert output_path.exists(), f"File not found: {output_path}"
        file_size = output_path.stat().st_size
        assert file_size > 0, f"File is empty: {output_path}"

        print(f"     OK - Saved to: {output_path}")
        print(f"     File size: {file_size / 1024:.1f} KB")

    except Exception as e:
        print(f"     FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("SUCCESS - E2E TEST PASSED")
    print("=" * 70)
    print(f"  Style: {args.style}")
    print(f"  Checkpoint: STANDARD_CINEMATIC (RealVisXL_V5.0)")
    print(f"  Output: {output_path}")
    print(f"  Render time: {render_time:.1f}s")
    print(f"  'detailed skin' verified: YES")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
