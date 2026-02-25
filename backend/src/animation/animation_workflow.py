"""
Generic Animation Music Video Workflow

End-to-end pipeline for creating animated music videos from:
- Audio file
- Character LoRAs (optional)
- Animation style preferences
- Scene descriptions OR stock footage

Workflow:
1. Analyze audio → extract beats, structure, timing
2. Generate scenes with character LoRAs (if specified)
3. OR collect stock footage
4. Apply rotoscope/animation style
5. Sync to music and assemble final video

This is GENERIC - works for any music video project by loading project configs.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import yaml
import json
from datetime import datetime

import cv2
import numpy as np

from src.audio.analyzer import MusicAnalyzer
from src.assets.sdxl_lora_generator import SDXLLoRAGenerator
from src.animation.rotoscope_generator import RotoscopeGenerator, RotoscopeConfig, ANIMATION_STYLES
from src.cinematography.cogvideox_generator import CogVideoXGenerator
from src.video.assembler import VideoAssembler


@dataclass
class AnimationProjectConfig:
    """Configuration for an animation music video project"""
    project_name: str
    audio_path: str
    animation_style: str = "watercolor"  # watercolor, cel_shaded, ghibli, etc.
    quality_tier: str = "professional"  # basic (12 scenes), professional (24), cinematic (48)

    # Character LoRAs
    protagonist_lora: Optional[str] = None  # e.g., "rob-character"
    supporting_loras: Optional[List[str]] = None  # e.g., ["girlfriend-character"]

    # Scene LoRAs to use
    scene_loras: Optional[List[str]] = None  # e.g., ["beach-sunset", "bonfire-beach"]

    # Style LoRA
    style_lora: Optional[str] = None  # e.g., "70s-film-retro"

    # Generation method
    use_cogvideox: bool = False  # Workflow B: CogVideoX text-to-video (skips SDXL + rotoscope)
    use_stock_footage: bool = False  # If True, use stock footage instead of AI generation
    stock_footage_queries: Optional[List[str]] = None  # Pexels search queries

    # Output
    output_dir: str = "output/animation_projects"

    # Advanced options
    fps: int = 24
    width: int = 1024
    height: int = 1024
    rotoscope_strength: float = 0.8


@dataclass
class AnimationWorkflowResult:
    """Result of animation workflow"""
    success: bool
    output_video_path: Optional[str] = None
    project_dir: Optional[str] = None
    generation_time_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class AnimationWorkflow:
    """
    Generic animation music video workflow orchestrator.

    Handles entire pipeline from audio → final animated video.
    """

    def __init__(self):
        self.music_analyzer = MusicAnalyzer()
        self.sdxl_generator = None       # Lazy load — Workflow A
        self.cogvideox_generator = None  # Lazy load — Workflow B
        self.rotoscope_generator = None  # Lazy load — Workflow A
        self.video_assembler = VideoAssembler()

    async def run_workflow(
        self,
        config: AnimationProjectConfig
    ) -> AnimationWorkflowResult:
        """
        Run complete animation workflow from config.

        This is the main entry point - everything else is called from here.
        """
        start_time = datetime.now()
        project_dir = Path(config.output_dir) / config.project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[ANIMATION] ═══════════════════════════════════════")
        print(f"[ANIMATION] Project: {config.project_name}")
        print(f"[ANIMATION] Style: {config.animation_style}")
        print(f"[ANIMATION] ═══════════════════════════════════════\n")

        try:
            # Step 1: Analyze audio
            print("[ANIMATION] Step 1: Analyzing audio...")
            audio_data = self._analyze_audio(config.audio_path, config.quality_tier)

            # Step 2 + 3: Generate footage and (optionally) apply style
            if config.use_cogvideox:
                # ── Workflow B: CogVideoX text-to-video ──────────────────────
                print(f"\n[ANIMATION] Step 2 (Workflow B): Generating video clips with CogVideoX...")
                clip_paths = await self._generate_cogvideox_clips(
                    audio_data, config, project_dir / "clips"
                )
                if not clip_paths:
                    return AnimationWorkflowResult(
                        success=False,
                        error="CogVideoX generated no clips"
                    )
                print(f"\n[ANIMATION] Step 3 (Workflow B): Concatenating {len(clip_paths)} clips...")
                styled_video_path = await self._concatenate_clips(
                    clip_paths, project_dir / "styled_video.mp4"
                )
                if not styled_video_path:
                    return AnimationWorkflowResult(
                        success=False,
                        error="Clip concatenation failed"
                    )
            else:
                # ── Workflow A: SDXL LoRA images → rotoscope ─────────────────
                print(f"\n[ANIMATION] Step 2 (Workflow A): Generating content...")
                if config.use_stock_footage:
                    footage_paths = await self._collect_stock_footage(
                        config.stock_footage_queries,
                        project_dir / "footage"
                    )
                else:
                    footage_paths = await self._generate_character_scenes(
                        audio_data, config, project_dir / "scenes"
                    )

                print(f"[ANIMATION] footage_paths count: {len(footage_paths) if footage_paths else 0}")
                if not footage_paths:
                    return AnimationWorkflowResult(
                        success=False,
                        error="No footage generated or collected"
                    )

                print(f"\n[ANIMATION] Step 3 (Workflow A): Applying {config.animation_style} animation style...")
                rotoscope_config = RotoscopeConfig(
                    style=config.animation_style,
                    fps=config.fps,
                    width=config.width,
                    height=config.height,
                    strength=config.rotoscope_strength
                )
                styled_video_path = await self._apply_rotoscope_style(
                    footage_paths,
                    rotoscope_config,
                    project_dir / "styled_video.mp4",
                    audio_duration=audio_data.get("duration", 0)
                )
                if not styled_video_path:
                    return AnimationWorkflowResult(
                        success=False,
                        error="Rotoscope processing failed"
                    )

            # Step 4: Sync to music and assemble final video
            print(f"\n[ANIMATION] Step 4: Syncing to music and assembling final video...")
            final_video_path = self._assemble_final_video(
                styled_video_path,
                config.audio_path,
                audio_data,
                project_dir / f"{config.project_name}_final.mp4"
            )

            # Calculate duration
            end_time = datetime.now()
            duration_seconds = (end_time - start_time).total_seconds()

            # Save metadata
            metadata = {
                "project_name": config.project_name,
                "config": asdict(config),
                "audio_analysis": audio_data,
                "generation_time_seconds": duration_seconds,
                "output_video": str(final_video_path),
                "timestamp": datetime.now().isoformat()
            }

            class _NumpyEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    if isinstance(obj, (np.integer,)):
                        return int(obj)
                    if isinstance(obj, (np.floating,)):
                        return float(obj)
                    return super().default(obj)

            metadata_path = project_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, cls=_NumpyEncoder)

            print(f"\n[ANIMATION] ═══════════════════════════════════════")
            print(f"[ANIMATION] ✅ SUCCESS!")
            print(f"[ANIMATION] Output: {final_video_path}")
            print(f"[ANIMATION] Time: {duration_seconds/60:.1f} minutes")
            print(f"[ANIMATION] ═══════════════════════════════════════\n")

            return AnimationWorkflowResult(
                success=True,
                output_video_path=str(final_video_path),
                project_dir=str(project_dir),
                generation_time_seconds=duration_seconds,
                metadata=metadata
            )

        except Exception as e:
            import traceback
            print(f"\n[ANIMATION] ❌ ERROR: {e}")
            print(f"[ANIMATION] TRACEBACK:\n{traceback.format_exc()}")
            return AnimationWorkflowResult(
                success=False,
                error=str(e)
            )

    def _analyze_audio(self, audio_path: str, quality_tier: str) -> Dict:
        """Analyze audio to get structure and timing"""
        audio_data = self.music_analyzer.analyze_song(audio_path)

        # Determine scene count based on quality tier
        scene_count_map = {
            "basic": 12,
            "professional": 24,
            "cinematic": 48
        }
        audio_data["scene_count"] = scene_count_map.get(quality_tier, 24)

        return audio_data

    async def _generate_character_scenes(
        self,
        audio_data: Dict,
        config: AnimationProjectConfig,
        output_dir: Path
    ) -> List[str]:
        """
        Generate scenes using character LoRAs and scene prompts.

        Returns list of generated image paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize SDXL generator if not already loaded
        if self.sdxl_generator is None:
            self.sdxl_generator = SDXLLoRAGenerator()

        # Tropical/island scene templates - protagonist solo in early scenes,
        # protagonist + supporting character together in later scenes
        SCENE_TEMPLATES_SOLO = [
            "ohwx man standing on a tropical beach at golden hour, palm trees, ocean waves",
            "ohwx man walking along white sand beach, turquoise Caribbean water, sunny day",
            "ohwx man at a beachside tiki bar, tropical drinks, island atmosphere",
            "ohwx man looking out at the ocean, sailboats on horizon, warm sunset",
            "ohwx man sitting under a palm tree, hammock, island relaxation",
            "ohwx man on a wooden dock, island marina, golden light reflections",
            "ohwx man at a beach bonfire at night, tiki torches, tropical stars",
            "ohwx man on a boat in crystal blue water, Caribbean sea, freedom",
        ]
        SCENE_TEMPLATES_TOGETHER = [
            "ohwx man meeting a beautiful woman on the beach, tropical sunset, romantic moment",
            "ohwx man and ohwx woman walking together on the beach, island romance, golden hour",
            "ohwx man and ohwx woman at a tiki bar dancing, island music, joyful",
            "ohwx man and ohwx woman watching the sunset, tropical beach, romantic",
            "ohwx man and ohwx woman swimming in a crystal lagoon, paradise",
            "ohwx man and ohwx woman in a tropical garden, colorful flowers, lush",
            "ohwx man and ohwx woman on a cliff overlooking the ocean, dramatic view",
            "ohwx man and ohwx woman sharing a meal at a beach restaurant, candlelight",
            "ohwx man and ohwx woman dancing on the beach under the stars, moonlight",
            "ohwx man and ohwx woman watching fireworks over the ocean, celebration",
            "ohwx man and ohwx woman walking hand in hand along the shoreline, sunset",
            "ohwx man and ohwx woman embracing at sunset, tropical paradise, golden light",
            "ohwx man and ohwx woman silhouette against a brilliant tropical sunset",
            "ohwx man and ohwx woman happy together on tropical beach, paradise found",
            "ohwx man and ohwx woman in love, beach, palm trees, island paradise",
            "ohwx man and ohwx woman, romantic ending, tropical sunset, happy together",
        ]
        ALL_TEMPLATES = SCENE_TEMPLATES_SOLO + SCENE_TEMPLATES_TOGETHER

        scene_count = audio_data.get("scene_count", 24)
        duration = audio_data.get("duration", 0)
        scene_duration = duration / max(scene_count, 1)

        # Get style suffix for prompt
        style_info = ANIMATION_STYLES.get(config.animation_style, {})
        style_suffix = style_info.get("prompt_suffix", "")

        # Split point: first N scenes are solo, rest include supporting character
        # Default: first third is solo, rest together (or all solo if no supporting chars)
        has_supporting = bool(config.supporting_loras)
        solo_count = scene_count // 3 if has_supporting else scene_count

        generated_images = []

        for i in range(scene_count):
            scene_time = i * scene_duration
            include_supporting = has_supporting and i >= solo_count

            # Pick scene description
            template_idx = i % len(ALL_TEMPLATES)
            scene_desc = ALL_TEMPLATES[template_idx]

            # Build full prompt
            if style_suffix:
                prompt = f"{scene_desc}, {style_suffix}, cinematic photography"
            else:
                prompt = f"{scene_desc}, cinematic photography, high quality"

            # Build LoRA list
            loras = []

            # Add protagonist LoRA
            if config.protagonist_lora:
                loras.append({
                    "path": f"{config.protagonist_lora}/{config.protagonist_lora}.safetensors",
                    "weight": 0.85,
                    "trigger": "ohwx man"
                })

            # Add supporting character LoRA for later scenes
            if include_supporting and config.supporting_loras:
                for supp_lora in config.supporting_loras:
                    loras.append({
                        "path": f"{supp_lora}/{supp_lora}.safetensors",
                        "weight": 0.7,
                        "trigger": "ohwx woman"
                    })

            # Add scene environment LoRA (vary across scenes)
            if config.scene_loras:
                scene_lora = config.scene_loras[i % len(config.scene_loras)]
                loras.append({
                    "path": f"{scene_lora}/{scene_lora}.safetensors",
                    "weight": 0.6
                })

            # Add style LoRA if specified
            if config.style_lora:
                loras.append({
                    "path": f"{config.style_lora}/{config.style_lora}.safetensors",
                    "weight": 0.5
                })

            # Generate image
            result = await self.sdxl_generator.generate_with_loras(
                prompt=prompt,
                loras=loras,
                num_images=1,
                scene_timestamp=scene_time
            )

            if result.success and result.images:
                generated_images.extend(result.images)

        return generated_images

    async def _collect_stock_footage(
        self,
        queries: List[str],
        output_dir: Path
    ) -> List[str]:
        """
        Collect stock footage from Pexels.

        Returns list of video file paths.
        """
        # This would call pexels_video_collector.py
        # For now, placeholder
        print(f"[ANIMATION] Stock footage collection not yet implemented")
        print(f"[ANIMATION] Queries: {queries}")
        return []

    async def _apply_rotoscope_style(
        self,
        input_paths: List[str],
        config: RotoscopeConfig,
        output_path: Path,
        audio_duration: float = 0.0
    ) -> Optional[str]:
        """
        Apply rotoscope/animation style to footage.

        Args:
            input_paths: List of video or image paths
            config: Rotoscope configuration
            output_path: Output video path
        """
        # Unload SDXL pipeline to free VRAM before loading ControlNet
        if self.sdxl_generator is not None:
            print("[ANIMATION] Unloading SDXL pipeline to free VRAM for ControlNet...")
            self.sdxl_generator.unload()

        try:
            # Initialize rotoscope generator if not already loaded
            if self.rotoscope_generator is None:
                self.rotoscope_generator = RotoscopeGenerator()

            # Check if input is images or video
            first_path = Path(input_paths[0])
            if first_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                result = await self.rotoscope_generator.process_video(
                    str(first_path),
                    str(output_path),
                    config
                )
            else:
                result = await self.rotoscope_generator.process_image_sequence(
                    input_paths,
                    str(output_path),
                    config
                )

            if result.success:
                return result.output_video_path

            print(f"[ANIMATION] ControlNet rotoscope failed: {result.error}")

        except Exception as e:
            import traceback
            print(f"[ANIMATION] ControlNet rotoscope exception: {e}")
            print(f"[ANIMATION] {traceback.format_exc()}")

        print("[ANIMATION] Rotoscope failed — returning None. Use use_cogvideox=True for a reliable fallback.")
        return None

    # ── Workflow B: CogVideoX ──────────────────────────────────────────────────

    async def _generate_cogvideox_clips(
        self,
        audio_data: Dict,
        config: AnimationProjectConfig,
        output_dir: Path,
    ) -> List[str]:
        """Generate per-scene video clips via CogVideoX (Workflow B).

        Produces one 6-second clip (48 frames @ 8 FPS) per scene.
        Returns list of .mp4 paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.cogvideox_generator is None:
            self.cogvideox_generator = CogVideoXGenerator()
            self.cogvideox_generator.load()

        scene_count = audio_data.get("scene_count", 24)
        style_info = ANIMATION_STYLES.get(config.animation_style, {})
        style_suffix = style_info.get("prompt_suffix", "cinematic, high quality")

        # Reuse the same scene templates as Workflow A
        SCENE_TEMPLATES_SOLO = [
            "ohwx man standing on a tropical beach at golden hour, palm trees, ocean waves",
            "ohwx man walking along white sand beach, turquoise Caribbean water, sunny day",
            "ohwx man at a beachside tiki bar, tropical drinks, island atmosphere",
            "ohwx man looking out at the ocean, sailboats on horizon, warm sunset",
            "ohwx man sitting under a palm tree, hammock, island relaxation",
            "ohwx man on a wooden dock, island marina, golden light reflections",
            "ohwx man at a beach bonfire at night, tiki torches, tropical stars",
            "ohwx man on a boat in crystal blue water, Caribbean sea, freedom",
        ]
        SCENE_TEMPLATES_TOGETHER = [
            "ohwx man meeting a beautiful woman on the beach, tropical sunset, romantic moment",
            "ohwx man and ohwx woman walking together on the beach, island romance, golden hour",
            "ohwx man and ohwx woman at a tiki bar dancing, island music, joyful",
            "ohwx man and ohwx woman watching the sunset, tropical beach, romantic",
            "ohwx man and ohwx woman swimming in a crystal lagoon, paradise",
            "ohwx man and ohwx woman in a tropical garden, colorful flowers, lush",
            "ohwx man and ohwx woman on a cliff overlooking the ocean, dramatic view",
            "ohwx man and ohwx woman sharing a meal at a beach restaurant, candlelight",
            "ohwx man and ohwx woman dancing on the beach under the stars, moonlight",
            "ohwx man and ohwx woman watching fireworks over the ocean, celebration",
            "ohwx man and ohwx woman walking hand in hand along the shoreline, sunset",
            "ohwx man and ohwx woman embracing at sunset, tropical paradise, golden light",
            "ohwx man and ohwx woman silhouette against a brilliant tropical sunset",
            "ohwx man and ohwx woman happy together on tropical beach, paradise found",
            "ohwx man and ohwx woman in love, beach, palm trees, island paradise",
            "ohwx man and ohwx woman, romantic ending, tropical sunset, happy together",
        ]
        ALL_TEMPLATES = SCENE_TEMPLATES_SOLO + SCENE_TEMPLATES_TOGETHER

        has_supporting = bool(config.supporting_loras)
        solo_count = scene_count // 3 if has_supporting else scene_count

        clip_paths = []
        for i in range(scene_count):
            include_supporting = has_supporting and i >= solo_count
            templates = (SCENE_TEMPLATES_TOGETHER if include_supporting else SCENE_TEMPLATES_SOLO)
            scene_desc = templates[i % len(templates)]
            prompt = f"{scene_desc}, {style_suffix}"

            print(f"[ANIMATION] CogVideoX clip {i + 1}/{scene_count}: {scene_desc[:60]}...")
            frames = self.cogvideox_generator.generate(
                prompt=prompt,
                num_frames=48,       # 6s @ 8fps — CogVideoX native
                guidance_scale=6.0,
                num_inference_steps=50,
                seed=i * 137,        # deterministic spread
                width=720,
                height=480,
            )

            if not frames:
                print(f"[ANIMATION] CogVideoX clip {i + 1} returned no frames — skipping")
                continue

            clip_path = output_dir / f"clip_{i:03d}.mp4"
            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(clip_path), fourcc, 8, (w, h))  # 8fps = CogVideoX native
            for frame in frames:
                writer.write(frame)
            writer.release()
            clip_paths.append(str(clip_path))
            print(f"[ANIMATION] Saved clip {i + 1}: {clip_path}")

        # Free VRAM after all clips are generated
        if self.cogvideox_generator is not None:
            self.cogvideox_generator.kill()
            self.cogvideox_generator = None

        print(f"[ANIMATION] CogVideoX: generated {len(clip_paths)}/{scene_count} clips")
        return clip_paths

    async def _concatenate_clips(
        self,
        clip_paths: List[str],
        output_path: Path,
    ) -> Optional[str]:
        """Concatenate video clips into a single video file."""
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
            output_path.parent.mkdir(parents=True, exist_ok=True)
            clips = [VideoFileClip(p) for p in clip_paths]
            final = concatenate_videoclips(clips)
            final.write_videofile(str(output_path), codec="libx264", logger=None)
            for c in clips:
                c.close()
            final.close()
            print(f"[ANIMATION] Concatenated {len(clip_paths)} clips → {output_path}")
            return str(output_path)
        except Exception as e:
            import traceback
            print(f"[ANIMATION] Clip concatenation failed: {e}")
            print(f"[ANIMATION] {traceback.format_exc()}")
            return None

    def _assemble_final_video(
        self,
        styled_video_path: str,
        audio_path: str,
        audio_data: Dict,
        output_path: Path
    ) -> str:
        """
        Combine styled video with audio track and export final video.
        """
        from moviepy import VideoFileClip, AudioFileClip

        print(f"[ANIMATION] Assembling final video with audio...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            video = VideoFileClip(styled_video_path)
            audio = AudioFileClip(audio_path)

            # Loop video if shorter than audio, or trim if longer
            audio_duration = audio.duration
            if video.duration < audio_duration:
                # Loop the video to match audio length
                loops = int(audio_duration / video.duration) + 1
                from moviepy import concatenate_videoclips
                video = concatenate_videoclips([video] * loops)

            # Trim to audio length and set audio
            final = video.subclipped(0, audio_duration).with_audio(audio)
            final.write_videofile(str(output_path), codec="libx264", audio_codec="aac", logger=None)
            final.close()
            audio.close()
            video.close()

            print(f"[ANIMATION] Final video assembled: {output_path}")

        except Exception as e:
            import traceback
            print(f"[ANIMATION] Video assembly error: {e}")
            print(f"[ANIMATION] {traceback.format_exc()}")
            # Still return the path - ffmpeg will be tried or the styled video used as-is
            import shutil
            if not output_path.exists():
                shutil.copy2(styled_video_path, str(output_path))

        return str(output_path)

    @staticmethod
    def load_project_config(config_path: str) -> AnimationProjectConfig:
        """Load project configuration from YAML file"""
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        return AnimationProjectConfig(**config_dict)

    @staticmethod
    def save_project_config(config: AnimationProjectConfig, config_path: str):
        """Save project configuration to YAML file"""
        with open(config_path, 'w') as f:
            yaml.dump(asdict(config), f, default_flow_style=False)

        print(f"[ANIMATION] Saved project config: {config_path}")
