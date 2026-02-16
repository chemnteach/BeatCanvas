# Animation Workflow Integration Guide

## Switching to Animation UI

To enable the animation workflow UI in your BeatCanvas frontend:

### Option 1: Replace App.tsx (Simple)

```bash
cd frontend/src
mv App.tsx App.basic.tsx.bak
mv App.animation.tsx App.tsx
npm start
```

Now you'll see a tab interface with both Storyboard and Animation workflows.

### Option 2: Manual Integration

Edit `frontend/src/index.tsx`:

```typescript
import App from './App.animation';  // Changed from './App'
```

---

## Backend Integration

The animation endpoints are already integrated into `backend/main.py`:

- ✅ `GET /api/animation/styles` - List 16 animation styles
- ✅ `GET /api/animation/loras` - List character/scene/style LoRAs
- ✅ `POST /api/animation/generate` - Start animation generation
- ✅ `POST /api/animation/upload-character-lora` - Upload custom LoRAs

No additional backend changes needed!

---

## File Structure

### Backend Files (Created)
```
backend/
├── src/
│   ├── assets/
│   │   └── sdxl_lora_generator.py       # Multi-LoRA SDXL generator
│   ├── animation/
│   │   ├── rotoscope_generator.py       # 16 animation styles + ControlNet
│   │   └── animation_workflow.py        # End-to-end orchestrator
│   └── ...
├── api_animation_endpoints.py           # Full endpoint definitions
└── main.py                              # ✅ Endpoints already added
```

### Frontend Files (Created)
```
frontend/src/
├── components/
│   ├── AnimationStyleSelector.tsx       # 16 style dropdown with genre categories
│   ├── CharacterLoRAUpload.tsx          # LoRA upload/management interface
│   └── AnimationVideoGenerator.tsx      # Main animation workflow component
├── App.animation.tsx                    # Tab-based UI (Storyboard + Animation)
└── ...
```

### Documentation (Created)
```
docs/
├── ANIMATION_STYLES.md                  # Genre-specific style guide
├── ANIMATION_WORKFLOW_USAGE.md          # Complete usage documentation
└── ANIMATION_INTEGRATION.md             # This file
```

---

## Testing the Integration

### 1. Start Backend
```bash
cd backend
uvicorn main:app --reload
```

Verify endpoints at http://localhost:8000/docs:
- `/api/animation/styles`
- `/api/animation/loras`
- `/api/animation/generate`

### 2. Start Frontend (with Animation UI)
```bash
cd frontend
# Replace App.tsx with App.animation.tsx (see above)
npm start
```

Navigate to http://localhost:3000

### 3. Test the Workflow

1. Click **"Animation Workflow"** tab
2. Upload a short audio file (30 seconds for testing)
3. Select an animation style (try "Watercolor" for Trop Rock)
4. Select quality tier: "Basic" for fast testing
5. Click **"Generate Animated Video"**
6. Wait ~3-5 minutes
7. Download and watch!

---

## Integration Checklist

- [x] Backend endpoints added to `main.py`
- [x] Frontend components created
- [x] Tab-based UI created (`App.animation.tsx`)
- [x] Animation styles documented
- [x] API documentation complete
- [ ] Replace `App.tsx` with `App.animation.tsx` (user decision)
- [ ] Test with real audio file
- [ ] Train and test custom character LoRA

---

## Next Steps for Testing

### Test Basic Workflow (No LoRAs)
```bash
# 1. Upload audio
# 2. Select "Watercolor" style
# 3. Select "Basic" tier (12 scenes)
# 4. Generate
```

Expected time: 3-5 minutes
Expected output: 12-scene animated video in watercolor style

### Test with Character LoRA
```bash
# 1. Train a character LoRA first:
cd backend
bash tools/train_lora.sh test-character "a portrait of ohwx person" 1000

# 2. Upload via UI
# 3. Generate video with character

Expected time: 5-10 minutes
Expected output: Video with consistent character appearance
```

---

## Known Limitations

1. **Stock footage integration incomplete** - `use_stock_footage` flag exists but not fully implemented
2. **SkyReels DF stitching** - Currently uses basic concatenation, not full DF API
3. **No video preview during generation** - Shows progress text only
4. **LoRA registry location** - Expects `backend/config/loras.yaml` (create if missing)

---

## Configuration

### Environment Variables (in ~/.claude/.env)

```bash
# Required for image generation
OPENAI_API_KEY=sk-...              # For DALL-E (if used as fallback)

# Optional (for future enhancements)
REPLICATE_API_TOKEN=...            # For Stable Diffusion models
```

### LoRA Registry (backend/config/loras.yaml)

Create this file if it doesn't exist:

```yaml
# Example LoRA registry
rob-character:
  description: "Main character Rob for Island Girl video"
  type: "character"
  triggers: ["ohwx"]
  file: "rob-character/rob-character.safetensors"
  default_weight: 0.8
  enabled: true

beach-sunset:
  description: "Tropical beach sunset scene"
  type: "scene"
  triggers: []
  file: "beach-sunset/beach-sunset.safetensors"
  default_weight: 0.7
  enabled: true
```

---

## Comparison: Storyboard vs Animation Workflow

| Feature | Storyboard Workflow | Animation Workflow |
|---------|---------------------|-------------------|
| **Visual Style** | Photorealistic (DALL-E, NovelAI) | 16 non-photorealistic styles |
| **Scene Control** | Full editing per scene | Automated based on audio |
| **Character Consistency** | Reference image analysis | LoRA-based (much better) |
| **Generation Time** | 5-12 minutes | 5-15 minutes |
| **Cost** | $4-18 per video | $2-18 per video |
| **Best For** | Narrative videos, specific scenes | Artistic videos, character-driven |
| **Editing** | Full storyboard editor | Minimal editing (style selection) |

---

## Sales Pitch Template

When offering this service to artists:

> "I can create an animated music video for [Song Name] in a [STYLE] style - think [DESCRIPTION]. The animation will be perfectly synced to your music and takes about [TIME] to create. Way more affordable than traditional video production, and you get a completely unique artistic look!"

**Examples:**
- Trop Rock: "...in a dreamy watercolor style - like a moving painting of island sunsets."
- Hip-Hop: "...in a living graffiti mural style - street art that moves to your beat."
- Electronic: "...in a neon synthwave style - 80s retro grids and cyberpunk vibes."

---

## Troubleshooting

### Frontend not showing animation tab
- **Fix:** Verify `App.animation.tsx` is imported in `index.tsx`
- **Check:** No TypeScript errors with `npm run build`

### Backend endpoints returning 404
- **Fix:** Restart backend with `uvicorn main:app --reload`
- **Check:** Visit http://localhost:8000/docs to see all endpoints

### "Failed to fetch animation styles"
- **Fix:** Backend must be running on port 8000
- **Check:** `netstat -an | grep 8000` or visit http://localhost:8000

### LoRA upload failing
- **Fix:** Create directory: `mkdir -p backend/output/loras`
- **Fix:** Create registry: `touch backend/config/loras.yaml`

---

**Ready to use!** Start the backend, switch to `App.animation.tsx`, and test with a short audio clip.
