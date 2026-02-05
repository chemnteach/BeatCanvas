# BeatCanvas Local Pipeline Refactoring Plan

**Objective:** Replace cloud API architecture (Luma/Gemini) with local GPU execution using Flux.1-schnell and LTX-Video.

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

## 2. New Class Structure

### 2.1 LocalImageGenerator

**File:** `backend/src/assets/local_generator.py`

```python
"""
Local GPU image generation using Flux.1-schnell.
Replaces MultiProviderImageGenerator for offline operation.
"""

import gc
import torch
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from PIL import Image
import uuid
from datetime import datetime

@dataclass
class GeneratedImage:
    scene_timestamp: float
    image_path: str
    provider: str  # "flux_local"
    prompt: str
    variation_index: int

class LocalImageGenerator:
    """
    Flux.1-schnell image generator for local GPU execution.

    Key differences from MultiProviderImageGenerator:
    - No API calls, no rate limits
    - Single provider (Flux), no fallback chain
    - Memory management between generations
    - Uses uncensored checkpoint for diverse content
    """

    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: Path to flux1-schnell-uncensored.gguf
                        If None, downloads from HuggingFace
        """
        self.model_path = model_path
        self.pipe = None
        self.output_dir = Path("data/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_model(self):
        """Load Flux pipeline (lazy initialization)"""
        if self.pipe is not None:
            return

        from diffusers import FluxPipeline

        print("[LOCAL] Loading Flux.1-schnell...")

        if self.model_path:
            # Load from local GGUF checkpoint
            self.pipe = FluxPipeline.from_single_file(
                self.model_path,
                torch_dtype=torch.bfloat16
            )
        else:
            # Download from HuggingFace
            self.pipe = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-schnell",
                torch_dtype=torch.bfloat16
            )

        self.pipe.enable_model_cpu_offload()
        print("[LOCAL] Flux.1-schnell loaded")

    def unload_model(self):
        """Release GPU memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            print("[LOCAL] Flux unloaded, memory cleared")

    async def generate_anchor_image(
        self,
        section_name: str,
        prompt: str,
        style: str,
        seed: int = None
    ) -> Optional[GeneratedImage]:
        """
        Generate ONE anchor image per song section.

        This is the key architectural change: instead of generating
        per-scene, we generate per-section (Intro, Verse 1, Chorus, etc.)
        and reuse the anchor for video loops.

        Args:
            section_name: "intro", "verse_1", "chorus_1", etc.
            prompt: Visual description from storyboard
            style: Style anchor for consistency
            seed: Optional seed for reproducibility
        """
        self._load_model()

        enhanced_prompt = self._enhance_prompt(prompt, style)

        generator = None
        if seed is not None:
            generator = torch.Generator("cpu").manual_seed(seed)

        print(f"[LOCAL] Generating anchor image for {section_name}...")

        result = self.pipe(
            prompt=enhanced_prompt,
            height=576,
            width=1024,
            num_inference_steps=4,
            guidance_scale=0.0,
            max_sequence_length=256,
            generator=generator
        )

        image = result.images[0]

        # Save image
        filename = f"anchor_{section_name}_{uuid.uuid4().hex[:8]}.png"
        filepath = self.output_dir / filename
        image.save(filepath)

        print(f"[LOCAL] Saved: {filepath}")

        return GeneratedImage(
            scene_timestamp=0.0,  # Will be set by caller
            image_path=str(filepath),
            provider="flux_local",
            prompt=enhanced_prompt,
            variation_index=0
        )

    async def generate_all_sections(
        self,
        song_structure: Dict
    ) -> Dict[str, GeneratedImage]:
        """
        Generate anchor images for all song sections.

        Args:
            song_structure: {
                "sections": [
                    {"name": "intro", "start": 0.0, "end": 15.0, "prompt": "..."},
                    {"name": "verse_1", "start": 15.0, "end": 45.0, "prompt": "..."},
                    ...
                ]
            }

        Returns:
            Dict mapping section_name -> GeneratedImage
        """
        anchors = {}

        for section in song_structure["sections"]:
            name = section["name"]
            prompt = section.get("prompt", section.get("image_prompt", ""))
            style = section.get("style", "cinematic")

            anchor = await self.generate_anchor_image(
                section_name=name,
                prompt=prompt,
                style=style
            )

            if anchor:
                anchor.scene_timestamp = section["start"]
                anchors[name] = anchor

        return anchors

    def _enhance_prompt(self, base_prompt: str, style: str) -> str:
        """Enhance prompt for Flux quality"""
        return f"""{base_prompt}

Style: {style}, photorealistic, professional cinematography
Quality: High resolution, sharp details, 16:9 widescreen
Lighting: Cinematic, atmospheric, professional
Composition: Rule of thirds, engaging perspective"""
```

### 2.2 LocalVideoGenerator

**File:** `backend/src/assets/local_video_generator.py`

```python
"""
Local GPU video generation using LTX-Video.
Replaces LumaVideoGenerator for offline operation.
"""

import gc
import torch
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from PIL import Image
import math

@dataclass
class GeneratedVideoLoop:
    section_name: str
    video_paths: List[str]  # Multiple 4-second loops
    total_duration: float
    anchor_image_path: str

class LocalVideoGenerator:
    """
    LTX-Video generator for local GPU execution.

    Key concept: Generate 4-second loops to fill section duration.
    Each loop uses the same anchor image for character consistency.
    """

    LOOP_DURATION = 4.0  # seconds per loop
    FRAMES_PER_LOOP = 97  # 4 seconds at 24fps (must be 8n+1)

    def __init__(self):
        self.pipe = None
        self.output_dir = Path("data/generated_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
        self.pipe.vae.enable_tiling()

        print("[LOCAL] LTX-Video loaded")

    def unload_model(self):
        """Release GPU memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            print("[LOCAL] LTX-Video unloaded, memory cleared")

    async def generate_section_loops(
        self,
        section_name: str,
        anchor_image_path: str,
        section_duration: float,
        motion_prompt: str
    ) -> GeneratedVideoLoop:
        """
        Generate enough 4-second loops to fill a section.

        Example: 32-second verse → 8 loops (32 / 4 = 8)

        Args:
            section_name: "verse_1", "chorus_1", etc.
            anchor_image_path: Path to Flux-generated anchor image
            section_duration: Total section length in seconds
            motion_prompt: Motion description for LTX

        Returns:
            GeneratedVideoLoop with list of video paths
        """
        self._load_model()

        # Calculate required loops
        num_loops = math.ceil(section_duration / self.LOOP_DURATION)

        print(f"[LOCAL] Section '{section_name}': {section_duration:.1f}s → {num_loops} loops")

        # Load and resize anchor image
        image = Image.open(anchor_image_path)
        image = image.resize((768, 512), Image.Resampling.LANCZOS)

        video_paths = []

        for loop_idx in range(num_loops):
            print(f"[LOCAL] Generating loop {loop_idx + 1}/{num_loops}...")

            result = self.pipe(
                image=image,
                prompt=motion_prompt,
                negative_prompt="worst quality, blurry, jittery, distorted, static",
                width=768,
                height=512,
                num_frames=self.FRAMES_PER_LOOP,
                num_inference_steps=50,
            )

            # Save loop video
            from diffusers.utils import export_to_video

            filename = f"{section_name}_loop_{loop_idx:02d}.mp4"
            filepath = self.output_dir / filename

            export_to_video(result.frames[0], str(filepath), fps=24)
            video_paths.append(str(filepath))

            print(f"[LOCAL] Saved: {filepath}")

        return GeneratedVideoLoop(
            section_name=section_name,
            video_paths=video_paths,
            total_duration=num_loops * self.LOOP_DURATION,
            anchor_image_path=anchor_image_path
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
            anchor_images: Dict from LocalImageGenerator

        Returns:
            Dict mapping section_name -> GeneratedVideoLoop
        """
        loops = {}

        for section in song_structure["sections"]:
            name = section["name"]
            duration = section["end"] - section["start"]
            motion_prompt = section.get("motion_prompt", "Slow camera drift, subtle motion")

            if name not in anchor_images:
                print(f"[LOCAL] Warning: No anchor image for {name}, skipping")
                continue

            anchor = anchor_images[name]

            loop_result = await self.generate_section_loops(
                section_name=name,
                anchor_image_path=anchor.image_path,
                section_duration=duration,
                motion_prompt=motion_prompt
            )

            loops[name] = loop_result

        return loops
```

### 2.3 ComplianceEngine

**File:** `backend/src/compliance/engine.py`

```python
"""
Compliance gate for content verification.
Runs AFTER image generation, BEFORE video generation.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import shutil

class ComplianceAction(Enum):
    PASS = "pass"
    REJECT_AGE = "reject_age"
    REJECT_NUDITY = "reject_nudity"
    HARD_DELETE = "hard_delete"

@dataclass
class ComplianceResult:
    image_path: str
    action: ComplianceAction
    confidence: float
    details: Dict
    policy_name: str

class ComplianceEngine:
    """
    Content compliance verification using NudeNet and AgeClassifier.

    Workflow:
    1. Load policy JSON (rapper_explicit.json, eu_standard.json, etc.)
    2. Run NudeNet for nudity detection
    3. Run AgeClassifier for age estimation
    4. Apply policy rules
    5. Hard delete violating content
    """

    def __init__(self, policy_path: str):
        """
        Args:
            policy_path: Path to policy JSON file
        """
        self.policy = self._load_policy(policy_path)
        self.policy_name = Path(policy_path).stem

        # Initialize detection models (lazy load)
        self.nudenet = None
        self.age_classifier = None

        # Quarantine directory for rejected content
        self.quarantine_dir = Path("data/quarantine")
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _load_policy(self, policy_path: str) -> Dict:
        """Load policy configuration"""
        with open(policy_path, 'r') as f:
            return json.load(f)

    def _load_models(self):
        """Lazy load detection models"""
        if self.nudenet is None:
            try:
                from nudenet import NudeDetector
                self.nudenet = NudeDetector()
                print("[COMPLIANCE] NudeNet loaded")
            except ImportError:
                print("[COMPLIANCE] Warning: nudenet not installed")
                self.nudenet = "unavailable"

        if self.age_classifier is None:
            try:
                # Using a face age estimation model
                # Options: deepface, InsightFace, etc.
                from deepface import DeepFace
                self.age_classifier = DeepFace
                print("[COMPLIANCE] Age classifier loaded")
            except ImportError:
                print("[COMPLIANCE] Warning: deepface not installed")
                self.age_classifier = "unavailable"

    async def check_image(self, image_path: str) -> ComplianceResult:
        """
        Check a single image against the loaded policy.

        Returns:
            ComplianceResult with action to take
        """
        self._load_models()

        details = {}

        # Step 1: Age Classification
        if self.age_classifier and self.age_classifier != "unavailable":
            try:
                analysis = self.age_classifier.analyze(
                    image_path,
                    actions=['age'],
                    enforce_detection=False
                )

                if analysis:
                    age = analysis[0].get('age', 25)
                    details['estimated_age'] = age

                    if age < 18:
                        # HARD DELETE - no exceptions
                        self._hard_delete(image_path, "age_violation")
                        return ComplianceResult(
                            image_path=image_path,
                            action=ComplianceAction.HARD_DELETE,
                            confidence=0.95,
                            details=details,
                            policy_name=self.policy_name
                        )
            except Exception as e:
                details['age_error'] = str(e)

        # Step 2: Nudity Detection
        if self.nudenet and self.nudenet != "unavailable":
            try:
                detections = self.nudenet.detect(image_path)

                nudity_labels = []
                max_confidence = 0.0

                for detection in detections:
                    label = detection.get('label', '')
                    confidence = detection.get('score', 0)
                    nudity_labels.append(label)
                    max_confidence = max(max_confidence, confidence)

                details['nudity_labels'] = nudity_labels
                details['nudity_confidence'] = max_confidence

                # Check against policy
                if not self._nudity_allowed(nudity_labels, max_confidence):
                    self._hard_delete(image_path, "nudity_violation")
                    return ComplianceResult(
                        image_path=image_path,
                        action=ComplianceAction.REJECT_NUDITY,
                        confidence=max_confidence,
                        details=details,
                        policy_name=self.policy_name
                    )

            except Exception as e:
                details['nudity_error'] = str(e)

        # Passed all checks
        return ComplianceResult(
            image_path=image_path,
            action=ComplianceAction.PASS,
            confidence=1.0,
            details=details,
            policy_name=self.policy_name
        )

    def _nudity_allowed(self, labels: List[str], confidence: float) -> bool:
        """Check if detected nudity is allowed by policy"""

        # Always-prohibited labels
        prohibited = self.policy.get("prohibited_labels", [
            "EXPOSED_GENITALIA_F",
            "EXPOSED_GENITALIA_M",
            "EXPOSED_ANUS"
        ])

        for label in labels:
            if label in prohibited:
                return False

        # Policy-specific allowances
        allowed = self.policy.get("allowed_labels", [])
        threshold = self.policy.get("confidence_threshold", 0.6)

        for label in labels:
            if label not in allowed and confidence > threshold:
                return False

        return True

    def _hard_delete(self, image_path: str, reason: str):
        """
        Hard delete violating content.
        Moves to quarantine with reason for audit trail.
        """
        src = Path(image_path)
        if not src.exists():
            return

        # Move to quarantine (not permanent delete for audit)
        dst = self.quarantine_dir / f"{reason}_{src.name}"
        shutil.move(str(src), str(dst))

        # Log deletion
        print(f"[COMPLIANCE] HARD DELETE: {src.name} → quarantine ({reason})")

        # Also delete associated metadata
        metadata_path = src.parent / "metadata" / f"{src.stem}.json"
        if metadata_path.exists():
            metadata_path.unlink()

    async def check_all_anchors(
        self,
        anchor_images: Dict[str, 'GeneratedImage']
    ) -> Dict[str, ComplianceResult]:
        """
        Check all anchor images before video generation.

        Args:
            anchor_images: Dict from LocalImageGenerator

        Returns:
            Dict mapping section_name -> ComplianceResult
        """
        results = {}
        passed = 0
        failed = 0

        print(f"\n[COMPLIANCE] === Checking {len(anchor_images)} images ===")
        print(f"[COMPLIANCE] Policy: {self.policy_name}")

        for section_name, anchor in anchor_images.items():
            result = await self.check_image(anchor.image_path)
            results[section_name] = result

            if result.action == ComplianceAction.PASS:
                passed += 1
                print(f"[COMPLIANCE] ✓ {section_name}: PASS")
            else:
                failed += 1
                print(f"[COMPLIANCE] ✗ {section_name}: {result.action.value}")

        print(f"[COMPLIANCE] === Results: {passed} passed, {failed} failed ===\n")

        return results
```

### 2.4 Policy JSON Examples

**File:** `backend/policies/rapper_explicit.json`

```json
{
    "name": "rapper_explicit",
    "description": "Urban/hip-hop music video standards",
    "allowed_labels": [
        "EXPOSED_BELLY",
        "EXPOSED_BUTTOCKS",
        "FEMALE_BREAST_COVERED",
        "MALE_BREAST_EXPOSED"
    ],
    "prohibited_labels": [
        "EXPOSED_GENITALIA_F",
        "EXPOSED_GENITALIA_M",
        "EXPOSED_ANUS",
        "FEMALE_BREAST_EXPOSED"
    ],
    "confidence_threshold": 0.7,
    "age_minimum": 18,
    "notes": "Allows revealing clothing, prohibits explicit nudity"
}
```

**File:** `backend/policies/eu_standard.json`

```json
{
    "name": "eu_standard",
    "description": "European broadcast standards",
    "allowed_labels": [
        "EXPOSED_BELLY",
        "EXPOSED_BUTTOCKS",
        "FEMALE_BREAST_EXPOSED",
        "MALE_BREAST_EXPOSED"
    ],
    "prohibited_labels": [
        "EXPOSED_GENITALIA_F",
        "EXPOSED_GENITALIA_M",
        "EXPOSED_ANUS"
    ],
    "confidence_threshold": 0.8,
    "age_minimum": 18,
    "notes": "Allows artistic nudity per European broadcasting norms"
}
```

---

## 3. Updated Pipeline Orchestration

### 3.1 New Pipeline Flow

```
Audio Upload
    ↓
[Phase 1] Audio Analysis (unchanged - librosa)
    ↓
[Phase 2] Concept Generation (unchanged - GPT-4)
    ↓
[Phase 3] Storyboard Generation (unchanged - generates section prompts)
    ↓
[Phase 4] LOCAL Image Generation ← NEW
    │   LocalImageGenerator.generate_all_sections()
    │   One anchor image per section (Intro, Verse 1, etc.)
    ↓
[Phase 4.5] COMPLIANCE GATE ← NEW
    │   ComplianceEngine.check_all_anchors()
    │   NudeNet + AgeClassifier
    │   Hard delete violations
    ↓
[Phase 5] LOCAL Video Generation ← NEW
    │   LocalVideoGenerator.generate_all_sections()
    │   4-second loops to fill section duration
    ↓
[Phase 6] Video Assembly (updated for loops)
    ↓
MP4 Output
```

### 3.2 SongStructure Threading

The existing `StoryboardScene` dataclass maps cleanly to sections:

```python
# Current storyboard output (generator.py:274-295)
[
    {
        'timestamp_start': 0.0,
        'timestamp_end': 15.0,
        'description': 'Opening scene...',
        'image_prompt': 'Dramatic wide shot...',
        'motion_prompt': 'Slow camera drift...',
        'scene_type': 'standard',
        'energy': 0.3
    },
    ...
]

# Transform to section-based structure:
{
    "sections": [
        {
            "name": "intro",
            "start": 0.0,
            "end": 15.0,
            "prompt": "Dramatic wide shot...",
            "motion_prompt": "Slow camera drift...",
            "style": "cinematic"
        },
        {
            "name": "verse_1",
            "start": 15.0,
            "end": 45.0,
            "prompt": "...",
            "motion_prompt": "..."
        }
    ]
}
```

**Transformation function:**

```python
def storyboard_to_song_structure(storyboard: List[Dict]) -> Dict:
    """
    Convert scene-based storyboard to section-based structure.
    Groups consecutive scenes with same section label.
    """
    sections = []
    current_section = None

    for scene in storyboard:
        section_label = scene.get('section', detect_section(scene))

        if current_section is None or current_section['name'] != section_label:
            if current_section:
                sections.append(current_section)
            current_section = {
                'name': section_label,
                'start': scene['timestamp_start'],
                'end': scene['timestamp_end'],
                'prompt': scene.get('image_prompt', ''),
                'motion_prompt': scene.get('motion_prompt', ''),
                'style': scene.get('visual_style', 'cinematic')
            }
        else:
            # Extend current section
            current_section['end'] = scene['timestamp_end']

    if current_section:
        sections.append(current_section)

    return {'sections': sections}
```

---

## 4. Files to Modify

| File | Changes |
|------|---------|
| `backend/src/assets/generator.py` | Remove all API providers, add import for `LocalImageGenerator` |
| `backend/src/assets/video_generator.py` | Remove Luma/Replicate, add import for `LocalVideoGenerator` |
| `backend/main.py` | Update `generate_video_pipeline()` to use local generators + compliance gate |
| `backend/src/video/assembler.py` | Update to handle loop-based video structure |

### 4.1 main.py Changes (Lines ~1417-1525)

```python
async def generate_video_pipeline(task_id: str, audio_path: str, ...):
    # ... existing Phase 1-3 unchanged ...

    # Phase 4: LOCAL Image Generation
    from src.assets.local_generator import LocalImageGenerator

    image_gen = LocalImageGenerator(
        model_path="models/flux1-schnell-uncensored.gguf"  # Optional
    )

    song_structure = storyboard_to_song_structure(storyboard)
    anchor_images = await image_gen.generate_all_sections(song_structure)
    image_gen.unload_model()  # Free VRAM for video

    # Phase 4.5: Compliance Gate
    from src.compliance.engine import ComplianceEngine

    policy_path = f"policies/{user_policy}.json"  # e.g., "rapper_explicit"
    compliance = ComplianceEngine(policy_path)
    results = await compliance.check_all_anchors(anchor_images)

    # Filter out failed sections
    passed_anchors = {
        name: img for name, img in anchor_images.items()
        if results[name].action == ComplianceAction.PASS
    }

    if not passed_anchors:
        raise ValueError("All images failed compliance check")

    # Phase 5: LOCAL Video Generation
    from src.assets.local_video_generator import LocalVideoGenerator

    video_gen = LocalVideoGenerator()
    video_loops = await video_gen.generate_all_sections(
        song_structure,
        passed_anchors
    )
    video_gen.unload_model()

    # Phase 6: Assembly (updated for loops)
    # ... existing assembly with loop support ...
```

---

## 5. New Dependencies

Add to `backend/requirements.txt`:

```
# Local GPU Generation
torch>=2.1.0
diffusers>=0.32.0
transformers>=4.40.0
sentencepiece>=0.2.0
accelerate>=1.0.0

# Compliance
nudenet>=3.0.0
deepface>=0.0.79

# Optional: GGUF support
# gguf>=0.1.0  # If using quantized models
```

---

## 6. Memory Management Strategy

```
VRAM Budget: 16GB

Phase 4 (Flux):
├── Load Flux.1-schnell (~12GB with CPU offload)
├── Generate all anchor images
└── Unload (del + gc + empty_cache)

Phase 4.5 (Compliance):
├── NudeNet (~1GB)
├── DeepFace (~500MB)
└── Sequential image checks (no unload needed)

Phase 5 (LTX-Video):
├── Load LTX-Video (~10GB)
├── Generate all loops
└── Unload before assembly
```

---

## 7. Testing Checklist

- [ ] Flux generates correct 1024x576 images
- [ ] LTX generates 4-second loops at 768x512
- [ ] Compliance correctly flags underage content
- [ ] Compliance correctly applies policy-specific nudity rules
- [ ] Video assembler concatenates loops correctly
- [ ] Audio sync maintained across loop boundaries
- [ ] Memory stays under 16GB throughout pipeline
- [ ] End-to-end test with sample audio file
