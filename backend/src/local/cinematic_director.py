"""
Cinematic Director - Full pipeline orchestration with VRAM lifecycle management.

STAGES (strict sequence with VRAM handover):
1. ImageGen.load → ImageGen.run → ImageGen.kill (VRAM → baseline)
2. VideoGen.load → VideoGen.run → VideoGen.kill (VRAM → baseline)
3. MotionSmoother.run → cleanup (VRAM → baseline)
4. Windows Handoff

VRAM Budget: 12GB (Acer Predator)
Rule: Only ONE model loaded at a time. Kill before next stage.
"""

import shutil
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any, TYPE_CHECKING

from src.local.vram_manager import VRAMManager
from src.local.image_generator import LocalImageGenerator, create_image_generator
from src.local.video_generator import LocalVideoGenerator, create_video_generator
from src.local.motion_smoother import MotionSmoother, create_motion_smoother
from src.utils.config import SETTINGS
from src.utils.env_loader import get_path

# Get output directory
_default_output = Path(__file__).parent.parent / "output"
OUTPUT_DIR = get_path("svd_output", default=_default_output)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class CinematicDirector:
    """
    Orchestrates the full cinematic video pipeline with strict VRAM lifecycle.

    Stage Sequence (VRAM Budget: 12GB):
    1. ImageGen (SDXL ~6GB) → kill → baseline
    2. VideoGen (SVD ~7GB) → kill → baseline
    3. MotionSmoother (RIFE via Vulkan) → cleanup → baseline
    4. Windows Handoff

    Each stage MUST complete and release VRAM before the next begins.
    """

    # VRAM threshold for baseline verification
    VRAM_BASELINE_THRESHOLD_GB = 1.5

    # Pipeline stages for tracking
    STAGES = [
        "image_generation",
        "video_generation",
        "motion_smoothing",
        "handoff"
    ]

    def __init__(
        self,
        vram_manager: Optional[VRAMManager] = None,
        heartbeat_callback: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize the Cinematic Director.

        Args:
            vram_manager: Optional shared VRAMManager. If None, creates one.
            heartbeat_callback: Optional callback for progress updates.
        """
        self.heartbeat_callback = heartbeat_callback

        # Shared VRAM manager for all stages
        self.vram_manager = vram_manager or VRAMManager()

        # Load Windows handoff path from .env
        self.windows_downloads = get_path("windows_downloads", default=None)

        # Stage components (created lazily with shared vram_manager)
        self._image_gen = None
        self._video_gen = None
        self._smoother = None

    @property
    def image_generator(self) -> LocalImageGenerator:
        """Get or create image generator with shared VRAM manager."""
        if self._image_gen is None:
            self._image_gen = create_image_generator(self.vram_manager)
        return self._image_gen

    @property
    def video_generator(self) -> LocalVideoGenerator:
        """Get or create video generator with shared VRAM manager."""
        if self._video_gen is None:
            self._video_gen = create_video_generator(
                self.vram_manager,
                heartbeat_callback=self.heartbeat_callback
            )
        return self._video_gen

    @property
    def motion_smoother(self) -> MotionSmoother:
        """Get or create motion smoother with shared VRAM manager."""
        if self._smoother is None:
            self._smoother = create_motion_smoother(
                self.vram_manager,
                heartbeat_callback=self.heartbeat_callback
            )
        return self._smoother

    def _emit_heartbeat(self, phase: str, message: str, **kwargs):
        """Emit JSON heartbeat for monitoring."""
        data = {
            "type": "heartbeat",
            "phase": phase,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "vram_usage_gb": round(self.vram_manager.get_vram_usage(), 2),
            **kwargs
        }
        if self.heartbeat_callback:
            self.heartbeat_callback(data)
        else:
            print(json.dumps(data), flush=True)

    def _verify_vram_baseline(self, stage_name: str) -> bool:
        """
        Verify VRAM is at baseline (<1.5GB) before proceeding.

        Args:
            stage_name: Name of the stage for logging

        Returns:
            True if at baseline, False otherwise
        """
        vram = self.vram_manager.get_vram_usage()
        at_baseline = vram < self.VRAM_BASELINE_THRESHOLD_GB

        if at_baseline:
            self._emit_heartbeat(
                "vram_check",
                f"✓ VRAM baseline verified for {stage_name}",
                vram_gb=round(vram, 2),
                threshold_gb=self.VRAM_BASELINE_THRESHOLD_GB,
                passed=True
            )
        else:
            self._emit_heartbeat(
                "vram_warning",
                f"⚠ VRAM above baseline before {stage_name}: {vram:.2f}GB",
                vram_gb=round(vram, 2),
                threshold_gb=self.VRAM_BASELINE_THRESHOLD_GB,
                passed=False
            )

        return at_baseline

    def _force_vram_baseline(self, stage_name: str) -> float:
        """
        Force VRAM to baseline state (kill everything).

        Args:
            stage_name: Name of the next stage

        Returns:
            VRAM usage after forcing baseline
        """
        self._emit_heartbeat(
            "vram_force",
            f"Forcing VRAM baseline before {stage_name}..."
        )

        self.vram_manager.kill()
        time.sleep(0.5)  # Allow CUDA to fully release

        vram_after = self.vram_manager.get_vram_usage()
        self._emit_heartbeat(
            "vram_force_complete",
            f"VRAM after force: {vram_after:.2f}GB",
            vram_gb=round(vram_after, 2)
        )

        return vram_after

    def handoff_to_windows(
        self,
        frame_paths: List[Path],
        raw_video: Path,
        smoothed_video: Optional[Path],
        timestamp: str
    ) -> Optional[Path]:
        """
        Complete handoff: create timestamped folder with frames + videos.

        Args:
            frame_paths: List of frame PNG paths
            raw_video: Path to raw 8fps video
            smoothed_video: Path to smoothed 60fps video (or None)
            timestamp: Timestamp for folder naming

        Returns:
            Handoff folder path or None if WINDOWS_DOWNLOADS not configured
        """
        if not self.windows_downloads:
            self._emit_heartbeat(
                "handoff",
                "WINDOWS_DOWNLOADS not configured - skipping handoff",
                skipped=True
            )
            return None

        if not self.windows_downloads.exists():
            self._emit_heartbeat(
                "warning",
                f"Windows path not accessible: {self.windows_downloads}",
                path=str(self.windows_downloads)
            )
            return None

        # Create timestamped folder
        handoff_folder = self.windows_downloads / f"synterra_{timestamp}"
        handoff_folder.mkdir(parents=True, exist_ok=True)

        self._emit_heartbeat(
            "handoff",
            f"Created handoff folder: {handoff_folder.name}",
            folder=str(handoff_folder)
        )

        # Copy all frames
        frames_subfolder = handoff_folder / "frames"
        frames_subfolder.mkdir(exist_ok=True)

        self._emit_heartbeat(
            "handoff",
            f"Copying {len(frame_paths)} frames...",
            frame_count=len(frame_paths)
        )

        for i, frame_path in enumerate(frame_paths):
            dest = frames_subfolder / frame_path.name
            shutil.copy2(frame_path, dest)

            if (i + 1) % 5 == 0 or i == len(frame_paths) - 1:
                self._emit_heartbeat(
                    "handoff",
                    f"Copied frame {i + 1}/{len(frame_paths)}",
                    frame=i + 1,
                    total=len(frame_paths),
                    progress=round((i + 1) / len(frame_paths) * 100, 1)
                )

        # Copy raw video
        if raw_video and raw_video.exists():
            raw_dest = handoff_folder / "raw_8fps.mp4"
            shutil.copy2(raw_video, raw_dest)
            self._emit_heartbeat("handoff", f"Copied: {raw_dest.name}")

        # Copy smoothed video
        if smoothed_video and smoothed_video.exists():
            smooth_dest = handoff_folder / "cinematic_60fps.mp4"
            shutil.copy2(smoothed_video, smooth_dest)
            self._emit_heartbeat("handoff", f"Copied: {smooth_dest.name}")

        self._emit_heartbeat(
            "handoff_complete",
            f"Handoff complete: {handoff_folder}",
            folder=str(handoff_folder),
            contents={
                "frames": len(frame_paths),
                "raw_video": "raw_8fps.mp4" if raw_video else None,
                "smoothed_video": "cinematic_60fps.mp4" if smoothed_video else None
            }
        )

        return handoff_folder

    def run(
        self,
        prompt: str,
        checkpoint: str = "pony",
        output_name: str = "synterra_cinematic_60fps.mp4",
        motion_bucket_id: Optional[int] = None,
        profile: str = "portrait_full_body",
        skip_smoothing: bool = False,
        skip_windows_copy: bool = False,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the full cinematic pipeline with VRAM lifecycle management.

        STAGE SEQUENCE:
        1. ImageGen.load → ImageGen.run → ImageGen.kill
        2. VideoGen.load → VideoGen.run → VideoGen.kill
        3. MotionSmoother.run → cleanup
        4. Windows Handoff

        Args:
            prompt: Text prompt for image generation
            checkpoint: Model checkpoint (pony, base, cinematic, etc.)
            output_name: Final output filename
            motion_bucket_id: SVD motion intensity (0-255)
            profile: Resolution profile (portrait_full_body, landscape)
            skip_smoothing: Skip RIFE interpolation
            skip_windows_copy: Skip Windows handoff
            style: Production style (STYLE_HARD_ACTION, STYLE_INTENSE_INTERACTION, etc.)

        Returns:
            dict with all output paths and VRAM checkpoints
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._emit_heartbeat(
            "pipeline_start",
            f"Cinematic Director starting pipeline",
            prompt=prompt[:50] + "..." if len(prompt) > 50 else prompt,
            checkpoint=checkpoint,
            timestamp=timestamp
        )

        result = {
            "prompt": prompt,
            "checkpoint": checkpoint,
            "timestamp": timestamp,
            "image_path": None,
            "raw_video": None,
            "frame_paths": None,
            "smoothed_video": None,
            "windows_path": None,
            "final_output": None,
            "vram_checkpoints": []
        }

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 1: IMAGE GENERATION
        # ═══════════════════════════════════════════════════════════════════
        self._emit_heartbeat("stage", "═══ STAGE 1: IMAGE GENERATION ═══", stage_num=1)

        # Verify baseline
        self._force_vram_baseline("ImageGen")

        # Generate image (with style injection if specified)
        image_path = OUTPUT_DIR / f"frame_source_{timestamp}.png"
        gen_result = self.image_generator.generate_and_save(
            prompt=prompt,
            output_path=image_path,
            checkpoint=checkpoint,
            profile=profile,
            style=style
        )

        result["image_path"] = str(gen_result["path"])
        image_path = gen_result["path"]

        self._emit_heartbeat(
            "stage_complete",
            f"Stage 1 complete: {image_path.name}",
            stage_num=1,
            image_path=str(image_path)
        )

        # KILL ImageGen - VRAM handover
        self._emit_heartbeat("vram_handover", "Killing ImageGen for VRAM handover...")
        checkpoint_1 = self.image_generator.kill()
        time.sleep(0.5)
        result["vram_checkpoints"].append({
            "stage": "after_image_gen",
            "vram_gb": round(checkpoint_1, 2)
        })

        self._emit_heartbeat(
            "vram_checkpoint",
            f"✓ Checkpoint 1: VRAM at {checkpoint_1:.2f}GB",
            checkpoint_num=1,
            vram_gb=round(checkpoint_1, 2)
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 2: VIDEO GENERATION (SVD)
        # ═══════════════════════════════════════════════════════════════════
        self._emit_heartbeat("stage", "═══ STAGE 2: VIDEO GENERATION ═══", stage_num=2)

        # Verify baseline
        self._verify_vram_baseline("VideoGen")

        raw_video_name = f"raw_8fps_{timestamp}.mp4"
        gen_result = self.video_generator.generate_video(
            image_path,
            motion_bucket_id=motion_bucket_id,
            output_name=raw_video_name,
            profile=profile
        )

        result["raw_video"] = str(gen_result["video_path"])
        result["frame_paths"] = [str(p) for p in gen_result["frame_paths"]]

        self._emit_heartbeat(
            "stage_complete",
            f"Stage 2 complete: {gen_result['video_path'].name}",
            stage_num=2,
            raw_video=str(gen_result["video_path"]),
            frame_count=len(gen_result["frame_paths"])
        )

        # KILL VideoGen - VRAM handover
        self._emit_heartbeat("vram_handover", "Killing VideoGen for VRAM handover...")
        checkpoint_2 = self.video_generator.kill()
        time.sleep(0.5)
        result["vram_checkpoints"].append({
            "stage": "after_video_gen",
            "vram_gb": round(checkpoint_2, 2)
        })

        self._emit_heartbeat(
            "vram_checkpoint",
            f"✓ Checkpoint 2: VRAM at {checkpoint_2:.2f}GB",
            checkpoint_num=2,
            vram_gb=round(checkpoint_2, 2)
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 3: MOTION SMOOTHING (RIFE)
        # ═══════════════════════════════════════════════════════════════════
        if not skip_smoothing:
            self._emit_heartbeat("stage", "═══ STAGE 3: MOTION SMOOTHING ═══", stage_num=3)

            # RIFE uses Vulkan, but verify CUDA is clean
            self._verify_vram_baseline("MotionSmoother")

            smoothed_path = self.motion_smoother.smooth_video(
                gen_result["video_path"],
                output_name=output_name
            )

            result["smoothed_video"] = str(smoothed_path)
            result["final_output"] = str(smoothed_path)

            self._emit_heartbeat(
                "stage_complete",
                f"Stage 3 complete: {smoothed_path.name}",
                stage_num=3,
                smoothed_video=str(smoothed_path)
            )

            # Cleanup MotionSmoother
            self.motion_smoother.cleanup()
        else:
            result["final_output"] = result["raw_video"]
            self._emit_heartbeat("stage", "Stage 3 skipped (--skip-smoothing)", stage_num=3)

        # Final VRAM checkpoint
        checkpoint_3 = self.vram_manager.get_vram_usage()
        result["vram_checkpoints"].append({
            "stage": "after_smoothing",
            "vram_gb": round(checkpoint_3, 2)
        })

        self._emit_heartbeat(
            "vram_checkpoint",
            f"✓ Checkpoint 3: VRAM at {checkpoint_3:.2f}GB",
            checkpoint_num=3,
            vram_gb=round(checkpoint_3, 2)
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 4: WINDOWS HANDOFF
        # ═══════════════════════════════════════════════════════════════════
        if not skip_windows_copy:
            self._emit_heartbeat("stage", "═══ STAGE 4: WINDOWS HANDOFF ═══", stage_num=4)

            handoff_folder = self.handoff_to_windows(
                frame_paths=gen_result["frame_paths"],
                raw_video=gen_result["video_path"],
                smoothed_video=Path(result["smoothed_video"]) if result["smoothed_video"] else None,
                timestamp=timestamp
            )

            if handoff_folder:
                result["windows_path"] = str(handoff_folder)

            self._emit_heartbeat(
                "stage_complete",
                f"Stage 4 complete: {handoff_folder or 'skipped'}",
                stage_num=4
            )
        else:
            self._emit_heartbeat("stage", "Stage 4 skipped (--skip-windows-copy)", stage_num=4)

        # ═══════════════════════════════════════════════════════════════════
        # PIPELINE COMPLETE
        # ═══════════════════════════════════════════════════════════════════
        self._emit_heartbeat(
            "pipeline_complete",
            "Cinematic Director pipeline complete",
            **{k: v for k, v in result.items() if k != "vram_checkpoints"},
            vram_checkpoints=result["vram_checkpoints"]
        )

        return result

    def run_from_image(
        self,
        image_path: str | Path,
        output_name: str = "synterra_cinematic_60fps.mp4",
        motion_bucket_id: Optional[int] = None,
        skip_smoothing: bool = False,
        skip_windows_copy: bool = False
    ) -> Dict[str, Any]:
        """
        Run pipeline from existing image (skip ImageGen stage).

        Args:
            image_path: Path to input image
            output_name: Final output filename
            motion_bucket_id: SVD motion intensity
            skip_smoothing: Skip RIFE interpolation
            skip_windows_copy: Skip Windows handoff

        Returns:
            dict with all output paths
        """
        image_path = Path(os.path.abspath(str(image_path)))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._emit_heartbeat(
            "pipeline_start",
            f"Cinematic Director starting from image",
            input_image=str(image_path),
            timestamp=timestamp
        )

        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        result = {
            "input_image": str(image_path),
            "timestamp": timestamp,
            "raw_video": None,
            "frame_paths": None,
            "smoothed_video": None,
            "windows_path": None,
            "final_output": None,
            "vram_checkpoints": []
        }

        # Force clean VRAM state
        self._force_vram_baseline("VideoGen")

        # Stage 2: Video Generation
        self._emit_heartbeat("stage", "═══ STAGE 2: VIDEO GENERATION ═══", stage_num=2)

        raw_video_name = f"raw_8fps_{timestamp}.mp4"
        gen_result = self.video_generator.generate_video(
            image_path,
            motion_bucket_id=motion_bucket_id,
            output_name=raw_video_name
        )

        result["raw_video"] = str(gen_result["video_path"])
        result["frame_paths"] = [str(p) for p in gen_result["frame_paths"]]

        # Kill VideoGen
        checkpoint_2 = self.video_generator.kill()
        time.sleep(0.5)
        result["vram_checkpoints"].append({
            "stage": "after_video_gen",
            "vram_gb": round(checkpoint_2, 2)
        })

        # Stage 3: Motion Smoothing
        if not skip_smoothing:
            self._emit_heartbeat("stage", "═══ STAGE 3: MOTION SMOOTHING ═══", stage_num=3)

            smoothed_path = self.motion_smoother.smooth_video(
                gen_result["video_path"],
                output_name=output_name
            )

            result["smoothed_video"] = str(smoothed_path)
            result["final_output"] = str(smoothed_path)
            self.motion_smoother.cleanup()
        else:
            result["final_output"] = result["raw_video"]

        # Stage 4: Handoff
        if not skip_windows_copy:
            handoff_folder = self.handoff_to_windows(
                frame_paths=gen_result["frame_paths"],
                raw_video=gen_result["video_path"],
                smoothed_video=Path(result["smoothed_video"]) if result["smoothed_video"] else None,
                timestamp=timestamp
            )
            if handoff_folder:
                result["windows_path"] = str(handoff_folder)

        self._emit_heartbeat("pipeline_complete", "Pipeline complete", **result)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI EXECUTION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entrypoint for cinematic director."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cinematic Director - Full pipeline with VRAM lifecycle"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Full pipeline from prompt
    gen_parser = subparsers.add_parser("generate", help="Generate from text prompt")
    gen_parser.add_argument("prompt", type=str, help="Text prompt for image")
    gen_parser.add_argument("-c", "--checkpoint", type=str, default="pony",
                            help="Model checkpoint (pony, base, cinematic)")
    gen_parser.add_argument("-o", "--output", type=str, default="synterra_cinematic_60fps.mp4",
                            help="Output filename")
    gen_parser.add_argument("-m", "--motion", type=int, default=127,
                            help="Motion bucket ID (0-255)")
    gen_parser.add_argument("-p", "--profile", type=str, default="portrait_full_body",
                            help="Resolution profile")
    gen_parser.add_argument("--skip-smoothing", action="store_true")
    gen_parser.add_argument("--skip-windows-copy", action="store_true")

    # Pipeline from existing image
    img_parser = subparsers.add_parser("from-image", help="Generate from existing image")
    img_parser.add_argument("image", type=Path, help="Input image path")
    img_parser.add_argument("-o", "--output", type=str, default="synterra_cinematic_60fps.mp4")
    img_parser.add_argument("-m", "--motion", type=int, default=127)
    img_parser.add_argument("--skip-smoothing", action="store_true")
    img_parser.add_argument("--skip-windows-copy", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    director = CinematicDirector()

    if args.command == "generate":
        result = director.run(
            prompt=args.prompt,
            checkpoint=args.checkpoint,
            output_name=args.output,
            motion_bucket_id=args.motion,
            profile=args.profile,
            skip_smoothing=args.skip_smoothing,
            skip_windows_copy=args.skip_windows_copy
        )
    elif args.command == "from-image":
        result = director.run_from_image(
            image_path=args.image,
            output_name=args.output,
            motion_bucket_id=args.motion,
            skip_smoothing=args.skip_smoothing,
            skip_windows_copy=args.skip_windows_copy
        )

    print("\n" + "=" * 60)
    print("CINEMATIC DIRECTOR - PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Image:         {result.get('image_path', 'N/A')}")
    print(f"Raw video:     {result['raw_video']}")
    print(f"Smoothed:      {result['smoothed_video'] or 'skipped'}")
    print(f"Windows path:  {result['windows_path'] or 'skipped'}")
    print(f"Final output:  {result['final_output']}")
    print("\nVRAM Checkpoints:")
    for cp in result.get("vram_checkpoints", []):
        print(f"  {cp['stage']}: {cp['vram_gb']}GB")
    print("=" * 60)


if __name__ == "__main__":
    main()
