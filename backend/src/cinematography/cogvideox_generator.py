"""
CogVideoX Video Generator - High-quality text-to-video generation.

Better temporal consistency and natural motion than AnimateDiff-Lightning.
"""
import torch
import numpy as np
import cv2
from pathlib import Path
from typing import List, Optional
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video


class CogVideoXGenerator:
    """
    CogVideoX text-to-video generator wrapper.

    Produces 6-second videos at 8 FPS (48 frames) with better quality
    and temporal consistency than AnimateDiff-Lightning.
    """

    def __init__(self):
        self.pipe = None
        self.model_id = "THUDM/CogVideoX-5b"  # 5B parameter model - MUCH better quality

    def load(self):
        """Load CogVideoX model"""
        print(f"Loading CogVideoX from {self.model_id}...")

        self.pipe = CogVideoXPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16
        )

        # Enable memory optimizations
        self.pipe.enable_model_cpu_offload()
        self.pipe.vae.enable_slicing()

        print(f"✓ CogVideoX loaded")

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 48,  # 6 seconds at 8 FPS
        guidance_scale: float = 6.0,  # CogVideoX works well at 6.0
        num_inference_steps: int = 50,
        seed: int = -1,
        width: int = 720,
        height: int = 480,
    ) -> List[np.ndarray]:
        """
        Generate video frames from text prompt.

        Args:
            prompt: Text description
            negative_prompt: What to avoid
            num_frames: Number of frames (default 48 = 6s @ 8fps)
            guidance_scale: CFG scale (6.0 recommended for CogVideoX)
            num_inference_steps: Denoising steps (50 recommended)
            seed: Random seed
            width: Frame width (720 default)
            height: Frame height (480 default)

        Returns:
            List of BGR numpy arrays (OpenCV format)
        """
        if seed >= 0:
            generator = torch.Generator(device="cuda").manual_seed(seed)
        else:
            generator = None

        print(f"Generating {num_frames} frames with CogVideoX...")
        print(f"  Prompt: {prompt[:60]}...")

        # Generate video
        video = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator,
            height=height,
            width=width,
        ).frames[0]  # Get first (and only) video

        # Convert to BGR numpy arrays
        frames = []
        for frame in video:
            # Convert PIL Image to numpy array
            frame_np = np.array(frame)
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
            frames.append(frame_bgr)

        print(f"✓ Generated {len(frames)} frames")
        return frames

    def kill(self):
        """Clean up model and free VRAM"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            torch.cuda.empty_cache()
            print("✓ CogVideoX unloaded")
