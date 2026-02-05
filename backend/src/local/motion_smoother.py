"""
RIFE Motion Smoother - Frame interpolation for cinematic 60fps output.

Uses RIFE (Real-Time Intermediate Flow Estimation) via rife-ncnn-vulkan
for GPU-accelerated frame interpolation.

VRAM Note: RIFE uses Vulkan (separate from CUDA), but still benefits from
clean VRAM state. Integrates with VRAMManager for lifecycle coordination.
"""

import subprocess
import shutil
import json
import gc
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List, TYPE_CHECKING

from src.utils.config import SETTINGS
from src.utils.env_loader import get_path

if TYPE_CHECKING:
    from src.local.vram_manager import VRAMManager

# Load motion smoothing config from settings.yaml
SMOOTH_CONFIG = SETTINGS.get("motion_smoothing", {})

# Output directory (same as SVD)
_default_output = Path(__file__).parent.parent / "output"
OUTPUT_DIR = get_path("svd_output", default=_default_output)


class MotionSmoother:
    """
    RIFE-based frame interpolation for smooth 60fps video output.

    Uses rife-ncnn-vulkan CLI for Vulkan GPU acceleration.
    Integrates with VRAMManager for pipeline lifecycle coordination.
    """

    def __init__(
        self,
        vram_manager: Optional["VRAMManager"] = None,
        heartbeat_callback: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize the motion smoother.

        Args:
            vram_manager: Optional shared VRAMManager for lifecycle coordination.
            heartbeat_callback: Optional callback for progress updates.
        """
        self.vram_manager = vram_manager
        self.heartbeat_callback = heartbeat_callback

        # Load config from settings.yaml
        self.engine = SMOOTH_CONFIG.get("engine", "rife")
        self.interpolation_factor = SMOOTH_CONFIG.get("interpolation_factor", 4)
        self.fps_target = SMOOTH_CONFIG.get("fps_target", 60)
        self.vulkan_device = SMOOTH_CONFIG.get("vulkan_device", 0)
        self.loop_blend_frames = SMOOTH_CONFIG.get("loop_blend_frames", 3)
        self.output_format = SMOOTH_CONFIG.get("output_format", "mp4")
        self.quality_crf = SMOOTH_CONFIG.get("quality_crf", 17)

        # Track temp directories for cleanup
        self._temp_dirs = []

        # Verify rife-ncnn-vulkan is available
        self.rife_bin = self._find_rife_binary()

    def _emit_heartbeat(self, phase: str, message: str, **kwargs):
        """Emit JSON heartbeat for monitoring."""
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

    def _find_rife_binary(self) -> Optional[Path]:
        """Find rife-ncnn-vulkan binary - prioritizes explicit .env path."""
        # Priority 1: Explicit path from .env (RIFE_ENGINE_PATH)
        env_rife_path = get_path("rife_engine", default=None)
        if env_rife_path and env_rife_path.exists():
            self._emit_heartbeat(
                "init",
                f"RIFE engine loaded from .env: {env_rife_path}",
                path=str(env_rife_path)
            )
            return env_rife_path

        # Priority 2: Check PATH
        rife_path = shutil.which("rife-ncnn-vulkan")
        if rife_path:
            return Path(rife_path)

        # Priority 3: Common install locations (fallback)
        common_paths = [
            Path.home() / "rife-engine" / "rife-ncnn-vulkan",
            Path.home() / ".local" / "bin" / "rife-ncnn-vulkan",
            Path("/usr/local/bin/rife-ncnn-vulkan"),
            Path("/usr/bin/rife-ncnn-vulkan"),
            Path("/mnt/c/Tools/rife-ncnn-vulkan/rife-ncnn-vulkan.exe"),
        ]

        for p in common_paths:
            if p.exists():
                return p

        self._emit_heartbeat(
            "error",
            "RIFE engine not found. Set RIFE_ENGINE_PATH in .env",
            hint="Add to backend/.env: RIFE_ENGINE_PATH=/home/craig/rife-engine/rife-ncnn-vulkan"
        )
        return None

    def cleanup(self) -> None:
        """
        Clean up temporary directories and release resources.

        Call this after smoothing is complete to free disk space.
        """
        self._emit_heartbeat("cleanup", "Cleaning up motion smoother resources...")

        # Remove any tracked temp directories
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self._emit_heartbeat(
                        "cleanup",
                        f"Removed temp directory: {temp_dir.name}",
                        path=str(temp_dir)
                    )
                except Exception as e:
                    self._emit_heartbeat(
                        "warning",
                        f"Failed to remove temp directory: {e}",
                        path=str(temp_dir)
                    )

        self._temp_dirs.clear()

        # Force garbage collection
        gc.collect()

        self._emit_heartbeat("cleanup_complete", "Motion smoother cleanup complete")

    def kill(self) -> None:
        """
        Alias for cleanup() - matches VRAMManager pattern.

        RIFE runs via external process (rife-ncnn-vulkan), so "kill"
        just means cleanup temp files. The Vulkan GPU memory is managed
        by the external process.
        """
        self.cleanup()

    def extract_frames(self, video_path: Path, frames_dir: Path) -> List[Path]:
        """Extract frames from video using ffmpeg."""
        frames_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dirs.append(frames_dir)

        self._emit_heartbeat(
            "extract",
            f"Extracting frames from {video_path.name}",
            video_path=str(video_path),
            frames_dir=str(frames_dir)
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-qscale:v", "2",
            str(frames_dir / "frame_%08d.png")
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self._emit_heartbeat("error", f"ffmpeg extract failed: {result.stderr}")
            raise RuntimeError(f"Frame extraction failed: {result.stderr}")

        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        self._emit_heartbeat(
            "extract",
            f"Extracted {len(frame_paths)} frames",
            frame_count=len(frame_paths)
        )

        return frame_paths

    def interpolate_frames(
        self,
        input_dir: Path,
        output_dir: Path,
        factor: Optional[int] = None
    ) -> List[Path]:
        """
        Run RIFE interpolation on extracted frames.

        Args:
            input_dir: Directory containing input frames
            output_dir: Directory for interpolated frames
            factor: Interpolation factor (2, 4, 8, etc.) - default from config

        Returns:
            List of interpolated frame paths
        """
        if not self.rife_bin:
            raise RuntimeError("rife-ncnn-vulkan not installed")

        factor = factor or self.interpolation_factor
        output_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dirs.append(output_dir)

        # Verify input frames exist
        input_frames = sorted(input_dir.glob("frame_*.png"))
        if not input_frames:
            raise ValueError(f"No frames found in {input_dir}")

        self._emit_heartbeat(
            "interpolate_verify",
            f"Verified {len(input_frames)} input frames",
            input_dir=str(input_dir),
            frame_count=len(input_frames),
            first_frame=input_frames[0].name,
            last_frame=input_frames[-1].name
        )

        if len(input_frames) < 10:
            self._emit_heartbeat(
                "warning",
                f"Only {len(input_frames)} frames - interpolation may be suboptimal",
                frame_count=len(input_frames)
            )

        self._emit_heartbeat(
            "interpolate",
            f"Running RIFE {factor}x interpolation",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            factor=factor,
            vulkan_device=self.vulkan_device,
            input_frame_count=len(input_frames),
            expected_output_frames=len(input_frames) * factor
        )

        cmd = [
            str(self.rife_bin),
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-m", "rife-v4.6",
            "-g", str(self.vulkan_device),
            "-j", "1:2:2",
            "-f", "frame_%08d.png",
            "-n", str(factor)
        ]

        self._emit_heartbeat(
            "interpolate",
            f"Executing: {' '.join(cmd[:6])}...",
            command=cmd
        )

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self._emit_heartbeat(
                "error",
                f"RIFE interpolation failed: {result.stderr}",
                stderr=result.stderr
            )
            raise RuntimeError(f"RIFE failed: {result.stderr}")

        interpolated_frames = sorted(output_dir.glob("*.png"))
        self._emit_heartbeat(
            "interpolate",
            f"Generated {len(interpolated_frames)} interpolated frames",
            frame_count=len(interpolated_frames),
            expected=f"~{factor}x original"
        )

        return interpolated_frames

    def stitch_to_video(
        self,
        frames_dir: Path,
        output_path: Path,
        fps: Optional[int] = None
    ) -> Path:
        """
        Stitch interpolated frames into final MP4 using ffmpeg.

        Args:
            frames_dir: Directory containing frames to stitch
            output_path: Output video path
            fps: Target FPS (default from config)

        Returns:
            Path to output video
        """
        fps = fps or self.fps_target

        self._emit_heartbeat(
            "stitch",
            f"Stitching frames to {fps}fps video",
            output_path=str(output_path),
            fps=fps,
            crf=self.quality_crf
        )

        frames = sorted(frames_dir.glob("*.png"))
        if not frames:
            raise ValueError(f"No frames found in {frames_dir}")

        # Detect frame naming pattern
        first_frame = frames[0].name
        if "frame_" in first_frame:
            pattern = str(frames_dir / "frame_%08d.png")
        else:
            pattern = str(frames_dir / "%04d.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", pattern,
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", str(self.quality_crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self._emit_heartbeat("error", f"ffmpeg stitch failed: {result.stderr}")
            raise RuntimeError(f"Video stitching failed: {result.stderr}")

        self._emit_heartbeat(
            "stitch_complete",
            f"Created {output_path.name} at {fps}fps",
            output_path=str(output_path),
            fps=fps
        )

        return output_path

    def smooth_video(
        self,
        input_video: Path,
        output_name: str = "cinematic_60fps.mp4",
        cleanup_temp: bool = True
    ) -> Path:
        """
        Full pipeline: extract → interpolate → stitch.

        Args:
            input_video: Input video (e.g., 8fps SVD output)
            output_name: Output filename
            cleanup_temp: Remove temp directories after completion

        Returns:
            Path to smoothed 60fps video
        """
        self._emit_heartbeat(
            "smooth_start",
            f"Starting motion smoothing pipeline",
            input_video=str(input_video),
            interpolation_factor=self.interpolation_factor,
            fps_target=self.fps_target
        )

        # Create temp directories
        temp_base = OUTPUT_DIR / "temp_smooth"
        raw_frames_dir = temp_base / "raw_frames"
        interp_frames_dir = temp_base / "interp_frames"
        output_path = OUTPUT_DIR / output_name

        try:
            # Step 1: Extract frames from input video
            self.extract_frames(input_video, raw_frames_dir)

            # Step 2: RIFE interpolation
            self.interpolate_frames(raw_frames_dir, interp_frames_dir)

            # Step 3: Stitch to final video
            self.stitch_to_video(interp_frames_dir, output_path)

            self._emit_heartbeat(
                "smooth_complete",
                f"Motion smoothing complete: {output_path}",
                output_path=str(output_path),
                fps=self.fps_target
            )

            return output_path

        finally:
            # Cleanup temp directories
            if cleanup_temp and temp_base.exists():
                shutil.rmtree(temp_base, ignore_errors=True)
                self._emit_heartbeat("cleanup", "Removed temp directories")


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION - For shared VRAMManager coordination
# ═══════════════════════════════════════════════════════════════════════════════

def create_motion_smoother(
    shared_vram_manager: Optional["VRAMManager"] = None,
    heartbeat_callback: Optional[Callable[[dict], None]] = None
) -> MotionSmoother:
    """
    Factory function to create a motion smoother.

    Args:
        shared_vram_manager: Pass a shared VRAMManager for lifecycle coordination.
        heartbeat_callback: Optional callback for progress updates.

    Returns:
        MotionSmoother instance
    """
    return MotionSmoother(
        vram_manager=shared_vram_manager,
        heartbeat_callback=heartbeat_callback
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CLI EXECUTION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

def smooth_video_cli():
    """CLI entrypoint for standalone smoothing."""
    import argparse

    parser = argparse.ArgumentParser(description="RIFE Motion Smoother")
    parser.add_argument("input", type=Path, help="Input video path")
    parser.add_argument("-o", "--output", type=str, default="cinematic_60fps.mp4",
                        help="Output filename")
    parser.add_argument("-f", "--factor", type=int, help="Interpolation factor (2,4,8)")
    parser.add_argument("--fps", type=int, help="Target FPS")
    args = parser.parse_args()

    smoother = MotionSmoother()

    if args.factor:
        smoother.interpolation_factor = args.factor
    if args.fps:
        smoother.fps_target = args.fps

    try:
        output = smoother.smooth_video(args.input, args.output)
        print(f"\nOutput: {output}")
    finally:
        smoother.cleanup()


if __name__ == "__main__":
    smooth_video_cli()
