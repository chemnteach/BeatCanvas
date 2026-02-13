"""
RunPod Hybrid Video Generator

Orchestrates hybrid WAN 2.6 + SkyReels V2 DF pipeline via RunPod API.
WAN 2.6 generates individual scenes (NSFW-capable), SkyReels V2 DF
stitches them into seamless infinite-length video.

Architecture:
- Laptop sends HTTP requests to RunPod pod endpoint
- RunPod pod has models loaded (WAN + SkyReels in VRAM)
- Pod processes requests and returns results
- No models stored locally (12GB VRAM laptop)
"""

import os
import requests
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RunPodHybridGenerator:
    """
    Hybrid video generator using WAN 2.6 + SkyReels V2 DF via RunPod.

    Workflow:
    1. Generate scenes with WAN 2.6 (via RunPod endpoint)
    2. Stitch scenes with SkyReels V2 DF (via RunPod endpoint)
    3. Download final video to local
    """

    def __init__(self, endpoint_url: Optional[str] = None):
        """
        Initialize RunPod hybrid generator.

        Args:
            endpoint_url: RunPod pod URL (e.g., https://abc123-8000.proxy.runpod.net)
                         If None, reads from RUNPOD_ENDPOINT_URL env var
        """
        self.endpoint_url = endpoint_url or os.getenv('RUNPOD_ENDPOINT_URL')

        if not self.endpoint_url:
            raise ValueError(
                "RUNPOD_ENDPOINT_URL not set. "
                "Set via environment variable or pass to constructor."
            )

        # Remove trailing slash
        self.endpoint_url = self.endpoint_url.rstrip('/')

        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"RunPodHybridGenerator initialized with endpoint: {self.endpoint_url}")

    def generate_video(
        self,
        scenes: List[Dict],
        audio_path: str,
        quality_tier: str = "professional"
    ) -> str:
        """
        Generate complete music video using hybrid WAN + SkyReels pipeline.

        Args:
            scenes: List of scene dicts with 'image_prompt', 'timestamp_start', etc.
            audio_path: Path to audio file
            quality_tier: 'basic' (12 scenes), 'professional' (24), 'cinematic' (48)

        Returns:
            Path to generated video file
        """
        logger.info(f"Starting hybrid video generation: {len(scenes)} scenes, {quality_tier} quality")

        # 1. Upload audio to RunPod (if needed)
        audio_url = self._upload_audio(audio_path)

        # 2. Generate scenes with WAN 2.6
        logger.info("Phase 1: Generating scenes with WAN 2.6...")
        scene_videos = []
        for idx, scene in enumerate(scenes):
            logger.info(f"  Scene {idx+1}/{len(scenes)}: {scene['image_prompt'][:50]}...")
            video_url = self._generate_wan_scene(
                prompt=scene['image_prompt'],
                scene_index=idx,
                audio_segment=audio_url
            )
            scene_videos.append(video_url)

        logger.info(f"Phase 1 complete: {len(scene_videos)} scenes generated")

        # 3. Stitch with SkyReels V2 DF
        logger.info("Phase 2: Stitching with SkyReels V2 DF...")
        final_video_url = self._stitch_skyreels(
            scene_urls=scene_videos,
            audio_url=audio_url
        )

        logger.info("Phase 2 complete: Seamless video stitched")

        # 4. Download final video
        logger.info("Phase 3: Downloading final video...")
        local_path = self._download_video(final_video_url)

        logger.info(f"Video generation complete: {local_path}")
        return local_path

    def _upload_audio(self, audio_path: str) -> str:
        """
        Upload audio file to RunPod.

        Args:
            audio_path: Path to local audio file

        Returns:
            URL to uploaded audio on RunPod
        """
        logger.info(f"Uploading audio: {audio_path}")

        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            response = requests.post(
                f"{self.endpoint_url}/api/upload-audio",
                files=files,
                timeout=300
            )

        response.raise_for_status()
        data = response.json()

        logger.info(f"Audio uploaded: {data['audio_url']}")
        return data['audio_url']

    def _generate_wan_scene(
        self,
        prompt: str,
        scene_index: int,
        audio_segment: Optional[str] = None
    ) -> str:
        """
        Generate single scene with WAN 2.6 via RunPod.

        Args:
            prompt: Scene description prompt
            scene_index: Scene number (for seed variation)
            audio_segment: Optional audio URL for sync

        Returns:
            URL to generated video clip on RunPod
        """
        payload = {
            "prompt": prompt,
            "scene_index": scene_index,
            "audio_segment": audio_segment,
            "resolution": "720p",
            "fps": 24,
            "duration": 5.0  # 5 seconds per scene
        }

        response = requests.post(
            f"{self.endpoint_url}/api/generate-wan",
            json=payload,
            timeout=600  # 10 min timeout for generation
        )

        response.raise_for_status()
        data = response.json()

        return data['video_url']

    def _stitch_skyreels(
        self,
        scene_urls: List[str],
        audio_url: str
    ) -> str:
        """
        Stitch scenes into seamless video using SkyReels V2 DF.

        Args:
            scene_urls: List of RunPod URLs to WAN-generated scene clips
            audio_url: RunPod URL to audio file

        Returns:
            URL to final stitched video on RunPod
        """
        payload = {
            "scene_urls": scene_urls,
            "audio_url": audio_url,
            "method": "diffusion_forcing",  # SkyReels V2 DF
            "output_fps": 24
        }

        response = requests.post(
            f"{self.endpoint_url}/api/stitch-skyreels",
            json=payload,
            timeout=1200  # 20 min timeout for stitching
        )

        response.raise_for_status()
        data = response.json()

        return data['final_video_url']

    def _download_video(self, video_url: str) -> str:
        """
        Download final video from RunPod to local storage.

        Args:
            video_url: RunPod URL to video file

        Returns:
            Path to downloaded video
        """
        # Generate local filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"beatcanvas_{timestamp}.mp4"

        # Download video
        response = requests.get(video_url, stream=True, timeout=600)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Downloaded video: {output_path} ({file_size_mb:.1f} MB)")

        return str(output_path)

    def health_check(self) -> Dict:
        """
        Check RunPod endpoint health and available models.

        Returns:
            Dict with endpoint status and loaded models
        """
        try:
            response = requests.get(
                f"{self.endpoint_url}/api/health",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
