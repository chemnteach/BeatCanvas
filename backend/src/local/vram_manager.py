"""
VRAM Manager and Model Router for BeatCanvas Production.

Handles model routing, VRAM management, and the 'Kill and Revive' pattern
for 12GB VRAM budget (Acer Predator).

Rule: Only ONE model loaded at a time. Kill before swap.
"""

import gc
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Lazy import torch to avoid import errors when CUDA unavailable
_torch = None


def _get_torch():
    """Lazy load torch module."""
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def load_checkpoints_config() -> Dict[str, Any]:
    """Load checkpoints.yaml configuration."""
    config_path = Path(__file__).parent.parent.parent / "config" / "checkpoints.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Checkpoints config not found: {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class ModelRouter:
    """
    Routes model requests and handles prompt/config modifications.

    Responsibilities:
    - Resolve standard names to physical file paths
    - Inject trigger tags for models that require them (PONY)
    - Return scheduler/config overrides for special models (LIGHTNING)
    """

    def __init__(self):
        self.checkpoints = load_checkpoints_config()

    def resolve(self, standard: str) -> Path:
        """
        Resolve a standard name to its absolute file path.

        Args:
            standard: Model standard name (e.g., "STANDARD_US")

        Returns:
            Absolute Path to the .safetensors file

        Raises:
            KeyError: If standard not found in config
            FileNotFoundError: If resolved path doesn't exist
        """
        if standard not in self.checkpoints:
            raise KeyError(f"Unknown standard: {standard}")

        config = self.checkpoints[standard]

        # Handle aliases
        if "alias_of" in config:
            return self.resolve(config["alias_of"])

        path = Path(config["path"])

        # Ensure absolute
        if not path.is_absolute():
            path = Path(os.path.abspath(str(path)))

        return path

    def prepare_prompt(self, standard: str, prompt: str) -> str:
        """
        Prepare prompt with any required trigger tags.

        Args:
            standard: Model standard name
            prompt: Original user prompt

        Returns:
            Modified prompt with trigger tags prepended (if required)
        """
        if standard not in self.checkpoints:
            return prompt

        config = self.checkpoints[standard]
        trigger_tags = config.get("trigger_tags")

        if trigger_tags:
            # Prepend trigger tags to prompt
            return f"{trigger_tags}, {prompt}"

        return prompt

    def get_generation_config(self, standard: str) -> Dict[str, Any]:
        """
        Get generation configuration for a standard.

        Args:
            standard: Model standard name

        Returns:
            Dict with scheduler, num_inference_steps, guidance_scale, etc.
        """
        if standard not in self.checkpoints:
            return self._default_config()

        config = self.checkpoints[standard]

        result = {
            "scheduler": config.get("scheduler"),
            "scheduler_config": config.get("scheduler_config"),
            "num_inference_steps": config.get("num_inference_steps", 30),
            "guidance_scale": config.get("guidance_scale", 7.5),
            "vram_estimate_gb": config.get("vram_estimate_gb", 6.5),
        }

        return result

    def _default_config(self) -> Dict[str, Any]:
        """Return default generation config."""
        return {
            "scheduler": None,
            "scheduler_config": None,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "vram_estimate_gb": 6.5,
        }

    def list_standards(self) -> list:
        """List all available standards (excluding aliases)."""
        return [
            name for name, config in self.checkpoints.items()
            if "alias_of" not in config and name.startswith("STANDARD_")
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# VRAM MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class VRAMManager:
    """
    Manages VRAM lifecycle with 'Kill and Revive' pattern.

    12GB VRAM Budget Rules:
    - Only ONE model loaded at a time
    - Kill current model before loading new one
    - Return to <1GB baseline after kill

    The 'Kill' sequence:
    1. Delete pipeline reference
    2. Clear internal state
    3. Force garbage collection
    4. Clear CUDA cache
    """

    VRAM_BASE_THRESHOLD_GB = 1.0  # Must return to <1GB after kill

    def __init__(self):
        self.pipe = None
        self.current_model: Optional[str] = None
        self.checkpoints = load_checkpoints_config()
        self.router = ModelRouter()

    def get_vram_usage(self) -> float:
        """
        Get current VRAM usage in GB.

        Returns:
            VRAM usage in gigabytes (float)
        """
        torch = _get_torch()

        if not torch.cuda.is_available():
            return 0.0

        # Get allocated memory (what our tensors are using)
        allocated = torch.cuda.memory_allocated()
        # Convert bytes to GB
        return allocated / (1024 ** 3)

    def get_vram_total(self) -> float:
        """
        Get total VRAM available in GB.

        Returns:
            Total VRAM in gigabytes (float)
        """
        torch = _get_torch()

        if not torch.cuda.is_available():
            return 0.0

        total = torch.cuda.get_device_properties(0).total_memory
        return total / (1024 ** 3)

    def get_vram_free(self) -> float:
        """
        Get free VRAM in GB.

        Returns:
            Free VRAM in gigabytes (float)
        """
        torch = _get_torch()

        if not torch.cuda.is_available():
            return 0.0

        free, total = torch.cuda.mem_get_info()
        return free / (1024 ** 3)

    def kill(self) -> float:
        """
        Kill current model and reclaim VRAM - DEEP PURGE.

        The 'Kill and Revive' sequence with Deep Purge:
        1. Unload any LoRA weights (critical for style isolation)
        2. Delete pipeline reference
        3. Clear internal state
        4. Force garbage collection (3 passes)
        5. Clear CUDA cache
        6. Synchronize CUDA

        Returns:
            VRAM usage after kill (should be <1GB for baseline, <1.5GB threshold)
        """
        torch = _get_torch()

        # Step 1: DEEP PURGE - Unload LoRAs first (prevents weight contamination)
        if self.pipe is not None:
            try:
                self.pipe.unload_lora_weights()
            except (AttributeError, Exception):
                # Pipeline may not have LoRA support
                pass

        # Step 2: Delete pipeline
        if self.pipe is not None:
            del self.pipe
            self.pipe = None

        # Step 3: Clear state
        self.current_model = None

        # Step 4: Force garbage collection (3 passes for deep cleanup)
        gc.collect()
        gc.collect()
        gc.collect()

        # Step 5 & 6: Clear CUDA cache and sync
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        # Return current usage for verification
        return self.get_vram_usage()

    def load(self, standard: str, force_reload: bool = False) -> bool:
        """
        Load a model by standard name.

        Args:
            standard: Model standard (e.g., "STANDARD_US")
            force_reload: If True, reload even if already loaded

        Returns:
            True if model was loaded, False if already loaded (no-op)
        """
        # No-op if already loaded
        if self.current_model == standard and not force_reload:
            return False

        # Kill current model first
        self.kill()

        # Resolve path
        model_path = self.router.resolve(standard)

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Get model config
        model_config = self.checkpoints.get(standard, {})

        # Import diffusers here to avoid top-level import issues
        from diffusers import StableDiffusionXLPipeline

        torch = _get_torch()

        print(f"⚡ Loading: {standard}")
        print(f"   Path: {model_path}")
        print(f"   VRAM before: {self.get_vram_usage():.2f}GB")

        # Check if model needs external base components (UNet + text encoders)
        base_source = model_config.get("requires_base_components_from")

        if base_source:
            # Load all base components from specified source
            print(f"   Loading base components from: {base_source}")
            from transformers import CLIPTextModel, CLIPTextModelWithProjection, CLIPTokenizer
            from diffusers import UNet2DConditionModel, AutoencoderKL

            # Load UNet from base model
            print(f"   Loading UNet...")
            unet = UNet2DConditionModel.from_pretrained(
                base_source,
                subfolder="unet",
                torch_dtype=torch.float16,
            )

            # Load text encoders from base model
            print(f"   Loading text encoders...")
            text_encoder = CLIPTextModel.from_pretrained(
                base_source,
                subfolder="text_encoder",
                torch_dtype=torch.float16,
            )
            text_encoder_2 = CLIPTextModelWithProjection.from_pretrained(
                base_source,
                subfolder="text_encoder_2",
                torch_dtype=torch.float16,
            )

            # Load tokenizers from base model (required for generation)
            print(f"   Loading tokenizers...")
            tokenizer = CLIPTokenizer.from_pretrained(
                base_source,
                subfolder="tokenizer",
            )
            tokenizer_2 = CLIPTokenizer.from_pretrained(
                base_source,
                subfolder="tokenizer_2",
            )

            # Load VAE from base model
            print(f"   Loading VAE...")
            vae = AutoencoderKL.from_pretrained(
                base_source,
                subfolder="vae",
                torch_dtype=torch.float16,
            )

            # Load pipeline with all external components
            # The checkpoint provides fine-tuned weights that will be merged
            self.pipe = StableDiffusionXLPipeline.from_single_file(
                str(model_path),
                unet=unet,
                text_encoder=text_encoder,
                text_encoder_2=text_encoder_2,
                tokenizer=tokenizer,
                tokenizer_2=tokenizer_2,
                vae=vae,
                torch_dtype=torch.float16,
                safety_checker=None,
                requires_safety_checker=False,
            )
        else:
            # Standard loading - model has all components embedded
            self.pipe = StableDiffusionXLPipeline.from_single_file(
                str(model_path),
                torch_dtype=torch.float16,
                safety_checker=None,
                requires_safety_checker=False,
                local_files_only=True
            )

        self.pipe.to("cuda")
        self.current_model = standard

        # VAE Precision Fix: Explicit dtype alignment for 9:16 vertical renders
        # UNet stays in float16 for VRAM speed, VAE goes to float32 for precision
        try:
            torch = _get_torch()
            # Move VAE to float32 for better precision during decoding
            self.pipe.vae.to(dtype=torch.float32)
            # Ensure UNet stays in float16 for performance
            self.pipe.unet.to(dtype=torch.float16)
            print(f"   VAE precision: float32 (pixel alignment)")
            print(f"   UNet precision: float16 (VRAM speed)")

            # Patch VAE decode to handle float16 latents → float32 VAE
            # This prevents dtype mismatch during decoding
            original_decode = self.pipe.vae.decode
            def decode_with_dtype_cast(latents, *args, **kwargs):
                # Cast latents from UNet's float16 to VAE's float32
                latents = latents.to(dtype=torch.float32)
                return original_decode(latents, *args, **kwargs)
            self.pipe.vae.decode = decode_with_dtype_cast
            print(f"   VAE decode: patched (auto float16→float32)")

        except (AttributeError, Exception) as e:
            # Fallback: try upcast_vae method
            try:
                self.pipe.upcast_vae()
                print(f"   VAE upcast: enabled (fallback)")
            except (AttributeError, Exception):
                print(f"   VAE precision: default (no upcast available)")

        print(f"   VRAM after: {self.get_vram_usage():.2f}GB")
        print(f"✅ Loaded: {standard}")

        return True

    def swap(self, standard: str) -> float:
        """
        Swap to a different model (kill + load).

        Args:
            standard: Target model standard

        Returns:
            VRAM delta (usage after - usage before kill)
        """
        vram_before = self.get_vram_usage()
        self.load(standard)
        vram_after = self.get_vram_usage()

        return vram_after - vram_before

    def is_loaded(self) -> bool:
        """Check if any model is currently loaded."""
        return self.pipe is not None

    def status(self) -> Dict[str, Any]:
        """Get current VRAM manager status."""
        return {
            "current_model": self.current_model,
            "is_loaded": self.is_loaded(),
            "vram_usage_gb": self.get_vram_usage(),
            "vram_free_gb": self.get_vram_free(),
            "vram_total_gb": self.get_vram_total(),
            "under_threshold": self.get_vram_usage() < self.VRAM_BASE_THRESHOLD_GB,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI for VRAM manager testing."""
    import argparse

    parser = argparse.ArgumentParser(description="VRAM Manager CLI")
    parser.add_argument("command", choices=["status", "kill", "list"],
                        help="Command to run")
    args = parser.parse_args()

    manager = VRAMManager()

    if args.command == "status":
        status = manager.status()
        print("=" * 50)
        print("VRAM MANAGER STATUS")
        print("=" * 50)
        for key, value in status.items():
            print(f"  {key}: {value}")
        print("=" * 50)

    elif args.command == "kill":
        print("Killing current model...")
        usage = manager.kill()
        print(f"VRAM after kill: {usage:.2f}GB")
        print(f"Under threshold (<{manager.VRAM_BASE_THRESHOLD_GB}GB): {usage < manager.VRAM_BASE_THRESHOLD_GB}")

    elif args.command == "list":
        print("Available Standards:")
        for std in manager.router.list_standards():
            config = manager.checkpoints[std]
            print(f"  {std}")
            print(f"    Path: {config['path']}")
            print(f"    VRAM: ~{config.get('vram_estimate_gb', '?')}GB")


if __name__ == "__main__":
    main()
