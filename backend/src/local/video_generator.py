"""
Local Video Generator - SVD pipeline with VRAM lifecycle management.

Uses Stable Video Diffusion (SVD) for image-to-video generation.
Integrates with shared VRAMManager for coordinated VRAM usage.

VRAM Budget: 12GB
SVD Requirement: ~7-8GB
Rule: Image model must be killed before SVD loads.
"""

import torch
import gc
import imageio
import numpy as np
import json
import sys
import cv2
import os
from pathlib import Path
from datetime import datetime
from PIL import Image
from diffusers import StableVideoDiffusionPipeline
from typing import Callable, Optional, List, TYPE_CHECKING

from src.utils.config import SETTINGS
from src.utils.env_loader import get_path

if TYPE_CHECKING:
    from src.local.vram_manager import VRAMManager

# Load SVD config from settings.yaml
SVD_CONFIG = SETTINGS.get("svd", {})

# Load output directory from .env with fallback
_default_output = Path(__file__).parent.parent / "output"
OUTPUT_DIR = get_path("svd_output", default=_default_output)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def get_vram_safe_decode_chunk_size() -> int:
    """
    Dynamically determine decode_chunk_size based on available VRAM.

    SVD VAE decode is the OOM hotspot. Smaller chunks = less peak VRAM.
    """
    if not torch.cuda.is_available():
        return 1

    thresholds = SVD_CONFIG.get("vram_thresholds", {})
    high_threshold = thresholds.get("high", 10)
    medium_threshold = thresholds.get("medium", 6)
    low_threshold = thresholds.get("low", 3)

    try:
        free_vram_gb = torch.cuda.mem_get_info()[0] / (1024**3)

        if free_vram_gb >= high_threshold:
            return 8
        elif free_vram_gb >= medium_threshold:
            return 4
        elif free_vram_gb >= low_threshold:
            return 2
        else:
            return 1
    except Exception:
        return 2


class LocalVideoGenerator:
    """
    SVD Video Generator with VRAM lifecycle management.

    Integrates with shared VRAMManager for coordinated VRAM usage
    across image and video generation stages.
    """

    # SVD requires ~7-8GB VRAM
    VRAM_ESTIMATE_GB = 7.5

    def __init__(
        self,
        vram_manager: Optional["VRAMManager"] = None,
        heartbeat_callback: Optional[Callable[[dict], None]] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize the video generator.

        Args:
            vram_manager: Optional shared VRAMManager for VRAM coordination.
                          Pass this when coordinating with ImageGenerator.
            heartbeat_callback: Optional callback for progress updates.
            output_dir: Optional output directory override.
        """
        self.vram_manager = vram_manager
        self.pipe = None
        self.model_id = SVD_CONFIG.get("model_id", "stabilityai/stable-video-diffusion-img2vid-xt")
        self.heartbeat_callback = heartbeat_callback
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load resolution from config
        resolution = SVD_CONFIG.get("resolution", {})
        self.width = resolution.get("width", 1024)
        self.height = resolution.get("height", 576)

        # Load default generation params
        defaults = SVD_CONFIG.get("defaults", {})
        self.default_steps = defaults.get("num_inference_steps", 25)
        self.default_motion = defaults.get("motion_bucket_id", 127)
        self.default_noise = defaults.get("noise_aug_strength", 0.1)
        self.default_fps = defaults.get("fps", 8)

        # Load encoding settings
        encoding = SVD_CONFIG.get("encoding", {})
        self.crf = encoding.get("crf", 17)
        self.preset = encoding.get("preset", "slow")

        # Load SVD resolution profiles
        self.profiles = SVD_CONFIG.get("profiles", {})

    def get_resolution(self, profile: Optional[str] = None) -> tuple:
        """Get width, height for a profile or return defaults."""
        if profile and profile in self.profiles:
            p = self.profiles[profile]
            return p.get("width", self.width), p.get("height", self.height)
        return self.width, self.height

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
        Kill SVD model and reclaim VRAM.

        MUST be called before handing off to another GPU-intensive stage.

        Returns:
            VRAM usage after kill (should be <1GB)
        """
        self._emit_heartbeat("kill", "Killing SVD model...")

        # Delete pipeline
        if self.pipe is not None:
            del self.pipe
            self.pipe = None

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
            f"SVD killed. VRAM: {vram_after:.2f}GB",
            vram_after_gb=round(vram_after, 2)
        )

        return vram_after

    def is_loaded(self) -> bool:
        """Check if SVD model is currently loaded."""
        return self.pipe is not None

    def load_model(self):
        """Load SVD model if not already loaded."""
        if self.pipe is not None:
            return

        # Check VRAM availability
        vram_free = self.get_vram_free()
        if vram_free < self.VRAM_ESTIMATE_GB:
            self._emit_heartbeat(
                "warning",
                f"Low VRAM: {vram_free:.1f}GB free, SVD needs ~{self.VRAM_ESTIMATE_GB}GB",
                vram_free_gb=round(vram_free, 2),
                vram_required_gb=self.VRAM_ESTIMATE_GB
            )

        self._emit_heartbeat("init", f"Loading Video Engine ({self.model_id})...")

        self.pipe = StableVideoDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16"
        )
        self.pipe.to("cuda")
        self.pipe.enable_model_cpu_offload()

        # Enable memory-efficient attention if available
        try:
            self.pipe.enable_xformers_memory_efficient_attention()
            self._emit_heartbeat("init", "xformers memory optimization enabled")
        except Exception:
            pass

        vram_after = self.get_vram_usage()
        self._emit_heartbeat(
            "init",
            f"SVD loaded. VRAM: {vram_after:.2f}GB",
            vram_usage_gb=round(vram_after, 2)
        )

    def save_frames(self, frames, prefix: str = "frame") -> List[Path]:
        """
        Save all frames as individual PNGs: frame_00000000.png, etc.
        Returns list of saved frame paths.
        """
        saved_paths = []
        total_frames = len(frames)

        self._emit_heartbeat(
            "save_frames",
            f"Saving {total_frames} frames to {self.output_dir}",
            output_dir=str(self.output_dir),
            total_frames=total_frames
        )

        for i, frame in enumerate(frames):
            # Convert to numpy array if needed
            if hasattr(frame, 'numpy'):
                frame_array = frame.numpy()
            elif isinstance(frame, Image.Image):
                frame_array = np.array(frame)
            else:
                frame_array = np.array(frame)

            # Ensure uint8
            if frame_array.dtype != np.uint8:
                if frame_array.max() <= 1.0:
                    frame_array = (frame_array * 255).astype(np.uint8)
                else:
                    frame_array = frame_array.astype(np.uint8)

            # Save as PNG
            frame_path = self.output_dir / f"{prefix}_{i:08d}.png"
            Image.fromarray(frame_array).save(frame_path, "PNG")
            saved_paths.append(frame_path)

            self._emit_heartbeat(
                "save_frames",
                f"Saved {frame_path.name}",
                frame=i + 1,
                total_frames=total_frames,
                path=str(frame_path),
                progress=round((i + 1) / total_frames * 100, 1)
            )

        self._emit_heartbeat(
            "save_frames",
            f"All {total_frames} frames saved",
            saved_count=total_frames,
            output_dir=str(self.output_dir)
        )

        return saved_paths

    def stitch_frames_to_video(
        self,
        frame_paths: Optional[List[Path]] = None,
        output_name: str = "output.mp4",
        fps: Optional[int] = None
    ) -> Path:
        """
        Stitch frames into MP4 using ffmpeg.
        If frame_paths not provided, auto-discovers frame_*.png in output_dir.
        """
        import subprocess

        fps = fps or self.default_fps

        if frame_paths is None:
            frame_paths = sorted(self.output_dir.glob("frame_*.png"))

        if not frame_paths:
            raise ValueError(f"No frames found in {self.output_dir}")

        output_path = self.output_dir / output_name
        total_frames = len(frame_paths)

        self._emit_heartbeat(
            "stitch",
            f"Stitching {total_frames} frames to {output_path}",
            output_path=str(output_path),
            total_frames=total_frames,
            fps=fps
        )

        frame_pattern = str(self.output_dir / "frame_%08d.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-preset", self.preset,
            "-crf", str(self.crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ]

        self._emit_heartbeat(
            "stitch",
            f"Running ffmpeg: {' '.join(cmd[:8])}...",
            command=cmd
        )

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self._emit_heartbeat(
                "error",
                f"ffmpeg failed: {result.stderr}",
                stderr=result.stderr
            )
            raise RuntimeError(f"Video stitching failed: {result.stderr}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Output video is empty or missing: {output_path}")

        probe_cmd = ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "csv=p=0", str(output_path)]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = probe_result.stdout.strip() if probe_result.returncode == 0 else "unknown"

        self._emit_heartbeat(
            "stitch_complete",
            f"Video created: {output_path.name}",
            output_path=str(output_path),
            total_frames=total_frames,
            fps=fps,
            duration_sec=duration,
            file_size_mb=round(output_path.stat().st_size / (1024 * 1024), 2)
        )

        return output_path

    def generate_video(
        self,
        image_path,
        motion_bucket_id: Optional[int] = None,
        noise_aug_strength: Optional[float] = None,
        num_inference_steps: Optional[int] = None,
        decode_chunk_size: Optional[int] = None,
        save_frames: bool = True,
        stitch_video: bool = True,
        output_name: str = "output.mp4",
        fps: Optional[int] = None,
        profile: Optional[str] = None
    ) -> dict:
        """
        Generate video from image, save all frames, and stitch to MP4.

        Args:
            image_path: Input image path (will be normalized to absolute)
            profile: Resolution profile ("landscape" or "portrait_full_body")

        Returns:
            dict with keys: frames, frame_paths, video_path
        """
        image_path = Path(os.path.abspath(str(image_path)))

        if not image_path.exists():
            self._emit_heartbeat(
                "error",
                f"Input image not found: {image_path}",
                path=str(image_path)
            )
            raise FileNotFoundError(f"Input image not found: {image_path}")

        self._emit_heartbeat(
            "input_verify",
            f"Input verified: {image_path}",
            path=str(image_path),
            size_kb=round(image_path.stat().st_size / 1024, 1)
        )

        self.load_model()

        motion_bucket_id = motion_bucket_id if motion_bucket_id is not None else self.default_motion
        noise_aug_strength = noise_aug_strength if noise_aug_strength is not None else self.default_noise
        num_inference_steps = num_inference_steps if num_inference_steps is not None else self.default_steps

        width, height = self.get_resolution(profile)
        fps = fps if fps is not None else self.default_fps

        if decode_chunk_size is None:
            decode_chunk_size = get_vram_safe_decode_chunk_size()

        if torch.cuda.is_available():
            free_gb = torch.cuda.mem_get_info()[0] / (1024**3)
            total_gb = torch.cuda.mem_get_info()[1] / (1024**3)
            self._emit_heartbeat(
                "vram",
                f"VRAM: {free_gb:.1f}GB free / {total_gb:.1f}GB total",
                free_gb=round(free_gb, 2),
                total_gb=round(total_gb, 2),
                decode_chunk_size=decode_chunk_size
            )

        self._emit_heartbeat(
            "generate",
            f"Animating: {image_path}",
            image_path=str(image_path),
            motion_bucket_id=motion_bucket_id,
            decode_chunk_size=decode_chunk_size,
            num_inference_steps=num_inference_steps
        )

        # Use PIL directly - diffusers load_image fails on WSL paths
        image = Image.open(str(image_path)).convert("RGB")
        image = image.resize((width, height), resample=Image.LANCZOS)

        # Setup heartbeat callback for generation steps
        heartbeat = HeartbeatCallback(self.heartbeat_callback)
        heartbeat.total_steps = num_inference_steps

        try:
            frames = self.pipe(
                image=image,
                motion_bucket_id=motion_bucket_id,
                noise_aug_strength=noise_aug_strength,
                num_inference_steps=num_inference_steps,
                decode_chunk_size=decode_chunk_size,
                callback_on_step_end=heartbeat
            ).frames[0]
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self._emit_heartbeat(
                    "error",
                    "VRAM OOM during generation. Retrying with smaller chunk size...",
                    error=str(e)
                )
                # Retry with minimum chunk size
                torch.cuda.empty_cache()
                gc.collect()
                frames = self.pipe(
                    image=image,
                    motion_bucket_id=motion_bucket_id,
                    noise_aug_strength=noise_aug_strength,
                    num_inference_steps=num_inference_steps,
                    decode_chunk_size=1,  # Minimum
                    callback_on_step_end=heartbeat
                ).frames[0]
            else:
                raise

        self._emit_heartbeat(
            "generate_complete",
            f"Generated {len(frames)} frames",
            frame_count=len(frames)
        )

        result = {
            "frames": frames,
            "frame_paths": None,
            "video_path": None
        }

        if save_frames:
            result["frame_paths"] = self.save_frames(frames)

        if stitch_video and result["frame_paths"]:
            result["video_path"] = self.stitch_frames_to_video(
                result["frame_paths"],
                output_name=output_name,
                fps=fps
            )

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION - For shared VRAMManager coordination
# ═══════════════════════════════════════════════════════════════════════════════

def create_video_generator(
    shared_vram_manager: Optional["VRAMManager"] = None,
    heartbeat_callback: Optional[Callable[[dict], None]] = None
) -> LocalVideoGenerator:
    """
    Factory function to create a video generator.

    Args:
        shared_vram_manager: Pass a shared VRAMManager for coordinated VRAM usage.
        heartbeat_callback: Optional callback for progress updates.

    Returns:
        LocalVideoGenerator instance

    Example:
        # Shared VRAM coordination
        from src.local.vram_manager import VRAMManager
        from src.local.image_generator import create_image_generator
        from src.local.video_generator import create_video_generator

        vram_mgr = VRAMManager()

        # Image generation
        img_gen = create_image_generator(vram_mgr)
        image = img_gen.generate("action scene", checkpoint="pony")
        img_gen.kill()  # MUST kill before SVD

        # Video generation
        video_gen = create_video_generator(vram_mgr)
        video_gen.generate_video(image_path)
        video_gen.kill()  # MUST kill before RIFE or next stage
    """
    return LocalVideoGenerator(
        vram_manager=shared_vram_manager,
        heartbeat_callback=heartbeat_callback
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CLI EXECUTION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entrypoint for standalone video generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Local Video Generator (SVD)")
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument("-o", "--output", type=str, default="output.mp4",
                        help="Output video filename")
    parser.add_argument("-m", "--motion", type=int, default=None,
                        help="Motion bucket ID (0-255)")
    parser.add_argument("-s", "--steps", type=int, default=None,
                        help="Inference steps")
    parser.add_argument("--fps", type=int, default=None,
                        help="Output FPS")
    parser.add_argument("-p", "--profile", type=str, default=None,
                        help="Resolution profile")
    args = parser.parse_args()

    generator = LocalVideoGenerator()

    try:
        result = generator.generate_video(
            args.image,
            motion_bucket_id=args.motion,
            num_inference_steps=args.steps,
            output_name=args.output,
            fps=args.fps,
            profile=args.profile
        )

        print("\n" + "=" * 60)
        print("VIDEO GENERATION COMPLETE")
        print("=" * 60)
        print(f"Frames: {len(result['frame_paths'])}")
        print(f"Video: {result['video_path']}")
        print(f"VRAM: {generator.get_vram_usage():.2f}GB")
        print("=" * 60)

    finally:
        # Always cleanup
        generator.kill()


if __name__ == "__main__":
    main()
