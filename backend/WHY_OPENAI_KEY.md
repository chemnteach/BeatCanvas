# Why BeatCanvas Needs OpenAI API Key

## TL;DR

**OpenAI (GPT-4) creates the creative vision** that tells AnimateDiff **what** to generate.

Without it, AnimateDiff would have no prompts to work with - it would be like having a painter but no instructions on what to paint!

---

## The Pipeline: What Each Phase Does

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Audio Analysis                                         │
│ ────────────────────────                                        │
│ Tool: librosa (Python library)                                  │
│ Input: audio file (MP3, WAV, etc.)                             │
│ Output: Music data (tempo, beats, energy, mood, structure)     │
│ API Key: NONE NEEDED ✓                                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Concept Generation                                     │
│ ───────────────────────────                                     │
│ Tool: GPT-4 (OpenAI)                                           │
│ Input: Music data + User prompt                                │
│ Output: Visual concept (style, colors, themes, mood)           │
│ API Key: OPENAI_API_KEY REQUIRED ← YOU ARE HERE               │
│                                                                 │
│ Example Output:                                                 │
│ {                                                               │
│   "overall_style": "cinematic beach sunset",                   │
│   "color_palette": ["#FF6B35", "#F7931E", "#FDC830"],         │
│   "visual_themes": ["waves", "golden hour", "peaceful"],      │
│   "mood_progression": "calm → energetic → serene"             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Storyboard Creation                                    │
│ ────────────────────────────                                    │
│ Tool: GPT-4 (OpenAI)                                           │
│ Input: Music data + Visual concept + Scene timings             │
│ Output: Detailed scene descriptions for each music segment     │
│ API Key: OPENAI_API_KEY REQUIRED ← YOU ARE HERE               │
│                                                                 │
│ Example Output (12-48 scenes):                                 │
│ Scene 1 (0.0-3.2s): "Wide shot of ocean waves at sunset,      │
│                      golden light reflecting on water"         │
│ Scene 2 (3.2-6.8s): "Medium shot of beach with palm trees,    │
│                      warm orange glow"                          │
│ Scene 3 (6.8-10.1s): "Close-up of waves crashing, dynamic     │
│                       motion, high energy"                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Video Generation (AnimateDiff)                        │
│ ────────────────────────────────────────                        │
│ Tool: AnimateDiff-Lightning (GPU-based)                        │
│ Input: Scene descriptions from Phase 3                         │
│ Output: Video clips for each scene (MP4 files)                │
│ API Key: NONE NEEDED ✓                                         │
│                                                                 │
│ This is what we tested standalone - WORKS PERFECTLY!          │
│ But it NEEDS the prompts from Phase 3 to know what to make.   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Video Assembly                                        │
│ ────────────────────────                                        │
│ Tool: MoviePy (Python library)                                 │
│ Input: Video clips + Audio file                                │
│ Output: Final video with music synchronized                    │
│ API Key: NONE NEEDED ✓                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## What GPT-4 Actually Does

### Phase 2: ConceptGenerator (`src/storyboard/conceptor.py`)

**GPT-4's Job:** Analyze the music and create an artistic vision

**What it receives:**
```python
{
    "music": {
        "tempo": 128 BPM,
        "energy": 0.75,
        "mood": "energetic",
        "segments": [...]
    },
    "user_prompt": "beach sunset waves peaceful"
}
```

**What it creates:**
```json
{
    "overall_style": "Photorealistic cinematic beach landscape",
    "color_palette": ["warm golden sunset", "deep blue ocean", "soft pink clouds"],
    "visual_themes": ["tranquility", "natural beauty", "golden hour"],
    "mood_progression": "peaceful introduction → building energy → calm resolution",
    "camera_style": "Wide establishing shots transitioning to intimate close-ups"
}
```

**Why you can't skip this:**
- Translates abstract music features into concrete visual directions
- Ensures coherent artistic vision across all scenes
- Matches visual mood to musical mood

---

### Phase 3: StoryboardGenerator (`src/storyboard/generator.py`)

**GPT-4's Job:** Create specific scene descriptions synced to music timing

**What it receives:**
```python
{
    "concept": { ... },  # From Phase 2
    "scene_timing": {
        "start": 0.0,
        "end": 3.2,
        "mood": "calm",
        "energy": 0.45
    }
}
```

**What it creates (for each scene):**
```json
{
    "timestamp_start": 0.0,
    "timestamp_end": 3.2,
    "description": "Wide establishing shot of serene beach at golden hour",
    "image_prompt": "cinematic beach sunset, golden light reflecting on calm ocean waves, warm orange and pink sky, wide angle lens, photorealistic, 4k",
    "camera_movement": "slow zoom in",
    "visual_intensity": "low",
    "section": "intro"
}
```

**Why you can't skip this:**
- AnimateDiff needs **detailed text prompts** to generate videos
- Each scene must match the music's timing and mood
- Creates progression/narrative across the video
- Ensures visual coherence between scenes

---

## Real Example: What Happens Without GPT-4

### ❌ Without OpenAI API Key

```
User: "Create video for my beach song"
  ↓
Phase 1: ✓ Audio analyzed (tempo, beats, energy)
  ↓
Phase 2: ✗ STUCK - No GPT-4 to create visual concept
  ↓
Pipeline ERROR: "OPENAI_API_KEY environment variable is required"
```

**Result:** AnimateDiff never runs because it has no prompts

---

### ✅ With OpenAI API Key

```
User: "Create video for my beach song"
  ↓
Phase 1: ✓ Audio analyzed
  ↓
Phase 2: ✓ GPT-4 creates concept: "cinematic beach sunset, warm tones..."
  ↓
Phase 3: ✓ GPT-4 creates 12 scene descriptions:
         - "Wide shot ocean waves golden hour..."
         - "Medium shot palm trees sunset glow..."
         - etc.
  ↓
Phase 4: ✓ AnimateDiff generates 12 video clips using those prompts
  ↓
Phase 5: ✓ MoviePy assembles final video
  ↓
Result: Beautiful music video! 🎬
```

---

## Could BeatCanvas Work Without OpenAI?

### Short Answer: **Not as-is**

### Longer Answer: **You'd need to replace GPT-4 with something else**

**Option 1: Use a different LLM**
- Replace GPT-4 with local model (Llama, Mistral, etc.)
- Modify `conceptor.py` and `generator.py` to use local inference
- **Downside:** Quality will be lower, prompts less creative

**Option 2: Manual mode (no AI storyboard)**
- User provides pre-written prompts for each scene
- Skip Phase 2 and 3 entirely
- **Downside:** Loses automatic music synchronization, much more work

**Option 3: Template-based (simple prompts)**
- Use simple prompt templates without AI
- "Beach scene {i}" for each segment
- **Downside:** No creativity, repetitive, doesn't match music mood

---

## Why GPT-4 Specifically?

**Reasons BeatCanvas uses GPT-4:**

1. **Creative Writing Quality**
   - Generates descriptive, detailed scene prompts
   - Better at artistic/cinematic language than smaller models

2. **Consistency**
   - Maintains coherent style across many scenes
   - Understands abstract concepts like "mood progression"

3. **Music Understanding**
   - Can interpret tempo/energy/mood data
   - Translates musical concepts to visual descriptions

4. **Reliability**
   - Stable API, well-documented
   - Fast response times (important for 12-48 scenes)

---

## Costs (Realistic Estimate)

### Per Video Generation

**GPT-4 Usage:**
- Phase 2: 1 concept generation (~500 tokens input, ~300 tokens output)
- Phase 3: 12-48 scene generations (~300 tokens input, ~150 tokens output per scene)

**Example Cost (24 scenes, professional tier):**
- Input: ~7,500 tokens
- Output: ~3,900 tokens
- **Total: ~$0.35-0.50** per video for GPT-4 calls

**Compare to:**
- DALL-E 3 image generation (if used): $0.12 per image × 24 = **$2.88**
- AnimateDiff: **Free** (uses your local GPU)

**Conclusion:** GPT-4 is actually the **cheapest part** of the pipeline!

---

## Summary

| Question | Answer |
|----------|--------|
| **Why OpenAI key?** | GPT-4 creates scene prompts for AnimateDiff |
| **Can we skip it?** | No - AnimateDiff needs text prompts to generate video |
| **Which phases use it?** | Phase 2 (Concept) and Phase 3 (Storyboard) |
| **Cost per video?** | ~$0.35-0.50 for GPT-4 calls |
| **Alternatives?** | Local LLM (lower quality) or manual prompts (more work) |

---

## Your Next Step

**Add your OpenAI API key to `~/.claude/.env`:**

```bash
nano ~/.claude/.env

# Replace this line:
OPENAI_API_KEY=your_openai_api_key_here

# With your actual key:
OPENAI_API_KEY=sk-proj-...
```

Then the **full pipeline** will work:
- GPT-4 creates the creative vision
- AnimateDiff brings it to life with video
- You get a complete music video! 🎬
