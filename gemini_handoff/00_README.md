# BeatCanvas Local Pipeline Refactoring - Handoff Package V2

## Project Goal
Refactor BeatCanvas from cloud API architecture (Gemini/Luma) to local GPU execution using:
- **Flux.1-schnell (Uncensored)** - GGUF checkpoint with LoRA style injection
- **LTX-Video** - 4-second loop generation for character consistency
- **ComplianceGate** - NudeNet + ViT-Age-Classifier safety layer

Target hardware: NVIDIA GPU with 16GB VRAM

---

## Files in This Package

| File | Purpose |
|------|---------|
| `01_main_orchestrator.py` | Pipeline orchestration - `generate_video_pipeline()` function |
| `02_image_generator.py` | Current Gemini/DALL-E APIs to replace |
| `03_video_generator.py` | Current Luma video generation to replace |
| `04_storyboard_model.py` | StoryboardScene dataclass with all fields |
| `05_compliance_reference.py` | Existing content moderation patterns |
| `06_REFACTORING_PLAN_V2.md` | **UPDATED** Complete refactoring plan with new requirements |

---

## V2 Key Changes

### 1. LoRA Style Injection (NEW)
```python
generator.load_style_lora("gritty_urban")   # Rapper content
generator.load_style_lora("realistic_euro")  # European content
```

### 2. Loop Calculator Logic
```python
num_loops = ceil(section_duration / 4.0)
# Example: 32-second verse → 8 loops
```

### 3. ComplianceGate with Dual Detection
- **ViT-Age-Classifier** (HuggingFace) - MANDATORY age check
- **NudeNet** - Policy-based nudity thresholds
- Age < 18 probability > 0.5 → CRITICAL_FAIL + IMMEDIATE DELETE

### 4. Admin Offline Mode (NEW)
```bash
python admin_generate_offline.py \
    --audio song.mp3 \
    --policy offline_explicit \
    --output_dir /mnt/external/private \
    --style gritty_urban
```

---

## New Module Structure

```
backend/
├── src/
│   ├── local/
│   │   ├── image_generator.py    # LocalImageGenerator (Flux + LoRA)
│   │   ├── video_generator.py    # LocalVideoGenerator (LTX loops)
│   │   └── lora_manager.py
│   │
│   ├── safety/
│   │   ├── compliance_gate.py    # NudeNet + ViT-Age check
│   │   └── age_classifier.py
│   │
│   └── policies/
│       ├── rapper_explicit.json
│       ├── eu_standard.json
│       ├── offline_explicit.json  # Admin-only
│       └── safe_default.json
│
├── scripts/
│   └── admin_generate_offline.py
│
└── models/
    ├── flux1-schnell-uncensored.gguf
    └── loras/
        ├── gritty_urban.safetensors
        └── realistic_euro.safetensors
```

---

## Pipeline Flow V2

```
Audio → Analysis → Concept → Storyboard
    ↓
[Phase 4] Flux.1-schnell + LoRA
    ├── load_style_lora("gritty_urban")
    └── Generate 1 anchor per section
    ↓
[Phase 4.5] ComplianceGate
    ├── ViT-Age-Classifier → age < 18 = DELETE
    └── NudeNet → policy threshold check
    ↓
[Phase 5] LTX-Video Loops
    ├── num_loops = ceil(duration / 4.0)
    └── Same anchor for all loops
    ↓
Assembly → MP4
```

---

## Safety Rules (MANDATORY)

1. **Age check CANNOT be disabled** - Even in admin mode
2. **Age probability > 0.5 for < 18 → CRITICAL_FAIL**
3. **Violating images are IMMEDIATELY DELETED**
4. **Only admin_generate_offline.py can relax NudeNet thresholds**

---

## Questions for Review

1. Is the LoRA loading approach compatible with GGUF checkpoints?
2. Should loop variations have different motion prompts, or same prompt repeated?
3. ViT-Age-Classifier vs DeepFace - which is more reliable for age estimation?
4. Should quarantine use secure deletion or just move files?

---

## Implementation Priority

1. **LocalImageGenerator** - Core Flux generation with LoRA
2. **ComplianceGate** - Safety layer (CRITICAL)
3. **LocalVideoGenerator** - LTX loop generation
4. **admin_generate_offline.py** - Standalone admin script
5. **Integration** - Wire into main.py pipeline
