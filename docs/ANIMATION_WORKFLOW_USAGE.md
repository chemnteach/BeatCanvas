# BeatCanvas Animation Workflow - Usage Guide

## Overview

The Animation Workflow transforms your music into stunning animated videos using **16 non-photorealistic art styles**. This is a GENERIC workflow designed to work for ANY artist, ANY genre, and ANY music video project.

## Quick Start

### 1. Start the Application

```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload

# Terminal 2: Start frontend with animation mode
cd frontend
# Edit src/index.tsx to import App.animation.tsx instead of App.tsx
npm start
```

### 2. Use the UI

1. Navigate to http://localhost:3000
2. Click **"Animation Workflow"** tab
3. Upload your audio file (MP3, WAV, etc.)
4. Select animation style and quality tier
5. (Optional) Upload character LoRAs
6. Click **"Generate Animated Video"**
7. Wait 5-15 minutes (depending on quality tier)
8. Download your animated video!

---

## Animation Styles (16 Total)

### For Tropical / Trop Rock Artists

| Style | Look | Best For |
|-------|------|----------|
| **Watercolor** | Soft brush strokes, dreamy, warm tones | Romantic island songs, sunset vibes |
| **Cel-Shaded** | Flat colors, clean outlines, vibrant | Upbeat beach party, summer anthems |
| **Impressionist** | Monet-style, soft focus, painterly | Beautiful ocean scenes, romantic ballads |
| **Pop Art** | Bold colors, Warhol-style, high contrast | Fun party energy, playful vibes |

### For Rock / Alternative

| Style | Look | Best For |
|-------|------|----------|
| **Comic Book** | Bold outlines, halftone dots, dynamic | Energetic rock, superhero vibes |
| **Graffiti** | Street art, spray paint, urban walls | Raw punk, rebellious energy |
| **Pencil Sketch** | Hand-drawn, monochrome shading | Intimate acoustic, raw energy |
| **Neon** | Glowing lines, cyberpunk, futuristic | Modern rock, club energy |

### For Electronic / EDM

| Style | Look | Best For |
|-------|------|----------|
| **Synthwave** | 80s neon grids, sunset gradients, retro | Synthpop, retrowave, 80s vibes |
| **Neon** | Glowing effects, cyberpunk | Modern EDM, festival-ready |
| **Pixel Art** | 8-bit retro, video game sprites | Chiptune, gaming nostalgia |

### For Jazz / Classical

| Style | Look | Best For |
|-------|------|----------|
| **Art Deco** | 1920s geometric, gold accents, glamorous | Jazz, swing, big band |
| **Oil Painting** | Thick brush strokes, classical art | Classical music, opera, dramatic |

### For Indie / Folk

| Style | Look | Best For |
|-------|------|----------|
| **Ghibli** | Studio Ghibli-style, nostalgic | Fantasy folk, whimsical indie |
| **Paper Cutout** | Handmade collage, layered, crafty | Quirky indie, artistic folk |

### For World Music

| Style | Look | Best For |
|-------|------|----------|
| **Ukiyo-e** | Japanese woodblock, traditional art | Japanese-inspired, cultural music |

---

## Quality Tiers

| Tier | Scene Count | Generation Time | Estimated Cost |
|------|-------------|-----------------|----------------|
| **Basic** | 12 scenes | 3-5 minutes | $2-4 per video |
| **Professional** ⭐ | 24 scenes | 5-10 minutes | $4-9 per video |
| **Cinematic** | 48 scenes | 10-20 minutes | $8-18 per video |

⭐ **Recommended:** Professional tier provides the best quality-to-cost ratio.

---

## Character LoRAs (Advanced)

Character LoRAs allow you to use **consistent custom characters** in your animations.

### Training a Character LoRA

```bash
# 1. Collect 15-30 reference images of your character
mkdir -p data/references/my-character

# 2. Place images in that folder

# 3. Train the LoRA
cd backend
bash tools/train_lora.sh my-character "a portrait of ohwx person" 1000

# 4. The trained LoRA will be saved to output/loras/my-character/
```

### Using Character LoRAs in the UI

1. Upload your trained LoRA file (.safetensors) via the **"Upload LoRA"** button
2. Enter a name (e.g., "rob-character")
3. Enter trigger word (e.g., "ohwx")
4. Select as **Protagonist** or **Supporting Character**
5. Generate your video!

### LoRA Types

- **Protagonist LoRA**: Main character, appears in most scenes
- **Supporting LoRAs**: Secondary characters, appear occasionally
- **Scene LoRAs**: Specific environments (beach, bonfire, etc.)
- **Style LoRAs**: Additional style modifiers (70s film, retro, etc.)

---

## API Endpoints

If building custom integrations:

### List Animation Styles
```bash
GET /api/animation/styles
```

### List Available LoRAs
```bash
GET /api/animation/loras
```

### Generate Animated Video
```bash
POST /api/animation/generate
Content-Type: application/json

{
  "task_id": "unique_task_id",
  "audio_path": "data/uploads/song.mp3",
  "animation_style": "watercolor",
  "protagonist_lora": "rob-character",
  "quality_tier": "professional",
  "fps": 24,
  "width": 1024,
  "height": 1024
}
```

### Upload Character LoRA
```bash
POST /api/animation/upload-character-lora
Content-Type: multipart/form-data

name: my-character
trigger: ohwx
description: Custom character for music videos
lora_file: <file.safetensors>
```

---

## Workflow Architecture

```
Audio Upload
    ↓
Audio Analysis (tempo, beats, structure)
    ↓
Scene Generation (SDXL + LoRAs)
    ↓
Rotoscope/Animation Style (ControlNet)
    ↓
Video Assembly (sync to music)
    ↓
Final Animated Video
```

### Key Components

- **SDXL LoRA Generator** (`backend/src/assets/sdxl_lora_generator.py`)
  - Generates character scenes with multi-LoRA support

- **Rotoscope Generator** (`backend/src/animation/rotoscope_generator.py`)
  - Applies 16 animation styles using ControlNet

- **Animation Workflow** (`backend/src/animation/animation_workflow.py`)
  - Orchestrates the entire pipeline

---

## Use Cases

### Trop Rock Artist
**Goal:** Romantic island sunset video

**Setup:**
- Style: Watercolor
- Quality: Professional
- No character LoRAs (generic scenes)

**Result:** Dreamy, painterly island scenes synced to music

---

### Hip-Hop Artist
**Goal:** Urban street art video with main character

**Setup:**
- Style: Graffiti
- Quality: Professional
- Protagonist LoRA: "rapper-character"

**Result:** Animated graffiti style with consistent rapper character

---

### Electronic Artist
**Goal:** 80s synthwave aesthetic

**Setup:**
- Style: Synthwave
- Quality: Cinematic
- Style LoRA: "80s-retro"

**Result:** Neon grid landscapes with retro 80s vibes

---

## Cost Optimization

### Save Money
- Use **Basic tier** for demos/tests
- Reuse character LoRAs across multiple videos
- Generate at lower resolution (512x512) for previews

### Maximize Quality
- Use **Cinematic tier** for final releases
- Train high-quality character LoRAs with 30+ images
- Use scene LoRAs for specific environments

---

## Troubleshooting

### "Failed to load animation styles"
- **Fix:** Backend not running. Start with `uvicorn main:app --reload`

### "LoRA upload failed"
- **Fix:** Ensure file is `.safetensors` format and under 500MB

### "Generation taking too long"
- **Expected:** Professional tier = 5-10 minutes, Cinematic = 10-20 minutes
- **If stuck:** Check backend logs for errors

### "Video has low quality"
- **Fix:** Increase quality tier or adjust width/height in advanced options

---

## Next Steps

1. **Test with sample audio** - Start with a 30-second clip
2. **Try different styles** - Experiment with all 16 styles
3. **Train your first LoRA** - Create a character for consistent branding
4. **Scale up** - Once satisfied, use Professional/Cinematic tiers

---

## Support

For questions or issues:
- Check logs: `backend/logs/` (if logging enabled)
- Review API responses in browser DevTools
- Verify environment setup: All API keys in `~/.claude/.env`

---

**Built for:** BeatCanvas Animation Workflow
**Version:** 1.0
**Date:** February 2026
**Author:** Built with Claude Code
