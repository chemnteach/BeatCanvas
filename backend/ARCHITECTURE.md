# Architecture Document

## BeatCanvas Cinematography Engine

**Version**: 2.0 (AKD Pivot)
**Last Updated**: 2026-02-04

---

## 1. System Overview

BeatCanvas implements a multi-stage video generation pipeline that transforms user prompts into photorealistic, temporally consistent 60fps videos. The architecture emphasizes:

- **Separation of Concerns** - Pure functions for testability, facades for orchestration
- **Physics-Based Validation** - AKD skeletal tracking prevents anatomical artifacts
- **Memory Efficiency** - Strict VRAM lifecycle management for 12GB GPUs

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                │
│                    (CLI: render_video_svd.py)                             │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Cinematography Engine                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ OpticsCatalog│  │ StyleLogic   │  │PromptComposer│  │   Engine     │  │
│  │   (YAML)     │  │ (Detection)  │  │(Pure Funcs)  │  │  (Facade)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Image Generation Layer                             │
│  ┌──────────────────────┐              ┌──────────────────────┐           │
│  │  LocalImageGenerator │              │    VRAMManager       │           │
│  │  (RealVisXL/SDXL)    │◄────────────►│  (Memory Lifecycle)  │           │
│  └──────────────────────┘              └──────────────────────┘           │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Video Generation Layer                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    TemporalConsistencySVD                            │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │ │
│  │  │ SVD-XT Pipeline│  │ Structural     │  │ SkeletalConsistency    │ │ │
│  │  │ (25 frames)    │  │ Checker        │  │ Checker (AKD)          │ │ │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Interpolation Layer                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                       RAFTInterpolator                               │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │ │
│  │  │ Optical Flow   │  │ Occlusion      │  │ Edge Damping           │ │ │
│  │  │ (Bidirectional)│  │ Detection      │  │ (Boundary Protection)  │ │ │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              Output Layer                                  │
│                     MP4 Export (60fps, H.264)                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Cinematography Engine (`src/cinematography/`)

#### Purpose
Transforms user prompts into CLIP-optimized generation parameters with camera, film stock, and lighting tokens.

#### Components

```
cinematography/
├── __init__.py              # Public API exports
├── engine.py                # Orchestration facade
├── prompt_composer.py       # Pure functions (100% testable)
├── style_logic.py           # Style detection and application
├── optics.py                # YAML catalog loader
├── temporal_consistency.py  # SVD wrapper with validation
├── raft_interpolator.py     # Optical flow upsampling
└── physics_motion_tracker.py # AKD skeletal tracking
```

#### Class Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CinematographyEngine                             │
├─────────────────────────────────────────────────────────────────────────┤
│ - optics_catalog: OpticsCatalog                                        │
│ - default_style: str                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ + compose(subject, style?, camera?, film?, lighting?) → ComposedPrompt │
│ + get_generation_config(style) → Dict                                  │
│ + get_negative_prompt(style) → str                                     │
│ + get_adetailer_config() → Dict                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│   OpticsCatalog     │ │   StyleLogic    │ │    PromptComposer       │
├─────────────────────┤ ├─────────────────┤ ├─────────────────────────┤
│ + cameras: Dict     │ │ + STYLES: Dict  │ │ + compose_prompt()      │
│ + film_stocks: Dict │ │ + detect_style()│ │ + merge_negative()      │
│ + lighting: Dict    │ │ + get_optics()  │ │ + build_adetailer()     │
│ + motion: Dict      │ │ + get_inject()  │ │                         │
└─────────────────────┘ └─────────────────┘ └─────────────────────────┘
```

#### Data Flow

```python
# Input
user_prompt = "muscular man throwing a punch"
style = "STYLE_HIGH_VELOCITY_ACTION"

# CinematographyEngine.compose()
1. detect_style(prompt) → STYLE_HIGH_VELOCITY_ACTION (if not provided)
2. get_style_optics(style) → OpticsProfile(camera, film, lighting, motion)
3. optics_catalog.get_tokens(camera) → "shot on RED camera, 8K resolution..."
4. compose_prompt(subject, tokens...) → ComposedPrompt

# Output
ComposedPrompt(
    full_prompt="score_9, score_8_up, muscular man throwing a punch, detailed skin, shot on RED camera...",
    subject="muscular man throwing a punch",
    camera_tokens="shot on RED camera, 8K resolution, digital cinema quality",
    film_tokens="Kodak Portra 160, natural skin tones...",
    lighting_tokens="hard light:1.4, sharp shadows...",
    quality_tokens="detailed skin, realistic skin texture"
)
```

### 2.2 Temporal Consistency (`temporal_consistency.py`)

#### Purpose
Wraps SVD-XT pipeline with dual-layer validation (structural + skeletal) and adaptive retry logic.

#### Class Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      TemporalConsistencySVD                             │
├─────────────────────────────────────────────────────────────────────────┤
│ - pipe: StableVideoDiffusionPipeline                                   │
│ - consistency_threshold: float = 0.18                                  │
│ - skeletal_tolerance: float = 0.08                                     │
│ - skeletal_checker: SkeletalConsistencyChecker                         │
├─────────────────────────────────────────────────────────────────────────┤
│ + generate_with_consistency(anchor, motion_bucket_id, fps, ...) → List │
│ + extract_structural_features(image) → np.ndarray                      │
│ + compute_structural_consistency(f1, f2) → float                       │
│ - _adaptive_rollback(violations) → float                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ uses
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SkeletalConsistencyChecker                           │
├─────────────────────────────────────────────────────────────────────────┤
│ - pose_estimator: LightweightPoseEstimator                             │
│ - tolerance: float = 0.08                                              │
│ - anchor_bones: Dict[str, float]                                       │
│ - anchor_keypoints: np.ndarray                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ + set_anchor(image) → bool                                             │
│ + check_frame(frame) → Tuple[bool, Dict[str, float]]                   │
│ + check_sequence(frames) → Dict[int, Dict]                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ uses
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LightweightPoseEstimator                             │
├─────────────────────────────────────────────────────────────────────────┤
│ - mp_pose: mediapipe.python.solutions.pose                             │
│ - pose: Pose                                                           │
│ - available: bool                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ + detect_keypoints(image) → np.ndarray (17, 3)                         │
│ + extract_arm_bones(keypoints) → Dict[str, float]                      │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Validation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Consistency Validation Flow                         │
└─────────────────────────────────────────────────────────────────────────┘

                              SVD-XT Output
                                   │
                                   ▼
                         ┌─────────────────┐
                         │  For each frame │
                         └────────┬────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     │
    ┌───────────────┐     ┌───────────────┐            │
    │  Structural   │     │   Skeletal    │            │
    │   Check       │     │    Check      │            │
    │ (Canny edges) │     │  (AKD bones)  │            │
    └───────┬───────┘     └───────┬───────┘            │
            │                     │                     │
            ▼                     ▼                     │
    ┌───────────────┐     ┌───────────────┐            │
    │ deviation >   │     │ deviation >   │            │
    │   0.18?       │     │   0.08?       │            │
    └───────┬───────┘     └───────┬───────┘            │
            │                     │                     │
       YES  │                YES  │                     │
            ▼                     ▼                     │
    ┌───────────────┐     ┌───────────────┐            │
    │ Add to        │     │ Add to        │            │
    │ structural    │     │ skeletal      │            │
    │ violations    │     │ violations    │            │
    └───────────────┘     └───────────────┘            │
                                  │                     │
                                  └─────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  Any violations?        │
                              └────────────┬────────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │ NO               │ YES              │
                        ▼                  ▼                  │
                ┌───────────────┐  ┌───────────────────────┐  │
                │ Return frames │  │ Retry < max_retries?  │  │
                │ (success)     │  └───────────┬───────────┘  │
                └───────────────┘              │              │
                                    ┌─────────┴─────────┐    │
                                    │ YES               │ NO │
                                    ▼                   ▼    │
                            ┌───────────────┐   ┌───────────┐│
                            │ Rollback      │   │ Return    ││
                            │ noise_aug     │   │ best      ││
                            │ (0.01 skel,   │   │ attempt   ││
                            │  0.02 struct) │   │ (warning) ││
                            └───────┬───────┘   └───────────┘│
                                    │                        │
                                    └────────────────────────┘
                                              │
                                              ▼
                                        Regenerate
```

### 2.3 Physics Motion Tracker (`physics_motion_tracker.py`)

#### Purpose
Implements AKD (Articulated Kinematics Distillation) for physics-based skeletal tracking.

#### Skeletal Model

```
                    COCO 17-Keypoint Skeleton

                         0 (nose)
                        /   \
                    1,2     3,4    (eyes, ears)
                       \   /
                        \ /
                    5 ─────── 6    (shoulders)
                    │         │
                    7         8    (elbows)
                    │         │
                    9        10    (wrists)

                   11 ─────── 12   (hips)
                    │         │
                   13        14    (knees)
                    │         │
                   15        16    (ankles)

    ARM BONES (Critical for punch tracking):
    ├── Left:  5→7 (upper_arm), 7→9 (forearm)
    └── Right: 6→8 (upper_arm), 8→10 (forearm)
```

#### Bone Length Constraints

```python
# Relative to body height (1.7m default)
BONE_LENGTH_RATIOS = {
    'upper_arm': 0.186,      # ~31.6cm
    'forearm': 0.146,        # ~24.8cm
    'thigh': 0.245,          # ~41.7cm
    'shin': 0.246,           # ~41.8cm
    'torso': 0.288,          # ~49.0cm
    'shoulder_width': 0.259  # ~44.0cm
}

# Tolerance: 8% deviation allowed
# Example: upper_arm 31.6cm ± 2.5cm
```

### 2.4 RAFT Interpolator (`raft_interpolator.py`)

#### Purpose
Deep learning optical flow interpolation to upsample 25 SVD frames to 240 frames (60fps).

#### Algorithm

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAFT Interpolation Algorithm                         │
└─────────────────────────────────────────────────────────────────────────┘

Input: frame1, frame2 (consecutive SVD frames)
Output: 9 intermediate frames

1. COMPUTE BIDIRECTIONAL FLOW
   ┌─────────┐           ┌─────────┐
   │ frame1  │──flow_fwd─▶│ frame2  │
   │         │◀─flow_bwd──│         │
   └─────────┘           └─────────┘

   flow_fwd = RAFT(frame1, frame2, iters=32)
   flow_bwd = RAFT(frame2, frame1, iters=32)

2. DETECT OCCLUSIONS
   consistency = warp(flow_fwd, flow_bwd) + flow_fwd
   occlusion_mask = |consistency| > threshold

3. APPLY EDGE DAMPING (20px boundary)
   ┌────────────────────────────┐
   │░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
   │░┌──────────────────────┐░░░│
   │░│                      │░░░│  ░ = damped region
   │░│    Active Region     │░░░│
   │░│                      │░░░│
   │░└──────────────────────┘░░░│
   │░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
   └────────────────────────────┘

4. GENERATE INTERMEDIATE FRAMES
   For i in 1..9:
       t = i / 10  # interpolation coefficient

       flow_fwd_scaled = flow_fwd * t
       flow_bwd_scaled = flow_bwd * (1 - t)

       warped1 = warp(frame1, flow_fwd_scaled)
       warped2 = warp(frame2, flow_bwd_scaled)

       # Blend with occlusion awareness
       intermediate[i] = blend(warped1, warped2, occlusion_mask, t)

Output: [inter_1, inter_2, ..., inter_9]
```

#### Frame Math

```
Input:  25 SVD frames @ 8fps = 3.125s base
Target: 4.0s @ 60fps = 240 frames

Gaps between frames: 25 - 1 = 24
Required intermediate frames per gap: (240 - 25) / 24 = 8.96 ≈ 9

Output: 25 + (24 × 9) = 25 + 216 = 241 frames ≈ 4.02s @ 60fps
```

---

## 3. Data Architecture

### 3.1 Configuration Schema

#### optics_presets.yaml

```yaml
# Camera definitions
cameras:
  ARRI_ALEXA_65:
    prompt_tokens: "shot on ARRI ALEXA 65, large format sensor, cinematic depth of field"
  RED_DIGITAL_CINEMA:
    prompt_tokens: "shot on RED camera, 8K resolution, digital cinema quality"
  BOLEX_H16:
    prompt_tokens: "shot on Bolex H16, 16mm film aesthetic, handheld texture"

# Film stock definitions
film_stocks:
  CINESTILL_800T:
    prompt_tokens: "Cinestill 800T film stock, (red halation:1.2), tungsten balanced"
  KODAK_PORTRA_160:
    prompt_tokens: "Kodak Portra 160, natural skin tones, soft pastel colors"
  KODAK_VISION3_500T:
    prompt_tokens: "Kodak Vision3 500T, motion picture film, cinema color grading"

# Lighting definitions
lighting:
  CHIAROSCURO:
    prompt_tokens: "chiaroscuro lighting, dramatic contrast, deep shadows"
  HARD_LIGHT:
    prompt_tokens: "(hard light:1.4), sharp shadows, high contrast"
  NEON_NOIR:
    prompt_tokens: "neon lighting, cyberpunk atmosphere, colorful reflections"

# Production styles (combine camera + film + lighting + motion params)
production_styles:
  STYLE_HIGH_VELOCITY_ACTION:
    camera: "RED_DIGITAL_CINEMA"
    film: "KODAK_PORTRA_160"
    lighting: "HARD_LIGHT"
    motion: "HIGH_SPEED_STATIC"
    motion_bucket_id: 110
    fps: 8
    augmentation_level: 0.12
```

### 3.2 Data Classes

```python
@dataclass(frozen=True)
class OpticsProfile:
    """Immutable optics configuration"""
    camera: Optional[str] = None
    film_stock: Optional[str] = None
    lighting: Optional[str] = None
    motion: Optional[str] = None

@dataclass(frozen=True)
class ComposedPrompt:
    """Output of prompt composition"""
    full_prompt: str
    subject: str
    style_prefix: str
    camera_tokens: str
    film_tokens: str
    lighting_tokens: str
    motion_tokens: str
    quality_tokens: str
    negative_prompt: str

@dataclass
class Joint:
    """Single joint in kinematic chain"""
    name: str
    id: int
    parent_id: Optional[int]
    position: np.ndarray  # (3,) - x, y, z
    rotation: np.ndarray  # (4,) - quaternion
    dof: int              # Degrees of freedom
    angle_limits: Optional[Tuple[float, float]]
```

---

## 4. Memory Architecture

### 4.1 VRAM Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VRAM Lifecycle Management                        │
└─────────────────────────────────────────────────────────────────────────┘

Timeline:
─────────────────────────────────────────────────────────────────────────▶

Phase 1: Image Generation
┌────────────────┐
│ RealVisXL      │  ~6GB VRAM
│ (SDXL model)   │
└───────┬────────┘
        │
        ▼
    VRAMManager.kill()  ← Force unload, GC, cache clear
        │
        ▼
    Baseline: <1GB VRAM
        │
Phase 2: Video Generation
        │
        ▼
┌────────────────┐
│ SVD-XT         │  ~8GB VRAM
│ (Video model)  │
└───────┬────────┘
        │
        ▼
    VRAMManager.kill()
        │
        ▼
    Baseline: <1GB VRAM
        │
Phase 3: Interpolation
        │
        ▼
┌────────────────┐
│ RAFT           │  ~4GB VRAM
│ (Flow model)   │
└───────┬────────┘
        │
        ▼
    Final cleanup
        │
        ▼
    Output: MP4 file
```

### 4.2 VRAMManager API

```python
class VRAMManager:
    @staticmethod
    def kill():
        """Force VRAM to <1GB baseline"""
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

        # Verify baseline
        current = torch.cuda.memory_allocated() / 1e9
        if current > 1.0:
            raise MemoryError(f"VRAM baseline exceeded: {current:.2f}GB")

    @staticmethod
    def get_usage() -> float:
        """Get current VRAM usage in GB"""
        return torch.cuda.memory_allocated() / 1e9
```

---

## 5. Error Handling

### 5.1 Graceful Degradation

| Component | Failure Mode | Degradation |
|-----------|--------------|-------------|
| MediaPipe | ImportError | Skeletal checks disabled, structural-only |
| RAFT | CUDA OOM | Reduce batch size, retry |
| SVD | Consistency failure | Rollback noise_aug, max 3 retries |
| OpticsCatalog | YAML parse error | Use hardcoded defaults |

### 5.2 Error Codes

```python
class CinematographyError(Exception):
    """Base exception for cinematography module"""
    pass

class SkeletalViolationError(CinematographyError):
    """Raised when bone length deviation exceeds tolerance"""
    def __init__(self, frame_idx: int, deviations: Dict[str, float]):
        self.frame_idx = frame_idx
        self.deviations = deviations
        max_dev = max(deviations.values())
        super().__init__(f"Frame {frame_idx}: {max_dev:.1%} bone deviation")

class VRAMExhaustedError(CinematographyError):
    """Raised when VRAM cannot be freed to baseline"""
    pass
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
                    ┌───────────────┐
                    │    E2E Test   │  1 test
                    │ (Full render) │
                    └───────────────┘
                   /                 \
          ┌───────────────┐   ┌───────────────┐
          │  Integration  │   │  Integration  │  5 tests
          │  (Pipeline)   │   │  (VRAM)       │
          └───────────────┘   └───────────────┘
         /                                     \
    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
    │   Unit    │ │   Unit    │ │   Unit    │ │   Unit    │  20+ tests
    │ (Composer)│ │ (Style)   │ │ (Optics)  │ │ (Skeletal)│
    └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

### 6.2 Test Examples

```python
# Unit test: Pure function (prompt_composer.py)
def test_compose_prompt_includes_detailed_skin():
    result = compose_prompt(subject="woman portrait")
    assert "detailed skin" in result.full_prompt

# Unit test: Style detection (style_logic.py)
def test_detects_action_style():
    style = detect_style("man throwing a punch")
    assert style == STYLE_HIGH_VELOCITY_ACTION

# Integration test: Skeletal checker
def test_skeletal_checker_detects_deviation():
    checker = SkeletalConsistencyChecker(tolerance=0.08)
    checker.set_anchor(anchor_image)
    passed, deviations = checker.check_frame(distorted_frame)
    assert not passed
    assert deviations['left_upper_arm'] > 0.08

# E2E test: Full render
def test_full_render_produces_valid_mp4():
    output = render_video(
        prompt="man throwing punch",
        style="STYLE_HIGH_VELOCITY_ACTION",
        duration=4.0
    )
    assert output.exists()
    assert get_video_duration(output) == pytest.approx(4.0, rel=0.05)
```

---

## 7. Deployment

### 7.1 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 4080 (12GB) | RTX 5070 Ti (16GB) |
| CUDA | 12.1 | 12.8 |
| PyTorch | 2.1.0 | 2.11.0 (nightly) |
| RAM | 16GB | 32GB |
| Storage | 50GB | 100GB |

### 7.2 Environment Variables

```bash
# Required
CUDA_VISIBLE_DEVICES=0

# Optional
BEATCANVAS_OUTPUT_DIR=/path/to/output
BEATCANVAS_MODEL_CACHE=/path/to/models
BEATCANVAS_LOG_LEVEL=INFO
```

### 7.3 Model Checkpoints

```
~/.cache/huggingface/hub/
├── stabilityai--stable-video-diffusion-img2vid-xt/  # SVD-XT
├── SG161222--RealVisXL_V5.0/                        # Image generation
└── models--raft-large/                              # RAFT optical flow
```

---

## 8. Future Considerations

### 8.1 Planned Enhancements

1. **Multi-GPU Support** - Distribute SVD and RAFT across GPUs
2. **Batch Processing** - Queue multiple renders
3. **Audio Sync** - Beat detection for scene cuts
4. **LoRA Integration** - Custom style fine-tuning

### 8.2 Technical Debt

| Item | Priority | Effort |
|------|----------|--------|
| Add comprehensive logging | P1 | Low |
| Implement progress callbacks | P1 | Medium |
| Add model versioning | P2 | Low |
| Create Docker container | P2 | Medium |

---

## Appendix A: API Reference

### CinematographyEngine

```python
class CinematographyEngine:
    def __init__(
        self,
        optics_catalog: Optional[OpticsCatalog] = None,
        custom_styles: Optional[Dict] = None
    ) -> None: ...

    def compose(
        self,
        subject: str,
        style: Optional[str] = None,
        camera: Optional[str] = None,
        film: Optional[str] = None,
        lighting: Optional[str] = None,
        motion: Optional[str] = None
    ) -> ComposedPrompt: ...

    def get_generation_config(self, style: str) -> Dict: ...
    def get_negative_prompt(self, style: str) -> str: ...
    def get_adetailer_config(self) -> Dict: ...
```

### TemporalConsistencySVD

```python
class TemporalConsistencySVD:
    def __init__(
        self,
        svd_pipeline: StableVideoDiffusionPipeline,
        consistency_threshold: float = 0.18,
        skeletal_tolerance: float = 0.08
    ) -> None: ...

    def generate_with_consistency(
        self,
        anchor_image: PIL.Image,
        num_frames: int = 25,
        motion_bucket_id: int = 110,
        fps: int = 8,
        noise_aug_strength: float = 0.12,
        max_retries: int = 3,
        height: int = 1024,
        width: int = 576
    ) -> List[np.ndarray]: ...
```

### RAFTInterpolator

```python
class RAFTInterpolator:
    def __init__(
        self,
        model_size: str = 'large',
        device: str = 'cuda'
    ) -> None: ...

    def interpolate_frames(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray,
        num_intermediate: int = 9,
        occlusion_aware: bool = True,
        edge_damping: bool = True
    ) -> List[np.ndarray]: ...

    def compute_flow(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray,
        iters: int = 32
    ) -> np.ndarray: ...
```
