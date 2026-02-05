# BeatCanvas Handoff - Nano Banana Rate Limit Fix

**Date:** 2026-01-27
**Session Focus:** Debugging Gemini image generation rate limits and model naming

## Problem Statement

Nano Banana (Google Gemini) image generation was failing:
1. Initially worked for ~11 scenes then hit rate limit (10 req/min)
2. After model changes, started returning 404 NOT_FOUND errors
3. Various model names tried, none working reliably

## Root Cause Analysis

### Critical Bug Found (Code Review)
The original code in `generate_all_scenes()` used:
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
```
This launched **all 24 scenes concurrently**, overwhelming the Gemini rate limit (10 req/min) within seconds. The 6-second delay was inside each task but didn't prevent the initial burst.

### Model Name Changes
Google deprecated/renamed models:
- `gemini-2.0-flash-exp` → 404 NOT_FOUND
- `gemini-2.5-flash-preview-04-17` → 404 NOT_FOUND
- `gemini-2.5-flash-image` → Listed but needs testing
- `gemini-2.0-flash-exp-image-generation` → **Current model (verified available)**

## Fixes Applied

### 1. Sequential Generation (Critical Fix)
Changed from concurrent to sequential for rate-limited providers:
```python
# Before: All 24 launched at once
results = await asyncio.gather(*tasks)

# After: One at a time with delays
for i, scene in enumerate(storyboard):
    result = await self._generate_scene_images(scene, provider)
    if i < len(storyboard) - 1:
        await asyncio.sleep(6)  # 6 sec = max 10/min
```

### 2. Model Name Update
```python
model="gemini-2.0-flash-exp-image-generation"
```

### 3. Narrative Token Increase
Increased `max_tokens` from 3000 to 4500 in `narrative_analyzer_ai.py` to ensure GPT-4 generates all 9 sections.

## Files Modified

| File | Change |
|------|--------|
| `backend/src/assets/generator.py` | Sequential generation, correct model name |
| `backend/src/storyboard/narrative_analyzer_ai.py` | Increased max_tokens to 4500 |
| `thoughts/ledgers/CONTINUITY_CLAUDE-beatcanvas-interactive-timeline.md` | Updated state |
| `TECHNICAL_DEBT_PHASE4.md` | Added pencil icon feature request |

## Current State

- **Server**: Running on port 8002 with sequential generation
- **Model**: `gemini-2.0-flash-exp-image-generation`
- **Rate Limiting**: 6-second delay between scenes (10 req/min max)
- **Status**: Needs testing to confirm fix works

## Available Gemini Models (Verified)

```
models/gemini-2.0-flash-exp-image-generation  <- Current
models/gemini-2.5-flash-image                 <- Alternative
models/gemini-3-pro-image-preview             <- Pro tier
```

## To Resume Testing

1. Start server: `cd backend && python -m uvicorn main:app --reload --port 8002`
2. Open: `frontend/advanced-production-ui.html`
3. Test with Professional tier (24 scenes)
4. Watch logs for sequential generation messages:
   ```
   [GENERATOR] Using sequential generation for 24 scenes
   [GENERATOR] Generating scene 1/24 (timestamp: 0.0)
   ```

## If Still Failing

1. **Try `gemini-2.5-flash-image`**: May have higher rate limits
2. **Try `gemini-3-pro-image-preview`**: Pro tier model
3. **Implement DALL-E fallback**: Use Gemini for first 10, DALL-E for rest
4. **Increase delay**: Try 10 seconds instead of 6

## Technical Debt

- Add pencil/edit icon to scene cards (StoryboardEditor.tsx)
- Implement proper logging framework (replace print statements)
- Add retry logic with exponential backoff for rate limits
- Surface generation errors to frontend UI

## Questions for Next Session

1. Does `gemini-2.0-flash-exp-image-generation` work with sequential generation?
2. Should we switch to `gemini-2.5-flash-image` for higher limits?
3. Is 6-second delay sufficient or need longer?
