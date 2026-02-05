# BeatCanvas Backend

**AI-Powered Video Generation Pipeline with Physics-Based Motion Tracking**

BeatCanvas transforms static images into high-fidelity 60fps videos using Stable Video Diffusion (SVD-XT), RAFT optical flow interpolation, and Articulated Kinematics Distillation (AKD) for anatomically correct motion.

## Features

- **Photorealistic Cinematography Engine** - CLIP-optimized prompt composition with camera, film stock, and lighting presets
- **Physics-Based Motion Tracking (AKD)** - Prevents anatomical distortion during high-velocity motion sequences
- **Temporal Consistency Validation** - Dual-layer checking (structural + skeletal) with adaptive rollback
- **RAFT Optical Flow Interpolation** - Deep learning upsampling from 25fps to 60fps
- **VRAM Management** - Strict memory lifecycle with <1GB baseline enforcement

## Quick Start

### Prerequisites

- Python 3.10+
- CUDA 12.8+ (RTX 30/40/50 series)
- 12GB+ VRAM (RTX 4080/5070 Ti recommended)
- PyTorch 2.11.0+ with CUDA support

### Installation

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install MediaPipe for skeletal tracking
pip install mediapipe

# For RTX 50 series (Blackwell), install PyTorch nightly
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
```

### Generate a Video

```bash
# Basic render with default style
python scripts/render_video_svd.py

# With custom image and style
python scripts/render_video_svd.py \
  --image /path/to/image.png \
  --style STYLE_HIGH_VELOCITY_ACTION \
  --duration 4.0
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BeatCanvas Render Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Prompt ──► CinematographyEngine ──► RealVisXL ──► Anchor Image       │
│                        │                                    │               │
│                        ▼                                    ▼               │
│              ┌─────────────────┐                  ┌─────────────────┐       │
│              │ OpticsCatalog   │                  │ VRAMManager     │       │
│              │ - Cameras       │                  │ - kill()        │       │
│              │ - Film Stocks   │                  │ - <1GB baseline │       │
│              │ - Lighting      │                  └────────┬────────┘       │
│              └─────────────────┘                           │               │
│                                                            ▼               │
│                                                  ┌─────────────────┐       │
│                                                  │ SVD-XT Pipeline │       │
│                                                  │ 25 frames @ 8fps│       │
│                                                  └────────┬────────┘       │
│                                                           │               │
│  ┌────────────────────────────────────────────────────────┼───────────────┐│
│  │                  Temporal Consistency Wrapper          │               ││
│  │  ┌─────────────────┐              ┌─────────────────┐  │               ││
│  │  │ Structural Check│              │ Skeletal Check  │◄─┘               ││
│  │  │ (Canny Edges)   │              │ (AKD Physics)   │                  ││
│  │  └────────┬────────┘              └────────┬────────┘                  ││
│  │           │          Violations?           │                           ││
│  │           └──────────────┬─────────────────┘                           ││
│  │                          ▼                                             ││
│  │                 noise_aug rollback (0.01)                              ││
│  │                 max 3 retries                                          ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                    │                                       │
│                                    ▼                                       │
│                          ┌─────────────────┐                               │
│                          │ RAFT Interpolator│                              │
│                          │ 32 iterations    │                              │
│                          │ 9 intermediate   │                              │
│                          │ frames/pair      │                              │
│                          └────────┬────────┘                               │
│                                   │                                        │
│                                   ▼                                        │
│                          ┌─────────────────┐                               │
│                          │ Output: 60fps   │                               │
│                          │ 240 frames      │                               │
│                          │ 4.0s duration   │                               │
│                          └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Configuration

### Production Styles

Defined in `library/optics_presets.yaml`:

| Style | Camera | Film Stock | Lighting | Use Case |
|-------|--------|------------|----------|----------|
| `STYLE_HIGH_VELOCITY_ACTION` | RED Digital Cinema | Kodak Portra 160 | Hard Light | Fight scenes, sports |
| `STYLE_URBAN_LUXURY` | ARRI ALEXA 65 | Kodak Vision3 500T | Neon Noir | Fashion, nightlife |
| `STYLE_PHYSICAL_DRAMA` | Sony Venice | Cinestill 800T | Chiaroscuro | Emotional portraits |

### Motion Parameters

```yaml
STYLE_HIGH_VELOCITY_ACTION:
  motion_bucket_id: 110   # SVD motion intensity (0-127)
  fps: 8                  # Internal FPS (affects temporal gap)
  augmentation_level: 0.12 # Noise divergence from anchor
```

### Skeletal Tolerance

```python
SKELETAL_TOLERANCE = 0.08  # 8% max bone length deviation
```

## Directory Structure

```
backend/
├── scripts/
│   └── render_video_svd.py      # Main render entry point
│
├── library/
│   └── optics_presets.yaml      # Cinematography presets
│
├── config/
│   ├── checkpoints.yaml         # Model standards (VRAM budgets)
│   └── settings.yaml            # Global paths and defaults
│
├── src/
│   ├── cinematography/          # Core render module
│   │   ├── engine.py            # Orchestration facade
│   │   ├── prompt_composer.py   # CLIP-optimized prompts
│   │   ├── style_logic.py       # Style detection/application
│   │   ├── optics.py            # YAML catalog loader
│   │   ├── temporal_consistency.py  # SVD wrapper + AKD
│   │   ├── raft_interpolator.py     # Optical flow upsampling
│   │   └── physics_motion_tracker.py # AKD skeletal tracking
│   │
│   ├── local/
│   │   ├── image_generator.py   # Diffusion model interface
│   │   ├── video_generator.py   # Legacy Wan 2.1 generator
│   │   └── vram_manager.py      # GPU memory lifecycle
│   │
│   └── assets/
│       └── generator.py         # Cloud API integration
│
└── tests/
    ├── test_prompt_composer.py
    ├── test_style_logic.py
    └── test_cinematography_engine.py
```

## Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Image Generation | RealVisXL V5.0 / SDXL | Photorealistic anchor images |
| Video Generation | SVD-XT (Stability AI) | 25-frame base video |
| Optical Flow | RAFT (torchvision) | Deep learning interpolation |
| Pose Estimation | MediaPipe | Skeletal keypoint detection |
| Physics Tracking | AKD (CVPR 2025) | Anatomical consistency |

## Testing

```bash
# Unit tests
pytest tests/test_prompt_composer.py -v
pytest tests/test_style_logic.py -v

# Integration test
pytest tests/test_cinematography_engine.py -v

# E2E render test
python scripts/render_video_svd.py --dry-run
```

## Troubleshooting

### MediaPipe Import Error

```
AttributeError: module 'mediapipe' has no attribute 'solutions'
```

**Solution**: The code uses explicit submodule imports:
```python
import mediapipe.python.solutions.pose as mp_pose
```

### VRAM Out of Memory

**Solution**: Ensure VRAMManager kills previous models:
```python
from src.local.vram_manager import VRAMManager
VRAMManager.kill()  # Force <1GB baseline
```

### Jittery Output

**Causes**:
- Wrong `num_intermediate` calculation (video stretched/compressed)
- Skeletal tolerance too loose (anatomical jumps)

**Solution**: Verify math:
```
25 frames @ 8fps = 3.125s base
Target: 4.0s @ 60fps = 240 frames
Intermediate per pair: (240 - 25) / 24 = 9
```

## References

- [Stable Video Diffusion](https://stability.ai/stable-video) - Base video generation
- [RAFT: Recurrent All-Pairs Field Transforms](https://arxiv.org/abs/2003.12039) - Optical flow
- [Articulated Kinematics Distillation](https://arxiv.org/abs/2501.xxxxx) - CVPR 2025 physics tracking
- [MediaPipe Pose](https://google.github.io/mediapipe/solutions/pose) - Skeletal estimation

## License

Part of the Synterra suite. Internal use only.
