# MoviePy 2.x imports
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, TextClip, concatenate_videoclips
import moviepy
from pathlib import Path
import numpy as np
from typing import List, Dict, Optional, Union
import os
import cv2
import subprocess
import shutil
import logging

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIDEO CONFIGURATION - Image-to-Video Upgrade
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Resolution: Standardized to 1080p for Luma compatibility
TARGET_RESOLUTION = (1920, 1080)  # Width x Height

# Transition settings
TRANSITION_DURATION = 0.75  # seconds - longer when switching video↔image
TRANSITION_DURATION_SAME = 0.375  # seconds - between same types

# Scene duration constraints
MIN_SCENE_DURATION = 2.5  # seconds - Luma needs ~3-5s to show motion
MAX_SCENE_DURATION = 8.0  # seconds - avoid visual fatigue


class VideoAssembler:
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.gpu_available = self._check_gpu_encoding()
        self.target_resolution = TARGET_RESOLUTION

    def _check_gpu_encoding(self) -> bool:
        """Check if NVIDIA GPU encoding (h264_nvenc) is available"""
        try:
            # Check if ffmpeg has nvenc support
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if 'h264_nvenc' in result.stdout:
                print("[ASSEMBLER] GPU encoding available (h264_nvenc)")
                return True
            else:
                print("[ASSEMBLER] GPU encoding not available, using CPU (libx264)")
                return False
        except Exception as e:
            print(f"[ASSEMBLER] Could not check GPU encoding: {e}, using CPU")
            return False

    def _get_encoding_params(self) -> Dict:
        """Get optimal encoding parameters based on available hardware"""
        if self.gpu_available:
            return {
                'codec': 'h264_nvenc',
                'preset': 'p4',  # NVENC preset (p1=fastest, p7=slowest/best quality)
                'ffmpeg_params': [
                    '-rc:v', 'vbr',      # Variable bitrate
                    '-cq:v', '19',       # Quality level (lower=better, 0-51)
                    '-b:v', '0',         # Let CQ control bitrate
                    '-maxrate', '50M',   # Max bitrate cap
                    '-bufsize', '100M',  # Buffer size
                ]
            }
        else:
            return {
                'codec': 'libx264',
                'preset': 'medium',
                'ffmpeg_params': [
                    '-crf', '18',        # Quality (lower=better, 0-51)
                ]
            }

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
                print(f"[ASSEMBLER] Processing scene at {timestamp}s")

                # Get selected image for this scene
                # Use round to handle floating point precision issues
                matching_key = None
                for key in scene_assets.keys():
                    if abs(key - timestamp) < 0.01:
                        matching_key = key
                        break

                if matching_key is not None and scene_assets[matching_key]:
                    # Use first available image (in real implementation, use selected_image index)
                    image_asset = scene_assets[matching_key][0]
                    image_path = image_asset.image_path
                    print(f"[ASSEMBLER] Found image: {image_path}, exists: {os.path.exists(image_path)}")

                    # Create image clip with duration
                    duration = scene['timestamp_end'] - scene['timestamp_start']

                    if os.path.exists(image_path):
                        clip = ImageClip(image_path, duration=duration)

                        # Resize to target resolution (1920x1080 standard)
                        clip = clip.resized(self.target_resolution)

                        # Apply cinematic processing (new "vibe pass")
                        clip = self._apply_cinematic_processing(clip, scene)

                        # Apply traditional effects
                        clip = self._apply_effects(clip, scene)

                        # Don't set start time - concatenate handles sequencing
                        video_clips.append(clip)
                    else:
                        # Create placeholder clip if image not found
                        print(f"[ASSEMBLER] Image NOT found: {image_path}")
                        clip = self._create_placeholder_clip(duration, scene)
                        video_clips.append(clip)
                else:
                    # Create placeholder clip if no assets
                    print(f"[ASSEMBLER] No asset match for timestamp {timestamp}")
                    duration = scene['timestamp_end'] - scene['timestamp_start']
                    clip = self._create_placeholder_clip(duration, scene)
                    video_clips.append(clip)

            # Combine all clips using concatenate (more stable than CompositeVideoClip)
            print(f"[ASSEMBLER] Total clips to combine: {len(video_clips)}")
            if video_clips:
                # Use concatenate_videoclips instead of CompositeVideoClip for better stability
                final_video = concatenate_videoclips(video_clips, method="compose")
                final_video = final_video.with_audio(audio_clip)
                final_video = final_video.with_duration(audio_clip.duration)
            else:
                # Fallback: create video with just audio and black screen
                black_clip = ColorClip(size=TARGET_RESOLUTION, color=(0, 0, 0), duration=audio_clip.duration)
                final_video = black_clip.with_audio(audio_clip)

            # Export video with GPU or CPU encoding
            output_path = self.output_dir / f"{task_id}.mp4"
            encoding = self._get_encoding_params()

            print(f"[ASSEMBLER] Encoding with {encoding['codec']} (GPU: {self.gpu_available})")

            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec=encoding['codec'],
                preset=encoding['preset'],
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                ffmpeg_params=encoding['ffmpeg_params']
            )

            # Cleanup
            final_video.close()
            audio_clip.close()

            return str(output_path)

        except Exception as e:
            raise Exception(f"Error assembling video: {str(e)}")

    def _apply_effects(self, clip: ImageClip, scene: Dict) -> ImageClip:
        """Apply effects based on scene requirements"""
        from moviepy import vfx

        effects = scene.get('effects', [])
        duration = clip.duration

        for effect in effects:
            if effect == "zoom_in":
                # Slow zoom in - use time_symmetrize for smooth effect
                # Scale from 1.0 to 1.15 over the clip duration
                def zoom_in_func(t, dur=duration):
                    return 1 + 0.15 * (t / dur) if dur > 0 else 1
                clip = clip.resized(zoom_in_func)
            elif effect == "zoom_out":
                # Slow zoom out - start zoomed in, end at normal
                def zoom_out_func(t, dur=duration):
                    return 1.15 - 0.15 * (t / dur) if dur > 0 else 1.15
                clip = clip.resized(zoom_out_func)
            elif effect == "fade_in":
                clip = clip.with_effects([vfx.CrossFadeIn(0.5)])
            elif effect == "fade_out":
                clip = clip.with_effects([vfx.CrossFadeOut(0.5)])
            elif effect == "pan_right":
                # Ken Burns pan right effect using scroll
                # Resize larger first, then crop/scroll
                w, h = clip.size
                clip = clip.resized(1.3)
                def pan_right_pos(t, dur=duration, width=w):
                    # Move from left edge to right edge
                    x_offset = -int((0.3 * width) * (t / dur)) if dur > 0 else 0
                    return (x_offset, 'center')
                clip = clip.with_position(pan_right_pos)
                # Wrap in CompositeVideoClip to apply the position
                clip = CompositeVideoClip([clip], size=(w, h))
            elif effect == "pan_left":
                # Ken Burns pan left effect
                w, h = clip.size
                clip = clip.resized(1.3)
                def pan_left_pos(t, dur=duration, width=w):
                    # Start offset to right, move left
                    start_offset = -int(0.3 * width)
                    x_offset = start_offset + int((0.3 * width) * (t / dur)) if dur > 0 else start_offset
                    return (x_offset, 'center')
                clip = clip.with_position(pan_left_pos)
                clip = CompositeVideoClip([clip], size=(w, h))
            elif effect == "crossfade":
                # Crossfade is handled between clips
                pass

        return clip

    def _create_placeholder_clip(self, duration: float, scene: Dict) -> ColorClip:
        """Create placeholder clip when image is not available"""

        # Choose color based on mood
        mood_colors = {
            'energetic': (255, 100, 100),  # Red
            'calm': (100, 150, 255),       # Blue
            'dark': (50, 50, 50),          # Dark gray
            'bright': (255, 255, 200),     # Light yellow
            'neutral': (128, 128, 128)     # Gray
        }

        mood = scene.get('mood', 'neutral')
        color = mood_colors.get(mood, (128, 128, 128))

        clip = ColorClip(size=TARGET_RESOLUTION, color=color, duration=duration)

        # Add text overlay with scene description
        txt_clip = TextClip(
            f"Scene: {scene.get('description', 'Generated scene')[:50]}...",
            fontsize=50,
            color='white',
            font='Arial'
        ).with_position('center').with_duration(duration)

        return CompositeVideoClip([clip, txt_clip])

    def create_preview_video(self,
                           audio_file: str,
                           storyboard: List[Dict],
                           task_id: str) -> str:
        """Create a preview video with just text overlays (no images)"""

        try:
            # Load audio
            audio_clip = AudioFileClip(audio_file)

            # Create text clips for each scene
            video_clips = []

            for i, scene in enumerate(storyboard):
                duration = scene['timestamp_end'] - scene['timestamp_start']

                # Create background color clip
                bg_clip = ColorClip(
                    size=TARGET_RESOLUTION,
                    color=(30, 30, 50),  # Dark blue
                    duration=duration
                )

                # Create text overlay
                scene_text = f"Scene {i+1}\n\n{scene['description']}\n\nMood: {scene['mood']}\nCamera: {scene['camera_direction']}"

                txt_clip = TextClip(
                    scene_text,
                    fontsize=40,
                    color='white',
                    font='Arial',
                    method='caption',
                    size=(1400, None)
                ).with_position('center').with_duration(duration)

                # Combine background and text
                scene_clip = CompositeVideoClip([bg_clip, txt_clip])
                scene_clip = scene_clip.with_start(scene['timestamp_start'])

                video_clips.append(scene_clip)

            # Combine all clips
            final_video = CompositeVideoClip(video_clips, size=TARGET_RESOLUTION)
            final_video = final_video.with_audio(audio_clip)
            final_video = final_video.with_duration(audio_clip.duration)

            # Export preview video with GPU or CPU encoding
            output_path = self.output_dir / f"{task_id}_preview.mp4"
            encoding = self._get_encoding_params()

            print(f"[ASSEMBLER] Encoding preview with {encoding['codec']} (GPU: {self.gpu_available})")

            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec=encoding['codec'],
                preset=encoding['preset'],
                audio_codec='aac',
                temp_audiofile='temp-audio-preview.m4a',
                remove_temp=True,
                ffmpeg_params=encoding['ffmpeg_params']
            )

            # Cleanup
            final_video.close()
            audio_clip.close()

            return str(output_path)

        except Exception as e:
            raise Exception(f"Error creating preview video: {str(e)}")

    def add_crossfade_transitions(self, clips: List, transition_duration: float = 0.5) -> List:
        """Add crossfade transitions between video clips"""

        if len(clips) <= 1:
            return clips

        processed_clips = []

        for i in range(len(clips)):
            clip = clips[i]

            if i > 0:
                # Add fade in for all clips except the first
                clip = clip.fadein(transition_duration)

            if i < len(clips) - 1:
                # Add fade out for all clips except the last
                clip = clip.fadeout(transition_duration)

            processed_clips.append(clip)

        return processed_clips

    def get_video_info(self, video_path: str) -> Dict:
        """Get information about the generated video"""

        try:
            if not os.path.exists(video_path):
                return {}

            clip = VideoFileClip(video_path)
            info = {
                'duration': clip.duration,
                'fps': clip.fps,
                'size': clip.size,
                'format': 'MP4',
                'codec': 'H.264',
                'audio_codec': 'AAC',
                'file_size': os.path.getsize(video_path)
            }
            clip.close()

            return info

        except Exception as e:
            print(f"Error getting video info: {e}")
            return {}

    def _apply_cinematic_processing(self, clip: ImageClip, scene: Dict) -> ImageClip:
        """
        Apply cinematic post-processing to make Nano Banana's clean output more film-like.
        This is the "vibe pass" that converts commercial-grade images to cinematic quality.
        """

        def cinematic_filter(frame):
            """Custom filter for cinematic look - takes frame directly (MoviePy 2.x API)"""
            # MoviePy can pass frames as either:
            # - uint8 (0-255) from ImageClip
            # - float64 (0.0-1.0) after some transforms
            # Detect and normalize to uint8 for OpenCV processing

            if frame.dtype == np.float64 or frame.dtype == np.float32:
                # Float format (0-1) - convert to uint8
                frame_uint8 = (frame * 255).astype(np.uint8)
            else:
                # Already uint8 (0-255)
                frame_uint8 = frame.astype(np.uint8)

            # Convert RGB to BGR for OpenCV
            frame_cv = cv2.cvtColor(frame_uint8, cv2.COLOR_RGB2BGR)

            # 1. Film Grain (subtle texture)
            noise = np.random.normal(0, 8, frame_cv.shape).astype(np.int16)
            frame_cv = np.clip(frame_cv.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            # 2. Color Grading (cinematic look)
            # Lift shadows, crush blacks slightly
            frame_cv = cv2.addWeighted(frame_cv, 1.1, frame_cv, 0, -10)

            # 3. Saturation adjustment (more moody)
            hsv = cv2.cvtColor(frame_cv, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)  # Increase saturation
            frame_cv = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # 4. Slight vignette
            h, w = frame_cv.shape[:2]
            center_x, center_y = w // 2, h // 2
            Y, X = np.ogrid[:h, :w]
            dist_from_center = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            vignette = 1 - (dist_from_center / max_dist) * 0.3

            for i in range(3):
                frame_cv[:, :, i] = np.clip(frame_cv[:, :, i] * vignette, 0, 255)

            # Convert back to RGB uint8 (MoviePy standard format)
            frame_rgb = cv2.cvtColor(frame_cv.astype(np.uint8), cv2.COLOR_BGR2RGB)
            return frame_rgb

        # Apply the cinematic filter
        return clip.image_transform(cinematic_filter)

    def create_davinci_project(self, storyboard: List[Dict], scene_assets: Dict[float, List], audio_file: str, task_id: str) -> str:
        """
        Create a DaVinci Resolve project file (.drp) for professional post-processing.
        This allows handoff to professional video editing software.
        """
        import json

        project_data = {
            "name": f"BeatCanvas_{task_id}",
            "timeline": {
                "framerate": 24,
                "resolution": f"{TARGET_RESOLUTION[0]}x{TARGET_RESOLUTION[1]}",
                "audio_track": audio_file,
                "video_tracks": []
            },
            "clips": []
        }

        # Add video clips with timing data
        for scene in storyboard:
            timestamp = scene['timestamp_start']
            if timestamp in scene_assets and scene_assets[timestamp]:
                image_asset = scene_assets[timestamp][0]

                clip_data = {
                    "start": scene['timestamp_start'],
                    "end": scene['timestamp_end'],
                    "source": image_asset.image_path,
                    "effects": scene.get('effects', []),
                    "description": scene.get('description', ''),
                    "mood": scene.get('mood', 'neutral'),
                    "suggested_grade": self._get_color_grade_suggestion(scene)
                }
                project_data["clips"].append(clip_data)

        # Export project file
        project_file = self.output_dir / f"{task_id}_davinci.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)

        return str(project_file)

    def _get_color_grade_suggestion(self, scene: Dict) -> Dict:
        """Suggest color grading based on scene mood"""
        mood = scene.get('mood', 'neutral').lower()

        if 'energetic' in mood or 'upbeat' in mood:
            return {
                "saturation": "+20%",
                "contrast": "+15%",
                "highlights": "+10%",
                "suggested_lut": "Rec709_to_Alexa"
            }
        elif 'melancholy' in mood or 'sad' in mood:
            return {
                "saturation": "-10%",
                "shadows": "+20%",
                "blue_tint": "+15%",
                "suggested_lut": "Cinematic_Blue"
            }
        elif 'intense' in mood or 'dramatic' in mood:
            return {
                "contrast": "+25%",
                "shadows": "-15%",
                "orange_teal": True,
                "suggested_lut": "Hollywood_Action"
            }
        else:
            return {
                "saturation": "+5%",
                "contrast": "+10%",
                "suggested_lut": "Natural_Color"
            }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ENHANCED VIDEO ASSEMBLY - Image-to-Video Upgrade
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_video_enhanced(
        self,
        audio_file: str,
        scene_assets: Dict[float, List],
        video_clips_map: Dict[float, str],  # timestamp -> video_path (for hero scenes)
        storyboard: List[Dict],
        task_id: str
    ) -> str:
        """
        Enhanced video assembly that handles mixed video/image content.

        This method supports:
        - AI-generated video clips for "hero" scenes (from Luma)
        - Ken Burns effects on images for "standard" scenes
        - Smooth transitions between video↔image types
        - Proper duration handling for both content types

        Args:
            audio_file: Path to audio track
            scene_assets: Dict mapping timestamp to image assets
            video_clips_map: Dict mapping timestamp to video file path (hero scenes only)
            storyboard: List of scene dicts with timing, effects, scene_type
            task_id: Unique task identifier

        Returns:
            Path to output video file
        """
        from moviepy import vfx

        try:
            audio_clip = AudioFileClip(audio_file)
            video_clips = []
            prev_scene_type = None

            for i, scene in enumerate(storyboard):
                timestamp = scene['timestamp_start']
                duration = scene['timestamp_end'] - scene['timestamp_start']
                scene_type = scene.get('scene_type', 'standard')

                print(f"[ASSEMBLER] Processing scene {i+1} at {timestamp}s ({scene_type})")

                # Check if we have a video clip for this scene (hero treatment)
                if timestamp in video_clips_map and video_clips_map[timestamp]:
                    video_path = video_clips_map[timestamp]
                    if os.path.exists(video_path):
                        clip = VideoFileClip(video_path)

                        # Trim video if needed to match scene duration
                        if clip.duration > duration:
                            clip = clip.subclipped(0, duration)
                        elif clip.duration < duration:
                            # Loop or hold last frame if video is shorter
                            # For now, just use the video duration
                            pass

                        # Resize to target resolution
                        clip = clip.resized(self.target_resolution)

                        # Skip cinematic filter for video - Luma has its own aesthetic
                        actual_type = "video"
                        print(f"[ASSEMBLER] Using video clip: {video_path}")
                    else:
                        # Video file missing, fallback to image
                        clip = self._create_image_clip(scene, scene_assets, timestamp, duration)
                        actual_type = "image"
                else:
                    # Standard scene - use image with Ken Burns
                    clip = self._create_image_clip(scene, scene_assets, timestamp, duration)
                    actual_type = "image"

                # Add transition if switching between video/image types
                if prev_scene_type and prev_scene_type != actual_type:
                    # Longer crossfade when switching types (reduces jarring)
                    clip = clip.with_effects([vfx.CrossFadeIn(TRANSITION_DURATION)])
                    if video_clips:
                        # Add fade out to previous clip
                        prev_clip = video_clips[-1]
                        video_clips[-1] = prev_clip.with_effects([vfx.CrossFadeOut(TRANSITION_DURATION)])
                elif i > 0:
                    # Standard crossfade between same types
                    clip = clip.with_effects([vfx.CrossFadeIn(TRANSITION_DURATION_SAME)])

                video_clips.append(clip)
                prev_scene_type = actual_type

            # Concatenate all clips
            print(f"[ASSEMBLER] Combining {len(video_clips)} clips (mixed video/image)")
            if video_clips:
                final_video = concatenate_videoclips(video_clips, method="compose")
                final_video = final_video.with_audio(audio_clip)
                final_video = final_video.with_duration(audio_clip.duration)
            else:
                black_clip = ColorClip(size=TARGET_RESOLUTION, color=(0, 0, 0), duration=audio_clip.duration)
                final_video = black_clip.with_audio(audio_clip)

            # Export with encoding settings
            output_path = self.output_dir / f"{task_id}.mp4"
            encoding = self._get_encoding_params()

            print(f"[ASSEMBLER] Encoding with {encoding['codec']} (GPU: {self.gpu_available})")

            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec=encoding['codec'],
                preset=encoding['preset'],
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                ffmpeg_params=encoding['ffmpeg_params']
            )

            # Cleanup
            final_video.close()
            audio_clip.close()
            for clip in video_clips:
                clip.close()

            return str(output_path)

        except Exception as e:
            raise Exception(f"Error assembling enhanced video: {str(e)}")

    def _create_image_clip(
        self,
        scene: Dict,
        scene_assets: Dict[float, List],
        timestamp: float,
        duration: float
    ) -> ImageClip:
        """
        Create an image clip with Ken Burns effects for standard scenes.

        This method:
        1. Finds the matching image asset
        2. Creates an ImageClip with proper duration
        3. Applies cinematic filter (for images only)
        4. Applies Ken Burns effects (zoom, pan)

        Args:
            scene: Scene dict with effects, mood, etc.
            scene_assets: Dict of timestamp -> asset list
            timestamp: Scene start time
            duration: Scene duration

        Returns:
            Processed ImageClip
        """
        # Find matching asset
        matching_key = None
        for key in scene_assets.keys():
            if abs(key - timestamp) < 0.01:
                matching_key = key
                break

        if matching_key is not None and scene_assets[matching_key]:
            image_asset = scene_assets[matching_key][0]
            image_path = image_asset.image_path

            if os.path.exists(image_path):
                clip = ImageClip(image_path, duration=duration)
                clip = clip.resized(self.target_resolution)

                # Apply cinematic processing for images
                clip = self._apply_cinematic_processing(clip, scene)

                # Apply Ken Burns effects
                clip = self._apply_effects(clip, scene)

                return clip

        # Fallback to placeholder
        return self._create_placeholder_clip(duration, scene)

    def get_video_stats(self, storyboard: List[Dict], video_clips_map: Dict[float, str]) -> Dict:
        """
        Get statistics about the video composition.

        Returns breakdown of:
        - Total scenes
        - Hero scenes (with video)
        - Standard scenes (Ken Burns)
        - Estimated cost

        Args:
            storyboard: Scene list
            video_clips_map: Map of timestamps to video paths

        Returns:
            Stats dict
        """
        total_scenes = len(storyboard)
        hero_scenes = sum(1 for s in storyboard if s.get('scene_type') == 'hero')
        video_scenes = sum(1 for ts in video_clips_map if video_clips_map.get(ts))
        ken_burns_scenes = total_scenes - video_scenes

        # Cost estimates (Luma 1080p = $0.34/clip, image = $0.04)
        video_cost = video_scenes * 0.34
        image_cost = (total_scenes) * 0.04  # All scenes need images
        total_cost = video_cost + image_cost

        return {
            'total_scenes': total_scenes,
            'hero_scenes': hero_scenes,
            'video_scenes_generated': video_scenes,
            'ken_burns_scenes': ken_burns_scenes,
            'estimated_cost': {
                'video_clips': f"${video_cost:.2f}",
                'images': f"${image_cost:.2f}",
                'total': f"${total_cost:.2f}"
            }
        }