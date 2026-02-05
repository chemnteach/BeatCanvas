"""
Multi-provider image generation for BeatCanvas.

Supports:
- Nano Banana (Google Gemini) - Default, best for consistency and cost
- DALL-E 3 - High quality, good for characters
- NovelAI - Placeholder, not yet implemented

Key improvements (2026-01-27):
- Structured error handling with GenerationResult
- Response validation before accessing nested properties
- Retry logic with exponential backoff for rate limits
- Diagnostic summary after generation completes
- Clear error categorization for debugging
"""

import openai
import requests
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import os
import aiofiles
import uuid
import json
from datetime import datetime

# Import custom exceptions
from src.utils.exceptions import (
    GenerationResult,
    ErrorCode,
    ImageGenerationError,
    RateLimitError,
    ModelNotFoundError,
    AuthenticationError,
    ResponseValidationError,
)

# Try new google-genai library first, fall back to old one
try:
    from google import genai
    from google.genai import types
    GENAI_NEW = True
except ImportError:
    try:
        import google.generativeai as genai_old
        GENAI_NEW = False
    except ImportError:
        GENAI_NEW = None


# Configuration constants (document why these values were chosen)
GEMINI_RATE_LIMIT_DELAY = 6  # seconds between requests (Gemini: 10 req/min limit)
RATE_LIMIT_RECOVERY_WAIT = 45  # seconds to wait after hitting rate limit
MAX_RETRIES = 3  # maximum retry attempts for retryable errors
INITIAL_RETRY_DELAY = 10.0  # seconds before first retry (doubles each attempt)

# Current Gemini model for image generation
# NOTE: Google deprecates models without warning. If you get 404 NOT_FOUND errors,
# check https://ai.google.dev/models for current available models
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-exp-image-generation"


@dataclass
class GeneratedImage:
    scene_timestamp: float
    image_path: str
    provider: str
    prompt: str
    variation_index: int


@dataclass
class ImageMetadata:
    """Metadata for a generated image - saved alongside the image"""
    image_path: str
    prompt: str
    enhanced_prompt: str
    provider: str
    scene_timestamp: float
    variation_index: int
    generated_at: str
    visual_style: str
    section_name: str = ""


@dataclass
class GenerationDiagnostics:
    """Summary of a generation run for debugging"""
    start_time: str
    end_time: str
    total_scenes: int
    successful_scenes: int
    failed_scenes: int
    errors: List[dict]
    provider: str

    @property
    def success_rate(self) -> str:
        if self.total_scenes == 0:
            return "0.0%"
        return f"{(self.successful_scenes / self.total_scenes) * 100:.1f}%"


class MultiProviderImageGenerator:
    def __init__(self):
        self.openai_client = None
        self.novelai_api_key = os.getenv("NOVELAI_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_TOKEN")
        self.gemini_client = None
        self.gemini_available = False

        # Initialize OpenAI if key available
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
            print(f"[GENERATOR] OpenAI/DALL-E initialized")

        # Initialize Gemini if key available (check both key names)
        google_ai_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if google_ai_key and GENAI_NEW is not None:
            try:
                if GENAI_NEW:
                    # New google-genai library
                    self.gemini_client = genai.Client(api_key=google_ai_key)
                    self.gemini_available = True
                    print(f"[GENERATOR] Nano Banana (Gemini) initialized with new SDK")
                    print(f"[GENERATOR] Using model: {GEMINI_IMAGE_MODEL}")
                else:
                    # Old google-generativeai library - limited image support
                    genai_old.configure(api_key=google_ai_key)
                    self.gemini_client = "legacy"
                    print(f"[GENERATOR] Nano Banana (Gemini) initialized with legacy SDK - limited image support")
            except Exception as e:
                print(f"[GENERATOR] ERROR: Failed to initialize Gemini client: {e}")
                print(f"[GENERATOR] Nano Banana will NOT be available")
                self.gemini_client = None
        elif google_ai_key:
            print(f"[GENERATOR] Warning: Gemini API key found but google-genai library not installed")
            print(f"[GENERATOR] Install with: pip install google-genai>=1.0.0")
        else:
            print(f"[GENERATOR] WARNING: No GOOGLE_AI_API_KEY found - Nano Banana DISABLED")
            print(f"[GENERATOR] Set GOOGLE_AI_API_KEY in ~/.claude/.env to enable Nano Banana")

        self.output_dir = Path("data/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metadata directory for storing prompts
        self.metadata_dir = Path("data/generated_images/metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting semaphores
        # DALL-E: 3 concurrent (OpenAI allows ~5/min for images)
        # NovelAI: 5 concurrent (their rate limits are more generous)
        # Gemini: 2 concurrent (10 req/min limit, sequential processing is preferred)
        self.dalle_semaphore = asyncio.Semaphore(3)
        self.novelai_semaphore = asyncio.Semaphore(5)
        self.gemini_semaphore = asyncio.Semaphore(2)

    def _save_metadata(self, metadata: ImageMetadata):
        """Save image metadata to JSON file alongside image"""
        image_name = Path(metadata.image_path).stem
        metadata_path = self.metadata_dir / f"{image_name}.json"

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

        print(f"[GENERATOR] Saved metadata: {metadata_path}")

    def get_metadata(self, image_path: str) -> Optional[ImageMetadata]:
        """Load metadata for an image"""
        image_name = Path(image_path).stem
        metadata_path = self.metadata_dir / f"{image_name}.json"

        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ImageMetadata(**data)
        return None

    async def generate_all_scenes(
        self,
        storyboard: List[Dict],
        provider_preference: str = "auto"
    ) -> Dict[float, List[GeneratedImage]]:
        """
        Generate images for all scenes in the storyboard.

        Returns a dict mapping timestamp -> list of generated images.
        Also prints diagnostic summary at the end.
        """
        start_time = datetime.now()
        scene_assets = {}
        errors = []
        successful = 0
        failed = 0

        # Determine provider and processing mode
        provider = self._select_provider(provider_preference, "", "")
        use_sequential = provider in ["nano_banana", "auto"]  # Gemini has strict rate limits

        print(f"\n[GENERATOR] === Starting Generation ===")
        print(f"[GENERATOR] Scenes: {len(storyboard)}, Provider: {provider}, Mode: {'sequential' if use_sequential else 'concurrent'}")

        if use_sequential:
            # Sequential generation with rate limiting for Gemini
            print(f"[GENERATOR] Using sequential generation (rate limit protection)")
            for i, scene in enumerate(storyboard):
                timestamp = scene['timestamp_start']
                section = scene.get('section', 'Scene')
                print(f"[GENERATOR] Scene {i+1}/{len(storyboard)} ({section}, t={timestamp:.1f}s)")

                result = await self._generate_scene_with_retry(scene, provider_preference)

                if result.success and result.images:
                    scene_assets[timestamp] = result.images
                    successful += 1
                else:
                    scene_assets[timestamp] = []
                    failed += 1
                    errors.append({
                        "scene_index": i,
                        "timestamp": timestamp,
                        "section": section,
                        "error": result.error,
                        "error_code": result.error_code
                    })

                # Rate limit delay BETWEEN scenes (not after last one)
                if i < len(storyboard) - 1:
                    await asyncio.sleep(GEMINI_RATE_LIMIT_DELAY)
        else:
            # Concurrent generation for providers without strict rate limits
            tasks = []
            for scene in storyboard:
                task = self._generate_scene_with_retry(scene, provider_preference)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (scene, result) in enumerate(zip(storyboard, results)):
                timestamp = scene['timestamp_start']
                section = scene.get('section', 'Scene')

                if isinstance(result, Exception):
                    scene_assets[timestamp] = []
                    failed += 1
                    errors.append({
                        "scene_index": i,
                        "timestamp": timestamp,
                        "section": section,
                        "error": str(result),
                        "error_code": "EXCEPTION"
                    })
                elif result.success and result.images:
                    scene_assets[timestamp] = result.images
                    successful += 1
                else:
                    scene_assets[timestamp] = []
                    failed += 1
                    errors.append({
                        "scene_index": i,
                        "timestamp": timestamp,
                        "section": section,
                        "error": result.error,
                        "error_code": result.error_code
                    })

        # Print diagnostic summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n[GENERATOR] === Generation Summary ===")
        print(f"[GENERATOR] Total: {len(storyboard)}, Success: {successful}, Failed: {failed}")
        print(f"[GENERATOR] Success Rate: {(successful/len(storyboard))*100:.1f}%")
        print(f"[GENERATOR] Duration: {duration:.1f}s ({duration/len(storyboard):.1f}s per scene)")

        if errors:
            print(f"[GENERATOR] Failed scenes:")
            for err in errors:
                print(f"[GENERATOR]   - Scene {err['scene_index']+1} ({err['section']}): {err['error_code']}")

        print(f"[GENERATOR] ===========================\n")

        return scene_assets

    async def _generate_scene_with_retry(
        self,
        scene: Dict,
        provider_preference: str,
        max_retries: int = MAX_RETRIES
    ) -> GenerationResult:
        """
        Generate images for a scene with automatic retry for transient failures.

        Uses exponential backoff: 10s, 20s, 40s between retries.
        Only retries for retryable errors (rate limits, temporary failures).
        """
        timestamp = scene['timestamp_start']
        delay = INITIAL_RETRY_DELAY
        last_result = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"[GENERATOR] Retry {attempt}/{max_retries} for scene {timestamp:.1f} (waiting {delay:.0f}s)")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

            result = await self._generate_scene_images(scene, provider_preference)
            last_result = result

            if result.success:
                if attempt > 0:
                    print(f"[GENERATOR] Retry succeeded for scene {timestamp:.1f}")
                return result

            if not result.retryable:
                print(f"[GENERATOR] Non-retryable error for scene {timestamp:.1f}: {result.error_code}")
                break

        return last_result or GenerationResult.fail(
            "Max retries exceeded",
            ErrorCode.MAX_RETRIES_EXCEEDED,
            retryable=False,
            scene_timestamp=timestamp
        )

    async def _generate_scene_images(self, scene: Dict, provider_preference: str) -> GenerationResult:
        """Generate image for a single scene, returning structured result."""
        timestamp = scene['timestamp_start']
        # Support both 'image_prompt' and 'description' field names for flexibility
        image_prompt = scene.get('image_prompt') or scene.get('description') or scene.get('prompt', '')
        visual_style = scene.get('visual_style', 'cinematic')
        section_name = scene.get('section', 'Scene')

        # Select provider based on preference and content
        provider = self._select_provider(provider_preference, visual_style, image_prompt)

        # Try primary provider
        result = await self._try_provider(provider, timestamp, image_prompt, visual_style, section_name)

        # If primary failed and not fatal, try fallback providers
        if not result.success and result.retryable:
            fallback_providers = self._get_fallback_providers(provider)
            for fallback in fallback_providers:
                print(f"[GENERATOR] Trying fallback provider: {fallback}")
                result = await self._try_provider(fallback, timestamp, image_prompt, visual_style, section_name)
                if result.success:
                    break

        return result

    def _get_fallback_providers(self, primary: str) -> List[str]:
        """Get ordered list of fallback providers if primary fails."""
        all_providers = []
        if self.gemini_client and self.gemini_available:
            all_providers.append("nano_banana")
        if self.openai_client:
            all_providers.append("dalle")
        if self.novelai_api_key:
            all_providers.append("novelai")

        # Remove primary and return rest as fallbacks
        return [p for p in all_providers if p != primary]

    async def _try_provider(
        self,
        provider: str,
        timestamp: float,
        prompt: str,
        style: str,
        section_name: str
    ) -> GenerationResult:
        """Try generating with a specific provider."""
        if provider == "dalle" and self.openai_client:
            return await self._generate_dalle_images(timestamp, prompt, style, section_name)
        elif provider == "novelai" and self.novelai_api_key:
            return await self._generate_novelai_images(timestamp, prompt, style, section_name)
        elif provider == "nano_banana" and self.gemini_client:
            return await self._generate_nano_banana_images(timestamp, prompt, style, section_name)
        else:
            return GenerationResult.fail(
                f"Provider {provider} not available",
                ErrorCode.PROVIDER_UNAVAILABLE,
                scene_timestamp=timestamp,
                provider=provider
            )

    def _select_provider(self, preference: str, visual_style: str, prompt: str) -> str:
        """Smart provider selection based on content and preference"""
        if preference in ["dalle", "novelai", "nano_banana", "both"]:
            return preference

        # Auto-selection based on content
        style_lower = visual_style.lower()
        prompt_lower = prompt.lower()
        combined_text = f"{style_lower} {prompt_lower}"

        anime_keywords = ["anime", "manga", "cartoon", "stylized", "artistic", "fantasy", "magical", "illustrated"]
        character_keywords = ["character", "person", "people", "dancer", "performer", "figure", "human", "face", "portrait"]

        anime_score = sum(1 for keyword in anime_keywords if keyword in combined_text)
        character_score = sum(1 for keyword in character_keywords if keyword in combined_text)

        # Default to Nano Banana for consistency + cost benefits
        if self.gemini_client and self.gemini_available:
            if anime_score > 2 and self.novelai_api_key:
                return "novelai"
            return "nano_banana"

        # Fallbacks only if Nano Banana unavailable
        if character_score > 0 and self.openai_client:
            return "dalle"
        if self.openai_client:
            return "dalle"
        if self.novelai_api_key:
            return "novelai"
        return "dalle"

    async def _generate_dalle_images(
        self,
        timestamp: float,
        prompt: str,
        style: str,
        section_name: str = ""
    ) -> GenerationResult:
        """Generate images using DALL-E 3"""
        if not self.openai_client:
            return GenerationResult.fail(
                "OpenAI client not initialized",
                ErrorCode.PROVIDER_UNAVAILABLE,
                provider="dalle",
                scene_timestamp=timestamp
            )

        images = []
        enhanced_prompt = self._enhance_dalle_prompt(prompt, style)

        async with self.dalle_semaphore:
            for variation in range(2):  # 2 variations
                try:
                    response = self.openai_client.images.generate(
                        model="dall-e-3",
                        prompt=enhanced_prompt,
                        size="1792x1024",
                        quality="hd",
                        n=1
                    )

                    image_url = response.data[0].url
                    filename = f"scene_{timestamp:.1f}_dalle_var_{variation}_{uuid.uuid4().hex[:8]}.png"
                    filepath = self.output_dir / filename

                    async with aiofiles.open(filepath, 'wb') as f:
                        image_data = requests.get(image_url).content
                        await f.write(image_data)

                    metadata = ImageMetadata(
                        image_path=str(filepath),
                        prompt=prompt,
                        enhanced_prompt=enhanced_prompt,
                        provider="dalle",
                        scene_timestamp=timestamp,
                        variation_index=variation,
                        generated_at=datetime.now().isoformat(),
                        visual_style=style,
                        section_name=section_name
                    )
                    self._save_metadata(metadata)

                    images.append(GeneratedImage(
                        scene_timestamp=timestamp,
                        image_path=str(filepath),
                        provider="dalle",
                        prompt=enhanced_prompt,
                        variation_index=variation
                    ))

                    await asyncio.sleep(1)

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate" in error_str.lower():
                        return GenerationResult.fail(
                            f"DALL-E rate limit: {error_str}",
                            ErrorCode.RATE_LIMIT,
                            retryable=True,
                            provider="dalle",
                            scene_timestamp=timestamp
                        )
                    print(f"[GENERATOR] DALL-E error for scene {timestamp}: {e}")

        if images:
            return GenerationResult.ok(images, provider="dalle", scene_timestamp=timestamp)
        return GenerationResult.fail(
            "No DALL-E images generated",
            ErrorCode.UNKNOWN_ERROR,
            provider="dalle",
            scene_timestamp=timestamp
        )

    async def _generate_novelai_images(
        self,
        timestamp: float,
        prompt: str,
        style: str,
        section_name: str = ""
    ) -> GenerationResult:
        """Generate images using NovelAI - NOT YET IMPLEMENTED"""
        print(f"[GENERATOR] NovelAI generation not yet implemented for scene {timestamp}")
        return GenerationResult.fail(
            "NovelAI not implemented",
            ErrorCode.PROVIDER_UNAVAILABLE,
            provider="novelai",
            scene_timestamp=timestamp
        )

    async def _generate_nano_banana_images(
        self,
        timestamp: float,
        prompt: str,
        style: str,
        section_name: str = ""
    ) -> GenerationResult:
        """
        Generate images using Nano Banana (Gemini Image Generation).

        Returns GenerationResult with explicit success/error information.
        """
        if not self.gemini_client:
            return GenerationResult.fail(
                "Gemini client not initialized - check GOOGLE_AI_API_KEY",
                ErrorCode.PROVIDER_UNAVAILABLE,
                provider="nano_banana",
                scene_timestamp=timestamp
            )

        if not self.gemini_available:
            return GenerationResult.fail(
                "Gemini using legacy SDK - image generation not supported",
                ErrorCode.PROVIDER_UNAVAILABLE,
                provider="nano_banana",
                scene_timestamp=timestamp
            )

        images = []
        enhanced_prompt = self._enhance_nano_banana_prompt(prompt, style)

        async with self.gemini_semaphore:
            try:
                print(f"[GENERATOR] Generating Nano Banana image for scene {timestamp:.1f}")

                # Call Gemini API
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.gemini_client.models.generate_content(
                        model=GEMINI_IMAGE_MODEL,
                        contents=enhanced_prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["TEXT", "IMAGE"],
                        )
                    )
                )

                # VALIDATION: Check response structure before accessing
                if not response:
                    return GenerationResult.fail(
                        "Empty response from Gemini API",
                        ErrorCode.EMPTY_RESPONSE,
                        retryable=True,
                        provider="nano_banana",
                        scene_timestamp=timestamp
                    )

                if not hasattr(response, 'candidates') or not response.candidates:
                    return GenerationResult.fail(
                        "No candidates in Gemini response",
                        ErrorCode.NO_CANDIDATES,
                        retryable=True,
                        provider="nano_banana",
                        scene_timestamp=timestamp
                    )

                candidate = response.candidates[0]
                if not hasattr(candidate, 'content') or not candidate.content:
                    return GenerationResult.fail(
                        "No content in Gemini response candidate",
                        ErrorCode.NO_CONTENT,
                        retryable=True,
                        provider="nano_banana",
                        scene_timestamp=timestamp
                    )

                if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                    return GenerationResult.fail(
                        "No parts in Gemini response content",
                        ErrorCode.NO_CONTENT,
                        retryable=True,
                        provider="nano_banana",
                        scene_timestamp=timestamp
                    )

                # Process response parts
                image_saved = False
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        filename = f"scene_{timestamp:.1f}_nano_banana_var_0_{uuid.uuid4().hex[:8]}.png"
                        filepath = self.output_dir / filename

                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(part.inline_data.data)

                        if filepath.stat().st_size > 0:
                            metadata = ImageMetadata(
                                image_path=str(filepath),
                                prompt=prompt,
                                enhanced_prompt=enhanced_prompt,
                                provider="nano_banana",
                                scene_timestamp=timestamp,
                                variation_index=0,
                                generated_at=datetime.now().isoformat(),
                                visual_style=style,
                                section_name=section_name
                            )
                            self._save_metadata(metadata)

                            images.append(GeneratedImage(
                                scene_timestamp=timestamp,
                                image_path=str(filepath),
                                provider="nano_banana",
                                prompt=enhanced_prompt,
                                variation_index=0
                            ))
                            image_saved = True
                            print(f"[GENERATOR] Saved Nano Banana image: {filepath} ({filepath.stat().st_size} bytes)")
                        else:
                            print(f"[GENERATOR] Warning: Image file is empty: {filepath}")
                            try:
                                filepath.unlink()  # Delete empty file
                            except:
                                pass
                        break
                    elif hasattr(part, 'text') and part.text:
                        print(f"[GENERATOR] Gemini text response: {part.text[:200]}...")

                if not image_saved:
                    return GenerationResult.fail(
                        "No image data in Gemini response",
                        ErrorCode.NO_IMAGE_DATA,
                        retryable=True,
                        provider="nano_banana",
                        scene_timestamp=timestamp
                    )

                return GenerationResult.ok(images, provider="nano_banana", scene_timestamp=timestamp)

            except Exception as e:
                error_str = str(e)
                error_code = ErrorCode.UNKNOWN_ERROR
                retryable = False

                # Categorize error for proper handling
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    error_code = ErrorCode.RATE_LIMIT
                    retryable = True
                    print(f"[GENERATOR] Rate limited - will retry after backoff")
                elif "404" in error_str or "NOT_FOUND" in error_str:
                    error_code = ErrorCode.MODEL_NOT_FOUND
                    print(f"[GENERATOR] ERROR: Model '{GEMINI_IMAGE_MODEL}' not found - may be deprecated")
                    print(f"[GENERATOR] Check https://ai.google.dev/models for current models")
                elif "INVALID_ARGUMENT" in error_str:
                    error_code = ErrorCode.INVALID_PROMPT
                    print(f"[GENERATOR] ERROR: Prompt rejected by Gemini")
                elif "PERMISSION_DENIED" in error_str or "401" in error_str:
                    error_code = ErrorCode.AUTH_ERROR
                    print(f"[GENERATOR] ERROR: API key invalid or lacks permission")

                print(f"[GENERATOR] Error ({error_code.value}) generating Nano Banana image: {e}")

                return GenerationResult.fail(
                    error_str,
                    error_code,
                    retryable=retryable,
                    provider="nano_banana",
                    scene_timestamp=timestamp
                )

    def _enhance_dalle_prompt(self, base_prompt: str, style: str) -> str:
        """Enhance prompt specifically for DALL-E 3"""
        return f"""
        {base_prompt}

        Style: {style}, photorealistic, professional photography quality
        Lighting: Cinematic, well-lit, professional
        Quality: High-resolution, sharp details, 16:9 widescreen format
        Camera: Professional video production quality, film-like
        Composition: Cinematic framing, rule of thirds, engaging perspective
        """

    def _enhance_novelai_prompt(self, base_prompt: str, style: str) -> str:
        """Enhance prompt specifically for NovelAI"""
        return f"""
        {base_prompt}

        Style: {style}, high-quality illustration, detailed artwork
        Quality: Professional digital art, consistent character design
        Composition: Cinematic framing, dynamic composition, expressive
        Art style: Clean lines, vibrant colors, detailed background
        """

    def _enhance_nano_banana_prompt(self, base_prompt: str, style: str) -> str:
        """Enhance prompt specifically for Nano Banana (Gemini)"""
        return f"""Generate a high-quality cinematic image:

{base_prompt}

Style: {style}
Aspect ratio: 16:9 widescreen
Quality: Professional, high resolution, detailed
Composition: Cinematic framing, engaging perspective
Lighting: Professional, atmospheric

Create this as a single photorealistic or artistic image suitable for a music video scene."""

    async def regenerate_scene_image(
        self,
        timestamp: float,
        new_prompt: str,
        provider: str = "nano_banana"
    ) -> List[GeneratedImage]:
        """Regenerate images for a specific scene"""
        result = await self._try_provider(provider, timestamp, new_prompt, "cinematic", "Regenerated")

        if result.success:
            return result.images
        else:
            print(f"[GENERATOR] Regeneration failed: {result.error}")
            return []

    def get_image_url(self, image: GeneratedImage) -> str:
        """Get URL for serving generated image"""
        relative_path = Path(image.image_path).name
        return f"/generated/{relative_path}"
