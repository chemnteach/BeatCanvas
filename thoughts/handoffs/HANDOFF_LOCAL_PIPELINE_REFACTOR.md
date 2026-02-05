# Handoff: BeatCanvas Local Pipeline Refactoring

**Created**: 2026-01-31
**Session**: Local GPU Pipeline Architecture
**Status**: Planning Complete, Ready for Implementation

---

## Summary

This session designed a complete refactoring of BeatCanvas from cloud APIs (Gemini/Luma) to local GPU execution using Flux.1-schnell and LTX-Video. The architecture includes a mandatory ComplianceGate safety layer with age verification and policy-based content filtering.

## What Was Accomplished

### 1. Prototype Created
- `prototype_engine.py` - Standalone script testing Flux + LTX pipeline
- `requirements_prototype.txt` - Dependencies for prototype
- `PROTOTYPE_QUICKSTART.md` - Quick start documentation

### 2. Architecture Designed
- **LocalImageGenerator** - Flux.1-schnell with GGUF + LoRA support
- **LocalVideoGenerator** - LTX-Video with loop calculator (`ceil(duration/4.0)`)
- **ComplianceGate** - NudeNet + ViT-Age-Classifier with policy JSON

### 3. Documentation Produced
- `REFACTORING_PLAN_LOCAL_PIPELINE_V2.md` - Complete implementation plan with code
- `gemini_handoff/` folder - Package for cross-AI collaboration
- `thoughts/ledgers/CONTINUITY_CLAUDE-local-pipeline.md` - Session ledger

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Image Model | Flux.1-schnell Uncensored | GGUF checkpoint, no content restrictions |
| Video Model | LTX-Video | Best image-to-video quality for 16GB VRAM |
| Style System | LoRA injection | Dynamic switching between gritty/realistic |
| Loop Strategy | 4-second clips | LTX native duration, seamless looping |
| Age Detection | ViT-Age-Classifier | HuggingFace, more reliable than DeepFace |
| Policy Format | JSON files | Easy to add new policies without code changes |

## Files Created/Modified

### New Files
```
prototype_engine.py
requirements_prototype.txt
PROTOTYPE_QUICKSTART.md
REFACTORING_PLAN_LOCAL_PIPELINE.md
REFACTORING_PLAN_LOCAL_PIPELINE_V2.md
gemini_handoff/00_README.md
gemini_handoff/01_main_orchestrator.py
gemini_handoff/02_image_generator.py
gemini_handoff/03_video_generator.py
gemini_handoff/04_storyboard_model.py
gemini_handoff/05_compliance_reference.py
gemini_handoff/06_REFACTORING_PLAN.md
gemini_handoff/06_REFACTORING_PLAN_V2.md
thoughts/ledgers/CONTINUITY_CLAUDE-local-pipeline.md
thoughts/handoffs/HANDOFF_LOCAL_PIPELINE_REFACTOR.md
```

## Implementation Roadmap

### Phase 1: Core Infrastructure
1. Create `backend/src/local/` directory structure
2. Create `backend/src/safety/` directory structure
3. Create `backend/policies/` with JSON files

### Phase 2: Image Generation
1. Implement `LocalImageGenerator` class
2. Add LoRA loading functionality
3. Test with prototype prompts

### Phase 3: Compliance Gate
1. Implement `ComplianceGate` class
2. Integrate ViT-Age-Classifier
3. Integrate NudeNet
4. Test with sample images

### Phase 4: Video Generation
1. Implement `LocalVideoGenerator` class
2. Implement loop calculator
3. Test with anchor images

### Phase 5: Integration
1. Update `main.py` pipeline
2. Implement `admin_generate_offline.py`
3. End-to-end testing

## Critical Safety Notes

⚠️ **MANDATORY RULES - Cannot be bypassed:**

1. Age check runs on EVERY image
2. `age_probability < 18 > 0.5` → CRITICAL_FAIL
3. Violating images are IMMEDIATELY deleted
4. Only `admin_generate_offline.py` can relax NudeNet thresholds
5. Age threshold (0.5) cannot be lowered, even in admin mode

## Unresolved Questions

1. **LoRA + GGUF Compatibility** - Need to verify LoRA loading works with GGUF checkpoints
2. **Memory Profiling** - Need to confirm 16GB is sufficient for full pipeline
3. **Loop Variation** - Should each loop have slightly different motion, or identical?

## How to Continue

### Option A: Implement Locally
1. Read `REFACTORING_PLAN_LOCAL_PIPELINE_V2.md`
2. Start with `LocalImageGenerator` (most critical)
3. Follow the implementation code in the plan

### Option B: Collaborate with Gemini
1. Upload `gemini_handoff/` folder to Gemini
2. Start with `00_README.md` for context
3. Use `06_REFACTORING_PLAN_V2.md` as implementation guide

### Option C: Test Prototype First
1. Run `python prototype_engine.py` on target GPU
2. Verify memory usage and output quality
3. Iterate on settings before full implementation

## Test Commands

```bash
# Test prototype (requires GPU)
pip install -r requirements_prototype.txt
python prototype_engine.py

# After implementation
cd backend
python scripts/admin_generate_offline.py \
    --audio test.mp3 \
    --policy eu_standard \
    --style realistic_euro \
    --output_dir ./test_output
```

---

**Next Session Priority**: Implement `LocalImageGenerator` and `ComplianceGate`
