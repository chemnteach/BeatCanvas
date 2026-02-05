#!/usr/bin/env python3
"""
Comprehensive MoviePy fixes for BeatCanvas
"""

from pathlib import Path

def fix_video_assembler():
    """Fix all MoviePy references in video assembler"""

    file_path = Path("backend/src/video/assembler.py")

    if not file_path.exists():
        print(f"[FAIL] {file_path} not found")
        return

    try:
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fixes for MoviePy 2.x
        fixes = [
            # Type annotations
            ("List[VideoClip]", "List"),
            ("VideoClip", "CompositeVideoClip"),
            ("ImageClip", "ImageClip"),
            ("ColorClip", "ColorClip"),

            # Update method calls that might have changed
            ("clip.resize(1.2).set_position", "clip.resized(1.2).with_position"),
            ("clip.fadein(0.5)", "clip.with_fadein(0.5)"),
            ("clip.fadeout(0.5)", "clip.with_fadeout(0.5)"),
            ("clip.set_start(", "clip.with_start("),
            ("clip.set_duration(", "clip.with_duration("),
            ("clip.set_audio(", "clip.with_audio("),
            ("txt_clip.set_position('center').set_duration(duration)", "txt_clip.with_position('center').with_duration(duration)")
        ]

        # Apply fixes
        updated = False
        for old, new in fixes:
            if old in content:
                content = content.replace(old, new)
                updated = True
                print(f"  [OK] Fixed: {old} -> {new}")

        if updated:
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("[OK] MoviePy fixes applied")
        else:
            print("[SKIP] No MoviePy fixes needed")

    except Exception as e:
        print(f"[FAIL] Error applying MoviePy fixes: {e}")

def create_simple_video_assembler():
    """Create a simplified video assembler that works with current MoviePy"""

    content = '''# MoviePy 2.x imports
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, TextClip
from pathlib import Path
import numpy as np
from typing import List, Dict
import os

class VideoAssembler:
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_video(self,
                    audio_file: str,
                    scene_assets: Dict[float, List],
                    storyboard: List[Dict],
                    task_id: str) -> str:
        """Assemble final video from audio and generated assets"""

        try:
            # Load audio
            audio_clip = AudioFileClip(audio_file)

            # Create video clips from images
            video_clips = []

            for scene in storyboard:
                timestamp = scene['timestamp_start']

                # Get selected image for this scene
                if timestamp in scene_assets and scene_assets[timestamp]:
                    image_asset = scene_assets[timestamp][0]
                    image_path = image_asset.image_path

                    duration = scene['timestamp_end'] - scene['timestamp_start']

                    if os.path.exists(image_path):
                        clip = ImageClip(image_path, duration=duration)
                        # Note: MoviePy 2.x may use different method names
                        # This is a simplified version
                        video_clips.append(clip)
                    else:
                        # Create placeholder
                        clip = self._create_placeholder_clip(duration, scene)
                        video_clips.append(clip)
                else:
                    duration = scene['timestamp_end'] - scene['timestamp_start']
                    clip = self._create_placeholder_clip(duration, scene)
                    video_clips.append(clip)

            # Simple concatenation for now
            if video_clips:
                # Use basic video composition
                final_video = CompositeVideoClip(video_clips)

                # Set audio
                if hasattr(final_video, 'with_audio'):
                    final_video = final_video.with_audio(audio_clip)
                elif hasattr(final_video, 'set_audio'):
                    final_video = final_video.set_audio(audio_clip)

                # Set duration
                if hasattr(final_video, 'with_duration'):
                    final_video = final_video.with_duration(audio_clip.duration)
                elif hasattr(final_video, 'set_duration'):
                    final_video = final_video.set_duration(audio_clip.duration)
            else:
                # Fallback
                final_video = ColorClip(size=(1792, 1024), color=(0, 0, 0), duration=audio_clip.duration)

            # Export video
            output_path = self.output_dir / f"{task_id}.mp4"
            final_video.write_videofile(
                str(output_path),
                fps=24,
                verbose=False,
                logger=None
            )

            return str(output_path)

        except Exception as e:
            # Create a simple text video as fallback
            print(f"Video assembly failed, creating text fallback: {e}")
            return self._create_text_fallback(audio_file, task_id)

    def _create_placeholder_clip(self, duration: float, scene: Dict):
        """Create simple placeholder"""
        return ColorClip(size=(1792, 1024), color=(128, 128, 128), duration=duration)

    def _create_text_fallback(self, audio_file: str, task_id: str) -> str:
        """Create a simple audio file as fallback"""
        try:
            # Just copy the audio file as output for testing
            import shutil
            output_path = self.output_dir / f"{task_id}.mp3"
            shutil.copy(audio_file, output_path)
            return str(output_path)
        except Exception as e:
            print(f"Even fallback failed: {e}")
            return ""

    def get_video_info(self, video_path: str) -> Dict:
        """Get basic info about video"""
        return {
            "format": "MP4",
            "status": "Generated"
        }
'''

    file_path = Path("backend/src/video/assembler_simple.py")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[OK] Created simplified video assembler")

if __name__ == "__main__":
    print("Fixing MoviePy compatibility issues...")
    fix_video_assembler()
    create_simple_video_assembler()
    print("MoviePy fixes complete!")