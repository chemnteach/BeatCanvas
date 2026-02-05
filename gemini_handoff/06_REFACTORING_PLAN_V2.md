# BeatCanvas Local Pipeline Refactoring Plan V2

**Objective:** Replace cloud API architecture (Luma/Gemini) with local GPU execution using Flux.1-schnell (Uncensored) and LTX-Video, with robust compliance safety layer.

**Target Hardware:** NVIDIA GPU with 16GB VRAM

---

## 1. API Calls to Remove

### Image Generation (`backend/src/assets/generator.py`)

| Function | Lines | API | Action |
|----------|-------|-----|--------|
| `_generate_nano_banana_images()` | 519-687 | Gemini `generate_content()` | **REMOVE** |
| `_generate_dalle_images()` | 421-501 | OpenAI `images.generate()` | **REMOVE** |
| `_generate_novelai_images()` | 503-517 | NovelAI (stub) | **REMOVE** |
| `_enhance_nano_banana_prompt()` | 712-724 | - | **REMOVE** |
| `_enhance_dalle_prompt()` | 689-699 | - | **REMOVE** |
| Gemini client init | 120-144 | `genai.Client()` | **REMOVE** |
| OpenAI client init | 114-118 | `openai.OpenAI()` | **REMOVE** |

### Video Generation (`backend/src/assets/video_generator.py`)

| Function | Lines | API | Action |
|----------|-------|-----|--------|
| `LumaVideoGenerator._generate_clip()` | 140-194 | Luma `generations.create()` | **REMOVE** |
| `ReplicateVideoGenerator` | 267-288 | Replicate API | **REMOVE** |
| Luma client init | 70-89 | `LumaAI()` | **REMOVE** |

---

## 2. New Module Structure

```
backend/
├── src/
│   ├── local/                          # NEW: Local generation module
│   │   ├── __init__.py
│   │   ├── image_generator.py          # LocalImageGenerator (Flux)
│   │   ├── video_generator.py          # LocalVideoGenerator (LTX)
│   │   └── lora_manager.py             # LoRA style management
│   │
│   ├── safety/                         # NEW: Compliance module
│   │   ├── __init__.py
│   │   ├── compliance_gate.py          # ComplianceGate class
│   │   └── age_classifier.py           # ViT-Age-Classifier wrapper
│   │
│   └── policies/                       # NEW: Policy configurations
│       ├── rapper_explicit.json
│       ├── eu_standard.json
│       ├── offline_explicit.json       # Admin-only relaxed policy
│       └── safe_default.json
│
├── scripts/
│   └── admin_generate_offline.py       # NEW: Standalone admin script
│
└── models/                             # NEW: Local model storage
    ├── flux1-schnell-uncensored.gguf
    └── loras/
        ├── gritty_urban.safetensors
        └── realistic_euro.safetensors
```

---

## 3. Class Implementations

### 3.1 LocalImageGenerator

**File:** `backend/src/local/image_generator.py`

```python
"""
Local GPU image generation using Flux.1-schnell (Uncensored).
Replaces MultiProviderImageGenerator for offline operation.

Key Features:
- GGUF checkpoint loading for uncensored generation
- Dynamic LoRA injection for style switching
- Memory-managed with explicit load/unload
"""

import gc
import torch
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from PIL import Image
import uuid
from datetime import datetime


@dataclass
class GeneratedImage:
    """Result of image generation"""
    section_name: str
    image_path: str
    prompt: str
    style_lora: Optional[str] = None
    seed: Optional[int] = None
    timestamp: float = 0.0


@dataclass
class LoRAConfig:
    """LoRA configuration for style injection"""
    name: str
    path: str
    weight: float = 0.8
    trigger_words: List[str] = field(default_factory=list)


class LocalImageGenerator:
    """
    Flux.1-schnell image generator for local GPU execution.

    Architectural Changes from Cloud API:
    - No API calls, no rate limits, no costs
    - Single provider (Flux), no fallback chain needed
    - LoRA injection for style switching (Gritty vs Realistic)
    - Uses uncensored checkpoint for diverse client requirements
    """

    # Default model paths
    DEFAULT_MODEL_PATH = "models/flux1-schnell-uncensored.gguf"
    LORA_DIR = Path("models/loras")

    # Generation settings
    IMAGE_WIDTH = 1024
    IMAGE_HEIGHT = 576  # 16:9 aspect ratio
    NUM_STEPS = 4       # Schnell is optimized for 4 steps
    GUIDANCE_SCALE = 0.0  # Must be 0 for schnell

    def __init__(
        self,
        model_path: str = None,
        output_dir: str = "data/generated_images"
    ):
        """
        Initialize the local image generator.

        Args:
            model_path: Path to flux1-schnell-uncensored.gguf
                       If None, uses DEFAULT_MODEL_PATH
            output_dir: Directory to save generated images
        """
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Pipeline state (lazy loaded)
        self.pipe = None
        self.current_lora: Optional[LoRAConfig] = None

        # Available LoRA styles
        self.available_loras: Dict[str, LoRAConfig] = {}
        self._scan_loras()

    def _scan_loras(self):
        """Scan for available LoRA files"""
        if not self.LORA_DIR.exists():
            self.LORA_DIR.mkdir(parents=True, exist_ok=True)
            return

        for lora_file in self.LORA_DIR.glob("*.safetensors"):
            name = lora_file.stem
            self.available_loras[name] = LoRAConfig(
                name=name,
                path=str(lora_file),
                weight=0.8
            )
            print(f"[LOCAL] Found LoRA: {name}")

    def _load_model(self):
        """Load Flux pipeline (lazy initialization)"""
        if self.pipe is not None:
            return

        from diffusers import FluxPipeline

        print(f"[LOCAL] Loading Flux.1-schnell from {self.model_path}...")

        model_path = Path(self.model_path)

        if model_path.suffix == ".gguf":
            # Load from GGUF checkpoint
            self.pipe = FluxPipeline.from_single_file(
                str(model_path),
                torch_dtype=torch.bfloat16
            )
        else:
            # Load from HuggingFace or local directory
            self.pipe = FluxPipeline.from_pretrained(
                str(model_path),
                torch_dtype=torch.bfloat16
            )

        self.pipe.enable_model_cpu_offload()
        print("[LOCAL] Flux.1-schnell loaded successfully")

    def unload_model(self):
        """Release GPU memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.current_lora = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            print("[LOCAL] Flux unloaded, GPU memory cleared")

    def load_style_lora(self, style_name: str, weight: float = 0.8) -> bool:
        """
        Load a style LoRA for dynamic style switching.

        Args:
            style_name: Name of the LoRA (e.g., "gritty_urban", "realistic_euro")
            weight: LoRA weight (0.0-1.0), default 0.8

        Returns:
            True if LoRA loaded successfully, False otherwise

        Usage:
            generator.load_style_lora("gritty_urban")  # For rapper content
            generator.load_style_lora("realistic_euro")  # For European content
        """
        if style_name not in self.available_loras:
            print(f"[LOCAL] Warning: LoRA '{style_name}' not found")
            print(f"[LOCAL] Available: {list(self.available_loras.keys())}")
            return False

        self._load_model()  # Ensure model is loaded

        lora_config = self.available_loras[style_name]
        lora_config.weight = weight

        try:
            # Load LoRA weights into pipeline
            self.pipe.load_lora_weights(
                lora_config.path,
                adapter_name=style_name
            )
            self.pipe.set_adapters([style_name], adapter_weights=[weight])

            self.current_lora = lora_config
            print(f"[LOCAL] Loaded LoRA: {style_name} (weight={weight})")
            return True

        except Exception as e:
            print(f"[LOCAL] Error loading LoRA: {e}")
            return False

    def unload_lora(self):
        """Unload current LoRA"""
        if self.pipe is not None and self.current_lora is not None:
            try:
                self.pipe.unload_lora_weights()
                print(f"[LOCAL] Unloaded LoRA: {self.current_lora.name}")
            except:
                pass
            self.current_lora = None

    async def generate_anchor_image(
        self,
        section_name: str,
        prompt: str,
        style: str = "cinematic",
        seed: Optional[int] = None
    ) -> Optional[GeneratedImage]:
        """
        Generate ONE anchor image for a song section.

        This anchor image will be used for all video loops in this section,
        ensuring character and scene consistency.

        Args:
            section_name: Section identifier (e.g., "intro", "verse_1", "chorus_1")
            prompt: Visual description from storyboard
            style: Style descriptor for prompt enhancement
            seed: Optional seed for reproducibility

        Returns:
            GeneratedImage with path to saved file, or None on failure
        """
        self._load_model()

        # Enhance prompt with style and quality modifiers
        enhanced_prompt = self._enhance_prompt(prompt, style)

        # Add LoRA trigger words if active
        if self.current_lora and self.current_lora.trigger_words:
            triggers = ", ".join(self.current_lora.trigger_words)
            enhanced_prompt = f"{triggers}, {enhanced_prompt}"

        # Setup generator for reproducibility
        generator = None
        if seed is not None:
            generator = torch.Generator("cpu").manual_seed(seed)
        else:
            seed = torch.randint(0, 2**32, (1,)).item()
            generator = torch.Generator("cpu").manual_seed(seed)

        print(f"[LOCAL] Generating anchor for '{section_name}' (seed={seed})...")

        try:
            result = self.pipe(
                prompt=enhanced_prompt,
                height=self.IMAGE_HEIGHT,
                width=self.IMAGE_WIDTH,
                num_inference_steps=self.NUM_STEPS,
                guidance_scale=self.GUIDANCE_SCALE,
                max_sequence_length=256,
                generator=generator
            )

            image = result.images[0]

            # Save image with descriptive filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anchor_{section_name}_{timestamp}_{seed}.png"
            filepath = self.output_dir / filename
            image.save(filepath, quality=95)

            print(f"[LOCAL] Saved: {filepath}")

            return GeneratedImage(
                section_name=section_name,
                image_path=str(filepath),
                prompt=enhanced_prompt,
                style_lora=self.current_lora.name if self.current_lora else None,
                seed=seed
            )

        except Exception as e:
            print(f"[LOCAL] Error generating image: {e}")
            return None

    async def generate_all_sections(
        self,
        song_structure: Dict,
        style_lora: Optional[str] = None
    ) -> Dict[str, GeneratedImage]:
        """
        Generate anchor images for all song sections.

        Args:
            song_structure: {
                "sections": [
                    {"name": "intro", "start": 0.0, "end": 15.0, "prompt": "..."},
                    {"name": "verse_1", "start": 15.0, "end": 45.0, "prompt": "..."},
                    {"name": "chorus_1", "start": 45.0, "end": 75.0, "prompt": "..."},
                    ...
                ]
            }
            style_lora: Optional LoRA style to apply (e.g., "gritty_urban")

        Returns:
            Dict mapping section_name -> GeneratedImage
        """
        # Load style LoRA if specified
        if style_lora:
            self.load_style_lora(style_lora)

        anchors = {}
        total = len(song_structure.get("sections", []))

        print(f"\n[LOCAL] === Generating {total} Anchor Images ===")

        for i, section in enumerate(song_structure["sections"]):
            name = section["name"]
            prompt = section.get("prompt") or section.get("image_prompt", "")
            style = section.get("style", "cinematic")

            print(f"[LOCAL] [{i+1}/{total}] Section: {name}")

            anchor = await self.generate_anchor_image(
                section_name=name,
                prompt=prompt,
                style=style
            )

            if anchor:
                anchor.timestamp = section["start"]
                anchors[name] = anchor
            else:
                print(f"[LOCAL] Warning: Failed to generate anchor for {name}")

        print(f"[LOCAL] === Generated {len(anchors)}/{total} anchors ===\n")

        return anchors

    def _enhance_prompt(self, base_prompt: str, style: str) -> str:
        """Enhance prompt with quality and style modifiers"""
        return f"""{base_prompt}

Style: {style}, photorealistic, professional cinematography
Quality: Ultra high resolution, sharp details, 16:9 widescreen cinematic
Lighting: Professional cinematic lighting, atmospheric, volumetric
Composition: Rule of thirds, dynamic framing, engaging perspective
Technical: 8K, HDR, film grain, shallow depth of field"""


# Convenience function for quick generation
async def generate_single_image(
    prompt: str,
    output_path: str = None,
    style_lora: str = None
) -> Optional[str]:
    """
    Quick helper to generate a single image.

    Args:
        prompt: Image description
        output_path: Where to save (optional)
        style_lora: LoRA style to apply (optional)

    Returns:
        Path to generated image
    """
    gen = LocalImageGenerator()

    if style_lora:
        gen.load_style_lora(style_lora)

    result = await gen.generate_anchor_image(
        section_name="single",
        prompt=prompt
    )

    gen.unload_model()

    return result.image_path if result else None
```

### 3.2 LocalVideoGenerator

**File:** `backend/src/local/video_generator.py`

```python
"""
Local GPU video generation using LTX-Video.
Replaces LumaVideoGenerator for offline operation.

Key Features:
- Loop-based generation (4-second clips to fill section duration)
- Same anchor image for all loops = character consistency
- Memory-managed sequential loading after Flux unload
"""

import gc
import torch
import math
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from PIL import Image


@dataclass
class GeneratedVideoLoop:
    """Result of video loop generation for a section"""
    section_name: str
    video_paths: List[str]      # List of 4-second loop files
    num_loops: int              # Number of loops generated
    total_duration: float       # Actual duration (num_loops * 4.0)
    anchor_image_path: str      # Source anchor image
    motion_prompt: str


class LocalVideoGenerator:
    """
    LTX-Video generator for local GPU execution.

    Loop Calculator Logic:
        num_loops = ceil(section_duration / 4.0)

    Example:
        - Intro (15s) → 4 loops (16s, slight overlap handled in assembly)
        - Verse (30s) → 8 loops (32s)
        - Chorus (20s) → 5 loops (20s)

    Character Consistency:
        Each loop uses the SAME anchor image, ensuring the character/scene
        remains consistent across the entire section.
    """

    # LTX-Video constraints
    LOOP_DURATION = 4.0         # seconds per loop
    FRAMES_PER_LOOP = 97        # 4 seconds at 24fps (must be 8n+1: 96+1=97)
    VIDEO_WIDTH = 768           # Must be divisible by 32
    VIDEO_HEIGHT = 512          # Must be divisible by 32
    FPS = 24

    # Generation settings
    NUM_INFERENCE_STEPS = 50

    def __init__(self, output_dir: str = "data/generated_videos"):
        """
        Initialize the local video generator.

        Args:
            output_dir: Directory to save generated video loops
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pipe = None

    def _load_model(self):
        """Load LTX-Video pipeline"""
        if self.pipe is not None:
            return

        from diffusers import LTXImageToVideoPipeline

        print("[LOCAL] Loading LTX-Video...")

        self.pipe = LTXImageToVideoPipeline.from_pretrained(
            "Lightricks/LTX-Video",
            torch_dtype=torch.bfloat16
        )
        self.pipe.to("cuda")
        self.pipe.vae.enable_tiling()  # Memory optimization

        print("[LOCAL] LTX-Video loaded successfully")

    def unload_model(self):
        """Release GPU memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            print("[LOCAL] LTX-Video unloaded, GPU memory cleared")

    def calculate_loops(self, section_duration: float) -> int:
        """
        Calculate number of 4-second loops needed for a section.

        Args:
            section_duration: Section length in seconds

        Returns:
            Number of loops (always rounds up)
        """
        return math.ceil(section_duration / self.LOOP_DURATION)

    async def generate_section_loops(
        self,
        section_name: str,
        anchor_image_path: str,
        section_duration: float,
        motion_prompt: str
    ) -> GeneratedVideoLoop:
        """
        Generate enough 4-second loops to fill a section.

        Args:
            section_name: Section identifier (e.g., "verse_1")
            anchor_image_path: Path to Flux-generated anchor image
            section_duration: Total section length in seconds
            motion_prompt: Motion/camera description for LTX

        Returns:
            GeneratedVideoLoop with list of video file paths
        """
        self._load_model()

        # Calculate required loops
        num_loops = self.calculate_loops(section_duration)

        print(f"[LOCAL] Section '{section_name}':")
        print(f"[LOCAL]   Duration: {section_duration:.1f}s")
        print(f"[LOCAL]   Loops needed: {num_loops} (@ {self.LOOP_DURATION}s each)")

        # Load and resize anchor image to LTX native resolution
        image = Image.open(anchor_image_path)
        image = image.resize(
            (self.VIDEO_WIDTH, self.VIDEO_HEIGHT),
            Image.Resampling.LANCZOS
        )

        video_paths = []

        for loop_idx in range(num_loops):
            print(f"[LOCAL]   Generating loop {loop_idx + 1}/{num_loops}...")

            try:
                result = self.pipe(
                    image=image,
                    prompt=motion_prompt,
                    negative_prompt="worst quality, blurry, jittery, distorted, static, frozen, morphing",
                    width=self.VIDEO_WIDTH,
                    height=self.VIDEO_HEIGHT,
                    num_frames=self.FRAMES_PER_LOOP,
                    num_inference_steps=self.NUM_INFERENCE_STEPS,
                )

                # Save loop video
                from diffusers.utils import export_to_video

                filename = f"{section_name}_loop_{loop_idx:02d}.mp4"
                filepath = self.output_dir / filename

                export_to_video(result.frames[0], str(filepath), fps=self.FPS)
                video_paths.append(str(filepath))

                print(f"[LOCAL]   Saved: {filename}")

            except Exception as e:
                print(f"[LOCAL]   Error generating loop {loop_idx}: {e}")
                # Continue with remaining loops

        return GeneratedVideoLoop(
            section_name=section_name,
            video_paths=video_paths,
            num_loops=len(video_paths),
            total_duration=len(video_paths) * self.LOOP_DURATION,
            anchor_image_path=anchor_image_path,
            motion_prompt=motion_prompt
        )

    async def generate_all_sections(
        self,
        song_structure: Dict,
        anchor_images: Dict[str, 'GeneratedImage']
    ) -> Dict[str, GeneratedVideoLoop]:
        """
        Generate video loops for all sections.

        Args:
            song_structure: Section definitions with timing
            anchor_images: Dict from LocalImageGenerator.generate_all_sections()

        Returns:
            Dict mapping section_name -> GeneratedVideoLoop
        """
        loops = {}
        total_sections = len(song_structure.get("sections", []))

        print(f"\n[LOCAL] === Generating Video Loops for {total_sections} Sections ===")

        for i, section in enumerate(song_structure["sections"]):
            name = section["name"]
            duration = section["end"] - section["start"]
            motion_prompt = section.get("motion_prompt", "Slow cinematic camera drift, subtle ambient motion")

            print(f"\n[LOCAL] [{i+1}/{total_sections}] Processing: {name}")

            # Check if we have an anchor image for this section
            if name not in anchor_images:
                print(f"[LOCAL] Warning: No anchor image for '{name}', skipping")
                continue

            anchor = anchor_images[name]

            # Generate loops for this section
            loop_result = await self.generate_section_loops(
                section_name=name,
                anchor_image_path=anchor.image_path,
                section_duration=duration,
                motion_prompt=motion_prompt
            )

            loops[name] = loop_result

        # Summary
        total_loops = sum(l.num_loops for l in loops.values())
        total_duration = sum(l.total_duration for l in loops.values())

        print(f"\n[LOCAL] === Video Generation Complete ===")
        print(f"[LOCAL] Sections processed: {len(loops)}/{total_sections}")
        print(f"[LOCAL] Total loops: {total_loops}")
        print(f"[LOCAL] Total video duration: {total_duration:.1f}s")
        print(f"[LOCAL] =====================================\n")

        return loops
```

### 3.3 ComplianceGate

**File:** `backend/src/safety/compliance_gate.py`

```python
"""
Compliance Gate - Content Safety Verification Layer

Runs AFTER image generation, BEFORE video generation.
Uses NudeNet for anatomy detection and ViT-Age-Classifier for age estimation.

CRITICAL SAFETY RULES:
1. Age check is MANDATORY and cannot be disabled
2. If age_probability < 18 exceeds 0.5, image is IMMEDIATELY deleted
3. Policy-specific rules can be relaxed ONLY in admin_generate_offline.py
"""

import json
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime


class ComplianceStatus(Enum):
    """Result status of compliance check"""
    PASS = "pass"
    FAIL_AGE = "fail_age"           # Age detection triggered
    FAIL_NUDITY = "fail_nudity"     # Nudity policy violation
    CRITICAL_FAIL = "critical_fail" # Immediate deletion required
    ERROR = "error"                 # Check failed to run


@dataclass
class NudityDetection:
    """Single detection result from NudeNet"""
    label: str          # e.g., "BUTTOCKS", "FEMALE_BREAST_EXPOSED"
    confidence: float   # 0.0 - 1.0
    box: Tuple[int, int, int, int] = None  # Bounding box if available


@dataclass
class ComplianceResult:
    """Complete result of compliance check"""
    image_path: str
    status: ComplianceStatus
    policy_name: str

    # Age analysis
    age_detected: bool = False
    age_estimate: Optional[float] = None
    age_confidence: Optional[float] = None

    # Nudity analysis
    nudity_detections: List[NudityDetection] = field(default_factory=list)
    nudity_labels: List[str] = field(default_factory=list)
    max_nudity_confidence: float = 0.0

    # Action taken
    deleted: bool = False
    deletion_reason: Optional[str] = None

    # Metadata
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None


class ComplianceGate:
    """
    Content compliance verification using NudeNet and ViT-Age-Classifier.

    Usage:
        gate = ComplianceGate("policies/rapper_explicit.json")
        result = await gate.check_image("path/to/image.png")

        if result.status == ComplianceStatus.PASS:
            # Safe to proceed to video generation
        else:
            # Image was rejected (and possibly deleted)

    Policy JSON Format:
        {
            "name": "policy_name",
            "nudity_thresholds": {
                "BUTTOCKS": 0.7,
                "FEMALE_BREAST_EXPOSED": 0.0,  # 0.0 = always reject
                "EXPOSED_GENITALIA_F": 0.0,
                ...
            },
            "allowed_labels": ["EXPOSED_BELLY", "MALE_BREAST_EXPOSED"],
            "age_threshold": 0.5,  # Cannot be overridden below 0.5
            "description": "Policy description"
        }
    """

    # NudeNet label categories
    ALWAYS_PROHIBITED = [
        "EXPOSED_GENITALIA_F",
        "EXPOSED_GENITALIA_M",
        "EXPOSED_ANUS"
    ]

    # Directories
    POLICIES_DIR = Path("policies")
    QUARANTINE_DIR = Path("data/quarantine")

    def __init__(
        self,
        policy_path: str,
        quarantine_dir: str = None,
        skip_age_check: bool = False  # ONLY for admin mode
    ):
        """
        Initialize the compliance gate.

        Args:
            policy_path: Path to policy JSON file
            quarantine_dir: Override quarantine directory
            skip_age_check: DANGEROUS - Only for admin_generate_offline.py
        """
        self.policy_path = Path(policy_path)
        self.policy = self._load_policy()
        self.policy_name = self.policy.get("name", self.policy_path.stem)

        # Age check can NEVER be fully skipped - only threshold adjusted
        self.skip_age_check = skip_age_check
        if skip_age_check:
            print("[COMPLIANCE] WARNING: Age check threshold relaxed (admin mode)")

        # Setup quarantine
        self.quarantine_dir = Path(quarantine_dir) if quarantine_dir else self.QUARANTINE_DIR
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Models (lazy loaded)
        self._nudenet = None
        self._age_classifier = None
        self._age_processor = None

    def _load_policy(self) -> Dict:
        """Load and validate policy configuration"""
        if not self.policy_path.exists():
            raise FileNotFoundError(f"Policy not found: {self.policy_path}")

        with open(self.policy_path, 'r') as f:
            policy = json.load(f)

        # Ensure critical fields exist
        if "nudity_thresholds" not in policy:
            policy["nudity_thresholds"] = {}
        if "allowed_labels" not in policy:
            policy["allowed_labels"] = []

        # Age threshold cannot go below 0.5 (MANDATORY SAFETY)
        policy["age_threshold"] = max(policy.get("age_threshold", 0.5), 0.5)

        print(f"[COMPLIANCE] Loaded policy: {policy.get('name', 'unnamed')}")
        return policy

    def _load_nudenet(self):
        """Lazy load NudeNet model"""
        if self._nudenet is not None:
            return

        try:
            from nudenet import NudeDetector
            self._nudenet = NudeDetector()
            print("[COMPLIANCE] NudeNet loaded")
        except ImportError:
            print("[COMPLIANCE] ERROR: nudenet not installed (pip install nudenet)")
            self._nudenet = "unavailable"

    def _load_age_classifier(self):
        """Lazy load ViT-Age-Classifier from HuggingFace"""
        if self._age_classifier is not None:
            return

        try:
            from transformers import ViTImageProcessor, ViTForImageClassification
            import torch

            model_name = "nateraw/vit-age-classifier"

            self._age_processor = ViTImageProcessor.from_pretrained(model_name)
            self._age_classifier = ViTForImageClassification.from_pretrained(model_name)
            self._age_classifier.eval()

            # Move to GPU if available
            if torch.cuda.is_available():
                self._age_classifier = self._age_classifier.to("cuda")

            print("[COMPLIANCE] ViT-Age-Classifier loaded")

        except ImportError:
            print("[COMPLIANCE] ERROR: transformers not installed")
            self._age_classifier = "unavailable"
        except Exception as e:
            print(f"[COMPLIANCE] ERROR loading age classifier: {e}")
            self._age_classifier = "unavailable"

    async def check_image(self, image_path: str) -> ComplianceResult:
        """
        Check a single image against the loaded policy.

        Checks performed (in order):
        1. Age classification - CRITICAL, cannot be disabled
        2. Nudity detection - Policy-specific thresholds

        Args:
            image_path: Path to image file

        Returns:
            ComplianceResult with status and details
        """
        result = ComplianceResult(
            image_path=image_path,
            status=ComplianceStatus.PASS,
            policy_name=self.policy_name
        )

        if not Path(image_path).exists():
            result.status = ComplianceStatus.ERROR
            result.error_message = "Image file not found"
            return result

        # ============================================
        # STEP 1: AGE CLASSIFICATION (MANDATORY)
        # ============================================
        age_result = await self._check_age(image_path)

        if age_result:
            result.age_detected = True
            result.age_estimate = age_result.get("age")
            result.age_confidence = age_result.get("confidence")

            # CRITICAL CHECK: If probability of being under 18 > threshold
            if age_result.get("under_18_probability", 0) > self.policy["age_threshold"]:
                result.status = ComplianceStatus.CRITICAL_FAIL
                result.deletion_reason = f"Age check failed: {age_result}"

                # IMMEDIATE DELETION - No exceptions
                self._hard_delete(image_path, "age_violation")
                result.deleted = True

                print(f"[COMPLIANCE] CRITICAL: Age violation detected, image deleted")
                return result

        # ============================================
        # STEP 2: NUDITY DETECTION (Policy-based)
        # ============================================
        nudity_result = await self._check_nudity(image_path)

        if nudity_result:
            result.nudity_detections = nudity_result
            result.nudity_labels = [d.label for d in nudity_result]
            result.max_nudity_confidence = max(
                (d.confidence for d in nudity_result),
                default=0.0
            )

            # Check against policy
            violation = self._check_nudity_policy(nudity_result)

            if violation:
                result.status = ComplianceStatus.FAIL_NUDITY
                result.deletion_reason = f"Nudity violation: {violation}"

                # Delete based on policy
                self._hard_delete(image_path, "nudity_violation")
                result.deleted = True

                print(f"[COMPLIANCE] Nudity violation: {violation}")
                return result

        # All checks passed
        print(f"[COMPLIANCE] ✓ Image passed: {Path(image_path).name}")
        return result

    async def _check_age(self, image_path: str) -> Optional[Dict]:
        """
        Run age classification on image.

        Returns:
            Dict with age estimate and under_18_probability, or None if no face
        """
        self._load_age_classifier()

        if self._age_classifier == "unavailable":
            return None

        try:
            from PIL import Image
            import torch

            image = Image.open(image_path).convert("RGB")

            inputs = self._age_processor(images=image, return_tensors="pt")

            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._age_classifier(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # Get age labels from model config
            labels = self._age_classifier.config.id2label
            probs_dict = {labels[i]: probs[0][i].item() for i in range(len(labels))}

            # Calculate probability of being under 18
            # Assumes labels like "0-2", "3-9", "10-19", etc.
            under_18_prob = 0.0
            for label, prob in probs_dict.items():
                # Parse age range
                if "-" in label:
                    low, high = map(int, label.split("-"))
                    if high < 18:
                        under_18_prob += prob
                    elif low < 18:
                        # Partial overlap
                        overlap = (18 - low) / (high - low + 1)
                        under_18_prob += prob * overlap

            # Get most likely age
            predicted_idx = probs.argmax(-1).item()
            predicted_label = labels[predicted_idx]

            return {
                "age": predicted_label,
                "confidence": probs[0][predicted_idx].item(),
                "under_18_probability": under_18_prob,
                "all_probs": probs_dict
            }

        except Exception as e:
            print(f"[COMPLIANCE] Age check error: {e}")
            return None

    async def _check_nudity(self, image_path: str) -> List[NudityDetection]:
        """
        Run NudeNet detection on image.

        Returns:
            List of NudityDetection objects
        """
        self._load_nudenet()

        if self._nudenet == "unavailable":
            return []

        try:
            detections = self._nudenet.detect(image_path)

            results = []
            for det in detections:
                results.append(NudityDetection(
                    label=det.get("class", det.get("label", "unknown")),
                    confidence=det.get("score", 0.0),
                    box=det.get("box")
                ))

            return results

        except Exception as e:
            print(f"[COMPLIANCE] Nudity check error: {e}")
            return []

    def _check_nudity_policy(self, detections: List[NudityDetection]) -> Optional[str]:
        """
        Check detections against policy thresholds.

        Returns:
            Violation description if policy violated, None otherwise
        """
        allowed = set(self.policy.get("allowed_labels", []))
        thresholds = self.policy.get("nudity_thresholds", {})

        for det in detections:
            label = det.label
            conf = det.confidence

            # Always-prohibited labels
            if label in self.ALWAYS_PROHIBITED:
                return f"{label} detected (always prohibited)"

            # Check if in allowed list
            if label in allowed:
                continue

            # Check threshold
            threshold = thresholds.get(label, 0.6)  # Default 0.6
            if threshold == 0.0:
                # 0.0 means always reject this label
                return f"{label} detected (prohibited by policy)"
            elif conf > threshold:
                return f"{label} confidence {conf:.2f} exceeds threshold {threshold}"

        return None

    def _hard_delete(self, image_path: str, reason: str):
        """
        Move image to quarantine (hard delete with audit trail).

        Args:
            image_path: Path to image
            reason: Reason for deletion (for audit)
        """
        src = Path(image_path)
        if not src.exists():
            return

        # Create timestamped quarantine path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = self.quarantine_dir / f"{reason}_{timestamp}_{src.name}"

        # Move to quarantine
        shutil.move(str(src), str(dst))

        # Log deletion
        print(f"[COMPLIANCE] DELETED: {src.name} → quarantine/{dst.name}")

        # Remove associated metadata if exists
        metadata_path = src.parent / "metadata" / f"{src.stem}.json"
        if metadata_path.exists():
            metadata_path.unlink()

    async def check_all_images(
        self,
        anchor_images: Dict[str, 'GeneratedImage']
    ) -> Tuple[Dict[str, ComplianceResult], Dict[str, 'GeneratedImage']]:
        """
        Check all anchor images before video generation.

        Args:
            anchor_images: Dict from LocalImageGenerator

        Returns:
            Tuple of (all_results, passed_images)
        """
        results = {}
        passed = {}

        total = len(anchor_images)
        pass_count = 0
        fail_count = 0

        print(f"\n[COMPLIANCE] === Checking {total} Images ===")
        print(f"[COMPLIANCE] Policy: {self.policy_name}")
        print(f"[COMPLIANCE] Age threshold: {self.policy['age_threshold']}")

        for section_name, anchor in anchor_images.items():
            result = await self.check_image(anchor.image_path)
            results[section_name] = result

            if result.status == ComplianceStatus.PASS:
                pass_count += 1
                passed[section_name] = anchor
                print(f"[COMPLIANCE] ✓ {section_name}: PASS")
            else:
                fail_count += 1
                status = result.status.value
                reason = result.deletion_reason or "Unknown"
                print(f"[COMPLIANCE] ✗ {section_name}: {status} - {reason}")

        print(f"\n[COMPLIANCE] === Results ===")
        print(f"[COMPLIANCE] Passed: {pass_count}/{total}")
        print(f"[COMPLIANCE] Failed: {fail_count}/{total}")
        print(f"[COMPLIANCE] =================\n")

        return results, passed
```

### 3.4 Policy JSON Files

**File:** `backend/policies/rapper_explicit.json`

```json
{
    "name": "rapper_explicit",
    "description": "Urban/hip-hop music video standards - allows revealing clothing",
    "version": "1.0",

    "nudity_thresholds": {
        "EXPOSED_BELLY": 1.0,
        "EXPOSED_BUTTOCKS": 0.85,
        "FEMALE_BREAST_COVERED": 1.0,
        "MALE_BREAST_EXPOSED": 1.0,
        "FEMALE_BREAST_EXPOSED": 0.0,
        "EXPOSED_GENITALIA_F": 0.0,
        "EXPOSED_GENITALIA_M": 0.0,
        "EXPOSED_ANUS": 0.0
    },

    "allowed_labels": [
        "EXPOSED_BELLY",
        "FEMALE_BREAST_COVERED",
        "MALE_BREAST_EXPOSED",
        "FACE_F",
        "FACE_M"
    ],

    "age_threshold": 0.5,

    "notes": "Allows revealing clothing and partial exposure, prohibits explicit nudity"
}
```

**File:** `backend/policies/eu_standard.json`

```json
{
    "name": "eu_standard",
    "description": "European broadcast standards - allows artistic nudity",
    "version": "1.0",

    "nudity_thresholds": {
        "EXPOSED_BELLY": 1.0,
        "EXPOSED_BUTTOCKS": 0.9,
        "FEMALE_BREAST_COVERED": 1.0,
        "MALE_BREAST_EXPOSED": 1.0,
        "FEMALE_BREAST_EXPOSED": 0.8,
        "EXPOSED_GENITALIA_F": 0.0,
        "EXPOSED_GENITALIA_M": 0.0,
        "EXPOSED_ANUS": 0.0
    },

    "allowed_labels": [
        "EXPOSED_BELLY",
        "EXPOSED_BUTTOCKS",
        "FEMALE_BREAST_COVERED",
        "FEMALE_BREAST_EXPOSED",
        "MALE_BREAST_EXPOSED"
    ],

    "age_threshold": 0.5,

    "notes": "Allows artistic nudity per European broadcasting norms, genitalia always prohibited"
}
```

**File:** `backend/policies/offline_explicit.json`

```json
{
    "name": "offline_explicit",
    "description": "ADMIN ONLY - Relaxed policy for offline/private generation",
    "version": "1.0",
    "admin_only": true,

    "nudity_thresholds": {
        "EXPOSED_BELLY": 1.0,
        "EXPOSED_BUTTOCKS": 1.0,
        "FEMALE_BREAST_COVERED": 1.0,
        "MALE_BREAST_EXPOSED": 1.0,
        "FEMALE_BREAST_EXPOSED": 0.95,
        "EXPOSED_GENITALIA_F": 0.0,
        "EXPOSED_GENITALIA_M": 0.0,
        "EXPOSED_ANUS": 0.0
    },

    "allowed_labels": [
        "EXPOSED_BELLY",
        "EXPOSED_BUTTOCKS",
        "FEMALE_BREAST_COVERED",
        "FEMALE_BREAST_EXPOSED",
        "MALE_BREAST_EXPOSED"
    ],

    "age_threshold": 0.5,

    "notes": "WARNING: Admin-only policy with relaxed thresholds. Age check CANNOT be disabled."
}
```

**File:** `backend/policies/safe_default.json`

```json
{
    "name": "safe_default",
    "description": "Maximum safety - strict content filtering",
    "version": "1.0",

    "nudity_thresholds": {
        "EXPOSED_BELLY": 0.9,
        "EXPOSED_BUTTOCKS": 0.0,
        "FEMALE_BREAST_COVERED": 0.95,
        "MALE_BREAST_EXPOSED": 0.9,
        "FEMALE_BREAST_EXPOSED": 0.0,
        "EXPOSED_GENITALIA_F": 0.0,
        "EXPOSED_GENITALIA_M": 0.0,
        "EXPOSED_ANUS": 0.0
    },

    "allowed_labels": [
        "FACE_F",
        "FACE_M"
    ],

    "age_threshold": 0.5,

    "notes": "Strictest policy - suitable for all audiences"
}
```

### 3.5 Admin Offline Generation Script

**File:** `backend/scripts/admin_generate_offline.py`

```python
#!/usr/bin/env python3
"""
Admin Offline Generation Script

Standalone script for direct local execution with custom policies.
This is the ONLY place where specific NudeNet filters can be relaxed.

SAFETY NOTES:
- Age check CANNOT be disabled (mandatory safety)
- This script should only be run by administrators
- Output can be directed to external drives for private storage

Usage:
    python admin_generate_offline.py \\
        --audio path/to/song.mp3 \\
        --policy offline_explicit \\
        --output_dir /mnt/external/private_output \\
        --style gritty_urban

Arguments:
    --audio         Path to input audio file
    --policy        Policy profile name (without .json)
    --output_dir    Output directory (can be external drive)
    --style         LoRA style: gritty_urban, realistic_euro
    --skip_video    Generate images only, skip video loops
    --seed          Random seed for reproducibility
    --dry_run       Show what would be generated without running
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.local.image_generator import LocalImageGenerator
from src.local.video_generator import LocalVideoGenerator
from src.safety.compliance_gate import ComplianceGate, ComplianceStatus
from src.audio.analyzer import MusicAnalyzer
from src.storyboard.conceptor import ConceptGenerator
from src.storyboard.generator import StoryboardGenerator


def parse_args():
    parser = argparse.ArgumentParser(
        description="Admin Offline Generation - Local GPU pipeline with custom policies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic generation with relaxed policy
    python admin_generate_offline.py --audio song.mp3 --policy offline_explicit

    # Output to external drive with gritty style
    python admin_generate_offline.py \\
        --audio song.mp3 \\
        --policy offline_explicit \\
        --output_dir E:/private_videos \\
        --style gritty_urban

    # Images only (no video generation)
    python admin_generate_offline.py \\
        --audio song.mp3 \\
        --policy eu_standard \\
        --skip_video
        """
    )

    parser.add_argument(
        "--audio", "-a",
        required=True,
        help="Path to input audio file (MP3, WAV, etc.)"
    )

    parser.add_argument(
        "--policy", "-p",
        default="offline_explicit",
        help="Policy profile name (default: offline_explicit)"
    )

    parser.add_argument(
        "--output_dir", "-o",
        default=None,
        help="Output directory (default: data/offline_output/)"
    )

    parser.add_argument(
        "--style", "-s",
        choices=["gritty_urban", "realistic_euro", "none"],
        default="none",
        help="LoRA style to apply (default: none)"
    )

    parser.add_argument(
        "--skip_video",
        action="store_true",
        help="Generate images only, skip video loop generation"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )

    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Show what would be generated without running"
    )

    parser.add_argument(
        "--prompt_override",
        type=str,
        default=None,
        help="Override storyboard with custom prompt for all sections"
    )

    parser.add_argument(
        "--sections",
        type=int,
        default=None,
        help="Override number of sections to generate"
    )

    return parser.parse_args()


def setup_output_directories(base_dir: Path) -> dict:
    """Create output directory structure"""
    dirs = {
        "base": base_dir,
        "images": base_dir / "images",
        "videos": base_dir / "videos",
        "metadata": base_dir / "metadata",
        "quarantine": base_dir / "quarantine"
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    return dirs


def storyboard_to_song_structure(storyboard: list) -> dict:
    """Convert scene-based storyboard to section-based structure"""
    sections = []
    current_section = None

    for scene in storyboard:
        # Try to detect section from scene data
        section_label = scene.get('section', f"section_{len(sections)}")

        if current_section is None or current_section['name'] != section_label:
            if current_section:
                sections.append(current_section)
            current_section = {
                'name': section_label,
                'start': scene['timestamp_start'],
                'end': scene['timestamp_end'],
                'prompt': scene.get('image_prompt', scene.get('description', '')),
                'motion_prompt': scene.get('motion_prompt', 'Slow cinematic drift'),
                'style': scene.get('visual_style', 'cinematic')
            }
        else:
            current_section['end'] = scene['timestamp_end']

    if current_section:
        sections.append(current_section)

    return {'sections': sections}


async def run_pipeline(args):
    """Execute the full offline generation pipeline"""

    print("=" * 60)
    print("ADMIN OFFLINE GENERATION")
    print("=" * 60)
    print(f"Audio: {args.audio}")
    print(f"Policy: {args.policy}")
    print(f"Style: {args.style}")
    print(f"Output: {args.output_dir or 'default'}")
    print("=" * 60)

    # Validate inputs
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"ERROR: Audio file not found: {audio_path}")
        return 1

    policy_path = Path(f"policies/{args.policy}.json")
    if not policy_path.exists():
        print(f"ERROR: Policy not found: {policy_path}")
        print(f"Available policies: {list(Path('policies').glob('*.json'))}")
        return 1

    # Setup output directories
    if args.output_dir:
        output_base = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base = Path(f"data/offline_output/{timestamp}")

    dirs = setup_output_directories(output_base)
    print(f"\nOutput directory: {dirs['base']}")

    if args.dry_run:
        print("\n[DRY RUN] Would execute pipeline with above settings")
        return 0

    # ============================================
    # PHASE 1: Audio Analysis
    # ============================================
    print("\n[PHASE 1] Analyzing audio...")

    analyzer = MusicAnalyzer()
    music_data = analyzer.analyze_song(str(audio_path))

    print(f"  Duration: {music_data['duration']:.1f}s")
    print(f"  Tempo: {music_data['tempo']:.1f} BPM")
    print(f"  Segments: {len(music_data['segments'])}")

    # ============================================
    # PHASE 2: Concept Generation (simplified for offline)
    # ============================================
    print("\n[PHASE 2] Generating concept...")

    if args.prompt_override:
        # Use custom prompt for all sections
        concept = type('Concept', (), {
            'overall_style': 'cinematic',
            'color_palette': ['warm', 'golden', 'shadows'],
            'mood_progression': ['building', 'intense', 'resolution'],
            'key_visual_themes': ['urban', 'nightlife', 'energy'],
            'camera_style': 'dynamic'
        })()
    else:
        conceptor = ConceptGenerator()
        concept = conceptor.generate_concept(
            music_data,
            user_prompt=f"Music video for {audio_path.stem}"
        )

    print(f"  Style: {concept.overall_style}")

    # ============================================
    # PHASE 3: Storyboard Generation
    # ============================================
    print("\n[PHASE 3] Creating storyboard...")

    if args.prompt_override:
        # Create simple sections from audio segments
        sections = []
        for i, seg in enumerate(music_data['segments'][:args.sections or 6]):
            sections.append({
                'name': f'section_{i}',
                'start': seg['start_time'],
                'end': seg['end_time'],
                'prompt': args.prompt_override,
                'motion_prompt': 'Slow cinematic camera drift, subtle motion',
                'style': 'cinematic'
            })
        song_structure = {'sections': sections}
    else:
        generator = StoryboardGenerator()
        storyboard = generator.create_storyboard(music_data, concept)
        storyboard_dicts = generator.scenes_to_dict_list(storyboard)
        song_structure = storyboard_to_song_structure(storyboard_dicts)

    print(f"  Sections: {len(song_structure['sections'])}")
    for sec in song_structure['sections']:
        duration = sec['end'] - sec['start']
        print(f"    - {sec['name']}: {sec['start']:.1f}s - {sec['end']:.1f}s ({duration:.1f}s)")

    # ============================================
    # PHASE 4: Image Generation
    # ============================================
    print("\n[PHASE 4] Generating anchor images...")

    image_gen = LocalImageGenerator(output_dir=str(dirs['images']))

    # Load style LoRA if specified
    if args.style and args.style != "none":
        image_gen.load_style_lora(args.style)

    anchor_images = await image_gen.generate_all_sections(song_structure)

    # Unload to free VRAM
    image_gen.unload_model()

    print(f"  Generated: {len(anchor_images)} anchor images")

    # ============================================
    # PHASE 4.5: Compliance Check
    # ============================================
    print("\n[PHASE 4.5] Running compliance checks...")

    compliance = ComplianceGate(
        policy_path=str(policy_path),
        quarantine_dir=str(dirs['quarantine'])
    )

    results, passed_anchors = await compliance.check_all_images(anchor_images)

    if not passed_anchors:
        print("\nERROR: All images failed compliance check!")
        print("Check quarantine directory for details.")
        return 1

    # ============================================
    # PHASE 5: Video Generation (optional)
    # ============================================
    if args.skip_video:
        print("\n[PHASE 5] Skipping video generation (--skip_video)")
    else:
        print("\n[PHASE 5] Generating video loops...")

        video_gen = LocalVideoGenerator(output_dir=str(dirs['videos']))

        video_loops = await video_gen.generate_all_sections(
            song_structure,
            passed_anchors
        )

        video_gen.unload_model()

        # Summary
        total_loops = sum(l.num_loops for l in video_loops.values())
        print(f"  Generated: {total_loops} video loops")

    # ============================================
    # COMPLETE
    # ============================================
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Output directory: {dirs['base']}")
    print(f"  Images: {dirs['images']}")
    if not args.skip_video:
        print(f"  Videos: {dirs['videos']}")
    print(f"  Quarantine: {dirs['quarantine']}")
    print("=" * 60)

    return 0


def main():
    args = parse_args()

    # Run async pipeline
    exit_code = asyncio.run(run_pipeline(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

---

## 4. Updated Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEATCANVAS LOCAL PIPELINE V2                  │
└─────────────────────────────────────────────────────────────────┘

Audio Upload
    │
    ▼
[Phase 1] Audio Analysis (librosa) ─────────────────── UNCHANGED
    │
    ▼
[Phase 2] Concept Generation (GPT-4) ───────────────── UNCHANGED
    │
    ▼
[Phase 3] Storyboard → SongStructure ───────────────── UNCHANGED
    │   Converts scenes to sections with Loop Calculator:
    │   num_loops = ceil(section_duration / 4.0)
    │
    ▼
[Phase 4] LOCAL Image Generation ───────────────────── NEW
    │   ├── LocalImageGenerator (Flux.1-schnell Uncensored)
    │   ├── GGUF checkpoint loading
    │   ├── LoRA injection: load_style_lora("gritty_urban")
    │   └── One anchor image per section
    │
    ▼
[Phase 4.5] COMPLIANCE GATE ────────────────────────── NEW
    │   ├── Load policy: policies/{profile}.json
    │   │
    │   ├── Age Check (ViT-Age-Classifier)
    │   │   └── MANDATORY: age_probability < 18 > 0.5 → CRITICAL_FAIL
    │   │       └── IMMEDIATE DELETE (cannot be disabled)
    │   │
    │   ├── Nudity Check (NudeNet)
    │   │   └── Compare against policy thresholds
    │   │   └── BUTTOCKS, GENITALIA, BREAST detection
    │   │
    │   └── Output: passed_anchors (failed images deleted)
    │
    ▼
[Phase 5] LOCAL Video Generation ───────────────────── NEW
    │   ├── LocalVideoGenerator (LTX-Video)
    │   ├── Loop Calculator: num_loops = ceil(duration / 4.0)
    │   ├── Same anchor image for ALL loops → character consistency
    │   └── 97 frames per loop (4 seconds @ 24fps)
    │
    ▼
[Phase 6] Video Assembly ───────────────────────────── UPDATED
    │   └── Concatenate loops with seamless transitions
    │
    ▼
MP4 Output
```

---

## 5. Memory Management Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    VRAM BUDGET: 16GB                             │
└─────────────────────────────────────────────────────────────────┘

Phase 4 (Flux):
├── Load Flux.1-schnell (~12GB with CPU offload)
├── Load LoRA (~200MB additional)
├── Generate all anchor images
└── UNLOAD: del pipe + gc.collect() + torch.cuda.empty_cache()

Phase 4.5 (Compliance):
├── NudeNet (~1GB)
├── ViT-Age-Classifier (~500MB)
├── Sequential image checks
└── Models can stay loaded (small footprint)

Phase 5 (LTX-Video):
├── Load LTX-Video (~10GB)
├── VAE tiling enabled
├── Generate all loops sequentially
└── UNLOAD before assembly
```

---

## 6. New Dependencies

**Add to `backend/requirements.txt`:**

```
# Local GPU Generation
torch>=2.1.0
diffusers>=0.32.0
transformers>=4.40.0
sentencepiece>=0.2.0
accelerate>=1.0.0
peft>=0.7.0  # For LoRA support

# Compliance/Safety
nudenet>=3.4.0
# ViT-Age-Classifier is loaded from transformers

# Optional: GGUF support
# gguf>=0.1.0
```

---

## 7. Files Summary

| File | Purpose |
|------|---------|
| `backend/src/local/image_generator.py` | LocalImageGenerator - Flux.1-schnell with LoRA |
| `backend/src/local/video_generator.py` | LocalVideoGenerator - LTX-Video loop generation |
| `backend/src/safety/compliance_gate.py` | ComplianceGate - NudeNet + ViT-Age-Classifier |
| `backend/policies/rapper_explicit.json` | Urban/hip-hop standards |
| `backend/policies/eu_standard.json` | European broadcast standards |
| `backend/policies/offline_explicit.json` | Admin-only relaxed policy |
| `backend/policies/safe_default.json` | Maximum safety policy |
| `backend/scripts/admin_generate_offline.py` | Standalone admin script |

---

## 8. Testing Checklist

### Image Generation
- [ ] Flux loads from GGUF checkpoint
- [ ] LoRA injection works for gritty_urban style
- [ ] LoRA injection works for realistic_euro style
- [ ] Images generate at 1024x576
- [ ] Memory clears properly after unload

### Compliance Gate
- [ ] Age classifier detects faces and estimates age
- [ ] Age < 18 detection triggers CRITICAL_FAIL
- [ ] Images are hard-deleted on age violation
- [ ] NudeNet detects BUTTOCKS, BREAST, GENITALIA
- [ ] Policy thresholds are respected
- [ ] offline_explicit policy relaxes thresholds

### Video Generation
- [ ] LTX generates 4-second loops at 768x512
- [ ] Loop calculator: 30s section → 8 loops
- [ ] Same anchor used for all loops in section
- [ ] Memory clears properly after unload

### Admin Script
- [ ] --policy loads correct JSON
- [ ] --output_dir saves to external path
- [ ] --style loads correct LoRA
- [ ] --skip_video works
- [ ] --dry_run shows plan without executing

### Integration
- [ ] Full pipeline runs end-to-end
- [ ] Memory stays under 16GB throughout
- [ ] Audio sync maintained in final video
