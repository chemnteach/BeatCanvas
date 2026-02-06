# Implementation Plan: Phase 8 -- Hybrid AnimateDiff + WAN 2.2 Video Generation

Generated: 2026-02-06

---

## Goal

Replace the SVD-XT video generation pipeline (poor quality -- motion blur, limb deformation) with a hybrid approach: AnimateDiff-Lightning for standard scenes (70-80%) and WAN 2.2 FP8 for hero scenes (20-30%). Both pipelines feed into the existing RAFT interpolator for 60fps output.

**Why hybrid:** AnimateDiff-Lightning is fast (~5.6GB VRAM, 4-step generation, text-to-video with image conditioning) and ideal for bulk scene generation. WAN 2.2 is state-of-the-art quality (image-to-video) but requires ~14-16GB VRAM and runs sequentially. Using both maximizes throughput for standard scenes while preserving quality for hero moments (chorus, drops).

---

## Research Summary

### AnimateDiff-Lightning (ByteDance)
- **Architecture:** SD 1.5 base model + motion adapter (distilled to 4-step)
- **HuggingFace repo:** `ByteDance/AnimateDiff-Lightning`
- **Best base models for realism:** `emilianJR/epiCRealism`, `cyberdelia/CyberRealistic`, `SG161222/Realistic_Vision_V5.1_noVAE`
- **Output:** 16 frames (configurable up to 32, but quality degrades beyond 16)
- **VRAM:** ~5.6GB with fp16 (allows parallel instances)
- **Image conditioning:** Via `AnimateDiffSparseControlNetPipeline` + SparseCtrl RGB encoder
- **Prompt limit:** 75 tokens (CLIP tokenizer)
- **Scheduler:** `EulerDiscreteScheduler` with `timestep_spacing="trailing"`, `beta_schedule="linear"`
- **Key finding:** `guidance_scale=1.0` works well; some base models benefit from higher CFG

### WAN 2.2 I2V A14B
- **Architecture:** MoE (Mixture-of-Experts) -- 2 experts, 14B active params per step
- **HuggingFace repo:** `Wan-AI/Wan2.2-I2V-A14B-Diffusers`
- **CRITICAL VRAM ISSUE:** Full fp16 requires **80GB VRAM** -- far beyond 16GB budget
- **FP8 quantized:** `wangkanai/wan22-fp8-i2v` -- ~14GB model, **minimum 16GB VRAM** with CPU offload
- **GGUF Q4_K_S:** ~8.2GB file size, runs on 12GB+ (ComfyUI-only, not diffusers-native)
- **Output:** 81 frames at 480p (720p less stable)
- **Inference steps:** 40 (FP8 may work with fewer)
- **Key finding:** FP8 with `enable_model_cpu_offload()` is the path for 16GB GPUs; GGUF is fallback

### RAFT Interpolation Compatibility
- Current: 25 SVD frames -> 240 frames (9 intermediate per gap)
- AnimateDiff: 16 frames -> 240 frames = `(240-16)/15 = 14.93` -> **14 intermediate per gap** (226 total, 3.77s @ 60fps) or adjust target
- WAN 2.2: 81 frames -> 240 frames = `(240-81)/80 = 1.99` -> **2 intermediate per gap** (241 total, 4.02s @ 60fps)
- **Both work** -- RAFT `interpolate_frames` is frame-count agnostic. The math in `render_video_svd.py:interpolate_with_raft()` handles arbitrary input counts.

---

## Existing Codebase Analysis

### Files That Will Be Modified

| File | Role | Changes |
|------|------|---------|
| `backend/library/optics_presets.yaml` | Style config | Add AnimateDiff + WAN params per style |
| `backend/config/settings.yaml` | Global config | Add `animatediff` and `wan` config sections |
| `backend/config/checkpoints.yaml` | Model registry | Add AnimateDiff + WAN model entries |
| `backend/src/cinematography/__init__.py` | Module exports | Export new generator classes |

### Files That Will Be Created

| File | Role |
|------|------|
| `backend/scripts/render_video_animatediff.py` | AnimateDiff test script (mirrors `render_video_svd.py`) |
| `backend/scripts/render_video_wan.py` | WAN 2.2 test script |
| `backend/scripts/render_video_hybrid.py` | Hybrid pipeline test script |
| `backend/src/cinematography/animatediff_generator.py` | AnimateDiff production wrapper |
| `backend/src/cinematography/wan_generator.py` | WAN 2.2 production wrapper |
| `backend/src/cinematography/video_generator_base.py` | Abstract base for both generators |
| `backend/src/cinematography/hybrid_router.py` | Scene-type routing logic |

### Files That Will Be Kept As-Is

| File | Reason |
|------|--------|
| `backend/src/cinematography/raft_interpolator.py` | Already frame-count agnostic; no changes needed |
| `backend/src/cinematography/physics_motion_tracker.py` | Skeletal checking applies to any video source |
| `backend/src/cinematography/temporal_consistency.py` | Keep for SVD fallback; not used by new generators |
| `backend/src/cinematography/prompt_composer.py` | 75-token CLIP limit already documented; AnimateDiff uses same tokenizer |
| `backend/src/cinematography/style_logic.py` | Style detection unchanged; add new params to YAML only |

### Key Patterns to Follow

1. **VRAM lifecycle:** Kill before swap (established in `VRAMManager.kill()` + `LocalVideoGenerator.kill()`)
2. **Frame format:** numpy BGR arrays (all existing code uses OpenCV BGR convention)
3. **Heartbeat callbacks:** JSON progress emission pattern (from `HeartbeatCallback`)
4. **Config loading:** YAML-driven with `src.utils.config.SETTINGS` pattern
5. **Prompt composition:** Director inject first, subject second, quality tokens last (from `prompt_composer.py`)

---

## Implementation Phases

---

### Phase 8.1: AnimateDiff Foundation (2-3 hours) -- PRIORITY

**Goal:** Working text-to-video pipeline with AnimateDiff-Lightning replacing SVD-XT for a single test scene.

#### Step 1: Install Dependencies (15 min)

Add to `backend/requirements.txt`:

```
# Phase 8: AnimateDiff + WAN Video Generation
diffusers>=0.34.0          # Required for AnimateDiff + WAN pipelines
safetensors>=0.4.0         # Model loading
huggingface-hub>=0.20.0    # Model downloads
accelerate>=0.25.0         # CPU offload support
```

**Note:** `diffusers` may already be installed (SVD uses it), but pin to >=0.34.0 for WAN 2.2 support. Check with `pip show diffusers` first.

Run:
```bash
cd /home/craig/AI_Workspace/synterra/beatcanvas/backend
pip install --upgrade diffusers safetensors huggingface-hub accelerate
```

#### Step 2: Download AnimateDiff Models (20 min)

Models will auto-download on first use via HuggingFace Hub. Pre-download for predictability:

```bash
# AnimateDiff-Lightning 4-step adapter (~400MB)
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download('ByteDance/AnimateDiff-Lightning', 'animatediff_lightning_4step_diffusers.safetensors')
print('AnimateDiff-Lightning adapter downloaded')
"

# epiCRealism base model (~2GB, SD 1.5)
python -c "
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained('emilianJR/epiCRealism', torch_dtype='float16')
print('epiCRealism base model downloaded')
del pipe
"

# SparseCtrl RGB encoder for image conditioning (~500MB)
python -c "
from diffusers.models import SparseControlNetModel
cn = SparseControlNetModel.from_pretrained('guoyww/animatediff-sparsectrl-rgb', torch_dtype='float16')
print('SparseCtrl RGB downloaded')
del cn
"
```

**Disk space required:** ~3GB total for AnimateDiff models.

#### Step 3: Create `render_video_animatediff.py` Test Script (60 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/scripts/render_video_animatediff.py`

This script mirrors the structure of `render_video_svd.py` (same 6-step pipeline pattern) but uses AnimateDiff-Lightning instead of SVD-XT.

**Critical code -- AnimateDiff pipeline loading:**

```python
import torch
from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

# Configuration
ANIMATEDIFF_STEP = 4  # 4-step distilled model
ANIMATEDIFF_REPO = "ByteDance/AnimateDiff-Lightning"
ANIMATEDIFF_CKPT = f"animatediff_lightning_{ANIMATEDIFF_STEP}step_diffusers.safetensors"
ANIMATEDIFF_BASE = "emilianJR/epiCRealism"  # SD 1.5 photorealistic base
ANIMATEDIFF_NUM_FRAMES = 16
ANIMATEDIFF_VRAM_ESTIMATE_GB = 5.6

def load_animatediff_pipeline():
    """Load AnimateDiff-Lightning pipeline with 4-step adapter."""
    device = "cuda"
    dtype = torch.float16

    print(f"   Loading MotionAdapter from {ANIMATEDIFF_REPO}...")
    adapter = MotionAdapter().to(device, dtype)
    adapter.load_state_dict(
        load_file(hf_hub_download(ANIMATEDIFF_REPO, ANIMATEDIFF_CKPT), device=device)
    )

    print(f"   Loading base model: {ANIMATEDIFF_BASE}...")
    pipe = AnimateDiffPipeline.from_pretrained(
        ANIMATEDIFF_BASE,
        motion_adapter=adapter,
        torch_dtype=dtype,
    ).to(device)

    # Configure scheduler for Lightning
    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config,
        timestep_spacing="trailing",
        beta_schedule="linear",
    )

    # Memory optimizations
    pipe.enable_vae_slicing()

    print(f"   VRAM after load: {torch.cuda.memory_allocated() / 1e9:.2f}GB")
    return pipe
```

**Critical code -- text-to-video generation:**

```python
def generate_video_animatediff(
    pipe,
    prompt: str,
    negative_prompt: str = "",
    num_frames: int = ANIMATEDIFF_NUM_FRAMES,
    guidance_scale: float = 1.0,
    seed: int = -1,
    width: int = 576,
    height: int = 1024,
) -> list:
    """
    Generate video frames with AnimateDiff-Lightning.

    Returns:
        List of numpy BGR frames (H, W, 3)
    """
    generator = None
    if seed >= 0:
        generator = torch.Generator(device="cuda").manual_seed(seed)

    output = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=ANIMATEDIFF_STEP,
        guidance_scale=guidance_scale,
        num_frames=num_frames,
        width=width,
        height=height,
        generator=generator,
    )

    # Convert PIL frames to numpy BGR (match existing convention)
    frames = []
    for frame_pil in output.frames[0]:
        frame_np = np.array(frame_pil)
        frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        frames.append(frame_bgr)

    return frames
```

**Full script structure** (follows `render_video_svd.py` pattern):
1. Load optics presets
2. Compose prompt (reuse `CinematographyEngine`)
3. Show configuration / dry-run exit
4. Kill any existing GPU models
5. Load AnimateDiff + generate 16 frames
6. Kill AnimateDiff, load RAFT, interpolate 16 -> 240 frames, export video

**CLI arguments:** Same as SVD script (`--source`, `--output`, `--style`, `--dry-run`, `--benchmark`) plus `--prompt` for direct text input.

#### Step 4: Update RAFT Interpolation Math (15 min)

The existing `interpolate_with_raft()` in `render_video_svd.py` (lines 301-380) already handles arbitrary frame counts via this calculation:

```python
num_intermediate = (target_total_frames - n_source) // n_gaps
```

For 16 AnimateDiff frames:
- `n_source = 16`, `n_gaps = 15`
- `target_total_frames = 240` (4s @ 60fps)
- `num_intermediate = (240 - 16) // 15 = 14`
- Actual output: `16 + 15 * 14 = 226 frames` = 3.77s @ 60fps

**Decision needed:** Either accept 3.77s duration or adjust target to 4.0s:
- Option A: Accept 3.77s (simplest)
- Option B: Set `target_total_frames = 16 + 15 * 15 = 241` -> 4.02s (round up intermediate to 15)
- **Recommended:** Option B -- set `num_intermediate = math.ceil((target_total_frames - n_source) / n_gaps)`

The RAFT function should be **copied** into the new script (not modified in `render_video_svd.py`) to avoid breaking the existing SVD pipeline. Later in Phase 8.4, a shared utility will be extracted.

#### Step 5: Test Beach Walking Scene (30 min)

```bash
cd /home/craig/AI_Workspace/synterra/beatcanvas/backend

# Text-to-video test with BEACH_CASUAL style
python scripts/render_video_animatediff.py \
    --style STYLE_BEACH_CASUAL \
    --prompt "muscular man walking along the beach, golden hour, natural lighting, relaxed" \
    --output /mnt/c/Users/craig/Downloads/synterra_production

# Compare: Open both SVD and AnimateDiff outputs side by side
```

#### Testing Checkpoint 8.1

| Criterion | How to Verify |
|-----------|--------------|
| AnimateDiff loads without OOM | VRAM usage < 7GB after load |
| 16 frames generated | Output frame count = 16 |
| No blur/deformation | Visual inspection -- hands, limbs, face intact |
| RAFT interpolation works | Output = ~240 frames, 60fps, ~4s duration |
| Video exports to MP4 | File exists in output dir, plays in VLC |
| Quality better than SVD | Side-by-side comparison -- less jitter, cleaner anatomy |

#### Rollback Strategy

If AnimateDiff produces worse quality than SVD:
1. Try different base model (`SG161222/Realistic_Vision_V5.1_noVAE` instead of epiCRealism)
2. Increase steps from 4 to 8 (use `animatediff_lightning_8step_diffusers.safetensors`)
3. If still worse, AnimateDiff becomes the "draft" generator and SVD remains for production

If RAFT interpolation fails with 16 frames:
1. Check frame dimensions match (576x1024)
2. Check dtype is uint8 BGR
3. Fall back to `num_frames=25` (AnimateDiff supports up to 32)

---

### Phase 8.2: AnimateDiff Production Integration (1-2 hours)

**Goal:** Production-ready AnimateDiff wrapper with prompt optimization, seed consistency, batch processing, and config-driven operation.

#### Step 1: Optimize Prompts for 75-Token Limit (30 min)

The existing `prompt_composer.py` already documents the 75-token CLIP limit (line 23: `CLIP_TOKEN_LIMIT = 75`). AnimateDiff uses the same SD 1.5 CLIP tokenizer, so this is already handled.

**However**, the current `director_inject` prompts in `optics_presets.yaml` are designed for SDXL (which has a 77+77 token dual encoder). For SD 1.5 AnimateDiff, we must be more aggressive.

Current token counts (estimated at ~1.3 tokens per word):

| Style | Current `prompt_tokens` | Est. Tokens | Over Limit? |
|-------|------------------------|-------------|-------------|
| HIGH_VELOCITY_ACTION | "score_9, score_8_up, (muscular man throwing..." | ~45 | No |
| URBAN_LUXURY | "(iced out jewelry:1.4), (diamond refraction:1.5)..." | ~30 | No |
| PHYSICAL_DRAMA | "score_9, score_8_up, (anatomical structural integrity:1.4)..." | ~50 | Tight |
| BEACH_CASUAL | "score_9, score_8_up, natural lighting, golden hour..." | ~20 | No |

**Action:** Remove `score_9, score_8_up` from AnimateDiff prompts (these are SDXL Pony triggers, meaningless for SD 1.5). This saves ~8 tokens.

Add to `optics_presets.yaml` under each production style:

```yaml
  STYLE_BEACH_CASUAL:
    # ... existing fields ...
    # AnimateDiff-specific prompt (SD 1.5, 75 token limit, no SDXL triggers)
    animatediff_prompt_tokens: "natural lighting, golden hour, relaxed atmosphere, detailed skin"
    animatediff_guidance_scale: 1.0
    animatediff_num_frames: 16
```

#### Step 2: Create `animatediff_generator.py` Production Wrapper (45 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/src/cinematography/animatediff_generator.py`

```python
"""
AnimateDiff-Lightning Video Generator for BeatCanvas Production.

Text-to-video generation using AnimateDiff-Lightning (4-step distilled).
Optimized for SD 1.5 base models with 75-token CLIP limit.

VRAM Budget: ~5.6GB (allows 2-3 parallel instances on 16GB GPU)
Frame Output: 16 frames -> RAFT interpolation to target FPS
"""

class AnimateDiffGenerator:
    """
    AnimateDiff-Lightning video generator.

    Integrates with:
    - CinematographyEngine for prompt composition
    - optics_presets.yaml for style-specific parameters
    - VRAMManager for coordinated GPU lifecycle
    """

    VRAM_ESTIMATE_GB = 5.6

    def __init__(self, vram_manager=None, base_model="emilianJR/epiCRealism"):
        self.vram_manager = vram_manager
        self.base_model = base_model
        self.pipe = None
        self.loaded = False

    def load(self):
        """Load AnimateDiff pipeline. Call once per session."""
        # ... (as shown in Phase 8.1 Step 3)

    def kill(self) -> float:
        """Kill pipeline and reclaim VRAM. Returns VRAM after kill."""
        # ... (follows LocalVideoGenerator.kill() pattern)

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 16,
        guidance_scale: float = 1.0,
        seed: int = -1,
        width: int = 576,
        height: int = 1024,
    ) -> list:
        """
        Generate video frames.

        Returns:
            List of numpy BGR frames (H, W, 3)
        """
        # ... (as shown in Phase 8.1 Step 3)

    def generate_batch(
        self,
        scenes: list,
        max_parallel: int = 1,
    ) -> dict:
        """
        Generate multiple scenes sequentially (parallel TBD).

        Args:
            scenes: List of dicts with {prompt, negative_prompt, seed, ...}
            max_parallel: Max concurrent generations (1 = sequential)

        Returns:
            Dict mapping scene index to frame list
        """
        # Sequential for now; parallel in future optimization
        results = {}
        for i, scene in enumerate(scenes):
            print(f"[AnimateDiff] Generating scene {i+1}/{len(scenes)}")
            frames = self.generate(**scene)
            results[i] = frames
        return results
```

**Key design decisions:**
- Sequential batch processing first (parallel adds OOM risk)
- Same `kill()` pattern as `LocalVideoGenerator` for VRAM management
- Returns numpy BGR frames to match existing pipeline convention

#### Step 3: Seed Locking for Character Consistency (20 min)

AnimateDiff with the same seed + same prompt produces visually consistent outputs. This is sufficient for maintaining character appearance across scenes within a section.

**Implementation in batch generation:**

```python
def generate_section(self, scenes: list, section_seed: int) -> dict:
    """Generate scenes for a music section with locked seed."""
    results = {}
    for i, scene in enumerate(scenes):
        # Same seed for all scenes in a section -> character consistency
        scene["seed"] = section_seed
        frames = self.generate(**scene)
        results[i] = frames
    return results
```

**Limitation:** Seed locking only works when prompts are similar. Different prompts with the same seed produce different outputs. For strong character consistency across very different scenes, IP-Adapter would be needed (Phase 8.5 future work).

#### Step 4: Update `optics_presets.yaml` (15 min)

Add AnimateDiff-specific parameters to each production style:

```yaml
production_styles:
  STYLE_HIGH_VELOCITY_ACTION:
    # ... existing SVD fields ...
    # AnimateDiff parameters (SD 1.5, 75 token limit)
    animatediff:
      prompt_tokens: "(muscular man throwing explosive fast haymaker punch:1.5), stationary camera, high contrast, detailed skin"
      guidance_scale: 1.2
      num_frames: 16
      base_model: "emilianJR/epiCRealism"

  STYLE_URBAN_LUXURY:
    # ... existing SVD fields ...
    animatediff:
      prompt_tokens: "(iced out jewelry:1.4), (diamond refraction:1.5), heavy gold chains, volumetric urban haze"
      guidance_scale: 1.0
      num_frames: 16
      base_model: "emilianJR/epiCRealism"

  STYLE_BEACH_CASUAL:
    # ... existing SVD fields ...
    animatediff:
      prompt_tokens: "natural lighting, golden hour, relaxed atmosphere, detailed skin"
      guidance_scale: 1.0
      num_frames: 16
      base_model: "emilianJR/epiCRealism"

  STYLE_PHYSICAL_DRAMA:
    # ... existing SVD fields ...
    animatediff:
      prompt_tokens: "(anatomical structural integrity:1.4), (raw visceral interaction:1.4), realistic skin, detailed skin"
      guidance_scale: 1.0
      num_frames: 16
      base_model: "emilianJR/epiCRealism"
```

#### Step 5: Add to `settings.yaml` (10 min)

```yaml
# AnimateDiff-Lightning configuration
animatediff:
  repo: "ByteDance/AnimateDiff-Lightning"
  step: 4  # 1, 2, 4, or 8
  base_model: "emilianJR/epiCRealism"

  resolution:
    width: 576
    height: 1024

  defaults:
    num_frames: 16
    guidance_scale: 1.0
    num_inference_steps: 4  # Must match step

  vram_estimate_gb: 5.6
  max_parallel: 1  # Conservative; increase after testing
```

#### Testing Checkpoint 8.2

| Criterion | How to Verify |
|-----------|--------------|
| All 4 styles generate successfully | Run test script with each `--style` option |
| Prompts under 75 tokens | Print `estimated_tokens` from `ComposedPrompt`; verify < 75 |
| Seed consistency works | Generate 3 scenes with same seed; compare character appearance |
| Batch generation works | Generate 5 scenes sequentially; no OOM |
| Config loads from YAML | `animatediff` section in `optics_presets.yaml` parsed correctly |

#### Rollback Strategy

If prompt optimization causes quality loss:
1. Try different base model (CyberRealistic V3.3 via `cyberdelia/CyberRealistic`)
2. Increase guidance_scale to 1.5-2.0 for more prompt adherence
3. Use 8-step model for better quality at cost of speed

---

### Phase 8.3: WAN 2.2 Hero Scenes (4-6 hours) -- ENHANCEMENT

**Goal:** High-quality image-to-video generation for hero scenes using WAN 2.2 FP8 within 16GB VRAM budget.

#### CRITICAL: VRAM Reality Check

**Research finding:** WAN 2.2 A14B full fp16 requires **80GB VRAM**. This is NOT feasible on a 16GB GPU.

**Viable paths for 16GB:**

| Approach | VRAM | Quality | Speed | Complexity |
|----------|------|---------|-------|------------|
| FP8 quantized + CPU offload | ~14-16GB | Good (minimal degradation) | Slow (~10-15 min) | Medium |
| GGUF Q4_K_S via ComfyUI | ~8-12GB | Acceptable | Moderate | High (ComfyUI dependency) |
| WAN 2.1 1.3B model | ~8GB | Lower (smaller model) | Fast (~4 min) | Low |
| **Recommended: FP8 + CPU offload** | **~15GB** | **Good** | **~10 min** | **Medium** |

**Decision:** Use FP8 quantized model with `enable_model_cpu_offload()`. If OOM occurs, fall back to WAN 2.1 1.3B or reduce resolution to 480p.

#### Step 1: Install WAN 2.2 Dependencies (15 min)

WAN 2.2 support requires diffusers from the main branch (already installed in Phase 8.1 if >=0.34.0):

```bash
# Verify diffusers version supports WAN
python -c "from diffusers import WanImageToVideoPipeline; print('WAN pipeline available')"
```

If not available:
```bash
pip install git+https://github.com/huggingface/diffusers
```

#### Step 2: Download WAN 2.2 FP8 Models (30 min)

```bash
# WAN 2.2 I2V FP8 models (~28GB total for both experts)
python -c "
from huggingface_hub import snapshot_download
snapshot_download('wangkanai/wan22-fp8-i2v', local_dir='/home/craig/AI_Workspace/synterra/models/wan22-fp8-i2v')
print('WAN 2.2 FP8 I2V downloaded')
"
```

**Alternative (recommended for first test):** Use the official diffusers model with bfloat16 and aggressive CPU offloading:

```bash
python -c "
from diffusers import WanImageToVideoPipeline
import torch
pipe = WanImageToVideoPipeline.from_pretrained('Wan-AI/Wan2.2-I2V-A14B-Diffusers', torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
print('WAN 2.2 pipeline loaded with CPU offload')
del pipe
"
```

**Disk space required:** ~28-56GB depending on variant.

#### Step 3: Create `render_video_wan.py` Test Script (90 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/scripts/render_video_wan.py`

**Critical code -- WAN 2.2 pipeline loading with memory optimization:**

```python
import torch
import numpy as np
from diffusers import WanImageToVideoPipeline
from diffusers.utils import load_image

WAN_MODEL_ID = "Wan-AI/Wan2.2-I2V-A14B-Diffusers"
WAN_DTYPE = torch.bfloat16
WAN_NUM_FRAMES = 81
WAN_VRAM_ESTIMATE_GB = 15.0

def load_wan_pipeline():
    """
    Load WAN 2.2 I2V pipeline with aggressive memory optimization.

    Uses CPU offload to fit within 16GB VRAM.
    """
    print(f"   Loading WAN 2.2: {WAN_MODEL_ID}")
    print(f"   Precision: bfloat16 with CPU offload")

    pipe = WanImageToVideoPipeline.from_pretrained(
        WAN_MODEL_ID,
        torch_dtype=WAN_DTYPE,
    )

    # CRITICAL: CPU offload -- moves model components to/from GPU as needed
    pipe.enable_model_cpu_offload()

    # Additional memory optimizations
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()

    print(f"   WAN 2.2 pipeline ready (CPU offload enabled)")
    return pipe


def generate_video_wan(
    pipe,
    image_path: str,
    prompt: str,
    negative_prompt: str = "",
    num_frames: int = WAN_NUM_FRAMES,
    guidance_scale: float = 3.5,
    num_inference_steps: int = 40,
    seed: int = -1,
) -> list:
    """
    Generate video from image using WAN 2.2 I2V.

    Args:
        pipe: WAN I2V pipeline
        image_path: Path to source image (from RealVisXL)
        prompt: Text description of desired motion
        negative_prompt: Negative prompt
        num_frames: Frame count (81 default)
        guidance_scale: Text guidance strength
        num_inference_steps: Denoising steps
        seed: Random seed (-1 for random)

    Returns:
        List of numpy BGR frames (H, W, 3)
    """
    image = load_image(image_path)

    # Calculate dimensions following WAN requirements
    # Must be divisible by vae_scale_factor * patch_size
    max_area = 480 * 832  # 480p area
    aspect_ratio = image.height / image.width
    mod_value = pipe.vae_scale_factor_spatial * pipe.transformer.config.patch_size[1]
    height = round(np.sqrt(max_area * aspect_ratio)) // mod_value * mod_value
    width = round(np.sqrt(max_area / aspect_ratio)) // mod_value * mod_value
    image = image.resize((width, height))

    generator = None
    if seed >= 0:
        generator = torch.Generator(device="cpu").manual_seed(seed)

    output = pipe(
        image=image,
        prompt=prompt,
        negative_prompt=negative_prompt,
        height=height,
        width=width,
        num_frames=num_frames,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
        generator=generator,
    ).frames[0]

    # Convert PIL frames to numpy BGR
    frames = []
    for frame_pil in output:
        frame_np = np.array(frame_pil)
        frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        frames.append(frame_bgr)

    return frames
```

**Important notes:**
- WAN generates at the resolution of the input image (respecting `mod_value` alignment)
- For 9:16 vertical video input at 576x1024, WAN will calculate an appropriate 480p resolution
- The `enable_model_cpu_offload()` is essential -- without it, 16GB VRAM will OOM

#### Step 4: Handle Resolution Mismatch (20 min)

Current pipeline uses 576x1024 (9:16 vertical). WAN 2.2 at 480p area gives approximately 416x736 or similar. The output frames will need upscaling to match the AnimateDiff output resolution.

**Solution:** Resize WAN output frames to target resolution after generation, before RAFT interpolation:

```python
def resize_frames_to_target(frames: list, target_width: int, target_height: int) -> list:
    """Resize frames to target resolution using Lanczos interpolation."""
    resized = []
    for frame in frames:
        resized_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
        resized.append(resized_frame)
    return resized
```

#### Step 5: Test Hero Scene (30 min)

```bash
# WAN 2.2 test with a hero scene image
python scripts/render_video_wan.py \
    --source /mnt/c/Users/craig/Downloads/synterra_production/cinematography_test_beach_casual_latest.png \
    --prompt "man walking confidently along the beach, waves crashing, golden hour sun, camera tracking shot" \
    --output /mnt/c/Users/craig/Downloads/synterra_production
```

#### Step 6: OOM Fallback Plan (if needed)

If WAN 2.2 A14B OOMs even with CPU offload:

**Fallback 1:** Reduce frames from 81 to 49 (still more than AnimateDiff's 16):
```python
num_frames = 49  # Reduces memory proportionally
```

**Fallback 2:** Use 480p with smaller area:
```python
max_area = 384 * 672  # Reduced from 480 * 832
```

**Fallback 3:** Use WAN 2.1 1.3B model instead (guaranteed to fit in 16GB):
```python
WAN_MODEL_ID = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"  # or the 1.3B if available
```

**Fallback 4:** Use GGUF Q4_K_S via ComfyUI API (deferred to Phase 8.5):
```bash
# ComfyUI running as server + API calls from Python
comfyui --listen 0.0.0.0 --port 8188
```

#### Testing Checkpoint 8.3

| Criterion | How to Verify |
|-----------|--------------|
| WAN pipeline loads without OOM | Peak VRAM < 16GB during generation |
| 81 frames generated | Output frame count = 81 |
| Quality exceeds AnimateDiff | Side-by-side: smoother motion, more realistic |
| RAFT interpolation works with 81 frames | Output ~240 frames at 60fps |
| Resolution matches target | Output video is 576x1024 (after resize) |
| Total generation time acceptable | < 15 min per scene |

#### Rollback Strategy

If WAN 2.2 cannot run on 16GB:
1. Reduce to 49 frames, 480p
2. Fall back to WAN 2.1 1.3B
3. If all WAN variants fail: AnimateDiff for ALL scenes (no hero distinction)
4. WAN becomes a future upgrade when GPU is upgraded to 24GB+

---

### Phase 8.4: Hybrid Pipeline Integration (2-3 hours)

**Goal:** Seamless routing between AnimateDiff (standard) and WAN 2.2 (hero) with a unified interface.

#### Step 1: Create Abstract Base Class (20 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/src/cinematography/video_generator_base.py`

```python
"""
Abstract base class for video generators.

All video generators (AnimateDiff, WAN, SVD) implement this interface
so the hybrid router can treat them uniformly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class VideoGeneratorBase(ABC):
    """Abstract video generator interface."""

    @abstractmethod
    def load(self) -> None:
        """Load model into GPU memory."""
        ...

    @abstractmethod
    def kill(self) -> float:
        """Unload model and reclaim VRAM. Returns VRAM usage after kill."""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 16,
        seed: int = -1,
        width: int = 576,
        height: int = 1024,
        **kwargs,
    ) -> List[np.ndarray]:
        """
        Generate video frames.

        Returns:
            List of numpy BGR frames (H, W, 3)
        """
        ...

    @property
    @abstractmethod
    def vram_estimate_gb(self) -> float:
        """Estimated VRAM usage when loaded."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable generator name."""
        ...

    @property
    @abstractmethod
    def native_frame_count(self) -> int:
        """Number of frames this generator produces natively."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded in GPU memory."""
        return False
```

#### Step 2: Create Scene Classification / Hybrid Router (30 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/src/cinematography/hybrid_router.py`

```python
"""
Hybrid Router - Routes scenes to AnimateDiff or WAN based on scene type.

Hero scenes (chorus, drops, climax) -> WAN 2.2 (highest quality)
Standard scenes (verse, bridge, intro, outro) -> AnimateDiff (fast, good quality)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class SceneType(Enum):
    """Scene type classification for routing."""
    HERO = "hero"        # Chorus, drop, climax -> WAN
    STANDARD = "standard"  # Verse, bridge, intro -> AnimateDiff


# Music section types that trigger hero routing
HERO_SECTIONS = frozenset([
    "chorus",
    "drop",
    "climax",
    "bridge_climax",  # If bridge builds to climax
    "breakdown",      # High-energy breakdowns
    "hook",
])

# All other sections route to standard
STANDARD_SECTIONS = frozenset([
    "verse",
    "bridge",
    "intro",
    "outro",
    "interlude",
    "pre_chorus",
])


@dataclass
class RoutedScene:
    """A scene with routing metadata."""
    scene_index: int
    prompt: str
    negative_prompt: str
    scene_type: SceneType
    music_section: str
    seed: int
    source_image_path: Optional[str] = None  # For WAN I2V


def classify_scene(
    music_section: str,
    force_hero: bool = False,
    force_standard: bool = False,
) -> SceneType:
    """
    Classify a scene based on its music section.

    Args:
        music_section: Section type from audio analysis (e.g., "chorus", "verse")
        force_hero: Override to force WAN routing
        force_standard: Override to force AnimateDiff routing

    Returns:
        SceneType.HERO or SceneType.STANDARD
    """
    if force_hero:
        return SceneType.HERO
    if force_standard:
        return SceneType.STANDARD

    section_lower = music_section.lower().strip()

    if section_lower in HERO_SECTIONS:
        return SceneType.HERO

    return SceneType.STANDARD


def route_scenes(scenes: list, wan_available: bool = True) -> dict:
    """
    Route a list of scenes to their generators.

    Args:
        scenes: List of scene dicts with 'music_section' key
        wan_available: Whether WAN generator is available (False = all AnimateDiff)

    Returns:
        Dict with 'hero' and 'standard' lists of RoutedScene
    """
    routed = {"hero": [], "standard": []}

    for i, scene in enumerate(scenes):
        section = scene.get("music_section", "verse")
        scene_type = classify_scene(section)

        # If WAN not available, downgrade hero to standard
        if scene_type == SceneType.HERO and not wan_available:
            scene_type = SceneType.STANDARD

        routed_scene = RoutedScene(
            scene_index=i,
            prompt=scene.get("prompt", ""),
            negative_prompt=scene.get("negative_prompt", ""),
            scene_type=scene_type,
            music_section=section,
            seed=scene.get("seed", -1),
            source_image_path=scene.get("source_image_path"),
        )

        if scene_type == SceneType.HERO:
            routed["hero"].append(routed_scene)
        else:
            routed["standard"].append(routed_scene)

    hero_count = len(routed["hero"])
    standard_count = len(routed["standard"])
    total = hero_count + standard_count

    print(f"[HybridRouter] Routed {total} scenes: {hero_count} hero (WAN), {standard_count} standard (AnimateDiff)")

    return routed
```

#### Step 3: Create Hybrid Pipeline Test Script (60 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/scripts/render_video_hybrid.py`

**Pipeline execution order:**

```
1. Route scenes (classify hero vs standard)
2. Load AnimateDiff
3. Generate ALL standard scenes (batch)
4. Kill AnimateDiff (VRAM reclamation)
5. Load WAN 2.2
6. Generate ALL hero scenes (sequential, each with source image)
7. Kill WAN (VRAM reclamation)
8. Load RAFT
9. Interpolate ALL scenes to 60fps
10. Assemble final video (scene ordering by original index)
```

**Why this order:** AnimateDiff uses ~5.6GB and can batch quickly. WAN uses ~15GB and must run alone. RAFT uses ~2GB and can run after both are killed.

**Critical code -- hybrid orchestration:**

```python
def run_hybrid_pipeline(scenes: list, output_dir: Path, style: str):
    """
    Execute hybrid pipeline: AnimateDiff (standard) + WAN (hero).

    Args:
        scenes: List of scene dicts from storyboard generator
        output_dir: Output directory
        style: Production style name
    """
    # Step 1: Route scenes
    routed = route_scenes(scenes, wan_available=True)

    all_frames = {}  # scene_index -> interpolated frames

    # Step 2-3: Generate standard scenes with AnimateDiff
    if routed["standard"]:
        print(f"\n[Phase A] AnimateDiff: {len(routed['standard'])} standard scenes")
        ad_gen = AnimateDiffGenerator()
        ad_gen.load()

        for scene in routed["standard"]:
            frames = ad_gen.generate(
                prompt=scene.prompt,
                negative_prompt=scene.negative_prompt,
                seed=scene.seed,
            )
            all_frames[scene.scene_index] = frames

        # Step 4: Kill AnimateDiff
        ad_gen.kill()

    # Step 5-6: Generate hero scenes with WAN
    if routed["hero"]:
        print(f"\n[Phase B] WAN 2.2: {len(routed['hero'])} hero scenes")
        wan_gen = WANGenerator()
        wan_gen.load()

        for scene in routed["hero"]:
            frames = wan_gen.generate(
                prompt=scene.prompt,
                negative_prompt=scene.negative_prompt,
                seed=scene.seed,
                source_image_path=scene.source_image_path,
            )
            all_frames[scene.scene_index] = frames

        # Step 7: Kill WAN
        wan_gen.kill()

    # Step 8-9: Interpolate all scenes with RAFT
    print(f"\n[Phase C] RAFT interpolation: {len(all_frames)} scenes")
    interpolator = initialize_raft()

    interpolated_frames = {}
    for scene_idx in sorted(all_frames.keys()):
        raw_frames = all_frames[scene_idx]
        interp = interpolate_with_raft(
            frames=raw_frames,
            interpolator=interpolator,
            target_fps=60,
            source_fps=len(raw_frames),  # Variable source FPS
            target_duration=4.0,
        )
        interpolated_frames[scene_idx] = interp

    del interpolator
    gc.collect()
    torch.cuda.empty_cache()

    # Step 10: Assemble (ordered by scene index)
    # ... export each scene as individual clip, or concatenate for full video
```

#### Step 4: Update Module Exports (10 min)

**File:** `/home/craig/AI_Workspace/synterra/beatcanvas/backend/src/cinematography/__init__.py`

Add:
```python
from src.cinematography.video_generator_base import VideoGeneratorBase
from src.cinematography.animatediff_generator import AnimateDiffGenerator
from src.cinematography.wan_generator import WANGenerator
from src.cinematography.hybrid_router import (
    SceneType,
    RoutedScene,
    classify_scene,
    route_scenes,
)
```

#### Step 5: End-to-End Test (30 min)

Create a mock storyboard with 8 scenes (2 hero, 6 standard):

```python
test_scenes = [
    {"prompt": "man walking on beach, golden hour", "music_section": "intro", "seed": 42},
    {"prompt": "man singing facing camera, ocean background", "music_section": "verse", "seed": 42},
    {"prompt": "man dancing energetically, waves crashing", "music_section": "chorus", "seed": 42,
     "source_image_path": "/path/to/chorus_image.png"},
    {"prompt": "man sitting on rock, contemplative", "music_section": "verse", "seed": 42},
    {"prompt": "man running along shoreline, dramatic", "music_section": "chorus", "seed": 42,
     "source_image_path": "/path/to/chorus2_image.png"},
    {"prompt": "man walking into sunset, peaceful", "music_section": "bridge", "seed": 42},
    {"prompt": "man standing arms raised, triumphant", "music_section": "outro", "seed": 42},
    {"prompt": "wide shot beach, man walking away", "music_section": "outro", "seed": 42},
]
```

Expected routing: scenes 2, 4 -> WAN (chorus); scenes 0, 1, 3, 5, 6, 7 -> AnimateDiff.

#### Testing Checkpoint 8.4

| Criterion | How to Verify |
|-----------|--------------|
| Scene routing correct | Print routed scenes; verify chorus -> hero, verse -> standard |
| AnimateDiff batch completes | 6 standard scenes generated without OOM |
| WAN hero scenes complete | 2 hero scenes generated without OOM |
| VRAM lifecycle correct | AnimateDiff killed before WAN loads; WAN killed before RAFT |
| RAFT handles mixed frame counts | 16-frame and 81-frame inputs both interpolate to ~240 |
| Total time < 45 minutes | End-to-end timing for 8 scenes |
| Hero scenes visibly higher quality | Side-by-side comparison of hero vs standard |

#### Rollback Strategy

If hybrid pipeline is too slow:
1. Reduce WAN frames from 81 to 49
2. Reduce WAN inference steps from 40 to 20
3. If WAN is unacceptably slow: use AnimateDiff for all scenes with SparseCtrl image conditioning for hero scenes

If VRAM lifecycle causes issues:
1. Add 5-second sleep between kill and next load (allow GPU memory to fully reclaim)
2. Add explicit `torch.cuda.synchronize()` after each kill
3. Monitor VRAM with `nvidia-smi` during test runs

---

## Testing Strategy

### Unit Tests (Phase 8.2)

```python
# test_animatediff_generator.py
def test_prompt_under_75_tokens():
    """Verify all style prompts are under CLIP limit."""
    for style in ALL_STYLES:
        prompt = build_animatediff_prompt(style, "man walking")
        assert estimated_token_count(prompt) <= 75

def test_scene_classification():
    """Verify hero/standard routing logic."""
    assert classify_scene("chorus") == SceneType.HERO
    assert classify_scene("verse") == SceneType.STANDARD
    assert classify_scene("drop") == SceneType.HERO
    assert classify_scene("bridge") == SceneType.STANDARD
```

### Integration Tests (Phase 8.3-8.4)

```bash
# Quick smoke test: single AnimateDiff scene
python scripts/render_video_animatediff.py --style STYLE_BEACH_CASUAL --dry-run

# Full AnimateDiff test
python scripts/render_video_animatediff.py --style STYLE_BEACH_CASUAL --prompt "man walking on beach"

# WAN smoke test
python scripts/render_video_wan.py --source test_image.png --prompt "man walking" --dry-run

# Hybrid end-to-end
python scripts/render_video_hybrid.py --test-scenes
```

### Quality Benchmarks

| Metric | SVD-XT (baseline) | AnimateDiff (target) | WAN 2.2 (target) |
|--------|-------------------|---------------------|-------------------|
| Motion blur | High (frequent) | Low (rare) | Minimal |
| Limb deformation | Common | Rare | Very rare |
| Character consistency | Poor across scenes | Good with seed lock | Good with I2V |
| Generation time (1 scene) | ~2 min | ~30 sec | ~10 min |
| VRAM usage | ~8GB | ~5.6GB | ~15GB |

---

## Risks and Considerations

### High Risk

1. **WAN 2.2 VRAM (Critical):** The A14B model officially requires 80GB VRAM. Even FP8 + CPU offload may OOM on 16GB with 576x1024 input. **Mitigation:** Test early in Phase 8.3; have fallback to WAN 2.1 1.3B or AnimateDiff-only mode.

2. **RAFT with 16 frames (Medium):** AnimateDiff produces only 16 frames vs SVD's 25. RAFT must generate 14 intermediate frames per gap (vs 9 for SVD). Higher interpolation ratio may introduce artifacts. **Mitigation:** Test RAFT quality at 14x interpolation; if artifacts appear, increase AnimateDiff to 24 or 32 frames.

### Medium Risk

3. **SD 1.5 quality ceiling:** AnimateDiff uses SD 1.5 (512px native) vs SVD-XT's bespoke architecture. Output at 576x1024 may be softer than SVD. **Mitigation:** Test with multiple base models; CyberRealistic V3.3 may be sharper than epiCRealism.

4. **Prompt incompatibility:** Current SDXL-optimized prompts (score_9, weighted tokens) may behave differently on SD 1.5. **Mitigation:** Phase 8.2 creates AnimateDiff-specific prompt tokens.

5. **ComfyUI vs diffusers for WAN:** If diffusers WAN OOMs, GGUF via ComfyUI is the fallback, but adds a service dependency. **Mitigation:** Phase 8.3 includes multiple fallback levels.

### Low Risk

6. **Seed consistency limitations:** Seed locking produces consistent noise but not identical characters across very different prompts. **Mitigation:** Acceptable for BeatCanvas (scenes within a section have similar subjects). IP-Adapter is future work.

7. **Frame count mismatch in assembly:** AnimateDiff (16 frames) and WAN (81 frames) produce different duration clips before interpolation. **Mitigation:** Both are interpolated to the same target (4s @ 60fps = 240 frames) by RAFT.

---

## Estimated Complexity

| Phase | Time Estimate | Difficulty | Dependencies |
|-------|--------------|------------|--------------|
| 8.1: AnimateDiff Foundation | 2-3 hours | Medium | None (standalone test) |
| 8.2: AnimateDiff Production | 1-2 hours | Low | Phase 8.1 complete |
| 8.3: WAN 2.2 Hero Scenes | 4-6 hours | High (VRAM debugging) | Phase 8.1 complete |
| 8.4: Hybrid Integration | 2-3 hours | Medium | Phase 8.1 + 8.3 complete |
| **Total** | **9-14 hours** | | |

**Recommended execution order:** 8.1 -> 8.2 -> 8.3 -> 8.4

Phase 8.1 and 8.2 can deliver immediate value (AnimateDiff replaces SVD for all scenes). Phase 8.3 and 8.4 are enhancements that add hero-scene quality but carry VRAM risk.

---

## File Inventory

### New Files

| File | Description | Phase |
|------|-------------|-------|
| `backend/scripts/render_video_animatediff.py` | AnimateDiff test script | 8.1 |
| `backend/scripts/render_video_wan.py` | WAN 2.2 test script | 8.3 |
| `backend/scripts/render_video_hybrid.py` | Hybrid pipeline test | 8.4 |
| `backend/src/cinematography/animatediff_generator.py` | AnimateDiff production wrapper | 8.2 |
| `backend/src/cinematography/wan_generator.py` | WAN 2.2 production wrapper | 8.3 |
| `backend/src/cinematography/video_generator_base.py` | Abstract base class | 8.4 |
| `backend/src/cinematography/hybrid_router.py` | Scene routing logic | 8.4 |

### Modified Files

| File | Changes | Phase |
|------|---------|-------|
| `backend/requirements.txt` | Add diffusers>=0.34.0, accelerate | 8.1 |
| `backend/library/optics_presets.yaml` | Add `animatediff` section per style | 8.2 |
| `backend/config/settings.yaml` | Add `animatediff` and `wan` config sections | 8.2, 8.3 |
| `backend/config/checkpoints.yaml` | Add AnimateDiff and WAN model entries | 8.2, 8.3 |
| `backend/src/cinematography/__init__.py` | Export new classes | 8.4 |

### Preserved Files (Read-Only)

| File | Reason |
|------|--------|
| `backend/scripts/render_video_svd.py` | Keep for SVD fallback; do not modify |
| `backend/src/cinematography/raft_interpolator.py` | Already frame-count agnostic |
| `backend/src/cinematography/temporal_consistency.py` | SVD-specific; not used by new generators |
| `backend/src/cinematography/physics_motion_tracker.py` | Can be applied to any generator's output |
| `backend/src/local/video_generator.py` | SVD wrapper; keep for backward compatibility |

---

## Future Work (Not in Phase 8)

- **Phase 8.5:** IP-Adapter integration for strong character consistency across diverse scenes
- **Phase 8.6:** AnimateDiff SparseCtrl image conditioning (use storyboard images as first-frame anchors)
- **Phase 8.7:** Parallel AnimateDiff batch processing (2-3 instances on 16GB)
- **Phase 8.8:** ComfyUI GGUF fallback for WAN on low-VRAM systems
- **Phase 8.9:** ControlNet integration (depth/pose control for AnimateDiff scenes)

---

## Multi-Format Output Strategy (Added 2026-02-06)

### Context

Music videos need multiple aspect ratios for different platforms:
- **Portrait (9:16):** TikTok, Instagram Reels, YouTube Shorts (15-60 sec clips)
- **Landscape (16:9):** YouTube, Vimeo (full 3-5 min videos)
- **Square (1:1):** Instagram feed (30-60 sec clips)

**Key Insight:** 70% of the pipeline is shared (audio analysis, narrative generation, prompts). Only video generation and assembly are format-specific.

### Architecture

```
Audio Analysis (shared)
    ↓
Beat Detection + Section Analysis (shared)
    ↓
GPT-4 Narrative Generation (shared)
    ↓
Scene Descriptions (shared)
    ↓
    ├─→ Portrait Generator (9:16)
    │   ├─ AnimateDiff: 768×1024 → upscale to 1080×1920
    │   └─ WAN 2.2 Q5: 480×854 (portrait) → upscale
    │
    ├─→ Landscape Generator (16:9)
    │   ├─ AnimateDiff: 1024×768 → upscale to 1920×1080
    │   └─ WAN 2.2 Q5: 854×480 → upscale
    │
    └─→ Square Generator (1:1)
        └─ AnimateDiff: 768×768 → upscale to 1080×1080
    ↓
RAFT Interpolation (shared, aspect-aware)
    ↓
Real-ESRGAN Upscaling (shared, aspect-aware)
    ↓
Optional: Topaz 4K Upscaling (premium delivery)
    ↓
Video Assembly (aspect-specific composition)
```

### Implementation

#### Phase 8.2 Enhancement: Add Aspect Ratio Parameter

Modify `animatediff_generator.py`:

```python
class AnimateDiffGenerator:
    def __init__(self, aspect_ratio="16:9"):
        self.aspect_ratio = aspect_ratio
        self.resolution = self._get_resolution(aspect_ratio)
    
    def _get_resolution(self, aspect_ratio):
        """Map aspect ratio to AnimateDiff native resolution"""
        resolutions = {
            "16:9": (1024, 768),   # Landscape
            "9:16": (768, 1024),   # Portrait
            "1:1": (768, 768),     # Square
        }
        return resolutions.get(aspect_ratio, (1024, 768))
    
    def generate(self, prompt, num_frames=16):
        width, height = self.resolution
        
        # AnimateDiff generation
        output = self.pipe(
            prompt=prompt,
            negative_prompt=self.negative_prompt,
            num_frames=num_frames,
            height=height,
            width=width,
            guidance_scale=1.0,
            num_inference_steps=4,
        )
        
        return output.frames
```

#### WAN 2.2 Aspect Ratio Support

WAN 2.2 supports both orientations by flipping dimensions:

```python
# Landscape
resolution = (854, 480)  # 16:9

# Portrait  
resolution = (480, 854)  # 9:16
```

### Prompt Composition Adjustments

**Landscape prompts:** Wider framing, more scene context
```
"wide shot, man walking on beach with ocean in background, cinematic composition"
```

**Portrait prompts:** Centered subject, vertical framing
```
"centered shot, man walking on beach, vertical composition optimized for mobile"
```

**Implementation:** Add `composition_hint` to prompt composer based on aspect ratio.

### Multi-Format Workflow

#### Option 1: Generate All Formats (Best Quality)

```python
def generate_multi_format(scene_description, audio_file):
    # Shared preprocessing
    audio_data = analyze_audio(audio_file)
    narrative = generate_narrative(audio_data, scene_description)
    
    # Generate each format
    portrait_video = generate_video(
        narrative=narrative,
        aspect_ratio="9:16",
        optimize_for="mobile"
    )
    
    landscape_video = generate_video(
        narrative=narrative,
        aspect_ratio="16:9",
        optimize_for="cinematic"
    )
    
    return {
        "portrait": portrait_video,
        "landscape": landscape_video
    }
```

**Time:** 2x generation time (both formats)  
**Quality:** Optimal for each format

#### Option 2: Generate Landscape, Adapt to Portrait (Fast)

```python
def generate_with_adaptation(scene_description, audio_file):
    # Generate landscape (primary)
    landscape = generate_video(aspect_ratio="16:9")
    
    # Adapt to portrait with blur bars
    portrait = add_blur_bars(landscape, target_aspect="9:16")
    
    return {"landscape": landscape, "portrait": portrait}
```

**Time:** 1x generation + 5 min adaptation  
**Quality:** Portrait is acceptable but not optimal

**Recommendation:** Use Option 1 (dual generation) - quality difference is significant.

### File Organization

```
backend/
├── src/
│   └── video/
│       ├── format_manager.py  # NEW: Multi-format orchestration
│       ├── aspect_ratio_config.py  # NEW: Resolution mappings
│       └── composition_optimizer.py  # NEW: Aspect-aware prompt hints
└── library/
    └── optics_presets.yaml  # Add aspect_ratio field per style
```

### Configuration Updates

**optics_presets.yaml:**

```yaml
STYLE_BEACH_CASUAL:
  camera: "SONY_VENICE"
  film: "KODAK_PORTRA_400"
  lighting: "BOUNCED_SOFT"
  motion: "STEADICAM_SMOOTH"
  
  # Multi-format configurations
  formats:
    landscape_16_9:
      resolution: (1024, 768)
      composition_hint: "wide cinematic framing"
    portrait_9_16:
      resolution: (768, 1024)
      composition_hint: "centered vertical mobile"
    square_1_1:
      resolution: (768, 768)
      composition_hint: "balanced square composition"
  
  # AnimateDiff settings (shared across formats)
  animatediff:
    motion_bucket_id: 70
    fps: 8
    num_frames: 16
```

---

## Beat Synchronization with Librosa (Added 2026-02-06)

### Context

Music videos need visual transitions synced to musical beats for professional feel. User already has **librosa** integrated for audio analysis. Beat detection capability exists but isn't used for visual sync yet.

### Current Beat Detection (Already Working!)

From `backend/src/audio/analyzer.py`:

```python
import librosa

def analyze_audio(audio_path):
    y, sr = librosa.load(audio_path)
    
    # Beat detection (already implemented)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    # Sections (already implemented)
    sections = detect_sections(y, sr)  # Intro, verse, chorus, etc.
    
    return {
        'tempo': tempo,
        'beat_times': beat_times,  # [0.5, 1.2, 1.8, 2.4, ...]
        'sections': sections
    }
```

**Beat timestamps already available!** Just need to use them for visual sync.

### Beat Sync Architecture

```
Audio Analysis
    ↓
Beat Timestamps + Sections
    ↓
Beat-Aligned Keyframes
    ↓
Scene Generation with Beat Transitions
    ↓
Video Assembly (sharp cuts on beats)
```

### Implementation

#### New Module: `backend/src/video/beat_sync.py`

```python
import numpy as np

class BeatSyncManager:
    """Manages beat-aligned scene timing and transitions"""
    
    def __init__(self, audio_file):
        from src.audio.analyzer import MusicAnalyzer
        
        self.analyzer = MusicAnalyzer()
        self.audio_data = self.analyzer.analyze(audio_file)
        self.beat_times = self.audio_data['beats']
        self.sections = self.audio_data['sections']
    
    def align_sections_to_beats(self):
        """Snap section boundaries to nearest beats"""
        aligned_sections = []
        
        for section in self.sections:
            # Find nearest beat to section start
            nearest_beat = self._find_nearest_beat(section.start_time)
            
            # Find nearest beat to section end
            end_beat = self._find_nearest_beat(section.end_time)
            
            aligned_section = {
                'type': section.type,  # verse, chorus, etc.
                'start_beat': nearest_beat,
                'end_beat': end_beat,
                'duration': end_beat - nearest_beat,
                'prompt': section.prompt
            }
            aligned_sections.append(aligned_section)
        
        return aligned_sections
    
    def _find_nearest_beat(self, timestamp):
        """Snap timestamp to nearest beat"""
        idx = np.argmin(np.abs(self.beat_times - timestamp))
        return self.beat_times[idx]
    
    def create_transition_timeline(self, aligned_sections):
        """Create timeline with beat-synced transitions"""
        timeline = []
        
        for i, section in enumerate(aligned_sections):
            # Calculate scene duration (beat-aligned)
            duration = section['end_beat'] - section['start_beat']
            
            # Determine transition style based on beat strength
            if i < len(aligned_sections) - 1:
                transition = self._get_transition_style(
                    section['type'],
                    aligned_sections[i+1]['type']
                )
            else:
                transition = 'fade_out'
            
            timeline.append({
                'start_time': section['start_beat'],
                'end_time': section['end_beat'],
                'duration': duration,
                'prompt': section['prompt'],
                'transition': transition,
                'on_beat': True  # Flag for sharp transition
            })
        
        return timeline
    
    def _get_transition_style(self, from_type, to_type):
        """Determine transition style based on section types"""
        transitions = {
            ('verse', 'chorus'): 'sharp_cut',  # Energetic transition
            ('chorus', 'verse'): 'fade',       # Calm down
            ('verse', 'verse'): 'crossfade',   # Smooth
            ('chorus', 'bridge'): 'sharp_cut', # Build tension
        }
        return transitions.get((from_type, to_type), 'crossfade')
```

#### Integration with Video Generator

Modify `backend/src/video/animatediff_generator.py`:

```python
class AnimateDiffGenerator:
    def generate_beat_synced_video(self, timeline, audio_file):
        """Generate video with beat-synchronized transitions"""
        scenes = []
        
        for entry in timeline:
            # Generate scene
            scene_frames = self.generate(
                prompt=entry['prompt'],
                num_frames=self._calculate_frames(entry['duration'])
            )
            
            # Add transition marker for assembly
            scene = {
                'frames': scene_frames,
                'start_time': entry['start_time'],
                'duration': entry['duration'],
                'transition': entry['transition'],
                'on_beat': entry['on_beat']
            }
            scenes.append(scene)
        
        return scenes
    
    def _calculate_frames(self, duration):
        """Calculate frame count for given duration"""
        # AnimateDiff outputs 16 frames, RAFT interpolates to 60fps
        # For beat-aligned scenes, adjust frame count to duration
        fps = 8  # AnimateDiff native FPS
        return min(int(duration * fps), 32)  # Cap at 32 frames
```

#### Video Assembly Enhancement

Modify `backend/src/video/assembler.py`:

```python
def assemble_with_beats(self, scenes, audio_file, beat_times):
    """Assemble video with beat-synchronized transitions"""
    clips = []
    
    for i, scene in enumerate(scenes):
        clip = self._create_clip(scene['frames'], scene['duration'])
        
        # Apply transition based on beat timing
        if scene['on_beat']:
            # Sharp transition on beat (no fade)
            clip = clip.set_duration(scene['duration'])
        else:
            # Smooth transition between beats
            clip = clip.crossfadein(0.5)
        
        clips.append(clip)
    
    # Concatenate with beat-aware transitions
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Add audio
    final_video = final_video.set_audio(AudioFileClip(audio_file))
    
    return final_video
```

### Workflow Integration

**Current workflow:**
```python
# 1. Audio analysis
audio_data = MusicAnalyzer.analyze(audio_file)
sections = audio_data['sections']

# 2. Generate prompts
prompts = GPT4.generate_prompts(sections, user_concept)

# 3. Generate videos (no beat sync)
videos = generate_videos(prompts)
```

**NEW: Beat-synced workflow:**
```python
# 1. Audio analysis (same)
audio_data = MusicAnalyzer.analyze(audio_file)

# 2. Beat alignment
beat_sync = BeatSyncManager(audio_file)
aligned_sections = beat_sync.align_sections_to_beats()
timeline = beat_sync.create_transition_timeline(aligned_sections)

# 3. Generate prompts (beat-aware)
prompts = GPT4.generate_prompts(aligned_sections, user_concept)

# 4. Generate videos with beat sync
videos = generate_beat_synced_videos(timeline, audio_file)

# 5. Assemble with beat transitions
final_video = assemble_with_beats(videos, audio_file, beat_times)
```

### Testing Strategy

**Phase 8.2 Enhancement: Add beat sync to AnimateDiff**

1. Test beat detection accuracy on sample song
2. Verify section boundaries align to beats correctly
3. Compare beat-synced vs non-beat-synced versions
4. User validation: Does it "feel" synced to music?

**Success Metrics:**
- Transitions occur within 100ms of beat (±2 frames @ 60fps)
- Visual rhythm matches musical rhythm subjectively
- Sharp transitions on downbeats, smooth between

### Alternative: madmom for Better Beat Accuracy

If librosa beat detection insufficient:

```python
# Install: pip install madmom
from madmom.features import DBNDownBeatTrackingProcessor

proc = DBNDownBeatTrackingProcessor(fps=100)
beats = proc(audio_file)  # More accurate, includes downbeat detection
```

**Recommendation:** Start with librosa (already integrated), upgrade to madmom only if accuracy issues arise.

---

## High-Resolution Output & Upscaling Strategy (Added 2026-02-06)

### Context

User wants 4K-ready output for professional delivery. Native 4K generation requires 500GB+ VRAM. Industry standard: generate at model's native resolution, upscale with AI.

### Resolution Targets

| Delivery Format | Resolution | Use Case |
|-----------------|------------|----------|
| **Social Media (Standard)** | 1080p (1920×1080) | YouTube, Instagram, TikTok |
| **Premium Delivery** | 1440p (2560×1440) | Vimeo, client review |
| **Archival/Future-Proof** | 4K (3840×2160) | High-end clients, future remaster |

### Multi-Stage Upscaling Pipeline

```
Native Generation
    ↓
RAFT Interpolation (16→240 frames @ 60fps)
    ↓
Real-ESRGAN Upscaling (2x or 4x)
    ↓
Optional: Topaz Video Enhance (2x)
    ↓
Final Output (1080p, 1440p, or 4K)
```

### Native Generation Resolutions

**AnimateDiff SD 1.5:**
- **Portrait:** 768×1024 (9:16)
- **Landscape:** 1024×768 (16:9)
- **Square:** 768×768 (1:1)

**WAN 2.2 Q5:**
- **Portrait:** 480×854 (9:16)
- **Landscape:** 854×480 (16:9)

### Upscaling Paths

#### Path 1: AnimateDiff 768×1024 → 1080p → 4K

```
768×1024 (native)
    ↓ Real-ESRGAN 2x
1536×2048
    ↓ Topaz 2x (optional)
3072×4096 (4K portrait)
```

**Final crop to standard 4K portrait:** 2160×3840

#### Path 2: WAN 2.2 854×480 → 1080p → 4K

```
854×480 (native)
    ↓ Real-ESRGAN 2.25x
1920×1080 (1080p landscape)
    ↓ Topaz 2x (optional)
3840×2160 (4K landscape)
```

### Implementation

#### Phase 8.2 Enhancement: Add Real-ESRGAN Integration

**Install Real-ESRGAN:**

```bash
# Add to requirements.txt
realesrgan>=0.3.0

# Or use standalone executable
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.3.0/realesrgan-ncnn-vulkan
```

**New Module: `backend/src/video/upscaler.py`**

```python
import subprocess
from pathlib import Path

class VideoUpscaler:
    """AI-based video upscaling using Real-ESRGAN"""
    
    def __init__(self, model="realesr-animevideov3"):
        self.model = model
        self.executable = "realesrgan-ncnn-vulkan"
    
    def upscale(self, input_video, scale=2, output_path=None):
        """
        Upscale video using Real-ESRGAN
        
        Args:
            input_video: Path to input video
            scale: Upscale factor (2 or 4)
            output_path: Output path (auto-generated if None)
        
        Returns:
            Path to upscaled video
        """
        if output_path is None:
            output_path = self._generate_output_path(input_video, scale)
        
        cmd = [
            self.executable,
            "-i", str(input_video),
            "-o", str(output_path),
            "-s", str(scale),
            "-n", self.model,
            "-f", "mp4"
        ]
        
        print(f"Upscaling {input_video.name} with {scale}x Real-ESRGAN...")
        subprocess.run(cmd, check=True)
        
        return output_path
    
    def _generate_output_path(self, input_path, scale):
        """Generate output filename"""
        stem = input_path.stem
        suffix = input_path.suffix
        parent = input_path.parent
        return parent / f"{stem}_{scale}x_upscaled{suffix}"
```

**Integration with Pipeline:**

```python
def generate_with_upscaling(scene, target_resolution="1080p"):
    # 1. Generate at native resolution
    native_video = animatediff_generator.generate(scene)
    # Output: 768×1024 @ 60fps (240 frames)
    
    # 2. Save to temp file
    temp_path = save_video(native_video, "temp_native.mp4")
    
    # 3. Upscale to target
    upscaler = VideoUpscaler()
    
    if target_resolution == "1080p":
        # 768×1024 → 1536×2048 (2x) → crop to 1080×1920
        upscaled = upscaler.upscale(temp_path, scale=2)
        final = crop_to_resolution(upscaled, (1080, 1920))
    
    elif target_resolution == "4K":
        # 768×1024 → 1536×2048 (2x) → 3072×4096 (2x)
        upscaled_2x = upscaler.upscale(temp_path, scale=2)
        upscaled_4x = upscaler.upscale(upscaled_2x, scale=2)
        final = crop_to_resolution(upscaled_4x, (2160, 3840))
    
    return final
```

### Topaz Video Enhance AI Integration (Optional Premium)

**For clients requiring best quality:**

```python
class TopazUpscaler:
    """Premium upscaling with Topaz Video Enhance AI"""
    
    def upscale(self, input_video, scale=2):
        cmd = [
            "topaz-video-enhance",
            "--input", str(input_video),
            "--output", str(output_path),
            "--scale", str(scale),
            "--model", "Artemis HQ",  # Best for AI-generated content
            "--enhancement", "Enhance Detail"
        ]
        subprocess.run(cmd, check=True)
        return output_path
```

**Cost:** $299 one-time (commercial license)  
**Speed:** ~10-20 min for 4-sec video  
**Quality:** 98-99% vs native generation

### Multi-Tier Delivery Pipeline

```python
def generate_multi_tier_delivery(scene, audio_file):
    # 1. Generate native
    native_video = generate_video(scene)
    
    # 2. Create delivery tiers
    deliverables = {
        "preview": native_video,  # 768×1024 for review
        "social": upscale_to_1080p(native_video),  # Fast iteration
        "premium": upscale_to_4k(native_video)  # Final delivery
    }
    
    return deliverables
```

**Workflow:**
1. Client reviews preview (native resolution, fast)
2. Approve → Generate social (1080p, Real-ESRGAN)
3. If premium client → Generate 4K (Topaz)

### Configuration

**optics_presets.yaml:**

```yaml
upscaling:
  enabled: true
  default_target: "1080p"  # or "4K"
  
  realesrgan:
    model: "realesr-animevideov3"
    device: "cuda"
  
  topaz:
    enabled: false  # Requires commercial license
    model: "Artemis HQ"
  
  delivery_tiers:
    - name: "preview"
      resolution: "native"
      upscale: false
    - name: "social"
      resolution: "1080p"
      upscale: true
      upscaler: "realesrgan"
    - name: "premium"
      resolution: "4K"
      upscale: true
      upscaler: "topaz"
```

### Performance Metrics

| Operation | Input | Output | Time (4-sec video) | VRAM |
|-----------|-------|--------|-------------------|------|
| **AnimateDiff** | Prompt | 768×1024 @ 16fps | ~30 sec | 5.6GB |
| **RAFT** | 16 frames | 240 frames @ 60fps | ~20 sec | 2-3GB |
| **Real-ESRGAN 2x** | 768×1024 | 1536×2048 | ~2 min | 2-3GB |
| **Real-ESRGAN 4x** | 768×1024 | 3072×4096 | ~8 min | 3-4GB |
| **Topaz 2x** | 1536×2048 | 3072×4096 | ~15 min | 4-6GB |

**Total for 4K output:** ~25-35 min per 4-sec scene (AnimateDiff → RAFT → Real-ESRGAN 2x → Topaz 2x)

---

## Updated Success Metrics

With multi-format, beat sync, and 4K support:

1. **Quality:**
   - No motion blur or limb deformation (vs SVD-XT baseline)
   - 4K upscaling indistinguishable from native (95%+ quality)

2. **Format Support:**
   - Portrait (9:16), landscape (16:9), square (1:1) all working
   - Composition optimized per aspect ratio

3. **Beat Synchronization:**
   - Transitions within 100ms of beat (±2 frames @ 60fps)
   - Visual rhythm matches musical rhythm subjectively

4. **Speed:**
   - 24-scene video (1080p) in <45 minutes
   - 4K delivery in <2 hours with Topaz

5. **Reliability:**
   - 95%+ success rate across all formats
   - Graceful fallbacks if WAN VRAM issues

