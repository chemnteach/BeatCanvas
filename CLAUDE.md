# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BeatCanvas is an AI-powered music video generator that transforms audio files into synchronized videos through a multi-stage pipeline: audio analysis → concept generation → storyboard creation → image generation → video assembly.

**Architecture**: React + TypeScript frontend with FastAPI + Python backend, featuring multi-provider AI integration (OpenAI, Google Gemini/Nano Banana, NovelAI, Replicate) and real-time WebSocket communication.

## Development Commands

### Environment Setup
```bash
# Windows-specific setup (recommended)
python setup_win.py

# Manual backend setup
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
```

### Running the Application
```bash
# Start backend (localhost:8000)
cd backend
uvicorn main:app --reload

# Start frontend (localhost:3000)
cd frontend
npm start
```

### Testing Commands
```bash
# Component import tests
python test_components.py

# Individual module tests
cd backend
python -m src.audio.analyzer          # Test audio analysis
python -m src.storyboard.conceptor    # Test concept generation
python -m src.video.assembler         # Test video assembly

# Frontend tests
cd frontend
npm test
```

### Building for Production
```bash
# Frontend build
cd frontend
npm run build

# Backend deployment (example)
cd backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Architecture Overview

### Processing Pipeline
```
Audio Upload → Audio Analysis → Concept Generation → Storyboard Creation → Image Generation → Video Assembly → Output
```

**Core Components:**

1. **Audio Analysis** (`backend/src/audio/analyzer.py`)
   - Uses librosa for music feature extraction
   - Detects tempo, beats, structure, and mood
   - Creates timing segments for video scenes

2. **Concept Generation** (`backend/src/storyboard/conceptor.py`)
   - GPT-4 analyzes music data + user prompt
   - Generates visual style, color palette, themes
   - Creates artistic direction for image generation

3. **Storyboard Generator** (`backend/src/storyboard/generator.py`)
   - Creates 12-48 scenes based on music structure
   - GPT-4 generates detailed scene descriptions
   - Syncs visual content to musical timing

4. **Image Generation** (`backend/src/assets/generator.py`)
   - Multi-provider async generation (DALL-E, NovelAI, Replicate)
   - Smart provider routing based on style requirements
   - Character consistency via reference image analysis

5. **Video Assembly** (`backend/src/video/assembler.py`)
   - MoviePy-based video creation
   - Applies effects (fade, zoom, pan) synchronized to music
   - Exports 1792x1024 MP4 at 24fps

### Frontend Structure
```
src/
├── App.tsx              # Main application component
├── components/
│   ├── AudioUpload.tsx      # Drag-drop audio interface
│   ├── VideoGenerator.tsx   # Main state management
│   ├── ProgressTracker.tsx  # 5-step progress visualization
│   ├── StoryboardEditor.tsx # Scene editing interface
│   ├── ProviderSettings.tsx # AI provider configuration
│   └── VideoPreview.tsx     # Download and playback
├── hooks/               # Custom React hooks
├── types/               # TypeScript interfaces
└── utils/               # Helper functions
```

### API Structure
- **WebSocket**: `/ws/{task_id}` - Real-time progress updates
- **REST APIs**:
  - `POST /api/generate-video` - Start video generation
  - `POST /api/upload-reference` - Character/background uploads
  - `GET /api/download/{video_id}` - Download generated videos

## Configuration

### Environment Configuration
**Global Configuration**: Uses centralized `~/.claude/.env` for API keys shared across all projects.

**Required API Keys** (add to `~/.claude/.env`):
```bash
OPENAI_API_KEY=sk-...          # Required for GPT-4, DALL-E 3, GPT-4 Vision
GOOGLE_AI_API_KEY=...          # Optional for Nano Banana (Gemini) - best for character consistency
NOVELAI_API_KEY=...            # Optional for artistic image generation
REPLICATE_API_TOKEN=...        # Optional for Stable Diffusion/Flux
MIDJOURNEY_API_KEY=...         # Optional for future Midjourney integration
```

**Environment Loading Pattern**: All Python scripts use `src.utils.env_loader` which loads:
1. Global config from `~/.claude/.env` (shared across projects)
2. Local `.env` overrides (project-specific settings)

### Quality Tiers (scene count)
- `basic`: 12 scenes (~$2-4 per video)
- `professional`: 24 scenes (~$4-9 per video, recommended)
- `cinematic`: 48 scenes (~$8-18 per video)

### Directory Structure
```
data/
├── uploads/           # User audio files
├── generated_images/  # AI-generated images
└── references/        # Character/background reference images
output/               # Final video files (.mp4)
```

## Key Dependencies

### Backend
- **FastAPI**: Web framework with WebSocket support
- **librosa**: Music analysis and feature extraction
- **moviepy**: Video editing and assembly
- **openai**: GPT-4 and DALL-E 3 integration
- **uvicorn**: ASGI server for development

### Frontend
- **React 18.2**: UI framework with TypeScript
- **Tailwind CSS**: Utility-first styling
- **axios**: HTTP client for API communication
- **react-dropzone**: Drag-and-drop file uploads
- **lucide-react**: Icon components

## Development Patterns

### Error Handling
- Backend uses try/catch with detailed error logging
- Frontend displays user-friendly error messages
- API failures trigger fallback mechanisms (e.g., simplified video assembly)

### State Management
- Frontend: React hooks for local state, WebSocket for real-time updates
- Backend: Task-based processing with progress tracking
- Persistence: File-based storage for generated assets

### Image Generation Strategy
- **DALL-E 3**: Photorealistic scenes, high quality
- **NovelAI**: Artistic/stylized content, anime aesthetics
- **Replicate**: Stable Diffusion/Flux models (optional)
- Provider selection based on visual style requirements

### Video Synchronization
- Audio beat detection drives scene timing
- ImageClips duration calculated from music structure
- Effects (fade, zoom, pan) applied based on mood analysis
- Precise frame-level synchronization with audio track

## Testing Status

**Current Coverage**: ~35% (architectural testing complete, functional testing needed)

**What's Tested**:
- Module imports and basic instantiation (8/8 components passing)
- Path resolution and directory creation
- Python 3.13 compatibility
- MoviePy 2.x compatibility fixes

**What Needs Testing**:
- End-to-end pipeline with real audio files and API keys
- Performance with different audio lengths and quality tiers
- Cross-browser compatibility for React frontend
- Error scenarios (API failures, network timeouts, invalid inputs)

## Known Limitations

### Technical Constraints
- **MoviePy 2.x Breaking Changes**: Some method names changed, compatibility layer implemented
- **Windows-Focused Setup**: Primary development/testing on Windows, cross-platform validation needed
- **API Dependencies**: Requires live OpenAI API key for core functionality
- **Memory Usage**: Large audio files (8+ minutes) may require performance optimization

### Missing Features
- No batch processing for multiple videos
- No user authentication or project management
- No video editing after generation (must regenerate)
- No mobile app (web-only interface)

## Cost Optimization

**Typical Costs** (4-minute video):
- Professional tier (24 scenes): $4-9
- Image regeneration: $0.12 per scene vs full rebuild
- Provider selection impacts cost (DALL-E more expensive than NovelAI)

**Optimization Strategies**:
- Scene-level editing to avoid full regeneration
- Smart provider routing based on content requirements
- Quality tier selection based on budget/quality needs

## Performance Guidelines

**Expected Processing Times** (4-minute audio):
- Audio analysis: 10-30 seconds
- Concept generation: 5-15 seconds
- Storyboard creation: 30-60 seconds
- Image generation: 3-8 minutes (24 scenes)
- Video assembly: 30-90 seconds
- **Total**: 5-12 minutes end-to-end

**Memory Requirements**:
- Audio analysis: ~500MB peak
- Image generation: ~1GB for batch processing
- Video assembly: ~2GB for HD output
- **Recommended**: 4GB+ system RAM

## Troubleshooting

### Common Issues
- **MoviePy errors**: Run `python fix_all_moviepy.py` to apply compatibility fixes
- **Import errors**: Verify Python path includes `backend/` directory
- **API timeouts**: Check network connectivity and API key validity
- **Audio format issues**: Ensure FFmpeg is installed and in system PATH

### Debugging Commands
```bash
# Test individual components
python test_components.py

# Verify environment setup
python setup_win.py

# Check audio analysis directly
cd backend && python -c "from src.audio.analyzer import MusicAnalyzer; print('OK')"

# Test API connectivity
curl -X GET http://localhost:8000/health  # If health endpoint exists
```