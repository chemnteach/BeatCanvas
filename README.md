# BeatCanvas

AI-powered music video storyboard generator and video assembly platform.

## Overview

BeatCanvas transforms songs into editable storyboards and final videos by:
1. Analyzing music structure and emotional content
2. Generating visual concepts based on user prompts
3. Creating scene-by-scene storyboards with timing
4. Generating images via multiple AI providers (DALL-E, Nano Banana/Gemini)
5. Assembling final videos with synchronized audio

## Architecture

- **Frontend**: React + TypeScript + Tailwind CSS (or standalone HTML)
- **Backend**: FastAPI + Python
- **Audio Analysis**: librosa
- **Video Assembly**: MoviePy with GPU encoding support
- **Image Generation**: Multi-provider (Nano Banana/Gemini default, DALL-E 3, NovelAI)
- **Video Generation**: Luma Dream Machine (Phase 6 - in progress)
- **Real-time Updates**: WebSocket

## Features

- Upload audio files and visual prompts
- Character reference image uploads for consistency
- Multi-provider image generation for flexibility
- Selective scene editing and regeneration
- Real-time progress tracking
- Professional video output (1920x1080, 24fps)
- GPU encoding support (3-10x faster on NVIDIA)

## Cost

- **Ken Burns only** (current): ~$3-4 per 4-minute video
- **Hybrid with Luma** (Phase 6): ~$8-10 per 4-minute video

---

## Setup on a New Machine (Step-by-Step)

### Prerequisites

1. **Python 3.10+** (tested with 3.13)
2. **Node.js 18+** (for frontend, optional)
3. **FFmpeg** - Must be in system PATH
4. **Git**

### Step 1: Clone Repository

```bash
git clone https://github.com/chemnteach/BeatCanvas.git
cd BeatCanvas
```

### Step 2: Create API Keys File

**IMPORTANT**: API keys are NOT in the repository. Create this file:

**Windows:** `C:\Users\<username>\.claude\.env`
**Mac/Linux:** `~/.claude/.env`

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_AI_API_KEY=...

# Optional (Phase 6 - video generation)
LUMAAI_API_KEY=...

# Optional (alternative providers)
NOVELAI_API_KEY=...
REPLICATE_API_TOKEN=...
```

### Step 3: Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Step 4: Verify FFmpeg

```bash
ffmpeg -version
```

If not found, install FFmpeg and add to PATH:
- **Windows**: Download from ffmpeg.org, add bin folder to PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Step 5: Start Backend

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

You should see:
```
[ASSEMBLER] GPU encoding available (h264_nvenc)  # if NVIDIA GPU
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### Step 6: Access Application

Open in browser: `http://localhost:8002/advanced`

(This uses the standalone HTML file - no frontend build needed)

### Optional: Frontend Development

```bash
cd frontend
npm install
npm start
```

Opens on `http://localhost:3000`

---

## Files NOT in GitHub (Transfer These!)

### 1. API Keys (CRITICAL)
```
~/.claude/.env
```
Contains: OPENAI_API_KEY, GOOGLE_AI_API_KEY, LUMAAI_API_KEY

### 2. Generated Data (Optional - can regenerate)
```
data/uploads/          # Uploaded audio files
data/generated_images/ # AI-generated images
data/references/       # Character reference images
output/                # Final video files
```

### 3. Continuity Ledger (Project context)
```
thoughts/ledgers/CONTINUITY_CLAUDE-beatcanvas-interactive-timeline.md
```
This IS in GitHub, but contains session history.

### 4. Implementation Plan (Reference)
```
~/.claude/plans/rippling-spinning-lightning.md
```
Phase 6 implementation plan (on local machine only).

---

## Quick Transfer Checklist

Before leaving:

- [ ] Copy `~/.claude/.env` to new machine
- [ ] Push any uncommitted changes: `git add . && git commit -m "WIP" && git push`
- [ ] Optionally: zip `data/` folder if you want to keep generated assets

On new machine:

- [ ] `git clone https://github.com/chemnteach/BeatCanvas.git`
- [ ] Create `~/.claude/.env` with API keys
- [ ] `cd backend && pip install -r requirements.txt`
- [ ] Verify FFmpeg: `ffmpeg -version`
- [ ] Start: `python -m uvicorn main:app --port 8002`
- [ ] Open: `http://localhost:8002/advanced`

---

## Current Status (Phase 6)

**Implemented:**
- Resolution standardized to 1920x1080
- Beat-based scene subdivision (60 scenes vs 24)
- Motion prompt generation for AI video
- Scene type classification (hero vs standard)
- Character management system
- GPU encoding support

**Awaiting:**
- `LUMAAI_API_KEY` to test video generation
- Integration into main.py pipeline

See `thoughts/ledgers/CONTINUITY_CLAUDE-beatcanvas-interactive-timeline.md` for full details.