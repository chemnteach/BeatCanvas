"""
Local SDXL Image Generator with Multi-LoRA Support

Generates images locally using Stable Diffusion XL with custom LoRAs.
Supports stacking multiple LoRAs (character + scene + style).

Requirements:
- diffusers, transformers, torch, safetensors
- 8-12GB VRAM for SDXL + LoRAs
- Trained LoRA files in output/loras/

Usage:
    generator = SDXLLoRAGenerator()
    images = await generator.generate_with_loras(
        prompt="ohwx man on beach meeting tropical woman",
        loras=[
            {"path": "output/loras/rob-character/rob-character.safetensors", "weight": 0.8},
            {"path": "output/loras/beach-sunset/beach-sunset.safetensors", "weight": 0.7},
            {"path": "output/loras/70s-film-retro/70s-film-retro.safetensors", "weight": 0.6}
        ],
        num_images=2
    )
"""

import torch
import asyncio
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import yaml

try:
    from diffusers import DiffusionPipeline, StableDiffusionXLPipeline
    from safetensors.torch import load_file
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    print("[SDXL-LORA] Warning: diffusers not installed")
    print("[SDXL-LORA] Install with: pip install diffusers transformers safetensors")


@dataclass
class LoRAConfig:
    """Configuration for a single LoRA"""
    path: str
    weight: float = 0.7
    trigger: Optional[str] = None


@dataclass
class SDXLGenerationResult:
    """Result of SDXL generation"""
    success: bool
    images: List[str] = None
    error: Optional[str] = None


class SDXLLoRAGenerator:
    """
    Local SDXL image generator with multi-LoRA stacking support.

    Loads and caches SDXL pipeline + LoRAs for efficient batch generation.
    """

    # Project root = 4 levels up from this file (backend/src/assets/sdxl_lora_generator.py)
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    _LORA_BASE = _PROJECT_ROOT / "output" / "loras"

    def __init__(
        self,
        model_id: str = "stabilityai/stable-diffusion-xl-base-1.0",
        device: str = "cuda",
        lora_registry_path: str = None
    ):
        if not DIFFUSERS_AVAILABLE:
            raise ImportError(
                "diffusers not available. Install with: "
                "pip install diffusers transformers safetensors torch"
            )

        self.model_id = model_id
        self.device = device if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.loaded_loras = {}  # Cache loaded LoRAs
        self.output_dir = self._PROJECT_ROOT / "backend" / "data" / "generated_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load LoRA registry
        if lora_registry_path is None:
            lora_registry_path = self._PROJECT_ROOT / "backend" / "config" / "loras.yaml"
        self.lora_registry_path = Path(lora_registry_path)
        self.lora_registry = self._load_lora_registry()

        print(f"[SDXL-LORA] Initialized on device: {self.device}")
        if self.device == "cpu":
            print("[SDXL-LORA] Warning: Running on CPU - generation will be slow")

    def _load_lora_registry(self) -> Dict:
        """Load LoRA registry from config file"""
        if not self.lora_registry_path.exists():
            print(f"[SDXL-LORA] Warning: LoRA registry not found: {self.lora_registry_path}")
            return {}

        with open(self.lora_registry_path, 'r') as f:
            registry = yaml.safe_load(f)

        # Filter to enabled LoRAs only
        enabled_loras = {
            name: config for name, config in registry.items()
            if config.get('enabled', False)
        }

        print(f"[SDXL-LORA] Loaded {len(enabled_loras)} enabled LoRAs from registry")
        return enabled_loras

    async def load_pipeline(self):
        """Load SDXL pipeline (lazy loading)"""
        if self.pipeline is not None:
            return

        print(f"[SDXL-LORA] Loading SDXL pipeline: {self.model_id}")
        print(f"[SDXL-LORA] This may take 30-60 seconds on first load...")

        # Load pipeline in executor to avoid blocking
        def _load():
            pipe = StableDiffusionXLPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
                variant="fp16" if self.device == "cuda" else None
            )
            pipe = pipe.to(self.device)

            # Enable memory optimizations
            if self.device == "cuda":
                pipe.enable_model_cpu_offload()
                pipe.enable_vae_slicing()
                pipe.enable_vae_tiling()

            return pipe

        self.pipeline = await asyncio.get_event_loop().run_in_executor(None, _load)
        print(f"[SDXL-LORA] Pipeline loaded successfully")

    def _load_lora_weights(self, lora_path: str) -> Dict:
        """Load LoRA weights from safetensors file"""
        lora_file = Path(lora_path)

        # Support relative paths from output/loras/
        if not lora_file.is_absolute():
            lora_file = self._LORA_BASE / lora_path

        if not lora_file.exists():
            raise FileNotFoundError(f"LoRA not found: {lora_file}")

        # Cache loaded LoRAs
        cache_key = str(lora_file)
        if cache_key in self.loaded_loras:
            return self.loaded_loras[cache_key]

        print(f"[SDXL-LORA] Loading LoRA: {lora_file.name}")
        lora_weights = load_file(lora_file)
        self.loaded_loras[cache_key] = lora_weights

        return lora_weights

    def _apply_loras_to_pipeline(self, loras: List[LoRAConfig]):
        """Apply multiple LoRAs to pipeline with weights"""
        # Clear any previously loaded LoRAs
        if hasattr(self.pipeline, 'unload_lora_weights'):
            self.pipeline.unload_lora_weights()

        # Load and fuse all LoRAs
        for lora_config in loras:
            lora_weights = self._load_lora_weights(lora_config.path)
            self.pipeline.load_lora_weights(lora_weights)
            self.pipeline.fuse_lora(lora_scale=lora_config.weight)

        print(f"[SDXL-LORA] Applied {len(loras)} LoRAs to pipeline")

    def get_lora_by_name(self, lora_name: str) -> Optional[Dict]:
        """Look up LoRA config by name from registry"""
        return self.lora_registry.get(lora_name)

    def build_prompt_with_triggers(
        self,
        base_prompt: str,
        loras: List[LoRAConfig]
    ) -> str:
        """
        Build final prompt with LoRA trigger words.

        Prepends trigger words to base prompt for LoRA activation.
        """
        triggers = []

        for lora_config in loras:
            if lora_config.trigger:
                triggers.append(lora_config.trigger)

        if triggers:
            trigger_string = ", ".join(triggers)
            return f"{trigger_string}, {base_prompt}"

        return base_prompt

    async def generate_with_loras(
        self,
        prompt: str,
        loras: List[Dict],  # List of {"path": str, "weight": float, "trigger": str}
        negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
        num_images: int = 1,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        scene_timestamp: float = 0.0,
    ) -> SDXLGenerationResult:
        """
        Generate images with multiple LoRAs stacked.

        Args:
            prompt: Base text prompt
            loras: List of LoRA configs [{"path": "...", "weight": 0.7, "trigger": "ohwx"}]
            negative_prompt: Things to avoid in generation
            num_images: Number of images to generate
            width, height: Image dimensions (must be multiples of 8)
            num_inference_steps: Quality vs speed tradeoff (20-50)
            guidance_scale: Prompt adherence (7-12)
            scene_timestamp: Scene timestamp for filename
        """
        try:
            # Load pipeline if not already loaded
            await self.load_pipeline()

            # Convert dict configs to LoRAConfig objects
            lora_configs = [
                LoRAConfig(
                    path=lora.get("path"),
                    weight=lora.get("weight", 0.7),
                    trigger=lora.get("trigger")
                )
                for lora in loras
            ]

            # Apply LoRAs to pipeline
            self._apply_loras_to_pipeline(lora_configs)

            # Build prompt with trigger words
            full_prompt = self.build_prompt_with_triggers(prompt, lora_configs)

            print(f"[SDXL-LORA] Generating {num_images} images")
            print(f"[SDXL-LORA] Prompt: {full_prompt[:100]}...")
            print(f"[SDXL-LORA] LoRAs: {[Path(lc.path).stem for lc in lora_configs]}")

            # Generate images
            def _generate():
                return self.pipeline(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    num_images_per_prompt=num_images,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                ).images

            images = await asyncio.get_event_loop().run_in_executor(None, _generate)

            # Save images
            image_paths = []
            for i, image in enumerate(images):
                filename = f"scene_{scene_timestamp:.1f}_sdxl_lora_var_{i}_{uuid.uuid4().hex[:8]}.png"
                filepath = self.output_dir / filename
                image.save(filepath)
                image_paths.append(str(filepath))
                print(f"[SDXL-LORA] Saved: {filepath.name}")

            return SDXLGenerationResult(
                success=True,
                images=image_paths
            )

        except Exception as e:
            print(f"[SDXL-LORA] Generation error: {e}")
            return SDXLGenerationResult(
                success=False,
                error=str(e)
            )

    async def generate_character_scene(
        self,
        character_lora: str,  # LoRA name from registry or path
        scene_description: str,
        scene_lora: Optional[str] = None,
        style_lora: Optional[str] = None,
        **kwargs
    ) -> SDXLGenerationResult:
        """
        Convenience method for generating character scenes.

        Args:
            character_lora: Character LoRA name (e.g., "rob-character") or path
            scene_description: Base prompt (e.g., "man on beach meeting tropical woman")
            scene_lora: Optional scene LoRA name (e.g., "beach-sunset")
            style_lora: Optional style LoRA name (e.g., "70s-film-retro")
            **kwargs: Additional arguments passed to generate_with_loras
        """
        loras = []

        # Add character LoRA
        char_config = self.get_lora_by_name(character_lora)
        if char_config:
            loras.append({
                "path": char_config["file"],
                "weight": char_config.get("default_weight", 0.8),
                "trigger": char_config.get("triggers", [None])[0]
            })
        else:
            # Assume it's a direct path
            loras.append({"path": character_lora, "weight": 0.8})

        # Add scene LoRA if specified
        if scene_lora:
            scene_config = self.get_lora_by_name(scene_lora)
            if scene_config:
                loras.append({
                    "path": scene_config["file"],
                    "weight": scene_config.get("default_weight", 0.7),
                    "trigger": scene_config.get("triggers", [None])[0] if scene_config.get("triggers") else None
                })

        # Add style LoRA if specified
        if style_lora:
            style_config = self.get_lora_by_name(style_lora)
            if style_config:
                loras.append({
                    "path": style_config["file"],
                    "weight": style_config.get("default_weight", 0.6),
                    "trigger": style_config.get("triggers", [None])[0] if style_config.get("triggers") else None
                })

        return await self.generate_with_loras(
            prompt=scene_description,
            loras=loras,
            **kwargs
        )

    def unload(self):
        """Free GPU memory by unloading pipeline"""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            self.loaded_loras.clear()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print("[SDXL-LORA] Pipeline unloaded, GPU memory freed")
