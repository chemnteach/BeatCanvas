# BeatCanvas Local Pipeline Refactoring Ledger

## Goal
Refactor BeatCanvas from cloud API architecture (Gemini/Luma) to local GPU execution using Flux.1-schnell (Uncensored) and LTX-Video, with a robust ComplianceGate safety layer.

**Success Criteria:**
- Full offline video generation on 16GB NVIDIA GPU
- LoRA style injection (gritty_urban, realistic_euro)
- Mandatory age verification with immediate deletion
- Policy-based nudity filtering
- Admin offline mode with custom output directories

## Constraints
- VRAM Budget: 16GB NVIDIA GPU
- Sequential model loading (Flux → unload → LTX)
- Age check CANNOT be disabled (mandatory safety)
- Only admin script can relax NudeNet thresholds

## Key Decisions
1. **Flux.1-schnell Uncensored**: GGUF checkpoint for diverse client requirements
2. **LoRA Injection**: `load_style_lora()` method for dynamic style switching
3. **Loop Calculator**: `num_loops = ceil(section_duration / 4.0)` for video loops
4. **ViT-Age-Classifier**: HuggingFace model for age detection (replaces DeepFace)
5. **NudeNet**: Policy-based thresholds per JSON config
6. **Character Consistency**: Same anchor image for all loops in a section

## State

### ✅ Completed
- [x] Analyzed current cloud API architecture
- [x] Identified all API calls to remove (Gemini, DALL-E, Luma)
- [x] Created prototype_engine.py for local GPU testing
- [x] Created PROTOTYPE_QUICKSTART.md documentation
- [x] Designed LocalImageGenerator class with LoRA support
- [x] Designed LocalVideoGenerator class with loop calculator
- [x] Designed ComplianceGate class with dual detection
- [x] Created policy JSON schemas (rapper_explicit, eu_standard, offline_explicit, safe_default)
- [x] Designed admin_generate_offline.py standalone script
- [x] Created V2 refactoring plan with full implementation code
- [x] Prepared gemini_handoff folder for cross-AI collaboration

### 🎯 Current: Documentation & Handoff
- [→] Update continuity ledger
- [ ] Create handoff document
- [ ] Push to GitHub

### 📋 Next: Implementation
- [ ] Create backend/src/local/ directory structure
- [ ] Implement LocalImageGenerator
- [ ] Implement ComplianceGate
- [ ] Implement LocalVideoGenerator
- [ ] Create policy JSON files
- [ ] Implement admin_generate_offline.py
- [ ] Update main.py pipeline orchestration
- [ ] Integration testing

## Open Questions
- CONFIRMED: Flux + LoRA approach for style switching
- CONFIRMED: 4-second loop strategy for LTX-Video
- CONFIRMED: ViT-Age-Classifier for age detection
- CONFIRMED: Policy JSON format for nudity thresholds
- UNCONFIRMED: LoRA compatibility with GGUF checkpoints (needs testing)
- UNCONFIRMED: Memory usage with both models (needs profiling)

## Working Set

### Key Files Created
```
BeatCanvas/
├── prototype_engine.py              # Standalone GPU test script
├── PROTOTYPE_QUICKSTART.md          # Quick start guide
├── requirements_prototype.txt       # Prototype dependencies
├── REFACTORING_PLAN_LOCAL_PIPELINE.md    # V1 plan
├── REFACTORING_PLAN_LOCAL_PIPELINE_V2.md # V2 plan (current)
└── gemini_handoff/                  # Cross-AI collaboration package
    ├── 00_README.md                 # Summary and questions
    ├── 01_main_orchestrator.py      # Current pipeline
    ├── 02_image_generator.py        # Current image gen (to replace)
    ├── 03_video_generator.py        # Current video gen (to replace)
    ├── 04_storyboard_model.py       # Data models
    ├── 05_compliance_reference.py   # Existing moderation
    └── 06_REFACTORING_PLAN_V2.md    # Full implementation plan
```

### Files to Create (Implementation Phase)
```
backend/
├── src/
│   ├── local/
│   │   ├── __init__.py
│   │   ├── image_generator.py       # LocalImageGenerator
│   │   ├── video_generator.py       # LocalVideoGenerator
│   │   └── lora_manager.py
│   │
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── compliance_gate.py       # ComplianceGate
│   │   └── age_classifier.py
│   │
│   └── policies/
│       ├── rapper_explicit.json
│       ├── eu_standard.json
│       ├── offline_explicit.json
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

### Branch/Environment
- **Location**: `c:\src\Synterra\BeatCanvas\`
- **Branch**: master
- **GPU Required**: NVIDIA 16GB VRAM

### Test Commands
```bash
# Prototype test
pip install -r requirements_prototype.txt
python prototype_engine.py

# Full pipeline (after implementation)
cd backend
python scripts/admin_generate_offline.py --audio song.mp3 --policy eu_standard
```

## Pipeline Architecture V2

```
Audio Upload
    ↓
[Phase 1] Audio Analysis (librosa) ─────────────── UNCHANGED
    ↓
[Phase 2] Concept Generation (GPT-4) ───────────── UNCHANGED
    ↓
[Phase 3] Storyboard → SongStructure ───────────── UNCHANGED
    ↓
[Phase 4] LOCAL Image Generation ───────────────── NEW
    │   ├── LocalImageGenerator (Flux.1-schnell)
    │   ├── GGUF checkpoint + LoRA injection
    │   └── One anchor image per section
    ↓
[Phase 4.5] COMPLIANCE GATE ────────────────────── NEW
    │   ├── ViT-Age-Classifier (age < 18 → DELETE)
    │   └── NudeNet (policy thresholds)
    ↓
[Phase 5] LOCAL Video Generation ───────────────── NEW
    │   ├── LocalVideoGenerator (LTX-Video)
    │   ├── Loop Calculator: ceil(duration / 4.0)
    │   └── Same anchor for all loops
    ↓
[Phase 6] Video Assembly ───────────────────────── UPDATED
    ↓
MP4 Output
```

## Dependencies (New)

```
# Local GPU Generation
torch>=2.1.0
diffusers>=0.32.0
transformers>=4.40.0
sentencepiece>=0.2.0
accelerate>=1.0.0
peft>=0.7.0  # LoRA support

# Compliance/Safety
nudenet>=3.4.0
```

---

**Status**: Planning Complete, Ready for Implementation
**Confidence**: 90% (architecture validated, code drafted)
**Next Action**: Create handoff document, push to GitHub
