# Handover Document: Video Assembly Fix & GPU Encoding

**Date:** 2026-01-29
**Session ID:** Phase 5h
**Status:** Complete - Ready for Testing

---

## Summary

This session fixed two critical video assembly bugs (black video output and static slideshow) and added GPU encoding support for 3-10x faster video generation.

---

## Changes Made

### 1. Fixed Black Video Output

**Problem:** Videos showed black screen with audio only (4.2 MB for 3:25 song was suspicious - should be 50MB+)

**Root Cause:** Frame format mismatch in `cinematic_filter`:
- MoviePy ImageClip returns `uint8` frames (0-255)
- `cinematic_filter` assumed frames were float (0-1)
- `frame * 255` on uint8 caused integer overflow → all zeros (black)

**Fix:** Updated [assembler.py:307-350](backend/src/video/assembler.py#L307-L350):
```python
def cinematic_filter(frame):
    # Detect input format
    if frame.dtype == np.float64 or frame.dtype == np.float32:
        frame_uint8 = (frame * 255).astype(np.uint8)
    else:
        frame_uint8 = frame.astype(np.uint8)
    # ... OpenCV processing ...
    # Return uint8 (MoviePy standard format)
    return cv2.cvtColor(frame_cv.astype(np.uint8), cv2.COLOR_BGR2RGB)
```

### 2. Fixed Static Slideshow (Added Ken Burns Effects)

**Problem:** Videos were just static images switching with no motion/transitions

**Root Cause:** Test storyboard had no `effects` or `mood` fields defined

**Fix:** Updated [main.py:309-331](backend/main.py#L309-L331):
```python
effect_options = [
    ['zoom_in', 'fade_in'],
    ['zoom_out', 'fade_out'],
    ['pan_right'],
    ['pan_left'],
    ['zoom_in'],
    ['fade_in', 'fade_out'],
]
mood_options = ['energetic', 'calm', 'dramatic', 'neutral', 'bright']
```

Effects implementation in [assembler.py:108-158](backend/src/video/assembler.py#L108-L158):
- `zoom_in` / `zoom_out` - Ken Burns zoom (1.0 → 1.15)
- `pan_right` / `pan_left` - Ken Burns pan using CompositeVideoClip
- `fade_in` / `fade_out` - CrossFade transitions via MoviePy vfx

### 3. Added GPU Encoding Support

**Problem:** CPU encoding slow (could take 5+ minutes for 4-minute video)

**Solution:** Auto-detect GPU and use hardware encoding when available

**Implementation:** [assembler.py:18-59](backend/src/video/assembler.py#L18-L59):
```python
def _check_gpu_encoding(self) -> bool:
    """Check if NVIDIA GPU encoding (h264_nvenc) is available"""
    result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], ...)
    return 'h264_nvenc' in result.stdout

def _get_encoding_params(self) -> Dict:
    if self.gpu_available:
        return {
            'codec': 'h264_nvenc',
            'preset': 'p4',
            'ffmpeg_params': ['-rc:v', 'vbr', '-cq:v', '19', ...]
        }
    else:
        return {
            'codec': 'libx264',
            'preset': 'medium',
            'ffmpeg_params': ['-crf', '18']
        }
```

**Expected Speedup:** 3-10x faster on machines with NVIDIA GPU

---

## Files Changed

| File | Changes |
|------|---------|
| `backend/src/video/assembler.py` | Fixed cinematic filter frame format, added GPU encoding |
| `backend/main.py` | Added effects/moods to test storyboard |
| `backend/test_assembler_debug.py` | NEW: Diagnostic script for tracing frame issues |
| `thoughts/ledgers/CONTINUITY_CLAUDE-beatcanvas-interactive-timeline.md` | Updated with Phase 5h |

---

## Hardware Recommendation

**User's machines:**
- Desktop: 256GB RAM, dual Xeons, 4GB VRAM
- Laptop: 32GB RAM, 16GB VRAM

**Recommendation:** Use the **laptop** for video generation. With GPU encoding enabled:
- GPU encoding is 3-10x faster than CPU
- 16GB VRAM is more than sufficient for 1080p encoding
- The laptop's NVIDIA GPU will use `h264_nvenc`
- The desktop falls back to CPU (`libx264`) due to limited VRAM

---

## Testing Status

**Verified Working:**
- Black video fix - videos now show actual images
- Ken Burns effects - zoom, pan, fade visible in output
- GPU detection - logs show `[ASSEMBLER] GPU encoding available (h264_nvenc)`

**Ready to Test:**
- Full workflow on laptop with 16GB VRAM
- Compare encoding times: GPU vs CPU
- Video quality with NVENC (CQ 19 = high quality)

---

## Console Logs to Expect

**On startup (GPU available):**
```
[ASSEMBLER] GPU encoding available (h264_nvenc)
```

**During video generation:**
```
[ASSEMBLER] Encoding with h264_nvenc (GPU: True)
```

**If no GPU:**
```
[ASSEMBLER] GPU encoding not available, using CPU (libx264)
[ASSEMBLER] Encoding with libx264 (GPU: False)
```

---

## Commands to Resume

```bash
# Restart backend server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8002

# Run diagnostic if black video issue returns
python test_assembler_debug.py
```

Then open `http://localhost:8002/advanced` and test video generation.

---

## Known Limitations

1. **GPU encoding requires NVIDIA:** AMD/Intel GPUs not supported (would need `h264_amf` or `h264_qsv`)
2. **FFmpeg must have NVENC:** Some FFmpeg builds don't include hardware encoders
3. **NVENC session limit:** NVIDIA limits concurrent encoding sessions (typically 3)

---

## Next Steps

1. **Test on laptop** - Run full video generation with GPU encoding
2. **Compare quality** - Verify NVENC CQ 19 matches libx264 CRF 18
3. **Measure speedup** - Time video assembly on both machines
4. **Consider AMD support** - Add `h264_amf` detection if needed
