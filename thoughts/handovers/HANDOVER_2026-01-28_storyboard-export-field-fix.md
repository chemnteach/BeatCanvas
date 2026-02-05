# Handover Document: Storyboard Export & Field Name Compatibility

**Date:** 2026-01-28
**Session ID:** Phase 5g
**Status:** Ready for Testing

---

## Summary

This session added storyboard export functionality and fixed a critical field name mismatch that caused video generation to fail with `'image_prompt'` KeyError.

---

## Changes Made

### 1. Storyboard Export Feature

**New Backend Endpoints:**
- `GET /api/export-storyboard/{task_id}?format=json|markdown`
  - JSON format: Re-importable, includes all scene data and timing
  - Markdown format: Human-readable for customer delivery
- `POST /api/import-storyboard` - Re-import previously exported storyboards

**Frontend Changes:**
- Added "JSON" and "Markdown" export buttons on Step 4 (Storyboard Review)
- Fixed export URL to use full `http://localhost:8002/api/...` (was relative `/api/...`)

**Files Modified:**
- `backend/main.py` - Added export/import endpoints and `_generate_storyboard_markdown()` helper
- `frontend/advanced-production-ui.html` - Added export buttons, fixed URL

### 2. Field Name Compatibility Fix

**Problem:** Video generation failed with `Generation error: 'image_prompt'`

**Root Cause:**
- Frontend sent `description` field
- Backend `generator.py` expected `image_prompt` field (using direct dict access)

**Solution:**
- Backend: Changed `scene['image_prompt']` to `scene.get('image_prompt') or scene.get('description') or scene.get('prompt', '')`
- Frontend: Now sends both `image_prompt` and `description` for compatibility

**Files Modified:**
- `backend/src/assets/generator.py` - Line 333: Made field access flexible
- `frontend/advanced-production-ui.html` - Lines 2076-2083: Send both field names

### 3. Whisper Lyrics Integration

**Status:** Working

The Whisper (speech-to-text) integration for lyrics extraction is functional:
- FFmpeg PATH fix applied in `extract_lyrics_from_audio()`
- Lyrics extracted with word-level timestamps
- Whisper `temperature: 0` in output = high confidence (expected behavior)

---

## Testing Status

**What Works:**
- Audio upload and analysis
- Whisper lyrics extraction
- AI Story Mapping with section recommendations
- Storyboard generation with preview images
- Export buttons (JSON/Markdown) visible on Step 4

**Ready to Test:**
- Full video generation pipeline (the `image_prompt` fix should resolve the error)
- Export/download functionality
- Lyrics-enhanced image prompts

---

## Known Issues / Technical Debt

1. **WebSocket closes after generation** - User noticed "WebSocket closed" in console. This appears normal (connection closes when task completes), but verify it's not causing issues.

2. **Remaining items from ledger:**
   - Video rebuild pipeline integration with scene changes
   - Performance optimization for large scene counts
   - Add pencil/edit icon to scene cards

---

## Files Changed This Session

| File | Changes |
|------|---------|
| `backend/main.py` | Added storyboard export/import endpoints |
| `backend/src/assets/generator.py` | Fixed field name flexibility |
| `frontend/advanced-production-ui.html` | Export buttons, field compatibility, full API URL |
| `thoughts/ledgers/CONTINUITY_CLAUDE-beatcanvas-interactive-timeline.md` | Updated State section |

---

## Next Steps

1. **Test video generation** - Restart server, upload audio, generate video
2. **Test storyboard export** - Click JSON/Markdown buttons, verify download
3. **Review generated images** - Check if lyrics context improves prompts
4. **Test full workflow end-to-end** - Upload → Story → Quality → Storyboard → Video

---

## Commands to Resume

```bash
# Restart backend server
cd backend
python restart_server.py

# Or directly:
python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

Then open `http://localhost:8002/advanced` and test the full workflow.
