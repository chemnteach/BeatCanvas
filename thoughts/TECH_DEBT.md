# BeatCanvas Tech Debt Tracker

**Last Updated:** 2026-02-13
**Reviewed By:** Claude Code Analysis Session

---

## Critical Priority (P0)

### 1. SkyReels V2 DF Stitching Not Implemented
**Location:** [skyreels_df_generator.py:93-102](../backend/src/cinematography/skyreels_df_generator.py#L93-L102)

**Issue:** The SkyReels V2 Diffusion Forcing video stitching is advertised but NOT implemented. Currently uses simple MoviePy concatenation as a fallback.

```python
# TODO: Implement actual SkyReels DF stitching
logger.warning("SkyReels DF stitching not yet fully implemented")
logger.info("Using simple concatenation as fallback...")
self._simple_concatenate(video_clips, output_path, audio_path)
```

**Impact:**
- "Seamless infinite-length video" feature does not work
- RunPod hybrid pipeline claims SkyReels capability it doesn't deliver
- Users expecting diffusion-based stitching get visible cuts

**Resolution:**
- [ ] Investigate SkyReels V2 API (may differ from standard diffusers)
- [ ] Implement actual diffusion-forcing stitching
- [ ] Add fallback with clear warning if SkyReels unavailable
- [ ] Update documentation to reflect current state

**Reference:** https://github.com/SkyworkAI/SkyReels-V2

---

### 2. ComplianceGate is Placeholder Only
**Location:** [compliance_gate.py](../backend/src/safety/compliance_gate.py)

**Issue:** The V2 refactoring plan specified NudeNet + ViT-Age-Classifier integration, but only basic keyword filtering exists.

```python
class ComplianceGate:
    """
    Simple content compliance checker.
    This is a placeholder implementation. In production, you would integrate:
    - LlamaGuard or similar safety model
    - Custom trained classifiers
    - Third-party moderation APIs
    """
```

**Missing from V2 Plan:**
- [ ] NudeNet integration for NSFW detection
- [ ] ViT-Age-Classifier for age verification
- [ ] Policy JSON system (eu_standard.json, rapper_explicit.json, offline_explicit.json)
- [ ] Admin offline mode with relaxed thresholds
- [ ] CRITICAL_FAIL handling for age_probability < 18 > 0.5
- [ ] Immediate deletion of violating images

**Impact:**
- Safety system not meeting planned specifications
- No image-based content moderation
- No age verification

**Resolution:**
- [ ] Implement NudeNet integration
- [ ] Implement ViT-Age-Classifier
- [ ] Create policy JSON schema and loader
- [ ] Add admin_generate_offline.py mode
- [ ] Test with sample images

---

## High Priority (P1)

### 3. File Handles Not Using Context Managers
**Location:** [wan26_cloud_generator.py:216, 227, 251, 253](../backend/src/cinematography/wan26_cloud_generator.py#L216)

**Issue:** File handles opened without `with` statement, may not be properly closed.

```python
inputs = {
    "image": open(image_path, "rb"),  # Not using context manager
    ...
}
if self.enable_audio_sync and audio_segment:
    inputs["audio"] = open(audio_segment, "rb")  # Same issue
```

**Impact:**
- Resource leaks under error conditions
- File handles may not be released

**Resolution:**
- [ ] Refactor to use context managers
- [ ] Or use try/finally to ensure cleanup

---

### 4. GPU Encoding Forcibly Disabled
**Location:** [assembler.py:37-38](../backend/src/video/assembler.py#L37-L38)

**Issue:** NVENC GPU encoding is detected but forcibly disabled due to compatibility issues.

```python
# Temporarily force CPU encoding due to NVENC compatibility issues
# TODO: Debug NVENC parameter compatibility with this ffmpeg version
self.gpu_available = False  # Force libx264 (CPU) for now
```

**Impact:**
- Video encoding uses CPU (slower)
- GPU resources underutilized

**Resolution:**
- [ ] Debug NVENC parameter compatibility
- [ ] Test with different ffmpeg versions
- [ ] Document compatible ffmpeg/NVENC combinations
- [ ] Re-enable GPU encoding when fixed

---

## Medium Priority (P2)

### 5. Hardcoded Negative Prompt in AnimateDiff Pipeline
**Location:** [animatediff_pipeline.py:216-217](../backend/src/video/animatediff_pipeline.py#L216-L217)

**Issue:** Negative prompt is hardcoded, not configurable.

```python
negative_prompt="silhouette, backlit, dark, shadowy, sunset backlighting, contre-jour, rim lighting, underexposed, low light, blurry, low quality, deformed, fused limbs",
```

**Resolution:**
- [ ] Move to configuration file or style definition
- [ ] Allow per-scene negative prompt overrides

---

### 6. Debug Print Statements in Production Code
**Location:** Multiple files in [animatediff_pipeline.py](../backend/src/video/animatediff_pipeline.py)

**Issue:** Debug print statements left in production code.

```python
print(f"[DEBUG] Scene {scene_index}: Loading AnimateDiff generator...")
print(f"[DEBUG AnimateDiffPipeline] generate_all_scenes called with {len(storyboard)} scenes")
```

**Resolution:**
- [ ] Replace with proper logging
- [ ] Use log levels (DEBUG, INFO, etc.)
- [ ] Configure log level via environment variable

---

### 7. Inconsistent Error Handling in AI Analyzer
**Location:** [narrative_analyzer_ai.py:72-82](../backend/src/storyboard/narrative_analyzer_ai.py#L72-L82)

**Issue:** Raises exceptions with user-facing messages instead of handling gracefully.

```python
raise Exception("OpenAI quota exceeded. Please wait or check your billing. No template fallback available - user requested real AI only.")
```

**Resolution:**
- [ ] Create custom exception classes
- [ ] Handle errors at API layer
- [ ] Return proper HTTP error codes
- [ ] Log errors separately from user messages

---

## Low Priority (P3)

### 8. Duplicate VRAM Cleanup Code
**Location:** Multiple generators have similar kill() implementations

**Issue:** VRAM cleanup pattern duplicated across:
- [animatediff_generator.py](../backend/src/cinematography/animatediff_generator.py)
- [video_generator.py](../backend/src/local/video_generator.py)
- [vram_manager.py](../backend/src/local/vram_manager.py)

**Resolution:**
- [ ] Extract common VRAM cleanup to utility function
- [ ] Use mixin or base class for generators

---

### 9. Magic Numbers in Scene Classification
**Location:** [generator.py:223-228](../backend/src/storyboard/generator.py#L223-L228)

**Issue:** Hardcoded thresholds for scene classification.

```python
is_climax = progress > 0.75
is_high_energy = energy > 0.7
```

**Resolution:**
- [ ] Move thresholds to configuration
- [ ] Document threshold meanings

---

### 10. Orphaned/Backup Files in Repository
**Location:** Root directory and various locations

**Files to clean up:**
- `=1.0.0` - Suspicious file (possibly pip output artifact)
- `backend/src/storyboard/narrative_analyzer_OLD_TEMPLATE_SYSTEM.py.bak`
- `backend/server.log` - Should be in .gitignore

**Resolution:**
- [ ] Delete orphaned files
- [ ] Add to .gitignore where appropriate
- [ ] Clean up backup files

---

## Tracking

| ID | Priority | Status | Assignee | Target Date |
|----|----------|--------|----------|-------------|
| 1  | P0       | Open   | -        | -           |
| 2  | P0       | Open   | -        | -           |
| 3  | P1       | Open   | -        | -           |
| 4  | P1       | Open   | -        | -           |
| 5  | P2       | Open   | -        | -           |
| 6  | P2       | Open   | -        | -           |
| 7  | P2       | Open   | -        | -           |
| 8  | P3       | Open   | -        | -           |
| 9  | P3       | Open   | -        | -           |
| 10 | P3       | Open   | -        | -           |

---

## Notes

### Priority Definitions
- **P0 (Critical):** Feature doesn't work as documented, safety issue, or blocks core functionality
- **P1 (High):** Performance issue, resource leaks, or significant UX problem
- **P2 (Medium):** Code quality issue, maintainability concern, or minor bug
- **P3 (Low):** Cleanup, refactoring opportunity, or nice-to-have improvement

### Related Documents
- [HANDOFF_LOCAL_PIPELINE_REFACTOR.md](handoffs/HANDOFF_LOCAL_PIPELINE_REFACTOR.md) - V2 plan details
- [CONTINUITY_CLAUDE-local-pipeline.md](ledgers/CONTINUITY_CLAUDE-local-pipeline.md) - Session ledger
