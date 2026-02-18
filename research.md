# BeatCanvas Comprehensive Codebase Research
Generated: 2026-02-17

---

## 1. OVERALL ARCHITECTURE

BeatCanvas is an AI-powered music video generator. The system has two distinct workflows and a layered backend architecture.

### Physical Layout
```
beatcanvas/
├── backend/                   # FastAPI Python backend (port 8000)
│   ├── main.py               # 2315-line monolith - all API endpoints
│   ├── api_animation_endpoints.py  # Router (NOT currently mounted in main.py)
│   ├── src/
│   │   ├── audio/            # librosa audio analysis
│   │   ├── storyboard/       # GPT-4 concept + storyboard generation
│   │   ├── assets/           # Image generation (multi-provider + SDXL local)
│   │   ├── video/            # Video assembly (MoviePy) + AnimateDiff pipeline
│   │   ├── animation/        # NEW: animation workflow + rotoscope generator
│   │   ├── cinematography/   # AnimateDiff-Lightning, RAFT, WAN2.6, SkyReels
│   │   ├── local/            # Local pipeline: SDXL image gen, SVD video gen
│   │   ├── content/          # Cultural content processor
│   │   ├── safety/           # Compliance gate
│   │   ├── skills/           # Scene analyzer
│   │   └── utils/            # Config, env_loader, exceptions, model_loader
│   ├── config/
│   │   ├── loras.yaml        # LoRA registry (5 entries: Rob, Michele, 3 scenes)
│   │   ├── checkpoints.yaml  # Model standards registry (5 standards)
│   │   └── settings.yaml     # SVD + generation config
│   ├── library/
│   │   ├── optics_presets.yaml
│   │   └── production_styles.yaml
│   ├── models/               # Local SDXL model files (on disk)
│   │   ├── RealVisXL_V5.0_fp16.safetensors (6.5GB)
│   │   ├── lustify_v2.safetensors (4.8GB)
│   │   ├── ponyDiffusionV6XL_v6StartWithThisOne.safetensors (6.5GB)
│   │   ├── sdxl_lightning_4step.safetensors (6.5GB)
│   │   └── loras/
│   │       ├── cinematic_grit_v1.safetensors (73MB)
│   │       ├── pony_anatomy_v2.safetensors (650MB)
│   │       └── urban_atmosphere.safetensors (218MB)
│   └── data/
│       ├── uploads/           # Uploaded audio files (many .wav/.mp3)
│       └── generated_images/  # Generated PNG scenes (many files)
├── frontend/                  # React TypeScript frontend (port 3000)
│   └── src/
│       ├── App.tsx            # Root - two tabs: Storyboard + Animation
│       └── components/        # 15 components
├── output/
│   └── loras/                 # TRAINED character LoRAs
│       ├── rob-character/rob-character.safetensors (82MB)
│       ├── michele-character/michele-character.safetensors (82MB)
│       ├── 70s-film-retro/ (3 checkpoint files, 82MB each)
│       ├── beach-bar-exterior/ (3 checkpoints)
│       ├── beach-sunset/ (3 checkpoints)
│       ├── boat-deck/ (3 checkpoints)
│       ├── bonfire-beach/ (3 checkpoints)
│       ├── ocean-underwater/ (3 checkpoints)
│       ├── stage-performance/ (3 checkpoints)
│       └── tiki-bar-interior/ (3 checkpoints)
├── datasets/
│   ├── rob-character/         # 25 PNG + 25 TXT training images
│   ├── michele-character/     # 25 PNG + 25 TXT training images
│   └── 70s-film-retro/        # 30 images + latent cache
└── config/loras/              # YAML descriptors per LoRA (not the registry)
    ├── rob-character.yaml
    ├── michele-character.yaml
    ├── 70s-film-retro.yaml
    └── ... (7 more)
```

### External Models (not in repo)
- `/home/craig/AI_Workspace/synterra/models/Juggernaut-XL-v9.safetensors` (6.7GB) - STANDARD_US

---

## 2. TWO PARALLEL WORKFLOWS

### Workflow A: Storyboard Pipeline (Production/Cloud)
Audio → MusicAnalyzer → ConceptGenerator (GPT-4) → StoryboardGenerator → MultiProviderImageGenerator → VideoAssembler (MoviePy)
- Requires OpenAI API key
- 3 quality tiers: basic (12), professional (24), cinematic (48) scenes
- Legacy mode: static images + Ken Burns effects
- Current mode: AnimateDiff video clips (USE_ANIMATEDIFF = True)

### Workflow B: Animation Pipeline (Local/GPU)
Audio → MusicAnalyzer → SDXLLoRAGenerator → RotoscopeGenerator (ControlNet) → VideoAssembler
- Fully local, 0 API cost
- 16 animation styles
- Character LoRA stacking (Rob + Michele)
- **Status: Code complete, NEVER TESTED end-to-end**

---

## 3. AUDIO ANALYSIS PIPELINE

### File: `/backend/src/audio/analyzer.py` (401 lines)

**Class: MusicAnalyzer**

Key constants:
- `MIN_SCENE_DURATION = 2.5` seconds
- `MAX_SCENE_DURATION = 8.0` seconds
- `DEFAULT_SCENE_COUNT = 60`
- `HERO_SCENE_RATIO = 0.25`

**Method: `analyze_song(audio_file: str) -> Dict`**
Returns:
```python
{
    'duration': float,           # seconds
    'tempo': float,              # BPM
    'segments': List[Dict],      # structure segments
    'overall_energy': float,     # mean spectral centroid
    'overall_mood': str,         # most common segment mood
    'beat_times': List[float],   # beat timestamps
    'sample_rate': int,
    'audio_features': {
        'spectral_centroid_mean': float,
        'spectral_centroid_std': float,
        'mfcc_mean': List[float],   # 20 MFCC means
        'chroma_mean': List[float]  # 12 chroma means
    }
}
```

Each segment dict:
```python
{
    'start_time': float,
    'end_time': float,
    'tempo': float,
    'energy': float,   # RMS energy
    'mood': str,       # energetic|calm|dark|bright|neutral
    'beat_strength': float
}
```

**Structure detection:** Uses `librosa.segment.agglomerative(chroma, k=8)` - agglomerative clustering into up to 8 segments. Falls back to 4 equally-spaced segments on error.

**Mood classification:** Simple threshold on spectral centroid + energy:
- energy > 0.7 AND centroid > 2000 → energetic
- energy < 0.3 → calm
- centroid < 1000 → dark
- centroid > 3000 → bright
- else → neutral

**`get_scene_timings(music_data, target_scene_count=60) -> List[Tuple[float,float]]`**
Simple: if enough segments, use them. Else evenly-spaced with beat alignment.

**`subdivide_by_beats(beat_times, duration, min_dur=2.5, max_dur=8.0) -> List[float]`**
Creates scene boundaries from beat timestamps, enforcing min/max duration constraints.

**`get_enhanced_scene_timings(music_data, target_scene_count=60, hero_ratio=0.25) -> List[Dict]`**
Returns scenes with `scene_type` ("hero" or "standard") for the image-to-video upgrade.

**Hero scene criteria:** Top 25% energy, or position > 75% of song, or labeled chorus/hook/drop.

**Lyrics extraction (in main.py, line 642):** Uses OpenAI Whisper ("base" model) with word-level timestamps. Extracts themes (love, loss, family, nostalgia, hope, struggle, freedom, celebration) and emotional tone. Called during `/api/analyze-audio`.

---

## 4. STORYBOARD / CONCEPT PIPELINE

### ConceptGenerator (`/backend/src/storyboard/conceptor.py`, 233 lines)
- Requires `OPENAI_API_KEY`
- `generate_concept(music_data, user_prompt) -> VisualConcept`
  - Calls GPT-4 with music analysis summary + user prompt
  - Returns: overall_style, color_palette, mood_progression, key_visual_themes, camera_style
- `suggest_visual_styles(content_prompt) -> List[str]` - generates style suggestions
- Has fallback concept on error

### StoryboardGenerator (`/backend/src/storyboard/generator.py`, 297 lines)
- `create_storyboard(music_data, visual_concept, scene_timings) -> List[StoryboardScene]`
  - Calls GPT-4 to generate scene descriptions
  - Each scene: timestamp_start, timestamp_end, description, image_prompt, mood, effects, camera_direction

### NarrativeAnalyzerAI (`/backend/src/storyboard/narrative_analyzer_ai.py`)
- `analyze_concept_with_song(user_concept, sections, song_analysis) -> List[SectionRecommendation]`
- Used by `/api/generate-section-recommendations`

---

## 5. ANIMATION WORKFLOW (`/backend/src/animation/animation_workflow.py`, 610 lines)

### AnimationProjectConfig (dataclass)
```python
project_name: str
audio_path: str
animation_style: str = "watercolor"
quality_tier: str = "professional"
protagonist_lora: Optional[str] = None   # e.g., "rob-character"
supporting_loras: Optional[List[str]] = None
scene_loras: Optional[List[str]] = None  # e.g., ["beach-sunset"]
style_lora: Optional[str] = None         # e.g., "70s-film-retro"
use_stock_footage: bool = False
stock_footage_queries: Optional[List[str]] = None
output_dir: str = "output/animation_projects"
fps: int = 24
width: int = 1024
height: int = 1024
rotoscope_strength: float = 0.8
```

### AnimationWorkflow.run_workflow(config) - Main entry point
Sequential 4-step pipeline:
1. `_analyze_audio(audio_path, quality_tier)` → calls MusicAnalyzer.analyze_song()
2. `_generate_character_scenes(audio_data, config, output_dir)` OR `_collect_stock_footage()`
3. `_apply_rotoscope_style(footage_paths, rotoscope_config, output_path)` → ControlNet
4. `_assemble_final_video(styled_video_path, audio_path, audio_data, output_path)` → MoviePy

**VRAM handover:** Between step 2 and 3, explicitly calls `self.sdxl_generator.unload()` to free VRAM before loading ControlNet.

### _generate_character_scenes() - HARDCODED SCENE TEMPLATES
Contains hardcoded tropical/island scene templates:
- 8 SOLO templates (ohwx man alone)
- 16 TOGETHER templates (ohwx man + ohwx woman)
- Split: first 1/3 of scenes solo, rest together (if supporting_loras present)
- NOT derived from audio analysis - purely template-driven

### _apply_rotoscope_style() fallback chain
1. Try ControlNet SDXL pipeline
2. On failure: fall back to `_create_slideshow_from_images()` with Ken Burns effects
3. Ken Burns uses OpenCV VideoWriter at config.fps, cycles through zoom_in/pan_right/zoom_out/pan_left

### _assemble_final_video()
- MoviePy VideoFileClip + AudioFileClip
- Loops video if shorter than audio, trims if longer
- Uses `subclipped(0, audio_duration).with_audio(audio)`

---

## 6. SDXL + LORA SYSTEM (`/backend/src/assets/sdxl_lora_generator.py`, 361 lines)

### SDXLLoRAGenerator class

**Initialization:**
- `model_id = "stabilityai/stable-diffusion-xl-base-1.0"` (default)
- `_LORA_BASE = PROJECT_ROOT / "output" / "loras"` - where LoRA files are looked up
- Loads LoRA registry from `backend/config/loras.yaml`
- Uses lazy loading - pipeline loaded on first generate call

**load_pipeline():**
- `StableDiffusionXLPipeline.from_pretrained()` with fp16 + safetensors
- `pipe.enable_model_cpu_offload()`
- `pipe.enable_vae_slicing()`
- `pipe.enable_vae_tiling()`

**_apply_loras_to_pipeline(loras: List[LoRAConfig]):**
IMPORTANT DESIGN QUIRK: Calls `unload_lora_weights()` then re-applies ALL loras from scratch on each call. Loads safetensors, then calls `pipeline.load_lora_weights(weights)` + `pipeline.fuse_lora(lora_scale=weight)` for each LoRA in sequence. This means LoRAs are FUSED into the weights, not applied additionally.

**generate_with_loras(prompt, loras, negative_prompt, num_images, width, height, steps, guidance_scale, scene_timestamp):**
- Default: 30 steps, guidance=7.5, 1024x1024, 1 image
- Files saved as: `scene_{timestamp:.1f}_sdxl_lora_var_{i}_{uuid8}.png`
- Returns `SDXLGenerationResult(success, images: List[str])`

**build_prompt_with_triggers():**
Prepends all LoRA trigger words to the base prompt: `"ohwx man, ohwx woman, {base_prompt}"`

**generate_character_scene():**
Convenience method: looks up LoRA by name from registry, builds lora list, calls generate_with_loras.

**LoRAConfig dataclass:** `path: str, weight: float = 0.7, trigger: Optional[str] = None`

---

## 7. LORA REGISTRY (`/backend/config/loras.yaml`)

5 entries currently registered (all enabled):

| Name | Type | Trigger | File | Weight | Status |
|------|------|---------|------|--------|--------|
| rob-character | character | ohwx, ohwx man | rob-character/rob-character.safetensors | 0.8 | trained Feb 16 |
| michele-character | character | ohwx, ohwx woman | michele-character/michele-character.safetensors | 0.8 | trained Feb 16 |
| tiki-bar-interior | scene | tiki_bar | tiki-bar-interior/tiki-bar-interior.safetensors | 0.7 | enabled |
| beach-sunset | scene | beach_sunset | beach-sunset/beach-sunset.safetensors | 0.7 | enabled |
| bonfire-beach | scene | bonfire_beach | bonfire-beach/bonfire-beach.safetensors | 0.7 | enabled |

**Critical path issue:** Registry says `file: "rob-character/rob-character.safetensors"` but the actual file is at `output/loras/rob-character/rob-character.safetensors`. `SDXLLoRAGenerator._LORA_BASE` resolves to `PROJECT_ROOT/output/loras/`, so the full path becomes `PROJECT_ROOT/output/loras/rob-character/rob-character.safetensors` - this IS correct.

**Not in registry but trained:** 70s-film-retro, beach-bar-exterior, boat-deck, ocean-underwater, stage-performance (all have 3 checkpoint files at steps 625, 1250, 1875 - need to pick 1875 as final).

**All character LoRAs:**
- Rob: 82MB, trigger "ohwx man", trained from 25 images, 1500 steps
- Michele: 82MB, trigger "ohwx woman", trained from 25 images, 1500 steps
- Both use identical caption "a photo of ohwx man/woman, portrait" for all training images
- Images are AI-generated (ChatGPT Image), NOT real photos of real artists

---

## 8. CONTROLNET ROTOSCOPE PIPELINE (`/backend/src/animation/rotoscope_generator.py`, 508 lines)

### 16 Animation Styles (ANIMATION_STYLES dict)
Original 6: watercolor, cel_shaded, ghibli, pencil_sketch, cartoon, neon
New 10: oil_painting, comic_book, synthwave, ukiyo_e, art_deco, pop_art, impressionist, graffiti, pixel_art, paper_cutout

Each style defines: prompt_suffix, negative, controlnet_conditioning_scale, guidance_scale, best_for

### RotoscopeGenerator class

**Dependencies:** diffusers, controlnet_aux - guarded by try/except, prints warning if missing
- If DIFFUSERS_AVAILABLE=False, __init__ raises ImportError

**Initialization:**
- `controlnet_model = "diffusion-edge/controlnet-canny-sdxl-1.0"` (NOT lineart despite the detector)
- Lazy pipeline loading
- Note: Uses LineartDetector from `lllyasviel/Annotators` for edge detection, but the ControlNet model says "canny" - mismatch in naming (uses lineart detector with canny controlnet)

**load_pipeline():**
- `ControlNetModel.from_pretrained("diffusion-edge/controlnet-canny-sdxl-1.0")` fp16
- `StableDiffusionXLControlNetPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0")`
- `enable_model_cpu_offload() + enable_vae_slicing() + enable_vae_tiling()`
- `UniPCMultistepScheduler` for speed
- All loaded in executor (non-blocking)

**detect_edges(frame: np.ndarray) -> Image.Image:**
Uses `LineartDetector(frame_pil)` from controlnet_aux

**process_frame(frame, config, previous_frame=None) -> Image.Image:**
1. Gets style config from ANIMATION_STYLES
2. Runs edge detection
3. Resizes edges to target dimensions
4. Calls pipeline with style's guidance_scale and controlnet_conditioning_scale
5. Note: `previous_frame` parameter exists but is NOT used (temporal consistency is scaffolded but not implemented)

**process_video(input_video_path, output_video_path, config) -> RotoscopeResult:**
(Not shown but exists) - extracts frames, processes each, saves output video

**process_image_sequence(image_paths, output_path, config) -> RotoscopeResult:**
(Not shown but exists) - takes list of image paths, processes each as a frame

**RotoscopeConfig dataclass:**
```python
style: str = "watercolor"
custom_prompt: Optional[str] = None
fps: int = 24
width: int = 1024
height: int = 1024
num_inference_steps: int = 25
strength: float = 0.8
temporal_consistency: bool = True  # Field exists but NOT implemented
```

---

## 9. SVD - STABLE VIDEO DIFFUSION

### Status: Available but NOT in active animation pipeline
SVD is integrated into the CinematicDirector / LocalVideoGenerator flow (old pipeline), not the new animation workflow.

**LocalVideoGenerator (`/backend/src/local/video_generator.py`, 638 lines):**
- Model: `stabilityai/stable-video-diffusion-img2vid-xt`
- VRAM: ~7.5GB
- Resolution: 1024x576 (landscape) or 576x1024 (portrait)
- Default: 25 inference steps, motion_bucket_id=127, noise_aug_strength=0.1, 8 FPS
- Dynamic decode_chunk_size based on free VRAM (1-8)
- Encoding: H.264 CRF=17 ("high quality")
- Uses HeartbeatCallback for step-by-step progress monitoring

**CinematicDirector (`/backend/src/local/cinematic_director.py`, 677 lines):**
Orchestrates the old pipeline: ImageGen → kill → VideoGen → kill → MotionSmoother → handoff
- Stage sequence: image_generation → video_generation → motion_smoothing → handoff
- VRAM baseline threshold: 1.5GB (must reach this between stages)
- Windows handoff: copies output to Windows Downloads folder

**SVD Config in settings.yaml:**
```yaml
svd:
  model_id: "stabilityai/stable-video-diffusion-img2vid-xt"
  resolution: {width: 1024, height: 576}
  defaults:
    num_inference_steps: 25
    motion_bucket_id: 127
    noise_aug_strength: 0.1
    fps: 8
  vram_thresholds: {high: 10, medium: 6, low: 3}
  encoding: {crf: 17, preset: "slow"}
```

SVD is NOT being used in the current active pipelines - the main generate_video_pipeline uses AnimateDiff instead.

---

## 10. ANIMATEDIFF-LIGHTNING

### Main integration: `AnimateDiffPipeline` (`/backend/src/video/animatediff_pipeline.py`)

**Config:**
- Repo: `ByteDance/AnimateDiff-Lightning`
- Checkpoint: `animatediff_lightning_4step_diffusers.safetensors`
- Base model: `emilianJR/epiCRealism` (SD 1.5 photorealistic)
- VRAM: ~5.6GB
- 4-step distilled (very fast)
- Default: 16 frames, guidance_scale=1.0 (Lightning-specific - low CFG)
- Default resolution: 576x1024 (portrait)
- 75-token CLIP limit (SD 1.5 constraint)

**AnimateDiffGenerator (`/backend/src/cinematography/animatediff_generator.py`, 381 lines):**
- `load()`: Loads motion adapter + base model + EulerDiscreteScheduler (trailing timestep spacing, linear beta schedule)
- `generate(prompt, negative_prompt, num_frames=16, guidance_scale=1.0, seed=-1, width=576, height=1024)`: Returns `List[np.ndarray]` as BGR frames
- `generate_batch(prompts, ...)`: Increments seed per video for variation
- `kill()`: Deletes all components (motion_adapter, unet, vae) + GC + CUDA cache clear
- HeartbeatCallback: JSON progress at each denoising step

**AnimateDiffPipeline (`/backend/src/video/animatediff_pipeline.py`):**
- `__init__(target_fps=8, interpolate=False, heartbeat_callback=None)`
- Note: `interpolate=False` by default - RAFT disabled to fix blur issue
- `generate_all_scenes(storyboard_dict) -> Dict[int, dict]`
  - Processes each scene sequentially
  - Selects appropriate style based on scene mood/description via `detect_style()` / `get_style_definition()`
  - Saves clips to `data/generated_videos/`
  - Returns `{scene_index: {"video_path": str, "frames": List}}`

**The USE_ANIMATEDIFF flag** in main.py (line 44): `True` - all /api/generate-video calls now use AnimateDiff.

**Integration in generate_video_pipeline:**
1. Calls `AnimateDiffPipeline.generate_all_scenes(storyboard_dict)`
2. Builds `video_clips_map = {timestamp: video_path}`
3. Calls `assembler.create_video_enhanced()` instead of `create_video()`

---

## 11. VRAM MANAGER & MODEL SYSTEM

### VRAMManager (`/backend/src/local/vram_manager.py`, 496 lines)
The "Kill and Revive" pattern for 12GB VRAM budget.

**Rule:** Only ONE model loaded at a time. Kill before swap.

**kill() method:**
1. `pipe.unload_lora_weights()` (prevents weight contamination)
2. `del self.pipe` + `self.pipe = None`
3. `gc.collect()` × 3
4. `torch.cuda.empty_cache()` + `torch.cuda.synchronize()`
- Must return to <1.5GB after kill

**ModelRouter:**
- Resolves standard names (e.g., "STANDARD_US") to absolute file paths
- Handles aliases (alias_of)
- Injects trigger_tags for PONY model ("score_9, score_8_up, score_7_up")
- Returns scheduler overrides for LIGHTNING

### 5 Model Standards (checkpoints.yaml)

| Standard | Path | VRAM | Trigger Tags |
|----------|------|------|-------------|
| STANDARD_US | /synterra/models/Juggernaut-XL-v9.safetensors | 6.5GB | none |
| STANDARD_CINEMATIC | backend/models/RealVisXL_V5.0_fp16.safetensors | 6.5GB | none |
| STANDARD_ANATOMY | backend/models/lustify_v2.safetensors | 4.8GB | none |
| STANDARD_ACTION | backend/models/ponyDiffusionV6XL.safetensors | 6.5GB | "score_9, score_8_up, score_7_up" |
| STANDARD_DRAFT | backend/models/sdxl_lightning_4step.safetensors | ~6GB | DPMSolverMultistep scheduler |

**Models physically present on disk:**
- Juggernaut-XL-v9: YES (at /synterra/models/)
- RealVisXL_V5.0_fp16: YES (6.5GB)
- lustify_v2: YES (4.8GB)
- ponyDiffusionV6XL: YES (6.5GB)
- sdxl_lightning_4step: YES (6.5GB)

---

## 12. VIDEO ASSEMBLER (`/backend/src/video/assembler.py`, 721 lines)

Uses MoviePy 2.x API (breaking changes from 1.x - methods renamed).

**Key constants:**
- `TARGET_RESOLUTION = (1920, 1080)`
- `TRANSITION_DURATION = 0.75` seconds
- GPU encoding forced OFF: `self.gpu_available = False` (NVENC disabled due to compatibility issues)

**create_video(audio_file, scene_assets, storyboard, task_id):**
- Takes scene_assets: `Dict[float, List[GeneratedImage]]`
- Each scene: looks up by timestamp (with 0.01 tolerance)
- Creates ImageClip per scene, applies cinematic processing + effects
- Uses `concatenate_videoclips(video_clips, method="compose")`
- Falls back to placeholder clip if image not found

**create_video_enhanced(audio_path, scene_assets, video_clips_map, storyboard, task_id):**
- Extended version that handles BOTH video clips (AnimateDiff) and static images
- Video clips get longer transition (0.75s), same-type transitions (0.375s)

**_apply_effects(clip, scene):** Ken Burns effects via resized():
- zoom_in: 1.0 → 1.15x
- zoom_out: 1.15 → 1.0x
- pan_right/pan_left: resize 1.3x then position-based scroll
- fade_in/fade_out: CrossFadeIn/CrossFadeOut vfx

**_apply_cinematic_processing(clip, scene):** The "vibe pass":
1. Film grain (normal noise σ=8)
2. Color grading: cv2.addWeighted(frame, 1.1, frame, 0, -10)
3. Saturation boost ×1.2 in HSV
4. Vignette: 30% darkening at edges

**create_davinci_project():** Exports JSON (not actual DRP format) with clip timing and suggested color grades.

**Encoding:** libx264, preset=medium, CRF=18 (forced CPU, NVENC disabled with TODO comment)

---

## 13. FASTAPI BACKEND - ALL ENDPOINTS

**Server:** main.py, port 8002 (when run directly), port 8000 (uvicorn default)

### Core Pipeline Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/analyze-audio | Upload audio, run librosa + Whisper, return song structure |
| POST | /api/generate-section-recommendations | AI narrative analysis per section |
| POST | /api/analyze-and-storyboard | Full audio→storyboard pipeline (background task) |
| POST | /api/generate-images-and-video | Generate images + video from approved storyboard |
| POST | /api/generate-video | Legacy: full pipeline in one call (no storyboard preview) |

### Task Management
| Method | Path | Purpose |
|--------|------|---------|
| WS | /ws/{task_id} | Real-time WebSocket progress updates (polls every 1s) |
| GET | /api/task-status/{task_id} | Polling fallback (no WebSocket) |
| GET | /api/download/{video_id} | Download generated MP4 |

### Storyboard Operations
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/generate-storyboard-previews | Generate preview images for review |
| POST | /api/cached-storyboard-previews | Use existing cached images (test mode) |
| POST | /api/regenerate-scene | Regenerate single scene with new prompt |
| GET | /api/regeneration-status/{task_id} | Check scene regeneration status |
| GET | /api/export-storyboard/{task_id} | Export as JSON or Markdown |
| POST | /api/import-storyboard | Re-import previously exported storyboard |

### Test/Debug Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/test-video-only | Skip generation, use cached images + stored audio |
| POST | /api/test-video-with-audio | Use your audio + cached images |
| GET | /api/test-debug | Verify server is running updated code |
| GET | /debug/routes | List all registered routes |

### AI / Style Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/style-suggestions | Get style suggestions from ConceptGenerator |
| POST | /api/rebuild-video | Rebuild video after scene edits |
| GET | /api/references | List reference images |

### Cultural Content Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/analyze-cultural-content | Analyze single image for cultural sensitivity |
| POST | /api/process-cultural-content | Process entire storyboard for cultural compliance |
| POST | /api/approve-cultural-modifications | Apply approved modifications |

### Animation Workflow Endpoints (INLINE in main.py, not the router)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/animation/styles | List 16 animation styles |
| GET | /api/animation/loras | List character/scene/style LoRAs from registry |
| POST | /api/animation/generate | Start animation workflow background task |
| POST | /api/upload-audio | Upload audio for animation |

### RunPod/Cloud Endpoints (Phase 9, cloud-only)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/generate-wan | WAN 2.6 scene generation (RunPod) |
| POST | /api/stitch-skyreels | SkyReels V2 DF stitching (RunPod) |

### Misc
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/export-davinci/{task_id} | Export DaVinci Resolve project JSON |
| POST | /api/set-cinematic-mode/{task_id} | Configure cinematic processing settings |
| GET | /api/health | Health check |
| GET | /api/status | API status |

### CRITICAL BUG: api_animation_endpoints.py router NOT mounted
`api_animation_endpoints.py` creates `animation_router = APIRouter(prefix="/api/animation")` with endpoints at `/api/animation/styles`, `/api/animation/loras`, `/api/animation/generate`, `/api/animation/upload-character-lora`, `/api/animation/projects`, `/api/animation/save-project`. However, this router is NEVER included in `main.py`. The animation endpoints that DO work are manually duplicated inline in main.py (lines 2186-2314). The router file is dead code.

**Task storage:** In-memory dict `active_tasks = {}`. No persistence - tasks lost on server restart.

---

## 14. REACT FRONTEND

### App.tsx (73 lines)
Two-tab mode selector: "Storyboard Workflow" (Film icon) vs "Animation Workflow" (Wand2 icon + NEW badge)
- Default mode: 'storyboard'
- Uses: VideoGenerator, AnimationVideoGenerator, Header components

### Component Overview

**VideoGenerator.tsx (878 lines)** - Main storyboard workflow orchestrator:
- Stages: upload → analyze → storyboard → preview → generate → complete
- WebSocket for progress via `ws://localhost:8000/ws/{task_id}`
- State: audioFile, taskId, songStructure, storyboardScenes, generatedPreviews, videoUrl
- Uses InteractiveTimeline, StoryboardEditor, SceneEditModal, ProgressTracker

**AnimationVideoGenerator.tsx (490 lines)** - Animation workflow UI:
- Stages: upload → configure → generating → complete
- Calls `/api/upload-audio`, then `/api/animation/generate`
- WebSocket via `ws://localhost:8000/ws/{task_id}`
- State: audioFile, animationStyle, qualityTier, protagonistLora, supportingLoras, sceneLoras, styleLora
- Shows stage progress with checkmarks

**AnimationStyleSelector.tsx** - Grid of 16 animation styles with preview cards

**CharacterLoRAUpload.tsx** - Upload interface for custom character LoRAs, calls LoRA listing endpoints

**AudioUpload.tsx** - Drag-drop audio file upload, accepts mp3/wav/m4a/flac

**StoryboardEditor.tsx** - Scene-by-scene preview grid, edit/regenerate per scene

**SceneEditModal.tsx** - Modal for editing scene description + triggering regeneration

**InteractiveTimeline.tsx** - Visual timeline of song structure with scene overlays

**ProgressTracker.tsx** - 5-step progress bar visualization

**VideoPreview.tsx** - Video player + download button for completed video

**CulturalContentSettings.tsx / CulturalProcessingModal.tsx** - Cultural compliance UI

**ReferenceImageUpload.tsx** - Character/background reference image management

**ProviderSettings.tsx** - AI provider configuration panel (DALL-E, NovelAI, etc.)

**Header.tsx** - App header with branding

### Frontend → Backend URL
Hardcoded `apiUrl = 'http://localhost:8000'` in AnimationVideoGenerator.
VideoGenerator likely uses same (no env config).

---

## 15. CINEMATOGRAPHY ENGINE

### CinematographyEngine (`/backend/src/cinematography/engine.py`, 345 lines)
Orchestration facade combining OpticsCatalog + StyleLogic + PromptComposer.

**`compose(subject, style=None, camera=None, film_stock=None, lighting=None) -> ComposedPrompt`**
Generates photorealistic prompts with specific optics profiles.

### StyleLogic (`/backend/src/cinematography/style_logic.py`, 399 lines)
- `detect_style(prompt: str) -> str`: Pattern-matches prompt to style
- `get_style_optics(style) -> dict`: Returns optics profile for style
- `get_style_prefix(style) -> str`: Style-specific prompt prefix
- Used by AnimateDiffPipeline to select appropriate generation style

### PromptComposer (`/backend/src/cinematography/prompt_composer.py`, 367 lines)
- `compose_prompt(subject, optics, style_prefix) -> ComposedPrompt`
- `MANDATORY_QUALITY_TOKENS`: appended to all prompts
- `inject_action_framing(prompt, scene_type) -> str`

### OpticsCatalog (`/backend/src/cinematography/optics.py`, 274 lines)
- Loads from `library/optics_presets.yaml`
- Cameras: ARRI_ALEXA_65, RED_MONSTRO, etc.
- Film stocks: CINESTILL_800T, etc.
- Lighting presets: DRAMATIC_RIM_LIGHTING, etc.
- ADetailerConfig for face/hand enhancement

---

## 16. OTHER CINEMATOGRAPHY MODULES

### RAFTInterpolator (`/backend/src/cinematography/raft_interpolator.py`, 280 lines)
- Uses `torchvision.models.optical_flow` (no compilation required)
- 'large' or 'small' model
- `interpolate(frame1, frame2, n_interp=7) -> List[np.ndarray]`
- Handles anatomical preservation during high-velocity motion
- Currently DISABLED in AnimateDiffPipeline (interpolate=False to fix blur)

### WAN26CloudGenerator (`/backend/src/cinematography/wan26_cloud_generator.py`, 329 lines)
- Runs ON RunPod pod
- WAN 2.6 text-to-video generation
- 720p/1080p output
- For photorealistic music videos

### SkyReelsDFGenerator (`/backend/src/cinematography/skyreels_df_generator.py`, 164 lines)
- SkyReels V2 Diffusion Forcing for seamless scene stitching
- Eliminates cuts between WAN scenes

### CogVideoXGenerator (`/backend/src/cinematography/cogvideox_generator.py`, 107 lines)
- New/experimental: CogVideoX model integration
- Test files exist: cogvideox_minimal_frame.png, cogvideox_test_frame.png
- NOT integrated into any active pipeline

### PhysicsMotionTracker (`/backend/src/cinematography/physics_motion_tracker.py`, 378 lines)
- Physics-based motion simulation
- Not integrated into active pipelines

### TemporalConsistency (`/backend/src/cinematography/temporal_consistency.py`, 355 lines)
- Frame-to-frame consistency maintenance
- Not integrated into active pipelines

---

## 17. IMAGE GENERATOR (`/backend/src/assets/generator.py`)
The older multi-provider generator (cloud APIs):
- `MultiProviderImageGenerator` - routes to DALL-E, NovelAI, or Nano Banana (Google Gemini)
- `GeneratedImage` dataclass: scene_timestamp, image_path, provider, prompt, variation_index
- `generate_all_scenes(storyboard, provider="auto") -> Dict[float, List[GeneratedImage]]`
- `regenerate_scene_image(timestamp, new_desc, provider) -> List[GeneratedImage]`
- Plans exist to REMOVE cloud API providers and replace with local (REFACTORING_PLAN_LOCAL_PIPELINE_V2.md)

---

## 18. LOCAL IMAGE GENERATOR (`/backend/src/local/image_generator.py`, 491 lines)
Universal wrapper for VRAMManager multi-model factory.

**Supports all 5 Standards via legacy checkpoint name mapping:**
- "base", "photoreal" → STANDARD_US
- "cinematic", "realvis" → STANDARD_CINEMATIC
- "anatomy", "lustify" → STANDARD_ANATOMY
- "action", "pony" → STANDARD_ACTION
- "draft", "lightning", "fast" → STANDARD_DRAFT

**generate(prompt, checkpoint="STANDARD_CINEMATIC", ...) -> GeneratedImage**
- Loads model via VRAMManager.load(standard)
- Applies trigger tags via ModelRouter.prepare_prompt()
- Saves to OUTPUT_DIR with UUID filename
- Returns GeneratedImage with path + metadata

---

## 19. MOTION SMOOTHER (`/backend/src/local/motion_smoother.py`, 467 lines)
RIFE-based frame interpolation via Vulkan.
- Uses `RIFE_ENGINE_PATH` from .env
- Target: 60 FPS from 8 FPS SVD output
- Interpolation factor: 4x (25 frames → 100 frames per settings.yaml)
- Loop blend frames: 3 (smooths loop point)

---

## 20. CULTURAL CONTENT PROCESSOR (`/backend/src/content/cultural_processor.py`)
Uses GPT-4 Vision to analyze and potentially modify generated images.
- Standards: "european", "american", "conservative"
- `analyze_scene_content(image_path) -> ContentAnalysis`
- `batch_process_storyboard(image_paths, standard, contexts) -> List[ProcessingResult]`
- `generate_modification_report(results) -> Dict`

---

## 21. SAFETY / COMPLIANCE GATE (`/backend/src/safety/compliance_gate.py`)
- `ComplianceGate` class
- Age classification via ViT-Age-Classifier
- Not fully implemented/integrated

---

## 22. TESTS

### Test Files in `/backend/tests/`:
- `conftest.py` - pytest configuration
- `test_cinematography_engine.py` - CinematographyEngine unit tests
- `test_prompt_composer.py` - PromptComposer unit tests
- `test_style_logic.py` - StyleLogic unit tests
- `test_temporal_consistency.py` - TemporalConsistency tests
- `test_vram_manager.py` - VRAMManager tests
- `test_vram_integration.py` - VRAM integration tests
- `test_multi_model_swap.py` - Multi-model switching tests
- `test_full_pipeline_handover.py` - Full pipeline handover tests
- `test_windows_handoff.py` - Windows file handoff tests

### Root-level test scripts:
- `autonomous_test_session.py` - Autonomous test runner
- `backend/production_smoke_test.py` - Smoke test
- `backend/test_animatediff_standalone.py` - AnimateDiff standalone test
- `backend/test_assembler_debug.py` - Assembler debugging

### Known Test Status (from TESTING_STATUS.md, FINAL_TEST_STATUS.md):
- Module import tests: 8/8 passing
- End-to-end pipeline: NEVER run successfully with real models

---

## 23. KNOWN BUGS & TECHNICAL DEBT

### Critical Issues
1. **`api_animation_endpoints.py` router is dead code** - never mounted in main.py. The duplicate inline endpoints at lines 2186-2314 work instead.

2. **LoRA fuse pattern may cause GPU memory leaks** - `_apply_loras_to_pipeline` calls `fuse_lora()` which permanently merges weights. Calling `unload_lora_weights()` before this may not fully clean up.

3. **Hardcoded scene templates in animation_workflow.py** - The `_generate_character_scenes()` method uses tropical island templates regardless of the actual song or config. Not driven by audio analysis.

4. **Stock footage collection not implemented** - `_collect_stock_footage()` returns empty list with print statement.

5. **Temporal consistency not implemented** - `RotoscopeConfig.temporal_consistency=True` and `process_frame(previous_frame=...)` parameter both exist but `previous_frame` is ignored in the implementation.

6. **`active_tasks` in-memory only** - All task state lost on server restart. No Redis or persistent storage.

7. **NVENC GPU encoding disabled** with hardcoded `self.gpu_available = False` - TODO comment suggests debugging needed.

8. **AnimateDiff RAFT interpolation disabled** (`interpolate=False`) - blur issue not resolved, just disabled.

9. **File path bugs possible** - `/api/animation/loras` in main.py looks at `config/loras.yaml` (relative) while running from `backend/` directory. Should work if CWD is backend/.

10. **Double-definition of AnimationProjectRequest** - Defined in both `api_animation_endpoints.py` (unused) AND in `main.py` (line 2172). The `from pydantic import BaseModel` reimport at line 2171 is redundant.

### Architecture Concerns
11. **main.py is 2315 lines** - Monolith with all pipelines, background tasks, models inlined. Should be split into routers.

12. **Two separate animation endpoint systems** - The router in `api_animation_endpoints.py` and the inline endpoints in main.py serve the same purpose but both exist.

13. **USE_ANIMATEDIFF flag** - When True, the storyboard generate_video pipeline uses AnimateDiff but the separate `generate_images_and_video_pipeline` (for the storyboard approval flow) still uses MultiProviderImageGenerator with cloud APIs.

14. **Scene LoRA path resolution**: Registry files say e.g. `file: "tiki-bar-interior/tiki-bar-interior.safetensors"` but only the 3 checkpoint files exist (625, 1250, 1875 steps), NOT a final `tiki-bar-interior.safetensors`. These would FileNotFoundError.

---

## 24. CONFIGURATION SYSTEM

**env_loader.py priority:**
1. `~/.claude/.env` (global, loaded first, lower priority)
2. `backend/.env` (local, overrides global)

**Key env variables:**
- `OPENAI_API_KEY` - required for ConceptGenerator, StoryboardGenerator, Whisper
- `GOOGLE_AI_API_KEY` - Nano Banana / Gemini image generation
- `NOVELAI_API_KEY` - NovelAI image generation
- `REPLICATE_API_TOKEN` - Replicate models
- `USE_RUNPOD_HYBRID` - Route to RunPod cloud (default: false)
- `RUNPOD_ENDPOINT_URL` - RunPod API endpoint
- `RIFE_ENGINE_PATH` - Path to RIFE executable
- `SVD_OUTPUT_PATH` or `svd_output` - Output directory for SVD/local pipeline
- `WINDOWS_DOWNLOADS` or `windows_downloads` - Windows handoff path (WSL)

**settings.yaml:** SVD config, motion smoothing, generation profiles
**checkpoints.yaml:** Model standards with paths and VRAM estimates
**loras.yaml:** LoRA registry with 5 enabled entries
**optics_presets.yaml:** Camera/film stock/lighting presets for CinematographyEngine
**production_styles.yaml:** Production style definitions used by LocalImageGenerator

---

## 25. CURRENT STATE OF TRAINED LORAS

### In `output/loras/` (the active directory):
| LoRA | Files | Status |
|------|-------|--------|
| rob-character | rob-character.safetensors (82MB) | TRAINED, in registry |
| michele-character | michele-character.safetensors (82MB) | TRAINED, in registry |
| 70s-film-retro | 3 checkpoints (625/1250/1875 steps) | Trained, NOT in registry, no final file |
| beach-bar-exterior | 3 checkpoints | Trained, NOT in registry, no final file |
| beach-sunset | 3 checkpoints | Trained, in registry AS FINAL but final file MISSING |
| boat-deck | 3 checkpoints | Trained, not in registry |
| bonfire-beach | 3 checkpoints | Trained, in registry AS FINAL but final file MISSING |
| ocean-underwater | 3 checkpoints | Trained, not in registry |
| stage-performance | 3 checkpoints | Trained, not in registry |
| tiki-bar-interior | 3 checkpoints | Trained, in registry AS FINAL but final file MISSING |

### CRITICAL BUG: Scene LoRA files missing
The registry expects `beach-sunset/beach-sunset.safetensors` but the directory only contains checkpoint files named `beach-sunset_000001875.safetensors`. The final merged file needs to be either:
- Renamed: `cp beach-sunset_000001875.safetensors beach-sunset/beach-sunset.safetensors`
- Or the registry needs to point to the checkpoint files

### In `backend/models/loras/` (old location):
- cinematic_grit_v1.safetensors (73MB)
- pony_anatomy_v2.safetensors (650MB)
- urban_atmosphere.safetensors (218MB)

These are style LoRAs not registered in `backend/config/loras.yaml`.

---

## 26. HANDOFF HISTORY & PROJECT VISION

### Phase evolution (from handoff documents):
- **Phases 1-7:** Built cloud-based storyboard pipeline (OpenAI + Google Gemini)
- **Phase 8:** Added AnimateDiff-Lightning as video generation, replaced static images
- **Phase 8.2:** AnimateDiff integration (USE_ANIMATEDIFF=True)
- **Phase 8.4 target:** Full AnimateDiff end-to-end working
- **Phase 9 plan:** Performance (parallel gen, RIFE), WAN 2.1/2.2, 1080p
- **Animation Workflow (Feb 16):** Completely new system added - SDXL + ControlNet rotoscope for local artistic generation

### Original vision: "Island Girl" by Rob Hill
- Trop Rock beach music video
- Rob (protagonist) + Michele (supporting character)
- Watercolor animation style recommended for genre
- Scenes: airport arrival → beach solo → meet island girl → together → bonfire → dancing
- No actual audio file for "Island Girl" in the repo (only `rob_hill_love_and_saltwater.wav`)
- The project was generalized from Island Girl → any music video project

### Two competing strategies (unresolved):
1. **Cloud photorealism** (WAN 2.6 + SkyReels on RunPod) - $0.30/video + RunPod costs
2. **Local artistic animation** (SDXL + ControlNet rotoscope) - $0 but requires GPU + ControlNet pipeline working

### What needs to happen for first working video:
1. Fix scene LoRA file paths (rename checkpoint files to final names)
2. Start servers: `cd backend && uvicorn main:app --reload`
3. Start frontend: `cd frontend && npm start` 
4. Upload test audio
5. Select watercolor style + Rob protagonist LoRA
6. Run Basic tier (12 scenes)
7. Verify ControlNet rotoscope works OR falls back to slideshow gracefully

---

## 27. DATASETS

### Rob character dataset (`datasets/rob-character/`)
- 25 PNG images (AI-generated via ChatGPT Image, Feb 16 2026 09:xx)
- 25 TXT captions (all: "a photo of ohwx man, portrait")
- Training: 1500 steps, SDXL, rank 16 LoRA, lr=5e-5, adamw8bit

### Michele character dataset (`datasets/michele-character/`)
- Same structure as Rob: 25 PNG + 25 TXT
- All captions: "a photo of ohwx woman, portrait"
- Same training config

### 70s-film-retro dataset (`datasets/70s-film-retro/`)
- 30 JPG images + latent cache (.safetensors)
- Caption files (.txt) and metadata (.meta.json) per image
- Diverse captions describing 70s film aesthetic scenes

---

## 28. KEY FILE LOCATIONS SUMMARY

| Purpose | File |
|---------|------|
| API server | `/backend/main.py` |
| Audio analysis | `/backend/src/audio/analyzer.py` |
| Concept generation (GPT-4) | `/backend/src/storyboard/conceptor.py` |
| Storyboard generation | `/backend/src/storyboard/generator.py` |
| SDXL + LoRA generation | `/backend/src/assets/sdxl_lora_generator.py` |
| ControlNet rotoscope | `/backend/src/animation/rotoscope_generator.py` |
| Animation workflow orchestrator | `/backend/src/animation/animation_workflow.py` |
| AnimateDiff pipeline | `/backend/src/video/animatediff_pipeline.py` |
| AnimateDiff generator | `/backend/src/cinematography/animatediff_generator.py` |
| SVD video generator | `/backend/src/local/video_generator.py` |
| VRAM manager | `/backend/src/local/vram_manager.py` |
| Cinematic director | `/backend/src/local/cinematic_director.py` |
| Video assembler (MoviePy) | `/backend/src/video/assembler.py` |
| RAFT interpolator | `/backend/src/cinematography/raft_interpolator.py` |
| Model standards | `/backend/config/checkpoints.yaml` |
| LoRA registry | `/backend/config/loras.yaml` |
| SVD/generation settings | `/backend/config/settings.yaml` |
| React app root | `/frontend/src/App.tsx` |
| Storyboard workflow UI | `/frontend/src/components/VideoGenerator.tsx` |
| Animation workflow UI | `/frontend/src/components/AnimationVideoGenerator.tsx` |
| Character LoRAs | `/output/loras/{name}/{name}.safetensors` |
| Training datasets | `/datasets/{name}/` |
| Generated images | `/backend/data/generated_images/` |
| Generated videos | `/backend/data/generated_videos/` |

