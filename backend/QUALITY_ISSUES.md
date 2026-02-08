# Video Quality Issues - Diagnosis & Solutions

**Date:** 2026-02-08
**Issue:** Generated video has severe motion blur and distortion
**Test:** Task 5f31671f-17c7-4a7f-b9df-bab601542203

---

## 🔍 **Root Causes Identified**

### 1. Test Audio Quality
**Issue:** Using `test_audio.mp3` which is likely just a 10-second tone, not real music

**Impact:**
- No musical structure (beats, tempo changes, sections)
- GPT-4 generates generic/poor scene descriptions
- AnimateDiff has no real creative direction

**Solution:** Use REAL music file for testing

---

### 2. RAFT Interpolation Artifacts
**Issue:** RAFT interpolation creating excessive motion blur

**Evidence:** Individual scene frames show heavy blur (not just final assembly)

**Current settings:**
```python
pipeline = AnimateDiffPipeline(
    target_fps=60,         # High FPS
    interpolate=True,      # RAFT enabled
    heartbeat_callback=None
)
```

**Solutions:**
- A. Disable interpolation temporarily: `interpolate=False`
- B. Use lower target FPS: `target_fps=24` or `target_fps=30`
- C. Switch to RIFE instead of RAFT (better quality)

---

### 3. AnimateDiff Generation Settings
**Possible issues:**
- Wrong guidance scale (causing instability)
- Too many frames being interpolated
- Base resolution too low (576×1024 upscaled to 1920×1080)

**Current AnimateDiff settings:**
```python
frames = self.animatediff.generate(
    prompt=prompt,
    negative_prompt="blurry, low quality, deformed, fused limbs",
    num_frames=16,         # Base frames
    guidance_scale=cfg,    # May be too high/low
    seed=42 + scene_index,
    width=576,
    height=1024,
)
```

**Solutions:**
- Test without interpolation (16 frames at 8fps = 2s per scene)
- Adjust guidance scale (try 7.5 default)
- Generate at higher resolution (768×1152 or 1024×576)

---

### 4. Resolution Mismatch
**Issue:** Generating at 576×1024 but upscaling to 1920×1080 in assembly

**Evidence:** Final video is 1920×1080 but source is 576×1024

**Impact:** Severe quality loss from upscaling

**Solution:**
- Keep output at native AnimateDiff resolution
- OR generate at higher resolution from start

---

## 🛠️ **Immediate Fixes**

### Fix 1: Disable Interpolation (Quick Test)
```python
# src/video/animatediff_pipeline.py line 34
def __init__(
    self,
    target_fps: int = 8,        # ← Lower FPS, no interpolation needed
    interpolate: bool = False,  # ← Disable RAFT
    heartbeat_callback: Optional[callable] = None
):
```

**Expected result:** Clearer frames, no motion blur

---

### Fix 2: Use Real Music
```bash
# Get a real music file (not test tone)
# YouTube, royalty-free music, or your own songs

# Test with real music
curl -X POST http://localhost:8000/api/generate-video \
  -F "audio=@/path/to/real_song.mp3" \
  -F "visual_prompt=cinematic beach sunset with golden waves" \
  -F "quality_tier=basic"
```

**Expected result:** Better prompts → Better video quality

---

### Fix 3: Match Output Resolution to AnimateDiff
```python
# src/video/assembler.py
# Don't upscale - keep native resolution
clip = clip.resize(width=576)  # Keep native width
```

**Expected result:** No upscaling artifacts

---

### Fix 4: Lower Guidance Scale
```python
# src/cinematography/style_logic.py
# Adjust cfg_scale values
cfg = 1.0  # AnimateDiff-Lightning works best at 1.0-2.0
```

---

## 🧪 **Recommended Test Sequence**

### Test 1: Disable Interpolation
```python
# Quick fix to test
pipeline = AnimateDiffPipeline(
    target_fps=8,
    interpolate=False
)
```

**Expected:** Clearer video, but lower FPS (8 fps instead of 60)

---

### Test 2: Use Real Music
**Find a real song** (4-minute music file)

**Expected:** Better scene descriptions → Better visual quality

---

### Test 3: Check Individual Scene Quality
```bash
# Play a single AnimateDiff scene video
vlc data/generated_videos/scene_0005_2083.mp4
```

**Look for:**
- Is it clear or blurry?
- Does the content make sense?
- Is there coherent motion or just blur?

---

## 📊 **Quality Checklist**

### Input Quality
- [ ] Real music file (not test tone)
- [ ] Music with clear structure (intro, verse, chorus)
- [ ] Good quality audio (not compressed/distorted)

### AnimateDiff Settings
- [ ] Guidance scale: 1.0-2.0 for AnimateDiff-Lightning
- [ ] Num frames: 16 (default)
- [ ] Resolution: Native (don't upscale)
- [ ] Interpolation: OFF for testing

### Prompt Quality
- [ ] Detailed scene descriptions from GPT-4
- [ ] Clear visual direction
- [ ] Consistent style across scenes

### Output Settings
- [ ] No unnecessary upscaling
- [ ] Proper FPS (8-24 for AnimateDiff, 60 only if interpolation works well)
- [ ] H.264 encoding working properly

---

## 🎯 **Expected Quality Standards**

### AnimateDiff-Lightning (Baseline)
- **Clarity:** Sharp frames (not blurry like current test)
- **Motion:** Smooth natural movement
- **Coherence:** Recognizable subjects and scenes
- **FPS:** 8-16 native (before interpolation)

### With RAFT Interpolation
- **FPS:** 60
- **Smoothness:** Very smooth motion
- **Quality:** Should NOT introduce blur (but currently does)

### Final Output
- **Resolution:** 576×1024 (native) or 768×1152 (higher quality)
- **Bitrate:** 5-10 Mbps
- **Audio:** Synced to video
- **Duration:** Matches music length

---

## 🚀 **Next Steps**

1. **Disable interpolation** → Test if frames are clearer
2. **Use real music** → Get proper storyboard/prompts
3. **Check individual scenes** → Isolate where blur comes from
4. **Adjust settings** → Fine-tune AnimateDiff parameters

**Goal:** Get clear, coherent video like the examples in the AI video guide you shared

---

**Status:** Quality issues identified, solutions proposed
**Next:** Test with fixes applied
