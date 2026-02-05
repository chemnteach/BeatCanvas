"""
Universal Image Generator - Wrapper for VRAMManager multi-model factory.

Supports all 5 Standards:
- STANDARD_US (Juggernaut XL) - General photorealism
- STANDARD_CINEMATIC (RealVisXL) - High-fidelity cinematic
- STANDARD_ANATOMY (Lustify) - Full-body artistic
- STANDARD_ACTION (Pony) - Dynamic poses, stylized
- STANDARD_DRAFT (Lightning) - Fast 4-step previews

VRAM Budget: 12GB
Rule: Only ONE model loaded at a time. Kill before swap.
"""

import os
import time
import yaml
from pathlib import Path
from typing import Optional, Union, Dict, Any

from src.local.vram_manager import VRAMManager, ModelRouter
from src.utils.config import SETTINGS
from src.utils.env_loader import get_path

# Load production styles
STYLES_PATH = Path(__file__).parent.parent.parent / "library" / "production_styles.yaml"
PRODUCTION_STYLES = {}
if STYLES_PATH.exists():
    with open(STYLES_PATH, "r") as f:
        PRODUCTION_STYLES = yaml.safe_load(f) or {}

# Default output directory
_default_output = Path(__file__).parent.parent / "output"
OUTPUT_DIR = get_path("svd_output", default=_default_output)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load generation config
GEN_CONFIG = SETTINGS.get("generation", {})

# Legacy checkpoint name → Standard mapping
CHECKPOINT_TO_STANDARD = {
    "base": "STANDARD_US",
    "photoreal": "STANDARD_US",
    "cinematic": "STANDARD_CINEMATIC",
    "realvis": "STANDARD_CINEMATIC",
    "anatomy": "STANDARD_ANATOMY",
    "lustify": "STANDARD_ANATOMY",
    "action": "STANDARD_ACTION",
    "pony": "STANDARD_ACTION",
    "draft": "STANDARD_DRAFT",
    "lightning": "STANDARD_DRAFT",
    "fast": "STANDARD_DRAFT",
    # Direct standard names also work
    "STANDARD_US": "STANDARD_US",
    "STANDARD_CINEMATIC": "STANDARD_CINEMATIC",
    "STANDARD_ANATOMY": "STANDARD_ANATOMY",
    "STANDARD_ACTION": "STANDARD_ACTION",
    "STANDARD_DRAFT": "STANDARD_DRAFT",
}


class LocalImageGenerator:
    """
    Universal Image Generator using VRAMManager for multi-model support.

    This is a wrapper that delegates to VRAMManager for:
    - Model loading with kill/revive pattern
    - VRAM management (12GB budget)
    - Prompt preparation (trigger tag injection)
    - Generation config (scheduler overrides)
    """

    def __init__(self, vram_manager: Optional[VRAMManager] = None):
        """
        Initialize the image generator.

        Args:
            vram_manager: Optional shared VRAMManager instance.
                          If None, creates a new one.
                          Pass shared instance for SVD handover coordination.
        """
        # Use shared VRAMManager or create new one
        self.vram_manager = vram_manager or VRAMManager()
        self.router = ModelRouter()

        # Load defaults from config
        self.default_width = GEN_CONFIG.get("width", 1024)
        self.default_height = GEN_CONFIG.get("height", 576)
        self.default_steps = GEN_CONFIG.get("steps", 30)
        self.default_guidance = GEN_CONFIG.get("guidance_scale", 7.5)

        # Anti-portrait bias negative prompt
        self.negative_prompt = GEN_CONFIG.get(
            "negative_prompt",
            "crop, headshot, portrait, close-up, cut off feet, cropped legs, partial body"
        )

        # Resolution profiles
        self.profiles = GEN_CONFIG.get("profiles", {})

    @property
    def pipe(self):
        """Access the underlying pipeline from VRAMManager."""
        return self.vram_manager.pipe

    @property
    def current_model(self) -> Optional[str]:
        """Get currently loaded model standard."""
        return self.vram_manager.current_model

    def _resolve_standard(self, checkpoint: str) -> str:
        """
        Resolve checkpoint name to Standard.

        Args:
            checkpoint: Legacy name (base, photoreal, pony) or Standard name

        Returns:
            Standard name (STANDARD_US, STANDARD_ACTION, etc.)

        Raises:
            KeyError: If checkpoint name not recognized
        """
        standard = CHECKPOINT_TO_STANDARD.get(checkpoint)
        if standard is None:
            # Try as-is (might be a direct standard name)
            if checkpoint in self.router.checkpoints:
                return checkpoint
            raise KeyError(
                f"Unknown checkpoint: {checkpoint}. "
                f"Valid options: {list(CHECKPOINT_TO_STANDARD.keys())}"
            )
        return standard

    def get_resolution(self, profile: Optional[str] = None) -> tuple:
        """Get width, height for a profile or return defaults."""
        if profile and profile in self.profiles:
            p = self.profiles[profile]
            return p.get("width", self.default_width), p.get("height", self.default_height)
        return self.default_width, self.default_height

    def get_vram_status(self) -> Dict[str, Any]:
        """Get current VRAM status."""
        return self.vram_manager.status()

    def kill(self) -> float:
        """
        Kill current model and reclaim VRAM.

        Call this before handing off to SVD or another generator.

        Returns:
            VRAM usage after kill (should be <1GB)
        """
        return self.vram_manager.kill()

    def load_model(self, checkpoint: str = "base") -> bool:
        """
        Load a model by checkpoint name or Standard.

        Uses VRAMManager's kill/revive pattern:
        1. Kill current model (if different)
        2. Reclaim VRAM to baseline
        3. Load new model

        Args:
            checkpoint: Model name (base, photoreal, pony, etc.) or Standard

        Returns:
            True if model was loaded, False if already loaded (no-op)
        """
        standard = self._resolve_standard(checkpoint)
        return self.vram_manager.load(standard)

    def generate(
        self,
        prompt: str,
        lora_names: Optional[str] = None,
        checkpoint: str = "base",
        profile: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        style: Optional[str] = None,
        # SDXL Geometry parameters for aspect ratio preservation
        target_size: Optional[tuple] = None,
        crops_coords_top_left: Optional[tuple] = None,
        original_size: Optional[tuple] = None,
    ):
        """
        Generate an image with the specified model.

        Automatically:
        - Resolves checkpoint to Standard
        - Loads model (with kill/revive if needed)
        - Injects trigger tags (for Pony, etc.)
        - Applies scheduler overrides (for Lightning, etc.)
        - Injects style prefixes/negatives (STYLE_HARD_ACTION, etc.)

        Args:
            prompt: The generation prompt
            lora_names: Comma-separated LoRA names (experimental)
            checkpoint: Model name or Standard
            profile: Resolution profile (portrait_full_body, landscape_16_9)
            negative_prompt: Override default negative prompt
            width: Override width
            height: Override height
            num_inference_steps: Override steps (uses model default if None)
            guidance_scale: Override guidance (uses model default if None)
            style: Production style (STYLE_HARD_ACTION, STYLE_INTENSE_INTERACTION, etc.)
            target_size: SDXL target (width, height) - prevents stretching
            crops_coords_top_left: SDXL crop origin (x, y) - prevents offset
            original_size: SDXL original (width, height) - prevents rescaling

        Returns:
            Generated PIL Image
        """
        # Load style config if specified
        style_config = None
        if style and style in PRODUCTION_STYLES:
            style_config = PRODUCTION_STYLES[style]
            print(f"🔥 Style loaded: {style_config.get('display_name', style)}")

            # Override checkpoint from style if not explicitly set
            if checkpoint == "base" and style_config.get("base_models"):
                # Use first available model from style's preference
                checkpoint = style_config["base_models"][0]
                print(f"   → Model override: {checkpoint}")

        # Resolve standard and load model
        standard = self._resolve_standard(checkpoint)
        self.load_model(checkpoint)

        # Get model-specific generation config
        gen_config = self.router.get_generation_config(standard)

        # Prepare prompt with trigger tags (for Pony, etc.)
        prepared_prompt = self.router.prepare_prompt(standard, prompt)

        # STYLE INJECTION: Prepend/append style prompts
        if style_config:
            prefix = style_config.get("prompt_prefix", "").strip()
            suffix = style_config.get("prompt_suffix", "").strip()
            if prefix:
                prepared_prompt = f"{prefix} {prepared_prompt}"
            if suffix:
                prepared_prompt = f"{prepared_prompt} {suffix}"
            print(f"   → Style prompt injected: {prefix[:50]}...")

        # Handle LoRAs if specified
        if lora_names:
            try:
                self.pipe.unload_lora_weights()
                print(f"🎨 Applying LoRAs: {lora_names}")
                active_loras = lora_names.split(",")
                for lora in active_loras:
                    try:
                        self.pipe.load_lora_weights(f"loras/{lora}.safetensors", adapter_name=lora)
                    except Exception:
                        pass
            except AttributeError:
                # Pipeline doesn't support LoRA
                pass

        # Resolve dimensions from profile or explicit params
        if width is None or height is None:
            profile_w, profile_h = self.get_resolution(profile)
            width = width or profile_w
            height = height or profile_h

        # STYLE INJECTION: Override negative prompt from style
        if style_config and style_config.get("negative_prompt") and negative_prompt is None:
            neg_prompt = style_config["negative_prompt"].strip()
            print(f"   → Style negative prompt injected")
        else:
            neg_prompt = negative_prompt if negative_prompt is not None else self.negative_prompt

        # STYLE INJECTION: Override steps/guidance from style
        style_gen = style_config.get("generation", {}) if style_config else {}
        steps = num_inference_steps or style_gen.get("steps") or gen_config.get("num_inference_steps") or self.default_steps
        guidance = guidance_scale or style_gen.get("cfg_scale") or gen_config.get("guidance_scale") or self.default_guidance

        print(f"🖌️ Generating with {standard}...")
        print(f"   Prompt: {prepared_prompt[:60]}...")
        print(f"   Resolution: {width}x{height}")
        print(f"   Steps: {steps} | Guidance: {guidance}")
        if style:
            print(f"   Style: {style}")

        # Build generation kwargs
        gen_kwargs = {
            "prompt": prepared_prompt,
            "negative_prompt": neg_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        # SDXL Geometry parameters - prevent aspect ratio distortion
        # These tell SDXL exactly what size we want without stretching/cropping
        if target_size is not None:
            gen_kwargs["target_size"] = target_size
            print(f"   SDXL target_size: {target_size}")
        if crops_coords_top_left is not None:
            gen_kwargs["crops_coords_top_left"] = crops_coords_top_left
        if original_size is not None:
            gen_kwargs["original_size"] = original_size

        image = self.pipe(**gen_kwargs).images[0]

        return image

    def save_image(self, image, output_path: Union[str, Path]) -> Path:
        """
        Save image with path normalization and verification.

        Args:
            image: PIL Image to save
            output_path: Destination path (will be normalized to absolute)

        Returns:
            Absolute path where image was saved
        """
        # Normalize to absolute path immediately
        output_path = Path(os.path.abspath(str(output_path)))

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"💾 Saving image to: {output_path}")
        image.save(output_path, "PNG")

        # Verify the file was written
        if not output_path.exists():
            raise FileNotFoundError(f"Save failed - file not found after write: {output_path}")

        file_size = output_path.stat().st_size
        if file_size == 0:
            raise IOError(f"Save failed - file is empty: {output_path}")

        print(f"✅ Verified: {output_path} ({file_size / 1024:.1f} KB)")
        return output_path

    def generate_and_save(
        self,
        prompt: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> dict:
        """
        Generate an image and save it with verification.

        Args:
            prompt: The generation prompt
            output_path: Where to save (default: OUTPUT_DIR/generated_<timestamp>.png)
            **kwargs: All args from generate() (profile, checkpoint, etc.)

        Returns:
            dict with 'image' (PIL), 'path' (absolute Path), 'verified' (bool)
        """
        # Generate the image
        image = self.generate(prompt, **kwargs)

        # Default output path with timestamp
        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"generated_{timestamp}.png"

        # Save with verification
        saved_path = self.save_image(image, output_path)

        return {
            "image": image,
            "path": saved_path,
            "verified": saved_path.exists()
        }

    def list_available_models(self) -> list:
        """List all available model Standards."""
        return self.router.list_standards()


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION - For shared VRAMManager across generators
# ═══════════════════════════════════════════════════════════════════════════════

def create_image_generator(shared_vram_manager: Optional[VRAMManager] = None) -> LocalImageGenerator:
    """
    Factory function to create an image generator.

    Args:
        shared_vram_manager: Pass a shared VRAMManager for coordinated VRAM usage
                             across image and video generators.

    Returns:
        LocalImageGenerator instance

    Example:
        # Shared VRAM coordination
        vram_mgr = VRAMManager()

        # Image generation
        img_gen = create_image_generator(vram_mgr)
        img_gen.generate("a sunset", checkpoint="pony")

        # Before SVD - kill image model
        vram_mgr.kill()

        # Now SVD can safely load
        video_gen = create_video_generator(vram_mgr)  # hypothetical
    """
    return LocalImageGenerator(vram_manager=shared_vram_manager)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI EXECUTION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entrypoint for standalone image generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Universal Image Generator")
    parser.add_argument("prompt", type=str, help="Generation prompt")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output path (default: auto-generated in OUTPUT_DIR)")
    parser.add_argument("-p", "--profile", type=str, default=None,
                        choices=["portrait_full_body", "landscape_16_9", "square"],
                        help="Resolution profile")
    parser.add_argument("-c", "--checkpoint", type=str, default="base",
                        help="Model: base, photoreal, cinematic, anatomy, action, draft")
    parser.add_argument("-s", "--steps", type=int, default=None,
                        help="Override inference steps")
    parser.add_argument("-g", "--guidance", type=float, default=None,
                        help="Override guidance scale")
    parser.add_argument("--list-models", action="store_true",
                        help="List available models and exit")
    args = parser.parse_args()

    gen = LocalImageGenerator()

    if args.list_models:
        print("Available Models:")
        print("=" * 40)
        for std in gen.list_available_models():
            config = gen.router.get_generation_config(std)
            print(f"  {std}")
            print(f"    VRAM: ~{config.get('vram_estimate_gb', '?')}GB")
            print(f"    Steps: {config.get('num_inference_steps', 30)}")
        print("\nCheckpoint Aliases:")
        for alias, standard in CHECKPOINT_TO_STANDARD.items():
            if not alias.startswith("STANDARD_"):
                print(f"  {alias} → {standard}")
        return

    print("=" * 60)
    print("UNIVERSAL IMAGE GENERATOR")
    print("=" * 60)
    print(f"Prompt: {args.prompt[:80]}...")
    print(f"Model: {args.checkpoint} → {gen._resolve_standard(args.checkpoint)}")
    print(f"Profile: {args.profile or 'default'}")
    print(f"Output: {args.output or 'auto'}")
    print("=" * 60)

    result = gen.generate_and_save(
        prompt=args.prompt,
        output_path=args.output,
        profile=args.profile,
        checkpoint=args.checkpoint,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance
    )

    # SUCCESS LOG
    print("\n" + "=" * 60)
    print("SUCCESS - IMAGE SAVED")
    print("=" * 60)
    print(f"ABSOLUTE PATH: {result['path']}")
    print(f"VERIFIED: {result['verified']}")
    print(f"SIZE: {result['path'].stat().st_size / 1024:.1f} KB")
    print(f"VRAM USAGE: {gen.get_vram_status()['vram_usage_gb']:.2f}GB")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()
