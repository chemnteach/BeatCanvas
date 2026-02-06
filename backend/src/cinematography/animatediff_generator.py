"""
AnimateDiff-Lightning Video Generator - Production wrapper for BeatCanvas.

Text-to-video generation using AnimateDiff-Lightning (4-step distilled).
Optimized for SD 1.5 base models with 75-token CLIP limit.

VRAM Budget: ~5.6GB (allows 2-3 parallel instances on 16GB GPU)
Frame Output: 16 frames -> RAFT interpolation to target FPS

Integrates with:
- CinematographyEngine for prompt composition
- optics_presets.yaml for style-specific parameters
- VRAMManager for coordinated GPU lifecycle
"""

import torch
import gc
import json
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List, TYPE_CHECKING
from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

if TYPE_CHECKING:
    from src.local.vram_manager import VRAMManager


# AnimateDiff Configuration
ANIMATEDIFF_STEP = 4  # 4-step distilled model
ANIMATEDIFF_REPO = "ByteDance/AnimateDiff-Lightning"
ANIMATEDIFF_CKPT = f"animatediff_lightning_{ANIMATEDIFF_STEP}step_diffusers.safetensors"
DEFAULT_BASE_MODEL = "emilianJR/epiCRealism"  # SD 1.5 photorealistic base
DEFAULT_NUM_FRAMES = 16


class HeartbeatCallback:
    """JSON heartbeat callback for step-by-step render monitoring."""

    def __init__(self, callback_fn: Optional[Callable[[dict], None]] = None):
        self.callback_fn = callback_fn or self._default_callback
        self.start_time = None
        self.total_steps = 0

    def _default_callback(self, data: dict):
        """Default: print JSON to stdout for external process monitoring."""
        print(json.dumps(data), flush=True)

    def __call__(self, pipe, step: int, timestep: int, callback_kwargs: dict):
        """Called by diffusers pipeline at each denoising step."""
        if self.start_time is None:
            self.start_time = datetime.now()

        elapsed = (datetime.now() - self.start_time).total_seconds()
        progress = (step + 1) / self.total_steps if self.total_steps > 0 else 0
        eta = (elapsed / (step + 1)) * (self.total_steps - step - 1) if step > 0 else 0

        heartbeat = {
            "type": "heartbeat",
            "phase": "denoise",
            "step": step + 1,
            "total_steps": self.total_steps,
            "progress": round(progress * 100, 1),
            "elapsed_sec": round(elapsed, 1),
            "eta_sec": round(eta, 1),
            "timestep": int(timestep),
            "timestamp": datetime.now().isoformat()
        }

        self.callback_fn(heartbeat)
        return callback_kwargs


class AnimateDiffGenerator:
    """
    AnimateDiff-Lightning video generator for production.

    Integrates with:
    - CinematographyEngine for prompt composition
    - optics_presets.yaml for style-specific parameters
    - VRAMManager for coordinated GPU lifecycle
    """

    # AnimateDiff requires ~5.6GB VRAM (allows 2-3 parallel on 16GB)
    VRAM_ESTIMATE_GB = 5.6

    def __init__(
        self,
        vram_manager: Optional["VRAMManager"] = None,
        heartbeat_callback: Optional[Callable[[dict], None]] = None,
        base_model: str = DEFAULT_BASE_MODEL
    ):
        """
        Initialize the AnimateDiff generator.

        Args:
            vram_manager: Optional shared VRAMManager for VRAM coordination
            heartbeat_callback: Optional callback for progress updates
            base_model: SD 1.5 base model (default: epiCRealism)
        """
        self.vram_manager = vram_manager
        self.pipe = None
        self.base_model = base_model
        self.heartbeat_callback = heartbeat_callback
        self.loaded = False

        # Generation defaults (can be overridden per call)
        self.default_num_frames = DEFAULT_NUM_FRAMES
        self.default_guidance_scale = 1.0
        self.default_steps = ANIMATEDIFF_STEP

    def _emit_heartbeat(self, phase: str, message: str, **kwargs):
        """Emit a JSON heartbeat for monitoring."""
        data = {
            "type": "heartbeat",
            "phase": phase,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        if self.heartbeat_callback:
            self.heartbeat_callback(data)
        else:
            print(json.dumps(data), flush=True)

    def get_vram_usage(self) -> float:
        """Get current VRAM usage in GB."""
        if self.vram_manager:
            return self.vram_manager.get_vram_usage()

        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 3)
        return 0.0

    def get_vram_free(self) -> float:
        """Get free VRAM in GB."""
        if self.vram_manager:
            return self.vram_manager.get_vram_free()

        if torch.cuda.is_available():
            free, _ = torch.cuda.mem_get_info()
            return free / (1024 ** 3)
        return 0.0

    def kill(self) -> float:
        """
        Kill AnimateDiff model and reclaim VRAM.

        MUST be called before handing off to another GPU-intensive stage.

        Returns:
            VRAM usage after kill (should be <1GB)
        """
        self._emit_heartbeat("kill", "Killing AnimateDiff model...")

        # Delete pipeline components
        if self.pipe is not None:
            if hasattr(self.pipe, 'motion_adapter'):
                del self.pipe.motion_adapter
            if hasattr(self.pipe, 'unet'):
                del self.pipe.unet
            if hasattr(self.pipe, 'vae'):
                del self.pipe.vae
            del self.pipe
            self.pipe = None

        self.loaded = False

        # Force garbage collection
        gc.collect()
        gc.collect()
        gc.collect()

        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        vram_after = self.get_vram_usage()
        self._emit_heartbeat(
            "kill_complete",
            f"AnimateDiff killed. VRAM: {vram_after:.2f}GB",
            vram_after_gb=round(vram_after, 2)
        )

        return vram_after

    def is_loaded(self) -> bool:
        """Check if AnimateDiff model is currently loaded."""
        return self.loaded and self.pipe is not None

    def load(self):
        """
        Load AnimateDiff-Lightning pipeline.

        Loads:
        - Motion adapter (4-step distilled)
        - SD 1.5 base model (epiCRealism or custom)
        - Configured scheduler
        """
        if self.pipe is not None:
            return

        # Check VRAM availability
        vram_free = self.get_vram_free()
        if vram_free < self.VRAM_ESTIMATE_GB:
            self._emit_heartbeat(
                "warning",
                f"Low VRAM: {vram_free:.1f}GB free, AnimateDiff needs ~{self.VRAM_ESTIMATE_GB}GB",
                vram_free_gb=round(vram_free, 2),
                vram_required_gb=self.VRAM_ESTIMATE_GB
            )

        self._emit_heartbeat("load", f"Loading AnimateDiff-Lightning from {ANIMATEDIFF_REPO}...")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16

        # Load motion adapter
        self._emit_heartbeat("load", "Loading motion adapter...")
        adapter = MotionAdapter().to(device, dtype)
        adapter.load_state_dict(
            load_file(hf_hub_download(ANIMATEDIFF_REPO, ANIMATEDIFF_CKPT), device=device)
        )

        # Load base model
        self._emit_heartbeat("load", f"Loading base model: {self.base_model}...")
        self.pipe = AnimateDiffPipeline.from_pretrained(
            self.base_model,
            motion_adapter=adapter,
            torch_dtype=dtype,
        ).to(device)

        # Configure scheduler for Lightning
        self.pipe.scheduler = EulerDiscreteScheduler.from_config(
            self.pipe.scheduler.config,
            timestep_spacing="trailing",
            beta_schedule="linear",
        )

        # Memory optimizations
        self.pipe.enable_vae_slicing()

        self.loaded = True

        vram_after = self.get_vram_usage()
        self._emit_heartbeat(
            "load_complete",
            f"AnimateDiff loaded. VRAM: {vram_after:.2f}GB",
            vram_after_gb=round(vram_after, 2)
        )

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: int = -1,
        width: int = 576,
        height: int = 1024,
    ) -> List[np.ndarray]:
        """
        Generate video frames with AnimateDiff-Lightning.

        Args:
            prompt: Text prompt for generation (SD 1.5, <75 tokens)
            negative_prompt: Negative prompt
            num_frames: Number of frames to generate (default: 16)
            guidance_scale: CFG scale (default: 1.0 for Lightning)
            seed: Random seed for reproducibility (-1 = random)
            width: Frame width (default: 576)
            height: Frame height (default: 1024)

        Returns:
            List of numpy BGR frames (H, W, 3)
        """
        # Ensure model is loaded
        if not self.is_loaded():
            self.load()

        # Apply defaults
        num_frames = num_frames or self.default_num_frames
        guidance_scale = guidance_scale if guidance_scale is not None else self.default_guidance_scale

        # Set up generator for seed locking
        generator = None
        if seed >= 0:
            generator = torch.Generator(device="cuda").manual_seed(seed)

        self._emit_heartbeat(
            "generate",
            f"Generating {num_frames} frames...",
            num_frames=num_frames,
            guidance_scale=guidance_scale,
            seed=seed,
            width=width,
            height=height
        )

        # Generate with callback
        callback = HeartbeatCallback(self.heartbeat_callback)
        callback.total_steps = self.default_steps

        output = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=self.default_steps,
            guidance_scale=guidance_scale,
            num_frames=num_frames,
            width=width,
            height=height,
            generator=generator,
            callback_on_step_end=callback,
        )

        # Convert PIL frames to numpy BGR (match existing convention)
        frames = []
        for frame_pil in output.frames[0]:
            frame_np = np.array(frame_pil)
            frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
            frames.append(frame_bgr)

        self._emit_heartbeat(
            "generate_complete",
            f"Generated {len(frames)} frames",
            num_frames=len(frames)
        )

        return frames

    def generate_batch(
        self,
        prompts: List[str],
        negative_prompts: Optional[List[str]] = None,
        num_frames: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: int = -1,
        width: int = 576,
        height: int = 1024,
    ) -> List[List[np.ndarray]]:
        """
        Generate multiple videos in sequence (seed-locked for consistency).

        Args:
            prompts: List of text prompts
            negative_prompts: List of negative prompts (or None for defaults)
            num_frames: Number of frames per video
            guidance_scale: CFG scale
            seed: Base seed (incremented per video for variation)
            width: Frame width
            height: Frame height

        Returns:
            List of frame lists (one per prompt)
        """
        if negative_prompts is None:
            negative_prompts = [""] * len(prompts)

        results = []
        for i, (prompt, neg_prompt) in enumerate(zip(prompts, negative_prompts)):
            # Lock seed or increment for variation
            video_seed = seed if seed >= 0 else -1
            if seed >= 0:
                video_seed = seed + i  # Increment seed per video

            frames = self.generate(
                prompt=prompt,
                negative_prompt=neg_prompt,
                num_frames=num_frames,
                guidance_scale=guidance_scale,
                seed=video_seed,
                width=width,
                height=height,
            )
            results.append(frames)

        return results
