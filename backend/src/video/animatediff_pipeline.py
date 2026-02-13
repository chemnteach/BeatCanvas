"""
AnimateDiff Video Generation Pipeline for BeatCanvas Production.

Replaces static image generation with AnimateDiff video clips.
Integrates with existing storyboard → RAFT → assembly workflow.
"""

import os
import cv2
import time
import torch
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

from src.cinematography import AnimateDiffGenerator
from src.cinematography.raft_interpolator import RAFTInterpolator
from src.cinematography.style_logic import detect_style, get_style_definition


# Output directory for generated video clips
VIDEO_CLIPS_DIR = Path("data/generated_videos")
VIDEO_CLIPS_DIR.mkdir(parents=True, exist_ok=True)


class AnimateDiffPipeline:
    """
    Production pipeline for AnimateDiff video generation.

    Generates video clips for storyboard scenes using AnimateDiff-Lightning,
    interpolates with RAFT, and saves as video files for assembly.
    """

    def __init__(
        self,
        target_fps: int = 8,         # Lower FPS, no interpolation artifacts
        interpolate: bool = False,    # Disable RAFT to fix blur issue
        heartbeat_callback: Optional[callable] = None
    ):
        """
        Initialize the AnimateDiff pipeline.

        Args:
            target_fps: Target FPS after RAFT interpolation (default: 60)
            interpolate: Whether to use RAFT interpolation (default: True)
            heartbeat_callback: Optional callback for progress updates
        """
        self.target_fps = target_fps
        self.interpolate = interpolate
        self.heartbeat_callback = heartbeat_callback

        # Will be lazy-loaded
        self.animatediff = None
        self.raft = None

    def _emit_progress(self, message: str, **kwargs):
        """Emit progress update."""
        if self.heartbeat_callback:
            self.heartbeat_callback({
                "phase": "animatediff",
                "message": message,
                **kwargs
            })
        else:
            print(f"[AnimateDiff] {message}")

    def _load_animatediff(self):
        """Lazy-load AnimateDiff generator."""
        if self.animatediff is None:
            self._emit_progress("Loading AnimateDiff-Lightning...")
            self.animatediff = AnimateDiffGenerator(
                heartbeat_callback=self.heartbeat_callback
            )
            self.animatediff.load()

    def _load_raft(self):
        """Lazy-load RAFT interpolator."""
        if self.raft is None and self.interpolate:
            self._emit_progress("Loading RAFT interpolator...")
            self.raft = RAFTInterpolator(model_size='large')

    def _save_video_clip(
        self,
        frames: List[np.ndarray],
        output_path: Path,
        fps: int = 60
    ) -> str:
        """
        Save frames as video file.

        Args:
            frames: List of BGR numpy frames
            output_path: Output video path
            fps: Frames per second

        Returns:
            Path to saved video file
        """
        if not frames:
            raise ValueError("No frames to save")

        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        for frame in frames:
            out.write(frame)

        out.release()
        return str(output_path)

    def _interpolate_frames(
        self,
        frames: List[np.ndarray],
        target_duration: float
    ) -> List[np.ndarray]:
        """
        Interpolate frames using RAFT.

        Args:
            frames: Source frames (16 from AnimateDiff)
            target_duration: Target video duration in seconds

        Returns:
            Interpolated frames list
        """
        if not self.interpolate or not self.raft:
            return frames

        # Calculate frames needed for target duration
        target_frames = int(target_duration * self.target_fps)
        n_source = len(frames)
        n_gaps = n_source - 1

        # Calculate intermediate frames per gap
        num_intermediate = max(1, (target_frames - n_source) // n_gaps)

        self._emit_progress(
            f"RAFT: {n_source} → {target_frames} frames ({target_duration:.2f}s @ {self.target_fps}fps)"
        )

        # Interpolate
        output_frames = [frames[0]]
        for i in range(n_gaps):
            frame1 = frames[i]
            frame2 = frames[i + 1]

            intermediate = self.raft.interpolate_frames(
                frame1, frame2,
                num_intermediate=num_intermediate,
                occlusion_aware=True,
                edge_damping=True,
            )

            output_frames.extend(intermediate)
            output_frames.append(frame2)

        return output_frames

    def generate_scene(
        self,
        scene: Dict[str, Any],
        scene_index: int,
        total_scenes: int,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate video clip for a single scene.

        Args:
            scene: Storyboard scene dict with prompt, duration, etc.
            scene_index: Index of this scene
            total_scenes: Total number of scenes
            style: Optional style override (e.g., "STYLE_BEACH_CASUAL")

        Returns:
            Dict with video_path, duration, fps, frame_count
        """
        start_time = time.time()

        # Extract scene info
        prompt = scene.get('image_prompt') or scene.get('description', '')
        timestamp_start = scene.get('timestamp_start', 0)
        timestamp_end = scene.get('timestamp_end', timestamp_start + 4)
        duration = timestamp_end - timestamp_start

        self._emit_progress(
            f"Scene {scene_index + 1}/{total_scenes}: Generating video...",
            scene_index=scene_index,
            total_scenes=total_scenes
        )

        # Auto-detect style if not provided
        if not style:
            style = detect_style(prompt) or "STYLE_BEACH_CASUAL"

        # Get style config
        style_def = get_style_definition(style)
        if style_def:
            # AnimateDiff-Lightning requires LOW guidance scale (1.0-2.0)
            # Style definitions use 6.5-8.0 which causes hallucinations!
            cfg = 1.0  # Force AnimateDiff-Lightning optimal value
            num_frames = 16  # AnimateDiff default
        else:
            cfg = 1.0
            num_frames = 16

        # Load AnimateDiff if not loaded
        print(f"[DEBUG] Scene {scene_index}: Loading AnimateDiff generator...")
        self._load_animatediff()
        print(f"[DEBUG] Scene {scene_index}: AnimateDiff loaded, generating {num_frames} frames...")

        # Generate with AnimateDiff
        frames = self.animatediff.generate(
            prompt=prompt,
            negative_prompt="silhouette, backlit, dark, shadowy, sunset backlighting, contre-jour, rim lighting, underexposed, low light, blurry, low quality, deformed, fused limbs",
            num_frames=num_frames,
            guidance_scale=cfg,
            seed=42 + scene_index,  # Seed variation per scene
            width=576,
            height=1024,
        )
        print(f"[DEBUG] Scene {scene_index}: Got {len(frames)} frames from AnimateDiff")

        gen_time = time.time() - start_time
        self._emit_progress(
            f"Generated {len(frames)} frames in {gen_time:.1f}s"
        )

        # Interpolate with RAFT
        if self.interpolate:
            self._load_raft()
            frames = self._interpolate_frames(frames, duration)

        # Save as video clip
        output_filename = f"scene_{scene_index:04d}_{int(timestamp_start*1000)}.mp4"
        output_path = VIDEO_CLIPS_DIR / output_filename

        video_path = self._save_video_clip(frames, output_path, self.target_fps)

        total_time = time.time() - start_time

        return {
            "video_path": video_path,
            "duration": len(frames) / self.target_fps,
            "fps": self.target_fps,
            "frame_count": len(frames),
            "generation_time": total_time,
            "scene_index": scene_index,
        }

    def generate_all_scenes(
        self,
        storyboard: List[Dict[str, Any]],
        style: Optional[str] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Generate video clips for all scenes in storyboard.

        Args:
            storyboard: List of storyboard scene dicts
            style: Optional style to use for all scenes

        Returns:
            Dict mapping scene index to video info dict
        """
        print(f"[DEBUG AnimateDiffPipeline] generate_all_scenes called with {len(storyboard)} scenes")
        results = {}
        total_scenes = len(storyboard)

        self._emit_progress(f"Starting generation for {total_scenes} scenes...")

        for i, scene in enumerate(storyboard):
            print(f"[DEBUG AnimateDiffPipeline] Processing scene {i+1}/{total_scenes}")
            try:
                result = self.generate_scene(
                    scene,
                    scene_index=i,
                    total_scenes=total_scenes,
                    style=style
                )
                print(f"[DEBUG AnimateDiffPipeline] Scene {i} SUCCESS: {result.get('video_path', 'NO PATH')}")
                results[i] = result
            except Exception as e:
                print(f"[DEBUG AnimateDiffPipeline] Scene {i} FAILED: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self._emit_progress(f"Scene {i} failed: {e}")
                results[i] = {
                    "error": str(e),
                    "scene_index": i,
                }

        print(f"[DEBUG AnimateDiffPipeline] generate_all_scenes complete: {len(results)} results")
        return results

    def cleanup(self):
        """Clean up models and reclaim VRAM."""
        if self.animatediff:
            self.animatediff.kill()
            self.animatediff = None

        if self.raft:
            del self.raft
            self.raft = None

        torch.cuda.empty_cache()
        self._emit_progress("Cleanup complete")
