# BeatCanvas Continuity Ledger

## Goal
Create a complete standalone music video storyboard generator called "BeatCanvas" that takes audio files and user prompts to generate editable storyboards and assemble final videos with AI-generated images.

## Constraints
- Standalone application (separate from Atlas)
- React + TypeScript frontend with FastAPI backend
- Multi-provider image generation (DALL-E, NovelAI, Replicate)
- Cost-optimized: $4-9 for 4-minute professional videos
- Character consistency through reference uploads
- Selective scene editing capabilities
- Professional 1792x1024 output at 24fps
- **Local GPU work offloaded to remote servers** (RunPod, etc.)

## Key Decisions
1. **Architecture**: React + FastAPI chosen over Gradio for professional UI/UX
2. **Multi-provider Strategy**: Smart provider routing (DALL-E for photorealism, NovelAI for artistic)
3. **Cost Optimization**: 24 scenes for professional quality vs 48 for cinematic
4. **Character Consistency**: Reference image upload + GPT-4 Vision analysis
5. **Scene Editing**: Individual scene regeneration ($0.12) vs full video rebuild
6. **Video Assembly**: MoviePy for local processing (no cloud dependency)
7. **GPU Strategy**: Remote GPU execution (RunPod hybrid pipeline) - local machine is orchestrator only
8. **Video Generation Stack**: Wan 2.6 R2V for scene generation (best identity preservation via reference video) → SkyReels V2 DF for seamless stitching. SkyReels V3 R2V as alternative for multi-reference image input (1-4 images)
9. **Character Consistency Strategy (Tiered)**:
   - Tier 1: R2V reference (included) — Wan 2.6 R2V with artist reference video/images
   - Tier 2: Artist-specific LoRA (premium) — trained on 20-50 photos, $7-10 on RunPod, reusable forever
   - LoRA = recurring revenue lock-in: train once, artist comes back for every future video
10. **LoRA Factory Strategy**: Build library of scene/style/motion LoRAs for Trop Rock genre
    - Image LoRAs (SDXL): trainable locally on both machines (8GB and 12GB VRAM)
    - Video LoRAs (Wan 14B): train on RunPod A100 ($7-10/LoRA, 4-6 hours)
    - Foundation library: ~$50-100 total for complete Trop Rock coverage
11. **Target Genre**: Trop Rock / Beach Country — beaches, tiki bars, boats, ocean, island lifestyle
12. **Local Hardware Roles**:
    - Desktop/Xeon (256GB RAM, 4GB VRAM Quadro M2000): Dataset collection (Pexels), bulk downloads, no training
    - Laptop (32GB RAM, 12GB VRAM): PRIMARY training machine — captioning (Florence-2), SDXL LoRA training, test inference
13. **LoRA Training Tool**: Ostris ai-toolkit — CLI-first (`python run.py config.yaml`), YAML configs, sequential batch support, 8GB VRAM viable
14. **Auto-Captioning**: Florence-2 (4GB VRAM, ~0.5s/img) for general captioning; Joy-Caption for character LoRAs (better identity details)

## State

### ✅ Completed
- [x] Complete project structure created in `/c/src/Synterra/BeatCanvas/`
- [x] React + TypeScript frontend with professional UI components
- [x] FastAPI backend with WebSocket real-time progress
- [x] Audio analysis module (librosa-based)
- [x] Concept generation system (GPT-4 integration)
- [x] Storyboard generator with scene-by-scene creation
- [x] Multi-provider image generation (DALL-E, NovelAI, Replicate)
- [x] Character & background reference upload system
- [x] Video assembly pipeline (MoviePy-based)
- [x] Environment setup automation (`setup_win.py`)
- [x] Component testing framework
- [x] Path issues resolved (relative path fixes)
- [x] MoviePy v2.x compatibility addressed
- [x] Comprehensive test plan created
- [x] Enhanced UI workflow implemented
- [x] Reference image upload system (character & background consistency)
- [x] Real-time progress tracking with cancellation support
- [x] Cost estimation and budget transparency features
- [x] Professional staged workflow (Upload → Prompts → Analysis → Review → Generation)
- [x] Backend API endpoints for enhanced workflow implemented
- [x] Server deployment issues resolved (port 8002)
- [x] **INTERACTIVE TIMELINE SYSTEM** - Complete scene editing workflow
- [x] **CULTURAL CONTENT PROCESSING** - European/American/Conservative standards
- [x] **LOCAL PIPELINE ARCHITECTURE** - AnimateDiff, VRAM management, style system
- [x] **RUNPOD HYBRID PIPELINE** - WAN 2.6 + SkyReels V2 DF integration
- [x] **TECH DEBT AUDIT** - 10 items documented in thoughts/TECH_DEBT.md
- [x] **CODEBASE ANALYSIS** - Full review of pulled changes from GitHub
- [x] **VIDEO GENERATION RESEARCH** - Evaluated SkyReels V2 vs V3, Wan 2.6 R2V, character consistency approaches
- [x] **LORA STRATEGY** - Defined tiered approach: scene/style/motion/artist LoRAs, local vs cloud training
- [x] **DATASET PIPELINE DESIGN** - Automated collection (Pexels API, YouTube CC, artist content), processing (ffmpeg), captioning (Qwen2.5-VL)
- [x] **LORA FACTORY TOOLS** - Built automated pipeline: pexels_collector.py, auto_caption.py, generate_lora_config.py, train_lora.sh
- [x] **LORA REGISTRY UPDATED** - backend/config/loras.yaml expanded with Trop Rock scene library, type/source/file fields
- [x] **SONG ANALYSIS: Love and Saltwater** - librosa + Whisper transcription, LoRA gap analysis complete
- [x] **AI-TOOLKIT INSTALLED** - Desktop (c:\src\Synterra\ai-toolkit), PyTorch 2.6.0+cu124, all deps resolved
- [x] **HARDWARE VERIFIED** - Desktop=4GB VRAM (collection only), Laptop=12GB VRAM (training machine)

### 🎯 Current Status: READY FOR FIRST LORA TRAINING ON LAPTOP
**All tools built and tested on desktop. Laptop (12GB VRAM) is the training machine. Need to clone repos + install deps there.**

### 📋 Tech Debt Summary (see thoughts/TECH_DEBT.md)
| Priority | Items | Examples |
|----------|-------|----------|
| P0 (Critical) | 2 | SkyReels DF not implemented, ComplianceGate placeholder |
| P1 (High) | 2 | File handles without context managers, GPU encoding disabled |
| P2 (Medium) | 3 | Hardcoded negative prompts, debug prints, error handling |
| P3 (Low) | 3 | Duplicate VRAM code, magic numbers, orphaned files |

### 📋 Environment Status
- **Windows Python**: Core deps installed (fastapi, librosa, moviepy) ✅
- **WSL**: Ubuntu running, CUDA 12.5 detected, but deps not installed
- **Local GPU**: Quadro M2000 (4GB) - too small for local AI models
- **Strategy**: Use remote GPU (RunPod) for heavy workloads

## Open Questions
- CONFIRMED: Multi-provider approach with smart routing
- CONFIRMED: Character reference system using GPT-4 Vision
- CONFIRMED: Cost structure ($4-9 for professional videos)
- CONFIRMED: Interactive timeline architecture and scene editing workflow
- CONFIRMED: Cultural processing system for international markets
- CONFIRMED: Remote GPU strategy (local machine = orchestrator only)
- CONFIRMED: Wan 2.6 R2V + SkyReels V2 DF as primary video generation stack
- CONFIRMED: Tiered character consistency (R2V included, LoRA premium)
- CONFIRMED: LoRA factory approach for Trop Rock scene/style/motion library
- CONFIRMED: Automated dataset pipeline (Pexels API + YouTube CC + artist content)
- CONFIRMED: Local machines for dataset prep + image LoRAs, cloud for video LoRAs
- UNCONFIRMED: Real-world video quality and timing accuracy (needs testing)
- UNCONFIRMED: RunPod endpoint configuration and API keys
- UNCONFIRMED: Wan 1.3B LoRA training viability on laptop (12GB VRAM) — needs testing
- CONFIRMED: Pexels API rate limits: 200 req/hour, 20,000/month (free tier)
- CONFIRMED: ai-toolkit (ostris) as LoRA training tool — CLI-first, YAML config, batch queue support
- CONFIRMED: Florence-2 for auto-captioning (4GB VRAM, 0.5s/image)
- UNCONFIRMED: ai-toolkit actual training success on 8GB VRAM with SDXL (settings configured but untested)
- UNCONFIRMED: Florence-2 caption quality sufficient for scene LoRAs (may need Joy-Caption for characters)

## Working Set

### Key Files
```
tools/                                  # LoRA Factory automation scripts
├── pexels_collector.py                 # Download images from Pexels API
├── auto_caption.py                     # Florence-2 / Joy-Caption auto-captioning
├── generate_lora_config.py             # Generate ai-toolkit YAML configs
└── train_lora.sh                       # End-to-end batch training orchestrator

backend/config/
└── loras.yaml                          # LoRA registry (scene/style/character)

datasets/                               # Training datasets (per-LoRA folders)
config/loras/                           # Generated ai-toolkit YAML configs
output/loras/                           # Trained .safetensors output

thoughts/
├── TECH_DEBT.md                        # Tech debt tracker (10 items)
├── ledgers/
│   └── CONTINUITY_CLAUDE-beatcanvas.md # This file
└── handoffs/
    └── HANDOFF_CODEBASE_ANALYSIS.md    # Session handoff

backend/src/
├── cinematography/
│   ├── animatediff_generator.py        # AnimateDiff-Lightning
│   ├── skyreels_df_generator.py        # NOT IMPLEMENTED - uses fallback
│   └── wan26_cloud_generator.py        # WAN 2.6 via Replicate/RunPod
├── local/
│   ├── cinematic_director.py           # Pipeline orchestration
│   ├── vram_manager.py                 # VRAM lifecycle management
│   └── video_generator.py              # SVD local generation
├── safety/
│   └── compliance_gate.py              # PLACEHOLDER - keyword filter only
└── video/
    ├── assembler.py                    # GPU encoding DISABLED
    └── animatediff_pipeline.py         # Debug prints need cleanup
```

### Branch/Environment
- **Location**: `c:\src\Synterra\BeatCanvas\`
- **Branch**: master
- **Environment**: Windows Python 3.x, deps installed
- **WSL**: Available but not configured for BeatCanvas

### Test Commands
```bash
# Verify deps
python -c "import fastapi; import librosa; import moviepy; print('OK')"

# Backend start
cd backend && uvicorn main:app --reload

# Frontend start
cd frontend && npm install && npm start
```

## LoRA Factory Plan

### Trop Rock Scene LoRA Library (Target)
| LoRA Name | Type | Training | Dataset Source |
|-----------|------|----------|----------------|
| tiki-bar-interior | Style (SDXL) | Local | Pexels, YouTube CC |
| beach-sunset | Style (SDXL) | Local | Pexels, Pixabay |
| boat-deck | Style (SDXL) | Local | Pexels, YouTube CC |
| ocean-underwater | Style (SDXL) | Local | Pexels, Pixabay |
| beach-bar-exterior | Style (SDXL) | Local | Pexels |
| island-aerial | Style (SDXL) | Local | YouTube CC drone footage |
| stage-performance | Style (SDXL) | Local | YouTube CC, artist content |
| golden-hour-beach | Style (Wan 14B) | RunPod | Pexels, Pixabay |
| lazy-pan | Motion (Wan 14B) | RunPod | Pexels, YouTube CC |
| boat-drift | Motion (Wan 14B) | RunPod | Pexels, YouTube CC |
| crowd-sway | Motion (Wan 14B) | RunPod | YouTube CC |
| Per-artist | Character (SDXL + Wan) | Local + RunPod | Artist photos/clips |

### Automated Dataset Pipeline
```
Phase 1: COLLECT (Xeon) — Pexels API, yt-dlp CC filter, artist uploads
Phase 2: PROCESS (Xeon) — ffmpeg trim/normalize, dedup, quality filter
Phase 3: CAPTION (Laptop) — Qwen2.5-VL auto-caption + manual review
Phase 4: ORGANIZE (Xeon) — training-ready folder structure
Phase 5: TRAIN — Image LoRAs local, Video LoRAs RunPod A100
```

## Next Session Priorities

### Immediate (On Laptop — 12GB VRAM)
1. **Clone BeatCanvas** from GitHub (has all tools/ scripts)
2. **Clone ai-toolkit** as sibling: `git clone https://github.com/ostris/ai-toolkit.git`
3. **Install deps** — PyTorch 2.6.0+cu124, ai-toolkit requirements (see HANDOFF for exact steps)
4. **PEXELS_API_KEY** already in ~/.claude/.env ✅
5. **Test first LoRA end-to-end**: `bash tools/train_lora.sh --name beach-sunset --query "tropical beach sunset ocean" --type scene --vram 12`
6. Validate trained .safetensors loads and produces expected output

### Next Phase (Scale Up)
1. Run `bash tools/train_lora.sh --batch` overnight for full Trop Rock library
2. Build LoRA Curator module (matches storyboard scenes to LoRA registry)
3. Test with "Love and Saltwater" song — full pipeline with LoRA-enhanced generation

### When Remote GPU Ready
1. Configure RunPod API endpoints
2. Train first Wan 14B video LoRA on RunPod
3. Test WAN 2.6 R2V with LoRA-generated reference images
4. Implement actual SkyReels DF stitching (P0)

### Tech Debt (When Time Permits)
1. Fix P1: file handles in wan26_cloud_generator.py
2. Fix P2: replace debug prints with proper logging
3. Clean up orphaned files (P3)

### Deferred
1. ComplianceGate V2 implementation (NudeNet, ViT-Age-Classifier)
2. End-to-end testing with real audio files
3. Performance benchmarking
4. European/US dual-version video generation (cultural processor exists, needs prompt branching + european-beach-natural LoRA)

---

**Status**: Ready for first LoRA training on laptop
**Confidence**: 90% (tools built, ai-toolkit tested on desktop, laptop setup pending)
**Next Action**: Set up laptop → run first LoRA training (beach-sunset)
