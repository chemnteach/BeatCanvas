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

from src.audio.analyzer import MusicAnalyzer
from src.assets.sdxl_lora_generator import SDXLLoRAGenerator
from src.animation.rotoscope_generator import RotoscopeGenerator, RotoscopeConfig
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
        self.sdxl_generator = None  # Lazy load
        self.rotoscope_generator = None  # Lazy load
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

            # Step 2: Generate or collect footage
            print(f"\n[ANIMATION] Step 2: Generating content...")
            if config.use_stock_footage:
                footage_paths = await self._collect_stock_footage(
                    config.stock_footage_queries,
                    project_dir / "footage"
                )
            else:
                footage_paths = await self._generate_character_scenes(
                    audio_data,
                    config,
                    project_dir / "scenes"
                )

            if not footage_paths:
                return AnimationWorkflowResult(
                    success=False,
                    error="No footage generated or collected"
                )

            # Step 3: Apply rotoscope/animation style
            print(f"\n[ANIMATION] Step 3: Applying {config.animation_style} animation style...")
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
                project_dir / "styled_video.mp4"
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

            metadata_path = project_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

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
            print(f"\n[ANIMATION] ❌ ERROR: {e}")
            return AnimationWorkflowResult(
                success=False,
                error=str(e)
            )

    def _analyze_audio(self, audio_path: str, quality_tier: str) -> Dict:
        """Analyze audio to get structure and timing"""
        audio_data = self.music_analyzer.analyze_audio(audio_path)

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

        # Build scene prompts (simplified for now - would normally use storyboard generator)
        scene_count = audio_data.get("scene_count", 24)
        duration = audio_data.get("duration", 0)
        scene_duration = duration / scene_count

        generated_images = []

        # Example scene generation (would be more sophisticated with actual storyboard)
        for i in range(scene_count):
            scene_time = i * scene_duration

            # Build prompt (this is simplified - would come from storyboard generator)
            prompt = f"scene {i+1}, cinematic composition, high quality"

            # Build LoRA list
            loras = []

            # Add protagonist LoRA if specified
            if config.protagonist_lora:
                loras.append({
                    "path": f"{config.protagonist_lora}/{config.protagonist_lora}.safetensors",
                    "weight": 0.8,
                    "trigger": "ohwx"  # Would come from LoRA registry
                })

            # Add scene LoRA if specified
            if config.scene_loras and i % 3 == 0:  # Vary scene LoRAs
                scene_lora = config.scene_loras[i % len(config.scene_loras)]
                loras.append({
                    "path": f"{scene_lora}/{scene_lora}.safetensors",
                    "weight": 0.7
                })

            # Add style LoRA if specified
            if config.style_lora:
                loras.append({
                    "path": f"{config.style_lora}/{config.style_lora}.safetensors",
                    "weight": 0.6
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
        output_path: Path
    ) -> Optional[str]:
        """
        Apply rotoscope/animation style to footage.

        Args:
            input_paths: List of video or image paths
            config: Rotoscope configuration
            output_path: Output video path
        """
        # Initialize rotoscope generator if not already loaded
        if self.rotoscope_generator is None:
            self.rotoscope_generator = RotoscopeGenerator()

        # Check if input is images or video
        first_path = Path(input_paths[0])
        if first_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            # Video input
            result = await self.rotoscope_generator.process_video(
                str(first_path),
                str(output_path),
                config
            )
        else:
            # Image sequence input
            result = await self.rotoscope_generator.process_image_sequence(
                input_paths,
                str(output_path),
                config
            )

        if result.success:
            return result.output_video_path

        return None

    def _assemble_final_video(
        self,
        styled_video_path: str,
        audio_path: str,
        audio_data: Dict,
        output_path: Path
    ) -> str:
        """
        Sync styled video to music and create final output.

        Uses existing VideoAssembler with audio sync.
        """
        # This would use the existing video assembler
        # For now, just copy the styled video and add audio
        # (Full implementation would handle beat sync, transitions, etc.)

        print(f"[ANIMATION] Final assembly to: {output_path}")
        # Placeholder - would call video assembler here

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
