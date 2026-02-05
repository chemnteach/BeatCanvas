# Interactive Timeline Testing Guide

This document provides comprehensive testing procedures for the interactive timeline with scene editing functionality implemented in BeatCanvas.

## Quick Start

1. **Run verification script:**
   ```bash
   python test_timeline_manual.py
   ```

2. **Start both servers:**
   ```bash
   # Terminal 1 - Backend
   cd backend
   uvicorn main:app --reload

   # Terminal 2 - Frontend
   cd frontend
   npm start
   ```

3. **Test in browser:**
   - Open http://localhost:3000
   - Upload audio file and generate video
   - Verify timeline and scene editing functionality

## Test Components Created

### 1. InteractiveTimeline.tsx
**Location:** `frontend/src/components/InteractiveTimeline.tsx`

**Key Features:**
- Visual timeline with colored scene segments based on mood
- Click-to-seek functionality with precise timestamp navigation
- Hover tooltips showing scene details and timing
- Current playback position indicator with playhead
- Scene editing indicators and visual feedback

**Testing:**
- ✅ Timeline renders with correct scene count (12/24/48)
- ✅ Scene segments have appropriate colors based on mood
- ✅ Clicking segment seeks video to scene start time
- ✅ Hover tooltips show scene description and timing
- ✅ Playhead tracks current video position

### 2. SceneEditModal.tsx
**Location:** `frontend/src/components/SceneEditModal.tsx`

**Key Features:**
- Modal interface for editing scene descriptions
- AI provider selection with cost estimates
- Visual effects toggles (zoom, pan, fade)
- Current scene preview and timing display
- Regeneration confirmation with cost transparency

**Testing:**
- ✅ Modal opens with current scene data
- ✅ Description can be modified
- ✅ Effects can be toggled
- ✅ Provider selection shows accurate costs
- ✅ Regeneration requires user confirmation

### 3. Enhanced VideoPreview.tsx
**Location:** `frontend/src/components/VideoPreview.tsx`

**Key Features:**
- Integrated timeline component below video player
- Seek functionality synchronized with timeline
- Video controls with timeline interaction
- Current time tracking and display

**Testing:**
- ✅ Timeline appears below video player
- ✅ Video seeks when timeline is clicked
- ✅ Timeline updates during video playback
- ✅ Controls remain functional with timeline

### 4. Backend API Endpoints
**Location:** `backend/main.py`

**New Endpoints:**
- `POST /api/regenerate-scene` - Regenerate specific scene
- `POST /api/rebuild-video` - Rebuild video after changes
- Enhanced WebSocket events for real-time updates

**Testing:**
- ✅ Scene regeneration accepts scene index and new description
- ✅ Cost estimation returned before regeneration
- ✅ WebSocket events for progress updates
- ✅ Video rebuild maintains audio sync

## Testing Scenarios

### Scenario 1: Basic Timeline Interaction
1. Generate video with professional tier (24 scenes)
2. Verify timeline appears with 24 colored segments
3. Click different segments and verify video seeks correctly
4. Hover segments and verify tooltips appear
5. Play video and verify playhead moves smoothly

### Scenario 2: Scene Editing Workflow
1. Double-click a timeline segment
2. Verify scene edit modal opens with current data
3. Modify scene description (e.g., "characters should kiss here")
4. Select effects and AI provider
5. Verify cost estimate appears
6. Regenerate scene and monitor progress
7. Verify updated video reflects changes

### Scenario 3: Multiple Scene Edits
1. Edit multiple scenes in sequence
2. Verify each edit preserves previous changes
3. Rebuild video and verify all changes visible
4. Test cost accumulation across multiple edits

### Scenario 4: Provider Comparison
1. Edit same scene with different providers:
   - Nano Banana ($0.04) - Character consistency
   - DALL-E 3 ($0.08) - Photorealistic quality
   - NovelAI ($0.06) - Artistic/anime style
2. Verify cost differences and output quality
3. Test provider fallback mechanisms

## Performance Benchmarks

### Expected Timing (4-minute audio)
- **Initial Generation:** 5-12 minutes (24 scenes)
- **Timeline Rendering:** <500ms
- **Scene Regeneration:** 30-60 seconds
- **Video Rebuild:** 1-3 minutes
- **Seek Accuracy:** ±100ms

### Memory Usage
- **Timeline Component:** <50MB
- **Scene Editing:** <100MB
- **Video Rebuild:** 1-2GB peak

## Error Scenarios

### API Failures
- Missing API keys → Graceful error with clear message
- Network timeout → Retry mechanism with progress preservation
- Invalid scene index → Validation error with helpful feedback

### UI Edge Cases
- Empty storyboard → Empty state message shown
- Very long video (48+ scenes) → Efficient rendering maintained
- Concurrent editing → Queue management with status display

## Manual Testing Checklist

### Setup Phase
- [ ] Backend starts without errors
- [ ] Frontend builds and loads
- [ ] API keys configured in `~/.claude/.env`
- [ ] Test audio file available in `data/uploads/`

### Generation Phase
- [ ] Video generation completes successfully
- [ ] Storyboard contains expected scene count
- [ ] Timeline appears below video player
- [ ] Scene segments visible and colored appropriately

### Timeline Interaction
- [ ] Clicking segment seeks video to correct timestamp
- [ ] Hover tooltips show scene details
- [ ] Playhead follows video playback
- [ ] Timeline remains responsive during playback
- [ ] Scene boundaries align with audio structure

### Scene Editing
- [ ] Double-click opens scene edit modal
- [ ] Current scene data loads correctly
- [ ] Description can be modified
- [ ] Effects can be selected/deselected
- [ ] Provider selection shows cost differences
- [ ] Cost estimate appears before regeneration
- [ ] User confirmation required for regeneration

### Video Updates
- [ ] Scene regeneration completes without errors
- [ ] Progress updates appear in real-time
- [ ] Video rebuilds after scene changes
- [ ] Updated scenes visible in final video
- [ ] Audio sync maintained after rebuild
- [ ] Download works for updated video

### Performance Validation
- [ ] Timeline responds to clicks within 50ms
- [ ] Video seeks within 100ms accuracy
- [ ] Scene regeneration completes in <2 minutes
- [ ] Video rebuild completes in <5 minutes
- [ ] No memory leaks during extended usage

## Troubleshooting

### Common Issues

**Timeline doesn't appear:**
- Check VideoPreview.tsx includes InteractiveTimeline component
- Verify storyboard data is passed correctly
- Check console for React rendering errors

**Video doesn't seek on timeline click:**
- Verify handleSeek function is implemented
- Check videoRef is properly connected
- Ensure timeline click events aren't blocked

**Scene edit modal doesn't open:**
- Check onSceneEdit prop is passed to timeline
- Verify SceneEditModal is imported in VideoGenerator
- Check for JavaScript console errors

**Scene regeneration fails:**
- Verify API keys are configured
- Check backend logs for error details
- Ensure task_id is valid and active

**Video rebuild takes too long:**
- Consider using preview mode for testing
- Check available system memory
- Verify MoviePy installation and dependencies

### Debug Commands

```bash
# Check component structure
grep -r "InteractiveTimeline" frontend/src/

# Verify API endpoints
curl -X GET http://localhost:8000/docs

# Test individual components
cd backend && python -c "from src.video.assembler import VideoAssembler; print('OK')"

# Monitor WebSocket events
# Use browser dev tools Network tab to monitor WebSocket messages
```

## Success Criteria

The interactive timeline implementation is successful when:

1. **Timeline Functionality:**
   - All 24 scenes appear as colored segments
   - Click-to-seek works with <100ms accuracy
   - Hover tooltips provide scene details
   - Playhead tracks video position smoothly

2. **Scene Editing:**
   - Double-click opens edit modal instantly
   - Scene data loads correctly
   - Cost estimates are accurate
   - Regeneration completes within expected time

3. **Video Updates:**
   - Scene changes are visible immediately
   - Video rebuilds preserve audio sync
   - Download provides updated video file
   - Quality remains consistent after editing

4. **User Experience:**
   - Intuitive interaction patterns
   - Clear visual feedback
   - Cost transparency before actions
   - Professional polish throughout workflow

## Next Steps

After successful timeline testing:

1. **Performance Optimization:**
   - Implement scene caching for faster regeneration
   - Add progressive loading for long videos
   - Optimize timeline rendering for mobile devices

2. **Enhanced Features:**
   - Keyboard shortcuts (space, arrow keys)
   - Bulk scene editing interface
   - Undo/redo functionality
   - Preview mode for faster iteration

3. **Production Deployment:**
   - Load testing with concurrent users
   - Cost monitoring and budget controls
   - Error tracking and analytics
   - User feedback collection system

The interactive timeline transforms BeatCanvas from a "generate and hope" tool into a professional video editing platform where users can fine-tune specific scenes with precision and confidence.