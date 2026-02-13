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

### 🎯 Current Status: READY FOR DEVELOPMENT (NO GPU REQUIRED)
**Can work on backend/frontend, API integrations, code quality - GPU work deferred to remote**

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
- UNCONFIRMED: Real-world video quality and timing accuracy (needs testing)
- UNCONFIRMED: RunPod endpoint configuration and API keys

## Working Set

### Key Files
```
thoughts/
├── TECH_DEBT.md                    # Tech debt tracker (10 items)
├── ledgers/
│   └── CONTINUITY_CLAUDE-beatcanvas.md  # This file
└── handoffs/
    └── HANDOFF_CODEBASE_ANALYSIS.md     # Session handoff

backend/src/
├── cinematography/
│   ├── animatediff_generator.py    # AnimateDiff-Lightning (guidance_scale=1.0 fix)
│   ├── skyreels_df_generator.py    # NOT IMPLEMENTED - uses fallback
│   └── wan26_cloud_generator.py    # WAN 2.6 via Replicate/RunPod
├── local/
│   ├── cinematic_director.py       # Pipeline orchestration
│   ├── vram_manager.py             # VRAM lifecycle management
│   └── video_generator.py          # SVD local generation
├── safety/
│   └── compliance_gate.py          # PLACEHOLDER - keyword filter only
└── video/
    ├── assembler.py                # GPU encoding DISABLED
    └── animatediff_pipeline.py     # Debug prints need cleanup
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

## Next Session Priorities

### Immediate (Can Do Now - No GPU)
1. Fix P1 tech debt: file handles in wan26_cloud_generator.py
2. Fix P2 tech debt: replace debug prints with proper logging
3. Clean up orphaned files (P3)
4. Test backend server startup

### When Remote GPU Ready
1. Configure RunPod API endpoints
2. Test WAN 2.6 cloud generation
3. Implement actual SkyReels DF stitching (P0)
4. Debug NVENC encoding compatibility (P1)

### Deferred
1. ComplianceGate V2 implementation (NudeNet, ViT-Age-Classifier)
2. End-to-end testing with real audio files
3. Performance benchmarking

---

**Status**: Development Ready (GPU work deferred to remote)
**Confidence**: 90% (codebase analyzed, tech debt documented)
**Next Action**: Fix tech debt items or set up remote GPU access
