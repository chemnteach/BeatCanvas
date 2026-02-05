# Product Requirements Document (PRD)

## BeatCanvas Cinematography Engine

**Version**: 2.0 (AKD Pivot)
**Last Updated**: 2026-02-04
**Status**: In Development

---

## 1. Executive Summary

BeatCanvas is an AI-powered video generation system that transforms static images into high-fidelity, temporally consistent videos. The system addresses the critical challenge of "anatomical melting" - a common artifact in AI video generation where limbs distort, stretch, or collapse during rapid motion sequences.

### Key Innovation

The **Articulated Kinematics Distillation (AKD)** integration provides physics-based skeletal tracking that enforces bone length constraints throughout the generation process, preventing anatomical distortion while preserving dynamic motion.

---

## 2. Problem Statement

### Current State
AI video generation models (SVD, Runway, Pika) produce impressive results but suffer from:

1. **Anatomical Melting** - Limbs stretch, merge, or disappear during motion
2. **Temporal Inconsistency** - Objects change shape/size between frames
3. **Motion-Quality Tradeoff** - Higher motion = more artifacts

### Target Users
- **Content Creators** - Need photorealistic video without manual VFX
- **Marketing Teams** - Require consistent brand visuals in motion
- **Independent Filmmakers** - Budget-constrained but quality-focused

### Success Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Anatomical consistency | 60% frames pass | 95% frames pass |
| Motion intensity | Low-Medium | High (action scenes) |
| Output resolution | 576x1024 | 576x1024 @ 60fps |
| Generation time | N/A | <5 minutes for 4s video |

---

## 3. Product Goals

### Primary Goals

1. **P0: Anatomical Integrity**
   - No frame should exhibit >8% bone length deviation from anchor
   - Skeletal structure must remain consistent across all 240 output frames

2. **P0: High-Velocity Motion Support**
   - Support explosive motion (punches, jumps, fast camera moves)
   - Maintain subject coherence at motion_bucket_id >= 100

3. **P1: Photorealistic Quality**
   - CLIP-optimized prompts with camera/film/lighting tokens
   - "Detailed skin" texture as mandatory quality gate

### Secondary Goals

4. **P1: Temporal Smoothness**
   - 60fps output with no visible frame jumps
   - RAFT interpolation with occlusion awareness

5. **P2: Style System**
   - 3 production styles out of box
   - Extensible via YAML configuration

---

## 4. Functional Requirements

### FR-1: Cinematography Engine

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Load optics presets from YAML | P0 |
| FR-1.2 | Compose CLIP-optimized prompts with template ordering | P0 |
| FR-1.3 | Auto-detect style from prompt keywords | P1 |
| FR-1.4 | Support manual style/camera/film override | P1 |
| FR-1.5 | Include "detailed skin" in all human subjects | P0 |

### FR-2: Video Generation (SVD-XT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Generate 25 frames at configurable FPS (6-12) | P0 |
| FR-2.2 | Support motion_bucket_id range 0-127 | P0 |
| FR-2.3 | Portrait orientation (576x1024) default | P0 |
| FR-2.4 | Landscape orientation (1024x576) optional | P2 |
| FR-2.5 | Noise augmentation control (0.02-0.20) | P0 |

### FR-3: Temporal Consistency

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Extract structural features via Canny edge detection | P1 |
| FR-3.2 | Compute frame-to-anchor consistency score | P1 |
| FR-3.3 | Reject frames exceeding 18% structural deviation | P1 |
| FR-3.4 | Auto-retry with reduced noise_aug on failure | P0 |
| FR-3.5 | Maximum 3 retry attempts before accepting | P1 |

### FR-4: Skeletal Tracking (AKD)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Detect 17 COCO keypoints via MediaPipe | P0 |
| FR-4.2 | Extract arm bone lengths (shoulder→elbow→wrist) | P0 |
| FR-4.3 | Compare frame bones to anchor with 8% tolerance | P0 |
| FR-4.4 | Report specific bone deviations on failure | P1 |
| FR-4.5 | Finer rollback (0.01) for skeletal vs structural (0.02) | P0 |

### FR-5: RAFT Interpolation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Compute bidirectional optical flow | P0 |
| FR-5.2 | Generate N intermediate frames per pair | P0 |
| FR-5.3 | Apply edge damping (20px boundary) | P1 |
| FR-5.4 | Detect and handle occlusions | P1 |
| FR-5.5 | 32 RAFT iterations for precision | P0 |

### FR-6: Output

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Export MP4 at 60fps | P0 |
| FR-6.2 | Exact 4.0s duration (no stretch/compress) | P0 |
| FR-6.3 | H.264 codec for compatibility | P1 |
| FR-6.4 | Save to configurable output directory | P1 |

---

## 5. Non-Functional Requirements

### NFR-1: Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1.1 | End-to-end generation time | <5 minutes |
| NFR-1.2 | VRAM usage (peak) | <12GB |
| NFR-1.3 | VRAM baseline after cleanup | <1GB |
| NFR-1.4 | RAFT frame processing | <2s per pair |

### NFR-2: Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-2.1 | Generation success rate | >95% |
| NFR-2.2 | Graceful degradation on MediaPipe unavailable | Yes |
| NFR-2.3 | Error logging with frame-level detail | Yes |

### NFR-3: Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-3.1 | Pure functions in prompt_composer.py | 100% |
| NFR-3.2 | Dependency injection for testing | Yes |
| NFR-3.3 | YAML-driven configuration | Yes |
| NFR-3.4 | Unit test coverage | >80% |

---

## 6. User Stories

### US-1: Action Scene Creator
> As a content creator, I want to generate a video of a person throwing a punch, so that I can use it in my action short film without hiring stunt performers.

**Acceptance Criteria**:
- [x] Punch motion is visible and dynamic
- [x] Arm does not stretch or deform
- [x] Subject remains recognizable throughout
- [x] Video is 4 seconds at 60fps

### US-2: Fashion Brand Marketer
> As a marketing manager, I want to generate a video of a model walking on a street at night, so that I can create atmospheric brand content.

**Acceptance Criteria**:
- [ ] Neon lighting effects preserved
- [ ] Model's proportions stay consistent
- [ ] Smooth camera-follow motion
- [ ] Cinematic film grain applied

### US-3: Technical Artist
> As a technical artist, I want to customize camera, film stock, and lighting independently, so that I can match a specific visual reference.

**Acceptance Criteria**:
- [ ] Override individual optics without affecting others
- [ ] Preview composed prompt before generation
- [ ] Access to all registered presets

---

## 7. Technical Constraints

### Hardware Requirements
- **GPU**: NVIDIA RTX 4080+ / RTX 5070 Ti (Blackwell)
- **VRAM**: 12GB minimum, 16GB recommended
- **RAM**: 32GB system memory
- **Storage**: 50GB for models + output

### Software Dependencies
- PyTorch 2.11.0+ (nightly for RTX 50 series)
- CUDA 12.8+
- diffusers (Stability AI SVD-XT)
- torchvision (RAFT models)
- mediapipe (pose estimation)

### API Constraints
- SVD-XT: 25 frames max per generation
- RAFT: GPU memory scales with resolution
- MediaPipe: CPU-only (to avoid VRAM conflict)

---

## 8. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| MediaPipe unavailable | Skeletal checks disabled | Medium | Graceful degradation, structural-only checks |
| VRAM exhaustion | Generation fails | Medium | VRAMManager.kill() before each stage |
| SVD motion collapse | Low-motion output | High | AKD rollback with noise_aug reduction |
| RAFT artifacts at edges | Visible seams | Medium | Edge damping with 20px boundary |

---

## 9. Release Plan

### Phase 1: AKD Integration (Current)
- [x] Physics motion tracker implementation
- [x] Temporal consistency wrapper integration
- [x] RAFT iteration increase (20→32)
- [x] Skeletal tolerance tuning (10%→8%)
- [ ] E2E validation with haymaker sequence

### Phase 2: Style Expansion
- [ ] Add 5 additional production styles
- [ ] Director-specific presets (Nolan, Villeneuve, Fincher)
- [ ] Custom style creation UI

### Phase 3: Audio Integration
- [ ] Beat detection for scene cuts
- [ ] Music-driven motion intensity
- [ ] Lip sync for dialogue scenes

---

## 10. Success Criteria

### MVP Definition
The system successfully generates a 4-second, 60fps video of a "muscular man throwing an explosive fast haymaker punch" where:

1. **Anatomical Test**: No frame exceeds 8% bone length deviation
2. **Motion Test**: Punch arc is clearly visible across frames
3. **Quality Test**: "Detailed skin" texture visible in close frames
4. **Timing Test**: Output is exactly 4.0s (240 frames @ 60fps)

### Validation Method
```bash
python scripts/render_video_svd.py \
  --style STYLE_HIGH_VELOCITY_ACTION \
  --duration 4.0 \
  --output /mnt/c/Users/craig/Downloads/synterra_production/
```

Inspect output for skeletal consistency violations in logs:
```
[TemporalConsistency] ✓ AKD skeletal check passed - bone lengths within 8% tolerance
```

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **AKD** | Articulated Kinematics Distillation - physics-based skeletal tracking |
| **Anchor Image** | The source image from which video is generated |
| **Bone Length Deviation** | Percentage change in skeletal segment length vs anchor |
| **motion_bucket_id** | SVD parameter controlling motion intensity (0-127) |
| **noise_aug_strength** | How much the generation can diverge from anchor |
| **RAFT** | Recurrent All-Pairs Field Transforms - optical flow algorithm |
| **SVD-XT** | Stable Video Diffusion Extended - 25-frame video model |
| **Temporal Consistency** | Frame-to-frame structural coherence |

---

## Appendix B: Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-04 | 2.0 | AKD Pivot - added skeletal tracking, jitter fixes |
| 2026-02-03 | 1.5 | Motion Overdrive - max motion parameters |
| 2026-02-02 | 1.0 | Initial RAFT interpolation integration |
