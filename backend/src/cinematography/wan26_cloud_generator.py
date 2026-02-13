"""
WAN 2.6 Cloud Video Generator

Generates live-action video clips using Alibaba's WAN 2.6 model.
Supports both Replicate API (cloud) and RunPod endpoints (self-hosted).

Features native audio synchronization, 1080p output, and multi-shot storytelling.

Model: wan-video/wan-2.6-i2v
Architecture: DiT (Diffusion Transformer) - 14B active parameters
Output: 1080p @ 24fps, up to 15 seconds per clip
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional
import requests
import cv2

logger = logging.getLogger(__name__)


class WAN26CloudGenerator:
    """
    WAN 2.6 video generation via Replicate API or RunPod endpoint.

    Features:
    - Native music synchronization (audio-visual alignment)
    - Professional 1080p @ 24fps output
    - Multi-shot storytelling capabilities
    - Zero local VRAM usage (cloud-based)

    Modes:
    - Replicate API: Set REPLICATE_API_TOKEN
    - RunPod endpoint: Set RUNPOD_ENDPOINT_URL
    """

    def __init__(self, heartbeat_callback=None, enable_audio_sync=True):
        """
        Initialize WAN 2.6 cloud generator.

        Args:
            heartbeat_callback: Optional callback for progress updates
            enable_audio_sync: Enable audio-visual synchronization (default: True)
        """
        self.heartbeat_callback = heartbeat_callback
        self.enable_audio_sync = enable_audio_sync

        # Check for RunPod endpoint first (priority over Replicate)
        self.runpod_endpoint = os.getenv('RUNPOD_ENDPOINT_URL')
        self.use_runpod = bool(self.runpod_endpoint)

        if self.use_runpod:
            # RunPod mode: HTTP requests to self-hosted endpoint
            logger.info(f"Using RunPod endpoint: {self.runpod_endpoint}")
            self.replicate_client = None
        else:
            # Replicate mode: Cloud API
            try:
                import replicate
                api_token = os.getenv('REPLICATE_API_TOKEN')
                if not api_token:
                    raise ValueError("REPLICATE_API_TOKEN not found in environment")
                self.replicate_client = replicate.Client(api_token=api_token)
                logger.info("Using Replicate API")
            except ImportError:
                raise ImportError("replicate package required. Install with: pip install replicate")

        # Lazy-loaded image generator
        self.image_generator = None

        # Output directory
        self.output_dir = Path("data/generated_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("WAN26CloudGenerator initialized (mode=%s, audio_sync=%s)",
                    "RunPod" if self.use_runpod else "Replicate", enable_audio_sync)

    def generate_scene(
        self,
        scene: Dict,
        scene_index: int,
        total_scenes: int,
        audio_segment: Optional[str] = None
    ) -> Dict:
        """
        Generate video for a single scene using WAN 2.6 I2V.

        Args:
            scene: Scene dict with 'image_prompt', 'timestamp_start', 'timestamp_end'
            scene_index: Index of this scene (for naming)
            total_scenes: Total number of scenes in storyboard
            audio_segment: Optional path to audio segment for sync

        Returns:
            {
                'video_path': str,
                'duration': float,
                'fps': int,
                'frame_count': int,
                'generation_time': float,
                'method': 'wan26_cloud',
                'resolution': str
            }
        """
        start_time = time.time()

        try:
            # 1. Generate anchor image
            logger.info(f"[Scene {scene_index}/{total_scenes}] Generating anchor image...")
            anchor_path = self._generate_anchor_image(scene)

            # 2. Call Replicate API
            logger.info(f"[Scene {scene_index}/{total_scenes}] Calling WAN 2.6 API...")
            video_url = self._call_replicate_api(anchor_path, scene, audio_segment)

            # 3. Download video
            logger.info(f"[Scene {scene_index}/{total_scenes}] Downloading video...")
            output_path = self._download_video(video_url, scene_index)

            # 4. Extract metadata
            metadata = self._extract_video_metadata(output_path)

            generation_time = time.time() - start_time
            logger.info(
                f"[Scene {scene_index}/{total_scenes}] Complete! "
                f"{metadata['duration']:.1f}s @ {metadata['fps']}fps "
                f"({generation_time:.1f}s generation)"
            )

            return {
                'video_path': output_path,
                'duration': metadata['duration'],
                'fps': metadata['fps'],
                'frame_count': metadata['frame_count'],
                'generation_time': generation_time,
                'method': 'wan26_cloud',
                'resolution': '1080p'
            }

        except Exception as e:
            logger.error(f"[Scene {scene_index}] Generation failed: {e}")
            raise

    def _generate_anchor_image(self, scene: Dict) -> str:
        """
        Generate high-quality anchor image using existing Gemini/DALL-E generators.

        Args:
            scene: Scene dict with 'image_prompt'

        Returns:
            Path to generated anchor image
        """
        if not self.image_generator:
            from src.assets.generator import MultiProviderImageGenerator
            self.image_generator = MultiProviderImageGenerator()

        # Use Gemini (Nano Banana) for fast, free anchor images
        # Falls back to DALL-E if Gemini unavailable
        try:
            result = self.image_generator._generate_nano_banana_images(
                prompts=[scene['image_prompt']],
                num_images=1
            )
            return result[0]  # Path to anchor image
        except Exception as e:
            logger.warning(f"Gemini failed, falling back to DALL-E: {e}")
            result = self.image_generator._generate_dalle_images(
                prompts=[scene['image_prompt']],
                num_images=1
            )
            return result[0]

    def _call_replicate_api(
        self,
        image_path: str,
        scene: Dict,
        audio_segment: Optional[str] = None
    ) -> str:
        """
        Call WAN 2.6 I2V API (Replicate or RunPod) with audio sync.

        Args:
            image_path: Path to anchor image
            scene: Scene dict with prompt and timing info
            audio_segment: Optional audio file for synchronization

        Returns:
            URL to generated video
        """
        # Calculate scene duration (max 15s per WAN 2.6 spec)
        duration = min(
            scene['timestamp_end'] - scene['timestamp_start'],
            15.0
        )

        if self.use_runpod:
            # RunPod endpoint mode: HTTP POST
            return self._call_runpod_endpoint(image_path, scene, audio_segment, duration)
        else:
            # Replicate mode: Cloud API
            return self._call_replicate_cloud(image_path, scene, audio_segment, duration)

    def _call_replicate_cloud(
        self,
        image_path: str,
        scene: Dict,
        audio_segment: Optional[str],
        duration: float
    ) -> str:
        """Call Replicate cloud API."""
        inputs = {
            "image": open(image_path, "rb"),
            "prompt": scene['image_prompt'],
            "cfg_scale": 1.5,  # Low CFG per CivitAI research
            "num_inference_steps": 10,
            "fps": 24,  # WAN 2.6 default
            "resolution": "1080p",
            "duration": duration,
        }

        # Add audio sync if enabled and audio provided
        if self.enable_audio_sync and audio_segment and os.path.exists(audio_segment):
            inputs["audio"] = open(audio_segment, "rb")
            inputs["sync_mode"] = "beat"  # Sync to audio beats
            logger.info(f"Audio sync enabled with segment: {audio_segment}")

        # Call Replicate API
        output = self.replicate_client.run(
            "wan-video/wan-2.6-i2v",
            input=inputs
        )

        # Output can be a URL string or list of URLs
        if isinstance(output, list):
            return output[0]
        return output

    def _call_runpod_endpoint(
        self,
        image_path: str,
        scene: Dict,
        audio_segment: Optional[str],
        duration: float
    ) -> str:
        """Call RunPod self-hosted endpoint."""
        # Upload image and audio to RunPod
        files = {'image': open(image_path, 'rb')}
        if self.enable_audio_sync and audio_segment and os.path.exists(audio_segment):
            files['audio'] = open(audio_segment, 'rb')

        data = {
            'prompt': scene['image_prompt'],
            'cfg_scale': 1.5,
            'num_inference_steps': 10,
            'fps': 24,
            'resolution': '1080p',
            'duration': duration,
            'sync_mode': 'beat' if audio_segment else 'none'
        }

        # POST to RunPod endpoint
        response = requests.post(
            f"{self.runpod_endpoint}/api/generate-wan",
            files=files,
            data=data,
            timeout=600  # 10 min timeout for generation
        )

        response.raise_for_status()
        result = response.json()

        return result['video_url']

    def _download_video(self, url: str, scene_index: int) -> str:
        """
        Download video from Replicate to local storage.

        Args:
            url: Replicate video URL
            scene_index: Scene index for naming

        Returns:
            Path to downloaded video file
        """
        output_path = str(self.output_dir / f"scene_{scene_index:04d}_wan26.mp4")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    def _extract_video_metadata(self, video_path: str) -> Dict:
        """
        Extract duration, fps, frame count from video file using OpenCV.

        Args:
            video_path: Path to video file

        Returns:
            Dict with 'duration', 'fps', 'frame_count'
        """
        cap = cv2.VideoCapture(video_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()

        return {
            'duration': duration,
            'fps': int(fps),
            'frame_count': frame_count
        }

    def cleanup(self):
        """
        Cleanup resources (no-op for cloud API - no local models to unload).
        """
        logger.info("WAN26CloudGenerator cleanup (no local resources)")
        pass
