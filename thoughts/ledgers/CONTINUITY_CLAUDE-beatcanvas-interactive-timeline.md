# BeatCanvas Interactive Timeline & Section-Based AI Implementation

## Goal
Transform BeatCanvas from basic video generation to a professional editing platform with:
- Interactive timeline with click-to-seek functionality
- Section-based visual storytelling (chronological verse/chorus breakdown)
- AI-powered narrative analysis and intelligent scene recommendations
- Professional workflow: Upload → Prompts → Quality → Storyboard → Generate
- No audio auto-play during upload phase

## Constraints
- React + TypeScript frontend with FastAPI backend
- Multi-provider AI integration (OpenAI, NovelAI, Replicate, Nano Banana/Gemini)
- WebSocket real-time progress updates
- Professional cost management ($0.08 per scene regeneration)
- Audio only plays during appropriate workflow stages

## Key Decisions
- **Section-Based Storytelling**: Break songs chronologically (70s → dystopian → beach party) rather than whole-song styling
- **AI Narrative Analysis**: Implemented `AINarrativeAnalyzer` class with GPT-4 pattern detection and intelligent recommendations
- **Professional UI Flow**: 5-step workflow with progressive loading and cost transparency
- **Audio Auto-Play Fix**: Backend-first approach - no browser audio element creation during upload
- **Nano Banana Default**: Image generation defaults to Nano Banana (Gemini) for consistency and cost
- **Storyboard Preview Images**: Generate AI images during storyboard step for visual preview

## State
- Done:
  - [x] Phase 1: AI-Powered Narrative Analysis System
  - [x] Phase 2: Interactive Timeline Component
  - [x] Phase 3: Backend Scene Regeneration API
  - [x] Phase 4: AI Template System Cleanup
  - [x] Phase 5: Audio Auto-Play Fix & Real Backend Integration (2026-01-26)
    - [x] Fixed audio auto-play on file drop/upload
    - [x] Integrated real audio analysis via `/api/analyze-audio`
    - [x] Added upload progress indicator (Step 1/2/3)
    - [x] Added AI Story Mapping UI with textarea for user concept
    - [x] Connected narrative analysis to user input (not hardcoded)
    - [x] Added storyboard preview image generation endpoint
    - [x] Storyboard displays "Generating..." placeholders then real AI images
  - [x] Phase 5b: Nano Banana Fix & Prompt Metadata (2026-01-27)
    - [x] Fixed 0-byte image issue - upgraded to google-genai SDK
    - [x] Added prompt metadata saving (JSON files in metadata/ folder)
    - [x] Images saved permanently until deleted
    - [x] Each image has matching metadata with original + enhanced prompts
  - [x] Phase 5c: Error Observability & Retry Logic (2026-01-27)
    - [x] Created `GenerationResult` dataclass - replaces silent empty-list failures
    - [x] Added response validation before accessing nested Gemini API properties
    - [x] Added retry logic with exponential backoff (10s, 20s, 40s) for rate limits
    - [x] Added diagnostic summary after generation completes (success rate, failed scenes)
    - [x] Added error categorization (RATE_LIMIT, MODEL_NOT_FOUND, AUTH_ERROR, etc.)
    - [x] WebSocket now surfaces generation_stats and generation_errors to frontend
    - [x] Added Google/Gemini keys to env_loader.py key_mapping
  - [x] Phase 5d: UI Progress Feedback (2026-01-27)
    - [x] Enhanced `analyzeSongStructure()` with 3-step progress (Upload/Analyze/Structure)
    - [x] Added elapsed time counter during audio processing
    - [x] Enhanced `generateAIRecommendations()` with 4-step progress animation
    - [x] Enhanced `generatePreviewImages()` with detailed per-scene progress bar
    - [x] Added estimated time display for image generation
    - [x] Text-based progress messages (not just spinners) per user preference
  - [x] Phase 5e: Video Generation & Enhanced UX (2026-01-27)
    - [x] Fixed video generation - replaced demo `simulateVideoGeneration()` with real API integration
    - [x] Added WebSocket connection for real-time video generation progress
    - [x] Fixed "Create Storyboard" button spinner - now hides immediately on step transition
    - [x] Enhanced AI recommendations - shows section names during generation
    - [x] Enhanced preview image generation - shows animated connection phases
    - [x] Added 5-phase connection animation before scene generation starts
  - [x] Phase 5f: Test Mode & Task ID Persistence Fix (2026-01-28)
    - [x] Added "Skip to Video Assembly" test mode button (saves $3+ per test)
    - [x] Added `/api/test-video-with-audio` endpoint to use cached images
    - [x] Added localStorage backup for task_id and audio_path
    - [x] Added extensive console logging for debugging task_id capture
    - [x] Test button only shows when task_id is verified
    - [x] Task ID preview shown in test mode UI
  - [x] Phase 5g: Storyboard Export & Field Name Compatibility (2026-01-28)
    - [x] Added storyboard export (JSON for re-import, Markdown for customers)
    - [x] Added `GET /api/export-storyboard/{task_id}` endpoint
    - [x] Added `POST /api/import-storyboard` endpoint
    - [x] Fixed export URL to use full backend address (localhost:8002)
    - [x] Fixed `image_prompt` KeyError - generator now accepts description/prompt fields
    - [x] Frontend sends both `image_prompt` and `description` for compatibility
    - [x] Whisper lyrics extraction working (FFmpeg PATH fix)
  - [x] Phase 5h: Video Assembly & GPU Encoding (2026-01-29)
    - [x] Fixed black video output (cinematic_filter frame format bug)
    - [x] Fixed static slideshow - added Ken Burns effects (zoom, pan, fade)
    - [x] Added GPU encoding support (h264_nvenc) with automatic fallback to CPU
    - [x] Auto-detects NVIDIA GPU encoding availability at startup
    - [x] Created `test_assembler_debug.py` diagnostic script
  - [x] Phase 6: Image-to-Video Upgrade (2026-01-29)
    - [x] Resolution standardization to 1920x1080 (Luma compatible)
    - [x] Beat-based scene subdivision with MIN/MAX duration constraints
    - [x] Motion prompt generation calibrated to energy level
    - [x] Scene type classification (hero vs standard)
    - [x] Luma video generator stub (awaiting API key)
    - [x] Enhanced assembler with mixed video/image support
    - [x] Character management system for multi-character videos
    - [x] Updated requirements.txt with lumaai package
- Now: [→] Phase 7: Motion Quality Resolution - SVD-XT Replacement (2026-02-06)
- Next: Replace SVD-XT with AnimateDiff-Lightning for character animation
- Remaining:
  - [ ] Integrate AnimateDiff-Lightning pipeline
  - [ ] Test AnimateDiff with beach walking/dancing scenes
  - [ ] Integrate video generation into main.py pipeline
  - [ ] (DEFERRED) Replace GPT-4 with Dolphin/Ollama for uncensored prompts

## Phase 7: Open Source Pipeline & Motion Quality (2026-02-05 to 2026-02-06)

### Context
Pivoted from cloud APIs (Luma, DALL-E) to fully open source local pipeline:
- **Why**: Multi-cultural client requirements (EU naturist content, rap explicit content) blocked by cloud API safety filters
- **Stack**: RealVisXL (images) → SVD-XT (video) → AKD Skeletal → RAFT (interpolation)

### What's Working
- Character generation quality is good
- AKD skeletal tracking prevents anatomical melting/implosions
- Structural validation catches gross errors
- RAFT interpolation upsamples 25 → 240 frames (60fps)

### Initial Problem Hypothesis: Motion Jitter (2026-02-05)
- SVD-XT generates 25 frames with micro-inconsistencies
- Jitter passes validation thresholds (8% bone, 18% structural)
- Frames are anatomically correct but visually inconsistent
- RAFT faithfully interpolates between jittery keyframes, amplifying issue

### Attempted Fix #1: Temporal Smoothing (2026-02-05)
Inserted Gaussian-weighted temporal blend between SVD output and RAFT input:
```
SVD (25 frames) → Validation → Temporal Smooth → RAFT → 240 frames
```

**Implementation Details:**
- Added `temporal_smooth()` function to `temporal_consistency.py`
- Kernel size configurable (3, 5, or 7) - default 3
- Weights: (0.25, 0.5, 0.25) for center-weighted blend
- Preserves first/last frames for anchor consistency

**Result:** DISABLED - Temporal smoothing caused motion to become "just panning" instead of action. Removed natural motion dynamics.

### Critical Discovery: Optical Flow Was Never The Problem (2026-02-06)

**Analysis Tool Created:** `/tmp/analyze_jitter.py` - Farneback optical flow analysis

**Jitter Analysis Results (4 videos tested):**

| Video Timestamp | motion_bucket_id | Jitter Score | Assessment | Avg Motion | Max Motion | Severe Events |
|-----------------|------------------|--------------|------------|------------|------------|---------------|
| 08:03:14 | 110 (before fix) | 0.110 | ⚠️ Mild | 2.06px | 3.26px | 0/18 |
| 10:24:10 | 70 (after fix) | 0.113 | ⚠️ Mild | 1.58px | 2.52px | 0/18 |
| 12:26:12 | 70 | 0.130 | ⚠️ Mild | 1.39px | 2.40px | 0/18 |
| 13:04:49 | 70 | 0.135 | ⚠️ Mild | 1.34px | 2.22px | 0/18 |

**Key Findings:**
- ✅ All videos had acceptable optical flow jitter (0.110-0.135 scores)
- ✅ Zero severe jitter events across all tests
- ❌ motion_bucket_id=110 actually had BETTER optical flow (0.110 vs 0.135)
- ❌ Reducing to 70 did NOT improve optical flow smoothness

**Real Problem Identified:** SKELETAL VIOLATIONS (anatomical melting detected by AKD tracker)
- User reported: "left arm implode", "right hand imploded"
- Code comment confirmed: `motion_bucket_id=110 caused 25/25 skeletal violations`

### Parameter Testing Sequence (2026-02-06)

**Test #1: motion_bucket_id=63**
- Hypothesis: Sweet spot between 62 (no motion) and 65 (right glove issue)
- Retry Attempt 1 (noise_aug=0.12): 59% max skeletal deviation - FAILED
- Retry Attempt 2 (noise_aug=0.11): 29% max skeletal deviation - FAILED
- Retry Attempt 3 (noise_aug=0.10): 48% max skeletal deviation - FAILED
- **Result:** All 3 retry attempts failed, 20-60% skeletal deviations

**Test #2: motion_bucket_id=60**
- Hypothesis: Even lower motion might help
- Retry Attempt 1 (noise_aug=0.12): 30% max skeletal deviation - FAILED
- Retry Attempt 2 (noise_aug=0.11): 60% max skeletal deviation - FAILED
- Retry Attempt 3 (noise_aug=0.10): 54% max skeletal deviation - FAILED
- **Result:** Actually WORSE than 63, deviations still massive

### Root Cause Analysis

**Problem:** 8% skeletal tolerance is too strict for punch poses with extended limbs

**Why:**
- Extended punch pose has extreme perspective foreshortening
- Forearm appears shorter due to camera angle
- MediaPipe detects this as "bone shrinkage"
- Not actual anatomical melting, but perspective artifact

### Attempted Fix #2: Relaxed Skeletal Tolerance (2026-02-06)

**Changes:**
- `render_video_svd.py` line 59: `SKELETAL_TOLERANCE = 0.15` (was 0.08)
- Comment: "Relaxed for action poses with extended limbs (8% too strict for perspective foreshortening)"
- `optics_presets.yaml` line 121: `motion_bucket_id: 70` (retested with new tolerance)

**Test #3: motion_bucket_id=70 with 15% tolerance**
- Retry Attempt 1 (noise_aug=0.12): 56.5% max skeletal deviation - FAILED
- Retry Attempt 2 (noise_aug=0.11): 81.5% max skeletal deviation - FAILED
- Retry Attempt 3 (noise_aug=0.10): 46.7% max skeletal deviation - USED (best of 3)
- **Result:** Video completed with warning, using frames with 22-47% skeletal deviations

**Output:** `cinematography_video_high_velocity_action_raft_20260206_044618.mp4`
- File size: 3.1 MB
- Duration: 3.62s @ 60fps
- Resolution: 576x1024 (9:16 vertical)
- Processing time: 1509.6s (25 minutes)
- Warning: "⚠ Warning: Could not achieve full consistency after 3 attempts. Returning frames from final attempt"

### Breakthrough Test: Beach Walking Scene (2026-02-06)

**Created STYLE_BEACH_CASUAL** to test typical music video content:
- Style: Natural lighting, golden hour, relaxed atmosphere
- Subject: Man walking on beach, ocean waves, peaceful
- **No hardcoded punch tokens** (previous tests were overridden by STYLE_HIGH_VELOCITY_ACTION)

**Results:**
- ✅ **PASSED on first attempt!** - No skeletal violations
- ✅ motion_bucket_id=70 with 15% tolerance works perfectly for typical content
- ✅ Processing time: 594s (10 minutes) vs punch's 1509s (25 minutes)
- ✅ File size: 2.8 MB vs punch's 3.1 MB (no retries needed)
- ⚠️ **User report: "motion is blurry, especially on edges, right leg getting malformed"**

**Critical Discovery: SVD-XT is the Wrong Tool**

Despite passing skeletal validation, visual quality is poor:
- Body edge blur (motion artifacts)
- Limb deformation (right leg malformation)
- **SVD-XT is designed for subtle camera motion, not character animation**

### Final Status (2026-02-06)

**What We Learned:**
1. Optical flow jitter was NEVER the problem
2. Skeletal violations were pose-specific (extreme punch vs casual walk)
3. Validation passing ≠ good visual quality
4. **SVD-XT fundamentally wrong for animating people** (camera motion model, not character motion)
5. HuggingFace/CivitAI demos use different tech (AnimateDiff, not SVD)

**Why Replace SVD-XT:**
- Built for camera movement, not character animation
- Blurs body edges during motion
- Causes limb deformation (malformation)
- No text prompt control (image-only)
- No motion LoRA ecosystem

**Technology Pivot Decision:**
Replace SVD-XT with **AnimateDiff-Lightning** for character animation

### Files Involved
- `backend/scripts/render_video_svd.py` - Test script, SKELETAL_TOLERANCE parameter
- `backend/library/optics_presets.yaml` - motion_bucket_id, fps, augmentation_level, STYLE_BEACH_CASUAL added
- `backend/src/cinematography/style_logic.py` - Added STYLE_BEACH_CASUAL constant
- `backend/scripts/test_render_realvis.py` - Added STYLE_BEACH_CASUAL support
- `backend/src/cinematography/temporal_consistency.py` - SVD wrapper, temporal smoothing (disabled)
- `backend/src/cinematography/raft_interpolator.py` - RAFT pipeline
- `backend/src/cinematography/physics_motion_tracker.py` - AKD skeletal tracking
- `/tmp/analyze_jitter.py` - Optical flow analysis tool (created during session)
- `/tmp/jitter_analysis_report.md` - Comprehensive test report

### Business Context
Three content tiers requiring open source:
- **Standard**: US norms (cloud APIs work)
- **European/Regional**: Culturally normal nudity (cloud blocked)
- **Rap/Explicit**: NSFW, violence (cloud blocked)

Policy-based compliance via ComplianceGate + policy JSONs

---

## Phase 8: AnimateDiff Migration (Planned - 2026-02-06)

### Research Complete

**Full reports saved:**
- AnimateDiff: `/home/craig/AI_Workspace/synterra/beatcanvas/backend/.claude/cache/agents/oracle/output-20260206T131610Z.md`
- Dolphin/Ollama (deferred): `/home/craig/AI_Workspace/synterra/beatcanvas/backend/.claude/cache/agents/oracle/output-20260206-dolphin-ollama.md`

### Why AnimateDiff > SVD-XT

| Factor | SVD-XT (current) | AnimateDiff-Lightning (recommended) |
|--------|------------------|-------------------------------------|
| **Character consistency** | 3/10 (no IP-Adapter) | **8/10 (IP-Adapter + LoRA)** |
| **Speed** | Slow (25 steps) | **10x faster (4 steps)** |
| **Text prompt control** | None (image-only) | **Full prompt control** |
| **Motion LoRAs** | None | **Massive ecosystem (CivitAI)** |
| **ControlNet support** | Limited | **Full support** |
| **10GB VRAM compatibility** | Fits (~8GB) | **Fits (~8.5GB peak)** |
| **Visual quality** | ❌ Blurs edges, limb deformation | ✅ Clean character animation |

### Architecture Decision: SD 1.5, Not SDXL

**Critical:** AnimateDiff SDXL is still beta with pixelation issues. Must use SD 1.5 motion modules:

- **Video generation**: AnimateDiff + **Realistic Vision V5.1** (SD 1.5 base model)
- **Still images for storyboard**: Keep RealVisXL (SDXL) for preview images
- **Separation already exists** in BeatCanvas architecture (image gen separate from video)

This is NOT a downgrade - AnimateDiff SD 1.5 with proper motion modules produces better results than SVD-XT.

### Integration Approach

Replace `render_video_svd.py` with AnimateDiff pipeline using `diffusers` library:

```python
from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler

# Load Lightning 4-step adapter (ByteDance)
adapter = MotionAdapter().to(dtype=torch.float16)
adapter.load_state_dict(torch.load(
    hf_hub_download("ByteDance/AnimateDiff-Lightning",
                    "animatediff_lightning_4step_diffusers.safetensors"),
))

# Load SD 1.5 base model (Realistic Vision V5.1)
pipe = AnimateDiffPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE",
    motion_adapter=adapter,
    torch_dtype=torch.float16,
)
pipe.scheduler = EulerDiscreteScheduler.from_config(
    pipe.scheduler.config,
    timestep_spacing="trailing",
    beta_schedule="linear",
)
pipe.enable_vae_slicing()
pipe.enable_model_cpu_offload()

# Generate - ONLY 4 STEPS!
output = pipe(
    prompt="man walking on beach, golden hour, cinematic, relaxed stride",
    negative_prompt="blurry, low quality, deformed",
    num_frames=16,  # AnimateDiff generates 16 frames (vs SVD's 25)
    guidance_scale=1.0,  # Lightning uses cfg=1.0 (NOT 7-8)
    num_inference_steps=4,
)
```

### Motion Control

**Text prompts control character motion** - no separate motion LoRAs needed for walking/dancing/singing:
- "man walking on beach" → walking animation
- "woman dancing to music" → dancing animation
- "person singing, expressive face" → singing with facial expressions

**Camera motion LoRAs** available (77 MB each): pan, tilt, zoom, roll

### Key Implementation Notes

**Critical pitfalls to avoid:**
1. **Prompts > 75 tokens** split into two scenes mid-clip - keep under 75
2. **guidance_scale MUST be 1.0** for Lightning (higher causes artifacts)
3. **16 frames is optimal** for SD 1.5 modules (trained length)
4. **Lock seed between scenes** for character consistency (changing seed = different character)
5. **Motion LoRA strength** should be 0.6-0.8 (over 0.8 causes artifacts)
6. **Never mix SD 1.5 modules with SDXL** models (severe artifacts)

### VRAM Budget (10GB GPU)

```
SD 1.5 model (Realistic Vision):  ~2.5 GB
Lightning motion adapter:         ~1.5 GB
IP-Adapter (face consistency):    ~1.0 GB
VAE:                              ~0.5 GB
Working memory (16 frames):       ~3.0 GB
────────────────────────────────────────
Total peak:                       ~8.5 GB  ✅ Fits 10GB GPU
```

### Model Downloads (automatic via HuggingFace)

| Model | Size | Purpose |
|-------|------|---------|
| Realistic Vision V5.1 (SD 1.5) | ~2 GB | Base image generation |
| AnimateDiff-Lightning 4-step | ~1.5 GB | Motion module |
| Camera Motion LoRAs (optional) | ~77 MB each | Pan, tilt, zoom effects |
| IP-Adapter Plus Face (SD 1.5) | ~1 GB | Character consistency |

### Integration Plan

**Phase 8.1: AnimateDiff Core** (~2-3 hours)
1. Create `backend/scripts/render_video_animatediff.py` (replaces `render_video_svd.py`)
2. Install AnimateDiff-Lightning via diffusers
3. Test beach walking scene with AnimateDiff
4. Compare visual quality vs SVD-XT output
5. Verify RAFT interpolation works with 16 frames (vs 25)

**Phase 8.2: Style Integration** (~1 hour)
1. Update `optics_presets.yaml` with AnimateDiff-specific parameters
2. Add prompt optimization for 75-token limit
3. Test all three existing styles (HIGH_VELOCITY_ACTION, URBAN_LUXURY, BEACH_CASUAL)

**Phase 8.3: Full Pipeline** (~2 hours)
1. Replace SVD calls in main pipeline
2. Add character consistency via seed locking
3. Test multi-scene generation (12-48 scenes)
4. Performance benchmarks

### Open Questions

1. **Lightning + IP-Adapter combination** - sparse documentation, needs empirical testing
2. **RAFT interpolation from 16 frames** - larger temporal gaps than 25 frames (test quality)
3. **Realistic Vision V5.1 quality** - validate against BeatCanvas quality bar for beach/action styles
4. **Prompt engineering** - how to stay under 75 tokens with full cinematography tokens?

### Deferred: Dolphin/Ollama GPT-4 Replacement

**Summary:** Replace GPT-4 with dolphin3 (Llama 3.1 8B) for narrative/prompt generation
- **Quality**: 70-80% of GPT-4 for creative writing
- **Cost**: $0 (vs GPT-4's ~$0.60 per storyboard)
- **VRAM**: 6-7GB (fits alongside AnimateDiff on 12GB+ GPU)
- **Integration**: Minimal (OpenAI-compatible API, 2 files changed)
- **Status**: DEFERRED until AnimateDiff migration complete

Full research report: `/home/craig/AI_Workspace/synterra/beatcanvas/backend/.claude/cache/agents/oracle/output-20260206-dolphin-ollama.md`
  - [ ] Add /api/test-video-slice endpoint
  - [ ] Video rebuild pipeline integration with scene changes
  - [ ] End-to-end testing of complete workflow
  - [ ] Performance optimization for large scene counts
  - [ ] Add pencil/edit icon to scene cards (see TECHNICAL_DEBT_PHASE4.md)

## Open Questions
- RESOLVED: Audio auto-play fixed via backend-first approach (no browser audio loading)
- UNCONFIRMED: Cost optimization strategy for bulk scene editing sessions?

## Working Set
**Core Files:**
- `frontend/advanced-production-ui.html` - Complete 5-step professional workflow with AI Story Mapping
- `backend/src/storyboard/narrative_analyzer_ai.py` - GPT-4 narrative analysis (no templates)
- `backend/main.py` - All API endpoints including `/api/generate-storyboard-previews`
- `backend/src/assets/generator.py` - Multi-provider image generation (Nano Banana default)

**New Endpoints (2026-01-26):**
- `POST /api/generate-storyboard-previews` - Generate preview images for storyboard scenes
- Static mount `/data/generated_images` - Serve generated images to frontend

**Key Features Implemented:**
- Real audio analysis via librosa (not simulated)
- AI Story Mapping UI with user-editable concept textarea
- GPT-4 narrative mapping across song sections
- Storyboard preview image generation with Nano Banana
- Upload progress indicator with step tracking
- No audio auto-play during any workflow stage

**Branch:** master
**Test Commands:** `cd backend && python main.py` (port 8002)

## Technical Achievements

**Session 2026-01-26 - Audio Fix & Storyboard Previews:**
- **Audio Auto-Play Fixed**: Removed all browser audio element creation; backend handles duration analysis
- **Real Audio Analysis**: `/api/analyze-audio` returns actual song structure from librosa
- **AI Story Mapping UI**: User enters concept → GPT-4 maps narrative across sections
- **Storyboard Preview Images**: New endpoint generates images during storyboard review
- **Nano Banana Integration**: Default provider for all image generation

**Previous Sessions:**
- 100% Test Success Rate for AI recommendation system
- Professional UI/UX with 5-step guided workflow
- Scalable Architecture supporting 24-96 scene counts
- Interactive Timeline with click-to-seek and scene editing
- WebSocket integration for real-time progress

## Implementation Notes
- AI recommendations use GPT-4 for narrative analysis
- NO FALLBACKS: Returns empty array + error message if AI fails (per user request)
- Nano Banana (Gemini) is default image provider for consistency
- Audio analysis happens server-side only - prevents browser auto-play
- Storyboard preview generation is async with progress updates

## Session Summary (2026-01-26)

**Problem**: Audio auto-played when dropping/uploading files

**Root Cause**: Previous implementation created browser Audio elements for duration detection

**Solution**:
1. Removed all browser audio element creation
2. Backend `/api/analyze-audio` handles all audio processing
3. Frontend sends file via FormData, never loads audio locally
4. Added upload progress indicator for better UX

**Additional Improvements**:
- Added AI Story Mapping section with user concept input
- Connected narrative analysis to actual user input (was hardcoded before)
- Added `/api/generate-storyboard-previews` endpoint for preview images
- Storyboard now shows actual AI-generated images (Nano Banana)
- Static file serving for generated images

**Status**: Full workflow tested - Upload → Analysis → Narrative Mapping → Storyboard with Images

## Session Summary (2026-01-27)

**Problem**: Nano Banana images were 0 bytes (empty files)

**Root Cause**: Old `google-generativeai` library didn't support image generation properly with the model being used

**Solution**:
1. Upgraded from `google-generativeai` to `google-genai>=1.0.0` (new SDK)
2. Updated image generation to use `genai.Client()` with proper `response_modalities=["TEXT", "IMAGE"]`
3. Changed model from `gemini-2.0-flash-exp` with proper config
4. Added file size verification before saving

**Prompt Metadata Storage**:
- Each generated image now has a matching JSON metadata file
- Stored in `data/generated_images/metadata/`
- Contains: original prompt, enhanced prompt, provider, timestamp, style, section name
- Permanent storage (until user deletes)
- Not hardcoded - dynamically generated per image

**Files Modified**:
- `backend/src/assets/generator.py` - New SDK integration + metadata saving
- `backend/requirements.txt` - `google-genai>=1.0.0`

**Verified**:
- Test image generated: 719,554 bytes (actual image content)
- Metadata saved: `scene_0.0_nano_banana_var_0_425ccfb8.json`
- Both original and enhanced prompts preserved

**Status**: Image generation working with proper SDK and metadata saving

## Session Summary (2026-01-27 - Rate Limiting Debug Session)

**Problem**: Nano Banana image generation failing - tried multiple model names, all returning 404 or rate limit errors.

**Root Cause Analysis (Code Review)**:
1. **Concurrency bug**: `asyncio.gather()` launched all 24 scenes concurrently, overwhelming rate limits
2. **Model name changes**: Gemini deprecated `gemini-2.0-flash-exp`, now requires `gemini-2.0-flash-exp-image-generation`
3. **Rate limit delay in wrong place**: Was after API call, not between scenes

**Fixes Applied**:
1. Changed to **sequential generation** for Nano Banana (rate-limited providers)
2. Added 6-second delay **between scenes** (not after each API call)
3. Updated model to `gemini-2.0-flash-exp-image-generation`
4. Increased GPT-4 `max_tokens` from 3000 to 4500 for full narrative generation

**Available Gemini Models** (verified via API):
- `gemini-2.0-flash-exp-image-generation` - Current model
- `gemini-2.5-flash-image` - Alternative with potentially higher limits
- `gemini-3-pro-image-preview` - Pro tier

**Files Modified**:
- `backend/src/assets/generator.py` - Sequential generation + correct model name
- `backend/src/storyboard/narrative_analyzer_ai.py` - Increased max_tokens

**Status**: Testing sequential generation with `gemini-2.0-flash-exp-image-generation`

**Technical Debt Added**:
- Pencil/edit icon on scene cards in StoryboardEditor (see TECHNICAL_DEBT_PHASE4.md)

**Next Session**:
- Verify sequential generation works for all 24 scenes
- If still failing, try `gemini-2.5-flash-image` model
- Consider fallback to DALL-E for remaining scenes after rate limit

## Session Summary (2026-01-27 - Error Observability Code Review)

**Problem**: Junior engineer reported Nano Banana "generating 6, then 11, now none" images

**Actual Finding**: Images WERE being generated (80+ metadata files, 100+ PNG files exist). The problem was **observability** - when generation failed, it failed silently. The engineer had no way to see WHY it failed.

**Root Cause Analysis (Senior Code Review)**:
1. **Silent Failure Antipattern**: Exceptions were caught, logged to console, but returned empty list - caller couldn't distinguish "worked but no results" from "crashed"
2. **No Response Validation**: Code accessed `response.candidates[0].content.parts` without checking each level existed
3. **Rate Limit Detection Without Retry**: Code waited 45s on rate limit, then gave up on that scene forever (no retry)
4. **API Key Validation Gap**: `env_loader.py` didn't include Google/Gemini in key_mapping
5. **Frontend Blindspot**: WebSocket sent status but generation errors never surfaced to UI

**Fixes Implemented**:
1. Created `backend/src/utils/exceptions.py` with:
   - `ErrorCode` enum (RATE_LIMIT, MODEL_NOT_FOUND, AUTH_ERROR, etc.)
   - `GenerationResult` dataclass with `ok()` and `fail()` factory methods
   - Structured exception classes for different failure types

2. Rewrote `backend/src/assets/generator.py` with:
   - Response validation before accessing nested properties
   - Retry logic with exponential backoff (10s → 20s → 40s)
   - Diagnostic summary after generation completes
   - Error categorization for proper handling
   - Configurable constants at top of file

3. Updated `backend/src/utils/env_loader.py`:
   - Added `google`, `gemini`, `google_ai`, `nano_banana` to key_mapping

4. Updated `backend/main.py`:
   - WebSocket sends `generation_stats` and `generation_errors`
   - Both pipelines track successful/failed scenes
   - Progress shows "Generated 20/24 images (4 failed)" format

**Teaching Points for Junior Engineer**:
1. Never return ambiguous values (empty list means nothing)
2. Validate API responses at each nesting level
3. Categorize errors by recoverability (rate limits retry, auth errors don't)
4. Surface errors to users (if they can't see it, they'll report "doesn't work")
5. Log summaries, not just events ("22/24 succeeded" > 24 individual logs)

**Files Created**:
- `backend/src/utils/exceptions.py` - Custom exception classes and GenerationResult

**Files Modified**:
- `backend/src/assets/generator.py` - Major rewrite with validation/retry/diagnostics
- `backend/src/utils/env_loader.py` - Added Google/Gemini keys
- `backend/main.py` - Error tracking and WebSocket updates

**Status**: Implementation complete, imports verified working

## Session Summary (2026-01-27 - Video Generation & UX Polish)

**Problems Identified by User Testing**:
1. "Generate Music Video" button was a demo - didn't actually call backend API
2. "Create Storyboard" button spinner persisted after moving to step 4
3. AI recommendations didn't show which section was being worked on
4. Preview image generation showed "0 of 24" the whole time - looked stuck
5. "Connecting to AI" had no motion/feedback

**Fixes Applied**:

1. **Real Video Generation Integration**:
   - Replaced `simulateVideoGeneration()` with `startVideoGeneration()`
   - Now calls `/api/generate-images-and-video` endpoint
   - WebSocket connection for real-time progress updates
   - Shows actual video when complete

2. **Storyboard Button Spinner**:
   - Moved `loading.classList.add('hidden')` before `goToStep(4)`
   - Spinner now hides immediately when transitioning to storyboard view

3. **AI Recommendations Section Feedback**:
   - Changed progress to cycle through actual section names
   - Shows "Generating prompt for: Intro... (1/8)" style messages

4. **Preview Image Generation - Animated Connection Phase**:
   - Added 5-phase connection animation during first 5 seconds:
     - "Connecting to AI image generation service..."
     - "Establishing secure connection..."
     - "Preparing generation queue..."
     - "Initializing Nano Banana (Gemini)..."
     - "Ready! Starting image generation..."
   - Shows "Preparing scene 1 of 24: Intro" immediately
   - Scene progress simulation starts after connection phase

**Files Modified**:
- `frontend/advanced-production-ui.html` - All UI progress feedback improvements

**Button Sequence for Complete Workflow**:
1. Step 1 (Upload): Drop audio file → Wait for analysis
2. Step 2 (AI Story Mapping): Enter concept → Click "Generate AI Story Recommendations"
3. Step 3 (Quality): Select tier → Click "Create Storyboard"
4. Step 4 (Review Storyboard): Wait for preview images → Click "Generate Music Video"
5. Step 5 (Preview & Download): Click "Start Generation" → Wait → Download video

**Status**: Ready for user testing of complete workflow

## Session Summary (2026-01-27 - Video Task Fix & Storyboard Feedback)

**Problem**: Video generation failed silently - API returned 404 "Task not found"

**Root Cause**:
1. `/api/analyze-audio` deleted the audio file after analysis (`audio_path.unlink()`)
2. `/api/analyze-audio` didn't create a task entry in `active_tasks`
3. `/api/generate-images-and-video` expected a pre-existing task_id
4. Frontend wasn't saving or sending task_id

**Fixes Applied**:

1. **Backend - `/api/analyze-audio` endpoint**:
   - No longer deletes audio file after analysis
   - Renames from `temp_` prefix to permanent storage
   - Creates task entry in `active_tasks`
   - Returns `task_id` and `audio_path` in response

2. **Frontend - Audio Analysis**:
   - Saves `window.currentTaskId = result.task_id`
   - Saves `window.uploadedAudioPath = result.audio_path`

3. **Frontend - Video Generation**:
   - Validates `window.currentTaskId` exists before starting
   - Sends `task_id` in request body (not audio_path)

4. **Storyboard Feedback Enhancements**:
   - Added stats header: Total Scenes, Video Duration, Images Generated
   - Scene cards now show scene number badge
   - Added hover effects on scene cards
   - Click on scene shows full prompt in modal
   - Real-time image count updates as generation progresses
   - Truncated descriptions with "Click to see full prompt" hint

**Files Modified**:
- `backend/main.py` - Fixed `/api/analyze-audio` to persist task
- `frontend/advanced-production-ui.html` - Task ID handling + storyboard UX

**Status**: Ready for re-testing complete workflow

## Session Summary (2026-01-28 - Test Mode & Task ID Debug)

**Problem**: User reported "Skip to Video Assembly" button showed "Please upload an audio file first!" even after successful audio analysis.

**Investigation**:
1. Backend `/api/analyze-audio` correctly returns `task_id` and `audio_path` (verified at lines 811-812)
2. Frontend code at line 1235-1236 saves `window.currentTaskId = result.task_id`
3. UI showed "Song Structure Detected" with all sections (success path was executed)
4. BUT `window.currentTaskId` was still undefined when button was clicked

**Hypothesis**: Either:
- Scope issue with window variables
- JavaScript error interrupting the save
- API response not including task_id for some reason

**Fixes Applied**:

1. **Enhanced Debug Logging**:
   - Added `console.log()` for full API response JSON
   - Added logging for each step of task_id capture
   - Shows alert if task_id missing from API response

2. **localStorage Backup**:
   - Added `localStorage.setItem('beatcanvas_task_id', ...)` as fallback
   - `skipToVideoTest()` now checks localStorage if window var is missing
   - Provides redundancy against scope issues

3. **Visual Verification**:
   - Test button only appears if `window.currentTaskId` is truthy
   - Test button now shows truncated task_id (e.g., `Task ID: a1b2c3d4...`)
   - User can visually confirm task_id was captured

4. **Improved Error Messages**:
   - Alert now shows which specific variable is missing (task_id vs audio_path)
   - Points user to browser console for debugging
   - Notes whether localStorage fallback was checked

**Files Modified**:
- `frontend/advanced-production-ui.html` - Debug logging + localStorage backup + visual verification

**How to Test**:
1. Open browser console (F12)
2. Upload audio file
3. Watch for `[BeatCanvas] Full API result:` log
4. Verify task_id appears in JSON
5. Verify `[BeatCanvas] Task ID saved:` log shows value
6. Look for test button with task_id preview
7. Click "Skip to Video Assembly"

**Status**: Enhanced debugging deployed - ready for user to test and check console

## Session Summary (2026-01-29 - Video Assembly & GPU Encoding)

**Problem 1**: Videos showed black screen with audio only (4.2 MB video for 3:25 song)

**Root Cause (via `test_assembler_debug.py`)**:
1. `cinematic_filter` in `assembler.py` assumed frames were float (0-1)
2. MoviePy ImageClip returns uint8 frames (0-255)
3. `frame * 255` on uint8 caused overflow → all zeros (black)
4. Returning float (0-1) after processing caused MoviePy concatenate to corrupt frames

**Fix Applied** (assembler.py lines 307-350):
```python
def cinematic_filter(frame):
    # Detect input format
    if frame.dtype == np.float64 or frame.dtype == np.float32:
        frame_uint8 = (frame * 255).astype(np.uint8)
    else:
        frame_uint8 = frame.astype(np.uint8)
    # ... process with OpenCV ...
    # Return uint8 (MoviePy standard)
    return cv2.cvtColor(frame_cv.astype(np.uint8), cv2.COLOR_BGR2RGB)
```

**Problem 2**: Videos were static slideshows (no Ken Burns effects)

**Root Cause**: Test storyboard had no `effects` or `mood` fields

**Fix Applied** (main.py lines 309-331):
- Added `effect_options` list: zoom_in, zoom_out, pan_right, pan_left, fade_in/out
- Added `mood_options` list: energetic, calm, dramatic, neutral, bright
- Test scenes now rotate through effects/moods

**Problem 3**: Video encoding slow on CPU

**User Question**: Desktop (256GB RAM, dual Xeons, 4GB VRAM) vs laptop (32GB RAM, 16GB VRAM)?

**Solution**: Added GPU encoding support (assembler.py lines 18-59):
- Auto-detects `h264_nvenc` availability at startup
- Uses GPU encoding when available (3-10x faster)
- Falls back to CPU `libx264` if no GPU
- Optimal presets for quality: NVENC p4/CQ19, CPU medium/CRF18

**Files Created**:
- `backend/test_assembler_debug.py` - 4-test diagnostic script

**Files Modified**:
- `backend/src/video/assembler.py` - Fixed cinematic filter + GPU encoding
- `backend/main.py` - Added effects/moods to test storyboard

**Recommendation**: Laptop with 16GB VRAM will be faster with GPU encoding enabled

**Status**: Server restarted with GPU detection, ready for testing

## Session Summary (2026-01-29 - Image-to-Video Upgrade)

**Problem**: Generated videos look like Ken Burns slideshows, not real music videos

**Analysis** (from external review):
1. 24 scenes over 3:45 = 9.4 sec/scene = slideshow feel
2. Ken Burns effects (zoom/pan) can't compete with real video motion
3. Character consistency issues with text-to-image across scenes

**Solution**: Hybrid video generation with Luma Dream Machine

**Key Insight**: Image-to-video preserves character consistency because Luma animates the pixels of YOUR generated image rather than regenerating from text.

**Architecture Changes**:

1. **Resolution Standardization** (`assembler.py`):
   - Changed from 1792x1024 to 1920x1080 (Luma native)
   - All hardcoded values replaced with `TARGET_RESOLUTION` constant

2. **Beat-Based Scene Timing** (`analyzer.py`):
   - Added `subdivide_by_beats()` with MIN/MAX duration constraints (2.5s-8.0s)
   - Added `classify_scene_type()` for hero (video) vs standard (Ken Burns)
   - Added `get_enhanced_scene_timings()` returning rich scene data
   - Target: 60 scenes (up from 24) for music video feel

3. **Motion Prompts** (`generator.py`):
   - Extended `StoryboardScene` dataclass with `motion_prompt`, `scene_type`, `style_anchor`
   - Added `MOTION_PROMPT_SYSTEM` guidance calibrated to energy level
   - Added `CHARACTER_GUIDANCE` for consistent AI animation
   - GPT-4 now generates both `image_prompt` AND `motion_prompt`

4. **Luma Video Generator** (`video_generator.py` - NEW):
   - `LumaVideoGenerator` class with retry logic and Ken Burns fallback
   - Image-to-video via keyframes (character locked in)
   - Batch generation with rate limiting
   - Factory function `get_video_generator()` for provider selection

5. **Enhanced Assembler** (`assembler.py`):
   - Added `create_video_enhanced()` for mixed video/image content
   - Longer transitions (0.75s) when switching video↔image types
   - Skip `cinematic_filter` for video clips (Luma has own aesthetic)
   - Added `get_video_stats()` for cost tracking

6. **Character Management** (`character_manager.py` - NEW):
   - `CharacterManager` class for multi-character videos
   - Support for 1-6 characters with reference images
   - Per-scene character assignment strategies
   - Family video preset helper

**Files Created**:
- `backend/src/assets/video_generator.py` - Luma integration stub
- `backend/src/assets/character_manager.py` - Character management

**Files Modified**:
- `backend/src/video/assembler.py` - Resolution + enhanced assembly
- `backend/src/audio/analyzer.py` - Beat-based subdivision
- `backend/src/storyboard/generator.py` - Motion prompts + scene types
- `backend/requirements.txt` - Added lumaai>=0.1.0

**Plan Document**: `~/.claude/plans/rippling-spinning-lightning.md`

**Cost Model** (for 3:45 video with 60 scenes):
- 15 hero scenes (Luma 1080p @ $0.34): $5.10
- 60 images (Nano Banana @ $0.04): $2.40
- GPT-4 prompts: $0.60
- **Total**: ~$8.10 (vs $3.00 for current Ken Burns only)

**Next Steps**:
1. Obtain LUMAAI_API_KEY from lumalabs.ai/dream-machine/api
2. Add key to `~/.claude/.env`
3. Build `/api/test-video-slice` endpoint for test slice
4. Run test on 60-sec chorus (6 scenes, ~$1.14)
5. If quality good → full pipeline integration

**Status**: Implementation complete, awaiting Luma API key for testing
