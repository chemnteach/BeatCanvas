#!/usr/bin/env python3
"""BeatCanvas API - Fresh implementation with all endpoints - UPDATED"""

from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict
import asyncio
import json
import uuid
import os
from pathlib import Path
from src.utils.env_loader import load_global_env

# Load environment variables from global Claude config and local .env
load_global_env()

app = FastAPI(title="BeatCanvas API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8002"],  # React dev server and built app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = Path("data/uploads")
OUTPUT_DIR = Path("output")
GENERATED_DIR = Path("data/generated_images")

# Ensure directories exist
for dir_path in [UPLOAD_DIR, OUTPUT_DIR, GENERATED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Active tasks storage (in production, use Redis)
active_tasks = {}

# Feature flag: Use AnimateDiff for video generation (Phase 8.2)
USE_ANIMATEDIFF = True  # Set to False to use legacy static images + Ken Burns

# Feature flag: Use RunPod hybrid WAN + SkyReels pipeline (Phase 9)
# When True, routes video generation to RunPod for WAN 2.6 + SkyReels V2 DF
# Requires RUNPOD_ENDPOINT_URL in environment
USE_RUNPOD_HYBRID = os.getenv('USE_RUNPOD_HYBRID', 'false').lower() == 'true'

# Pydantic models for request validation
class StyleSuggestionRequest(BaseModel):
    content_prompt: str

class AnalyzeStoryboardRequest(BaseModel):
    content_prompt: str
    style_prompt: str
    quality_tier: str = "professional"
    character_references: Optional[List[str]] = []
    background_references: Optional[List[str]] = []

class GenerateVideoRequest(BaseModel):
    task_id: str
    approved_storyboard: List[dict]

class GeneratePreviewRequest(BaseModel):
    scenes: List[dict]  # List of {prompt, timestamp, section}
    provider: str = "auto"

@app.get("/")
async def root():
    """Serve the frontend UI"""
    print("[ROOT DEBUG] Root endpoint called - SERVER IS UPDATED!")
    # Check for built React frontend first
    frontend_build_path = Path("../frontend/build")
    index_path = frontend_build_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))

    # Serve advanced production UI
    advanced_ui_path = Path(__file__).parent.parent / "frontend" / "advanced-production-ui.html"
    if advanced_ui_path.exists():
        response = FileResponse(str(advanced_ui_path))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Fallback to basic production UI
    production_ui_path = Path(__file__).parent.parent / "frontend" / "production-ui.html"
    if production_ui_path.exists():
        return FileResponse(str(production_ui_path))

    # Fallback to test-ui.html
    test_ui_path = Path(__file__).parent.parent / "frontend" / "test-ui.html"
    if test_ui_path.exists():
        return FileResponse(str(test_ui_path))

    # API status if no frontend available
    return {"message": "BeatCanvas API is running", "version": "fresh-enhanced-endpoints", "status": "operational"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint for frontend"""
    return {"status": "healthy", "message": "BeatCanvas API is running", "version": "1.0.0"}

@app.get("/api/status")
async def api_status():
    """API status endpoint for frontend compatibility"""
    return {"message": "BeatCanvas API is running", "version": "fresh-enhanced-endpoints", "status": "operational"}

@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all routes"""
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes_info.append({
                "path": route.path,
                "methods": getattr(route, 'methods', None),
                "name": getattr(route, 'name', None)
            })
    return {"routes": routes_info, "total": len(routes_info)}

@app.post("/api/style-suggestions")
async def get_style_suggestions(request: StyleSuggestionRequest):
    """Get AI-powered style suggestions based on content prompt"""
    try:
        from src.storyboard.conceptor import ConceptGenerator

        conceptor = ConceptGenerator()
        suggestions = conceptor.suggest_visual_styles(request.content_prompt)

        return {
            "suggestions": suggestions,
            "status": "success"
        }

    except Exception as e:
        # Return fallback suggestions if AI fails
        fallback_suggestions = [
            "Photorealistic cinematic",
            "Artistic illustration",
            "Abstract expressionist",
            "Neon cyberpunk aesthetic",
            "Studio Ghibli inspired",
            "Film noir style"
        ]
        return {
            "suggestions": fallback_suggestions,
            "status": "fallback",
            "note": "AI temporarily unavailable, showing fallback suggestions"
        }

@app.get("/api/test-debug")
async def test_debug():
    """Simple test endpoint to verify server is using updated code"""
    print("[TEST DEBUG] Test endpoint was called - server is using updated code!")
    return {"message": "Debug test successful", "timestamp": "2026-01-24", "status": "updated_code_confirmed"}

@app.post("/api/generate-section-recommendations")
async def generate_section_recommendations(request: dict):
    """Generate intelligent section-based visual recommendations"""
    print(f"[API DEBUG] Section recommendations endpoint called")
    print(f"[API DEBUG] Request: {request}")

    user_concept = request.get("user_concept", "")
    song_structure = request.get("song_structure", [])

    try:
        from src.storyboard.narrative_analyzer_ai import AINarrativeAnalyzer, SongSection

        print(f"[API DEBUG] User concept length: {len(user_concept)}")
        print(f"[API DEBUG] Song structure: {len(song_structure)} sections")

        if not user_concept:
            raise HTTPException(status_code=400, detail="User concept is required")

        # Convert song structure to SongSection objects
        sections = []
        for section_data in song_structure:
            section = SongSection(
                name=section_data.get("name", "Unknown"),
                start_time=float(section_data.get("start", 0)),
                end_time=float(section_data.get("end", 30))
            )
            sections.append(section)

        # Get song analysis data if available (for enhanced context)
        song_analysis = request.get("song_analysis", {})

        # Generate intelligent AI-powered recommendations
        print(f"[API DEBUG] Calling AI NarrativeAnalyzer with song context...")
        analyzer = AINarrativeAnalyzer()
        recommendations = analyzer.analyze_concept_with_song(user_concept, sections, song_analysis)
        print(f"[API DEBUG] Got {len(recommendations)} AI recommendations")

        # Convert SectionRecommendation objects to dictionaries
        recommendations_dict = []
        for rec in recommendations:
            recommendations_dict.append({
                "section_name": rec.section_name,
                "visual_prompt": rec.visual_prompt,
                "style_notes": rec.style_notes,
                "mood": rec.mood,
                "color_palette": rec.color_palette,
                "lighting": rec.lighting
            })

        return {
            "recommendations": recommendations_dict,
            "status": "success",
            "message": f"Generated {len(recommendations)} section recommendations"
        }

    except Exception as e:
        print(f"Error generating section recommendations: {e}")
        # NO FALLBACK TEMPLATES - User explicitly requested to remove all fallbacks
        # Return error response instead of generic templates
        return {
            "recommendations": [],
            "status": "error",
            "message": f"AI analysis failed: {str(e)}. No template fallback available - waiting for proper LLM connection."
        }

@app.post("/api/analyze-and-storyboard")
async def analyze_and_storyboard(
    audio: UploadFile = File(...),
    content_prompt: str = None,
    style_prompt: str = None,
    quality_tier: str = "professional"
):
    """Analyze audio and create storyboard without image generation"""

    if not audio.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        # Save uploaded audio
        task_id = str(uuid.uuid4())
        audio_path = UPLOAD_DIR / f"{task_id}_{audio.filename}"

        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)

        # Create task info for tracking
        task_info = {
            "id": task_id,
            "status": "analyzing",
            "audio_path": str(audio_path),
            "content_prompt": content_prompt,
            "style_prompt": style_prompt,
            "quality_tier": quality_tier,
            "progress": "Analyzing audio and creating storyboard...",
            "storyboard": [],
        }

        active_tasks[task_id] = task_info

        # Start analysis pipeline in background
        asyncio.create_task(analyze_and_storyboard_pipeline(task_id, str(audio_path), content_prompt, style_prompt, quality_tier))

        return {"task_id": task_id, "status": "analyzing"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

class TestVideoRequest(BaseModel):
    task_id: str
    audio_path: str

@app.post("/api/test-video-with-audio")
async def test_video_with_audio(request: TestVideoRequest):
    """
    TEST MODE: Use the uploaded audio file with cached images.
    Skips prompt generation and image generation - goes straight to video assembly.
    """
    task_id = request.task_id
    audio_path = request.audio_path

    # Verify audio file exists
    if not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_path}")

    # Find existing generated images (non-zero size)
    image_dir = Path("data/generated_images")
    all_images = sorted([
        f for f in image_dir.glob("*.png")
        if f.stat().st_size > 0
    ], key=lambda x: x.stat().st_mtime, reverse=True)

    if len(all_images) < 24:
        raise HTTPException(status_code=404, detail=f"Need at least 24 cached images, found {len(all_images)}")

    # Use the 24 most recent valid images
    test_images = all_images[:24]

    # Get audio duration for timing
    try:
        from src.audio.analyzer import MusicAnalyzer
        analyzer = MusicAnalyzer()
        music_data = analyzer.analyze_song(audio_path)
        duration = music_data.get('duration', 180.0)
    except:
        duration = 180.0  # Default 3 minutes

    scene_duration = duration / 24

    storyboard = []
    scene_assets = {}

    class FakeImage:
        def __init__(self, path):
            self.image_path = path

    # Rotate through different effects to make video more dynamic
    effect_options = [
        ['zoom_in', 'fade_in'],
        ['zoom_out', 'fade_out'],
        ['pan_right'],
        ['pan_left'],
        ['zoom_in'],
        ['fade_in', 'fade_out'],
    ]
    mood_options = ['energetic', 'calm', 'dramatic', 'neutral', 'bright']

    for i, img_path in enumerate(test_images):
        timestamp = i * scene_duration
        storyboard.append({
            'timestamp_start': timestamp,
            'timestamp_end': timestamp + scene_duration,
            'section': f'Scene {i+1}',
            'description': 'Test scene (cached image)',
            'images': [str(img_path)],
            'selected_image': 0,
            'effects': effect_options[i % len(effect_options)],
            'mood': mood_options[i % len(mood_options)]
        })
        scene_assets[timestamp] = [FakeImage(str(img_path))]

    # Update existing task or create new one
    if task_id in active_tasks:
        task_info = active_tasks[task_id]
        task_info["status"] = "generating"
        task_info["progress"] = "TEST MODE: Assembling video with your audio..."
        task_info["storyboard"] = storyboard
    else:
        task_info = {
            "id": task_id,
            "status": "generating",
            "audio_path": audio_path,
            "progress": "TEST MODE: Assembling video with your audio...",
            "storyboard": storyboard,
            "video_url": None
        }
        active_tasks[task_id] = task_info

    # Start video assembly
    asyncio.create_task(test_video_assembly_pipeline(task_id, audio_path, scene_assets, storyboard))

    return {
        "task_id": task_id,
        "status": "generating",
        "message": f"TEST MODE: Using your audio ({Path(audio_path).name}) with {len(test_images)} cached images"
    }

@app.post("/api/test-video-only")
async def test_video_only():
    """
    TEST MODE: Skip image generation and create video using existing cached images.
    This saves $3+ per test run by reusing previously generated images.
    """
    import glob

    # Create a test task
    task_id = str(uuid.uuid4())

    # Find an existing audio file
    audio_files = list(UPLOAD_DIR.glob("*.wav")) + list(UPLOAD_DIR.glob("*.mp3"))
    if not audio_files:
        # Use a default test file if available
        default_audio = Path("data/uploads/WrapAroundMeVoxLoop-10Bar_keyC#min_88bpm.wav")
        if default_audio.exists():
            audio_path = str(default_audio)
        else:
            raise HTTPException(status_code=404, detail="No audio files found for testing")
    else:
        audio_path = str(audio_files[0])

    # Find existing generated images (non-zero size)
    image_dir = Path("data/generated_images")
    all_images = sorted([
        f for f in image_dir.glob("*.png")
        if f.stat().st_size > 0
    ], key=lambda x: x.stat().st_mtime, reverse=True)

    if len(all_images) < 24:
        raise HTTPException(status_code=404, detail=f"Need at least 24 images, found {len(all_images)}")

    # Use the 24 most recent valid images
    test_images = all_images[:24]

    # Create fake storyboard with these images
    duration = 180.0  # 3 minute video
    scene_duration = duration / 24

    storyboard = []
    scene_assets = {}

    for i, img_path in enumerate(test_images):
        timestamp = i * scene_duration
        storyboard.append({
            'timestamp_start': timestamp,
            'timestamp_end': timestamp + scene_duration,
            'section': f'Scene {i+1}',
            'description': 'Test scene',
            'images': [str(img_path)],
            'selected_image': 0
        })
        # Create a simple object to hold image path
        class FakeImage:
            def __init__(self, path):
                self.image_path = path
        scene_assets[timestamp] = [FakeImage(str(img_path))]

    # Create task entry
    task_info = {
        "id": task_id,
        "status": "generating",
        "audio_path": audio_path,
        "progress": "TEST MODE: Skipping image generation, assembling video...",
        "storyboard": storyboard,
        "video_url": None
    }
    active_tasks[task_id] = task_info

    # Start video assembly directly (skip image generation)
    asyncio.create_task(test_video_assembly_pipeline(task_id, audio_path, scene_assets, storyboard))

    return {
        "task_id": task_id,
        "status": "generating",
        "message": f"TEST MODE: Using {len(test_images)} cached images, skipping generation"
    }

async def test_video_assembly_pipeline(task_id: str, audio_path: str, scene_assets: dict, storyboard: list):
    """Test pipeline that skips image generation and goes straight to video assembly"""
    try:
        from src.video.assembler import VideoAssembler

        task = active_tasks[task_id]
        task["progress"] = "Assembling video from cached images..."

        assembler = VideoAssembler()
        video_path = assembler.create_video(audio_path, scene_assets, storyboard, task_id)

        task["status"] = "complete"
        task["progress"] = "TEST MODE: Video complete!"
        task["video_url"] = f"/api/download/{task_id}"

        print(f"[TEST] Video assembled: {video_path}")

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Test error: {str(e)}"
        print(f"[TEST] Error: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/cached-storyboard-previews")
async def cached_storyboard_previews(request: GeneratePreviewRequest):
    """
    TEST MODE: Return cached images instead of generating new ones.
    Saves $3+ per test by reusing previously generated images.
    """
    image_dir = Path("data/generated_images")

    # Find existing valid images (non-zero size)
    all_images = sorted([
        f for f in image_dir.glob("*.png")
        if f.stat().st_size > 0
    ], key=lambda x: x.stat().st_mtime, reverse=True)

    results = []
    for i, scene in enumerate(request.scenes):
        if i < len(all_images):
            img_path = all_images[i]
            results.append({
                'index': i,
                'section': scene.get('section', f'Scene {i+1}'),
                'image_url': f"/data/generated_images/{img_path.name}",
                'provider': 'cached',
                'cached': True
            })
        else:
            results.append({
                'index': i,
                'section': scene.get('section', f'Scene {i+1}'),
                'image_url': None,
                'error': 'No cached image available'
            })

    return {
        'status': 'success',
        'previews': results,
        'total': len(results),
        'successful': len([r for r in results if r.get('image_url')]),
        'cached': True,
        'message': f'TEST MODE: Returned {len(results)} cached images'
    }

@app.post("/api/generate-images-and-video")
async def generate_images_and_video(request: GenerateVideoRequest):
    """Generate images and assemble video from approved storyboard"""

    task_id = request.task_id

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task_info = active_tasks[task_id]
        task_info["status"] = "generating"
        task_info["progress"] = "Starting image generation..."
        task_info["storyboard"] = request.approved_storyboard

        # Start generation pipeline in background
        asyncio.create_task(generate_images_and_video_pipeline(task_id, request.approved_storyboard))

        return {"task_id": task_id, "status": "generating"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/generate-storyboard-previews")
async def generate_storyboard_previews(request: GeneratePreviewRequest):
    """Generate preview images for storyboard scenes"""
    try:
        from src.assets.generator import MultiProviderImageGenerator

        image_generator = MultiProviderImageGenerator()

        # Convert scenes to storyboard format expected by generator
        storyboard = []
        for i, scene in enumerate(request.scenes):
            storyboard.append({
                'timestamp_start': scene.get('timestamp', i * 10.0),
                'timestamp_end': scene.get('timestamp', i * 10.0) + 5.0,
                'image_prompt': scene.get('prompt', ''),
                'visual_style': 'cinematic',
                'section': scene.get('section', 'Scene')
            })

        # Generate all images
        scene_assets = await image_generator.generate_all_scenes(storyboard, request.provider)

        # Build results
        results = []
        for i, scene in enumerate(storyboard):
            timestamp = scene['timestamp_start']
            section = scene.get('section', 'Scene')

            if not scene['image_prompt']:
                results.append({
                    'index': i,
                    'section': section,
                    'image_url': None,
                    'error': 'No prompt provided'
                })
                continue

            images = scene_assets.get(timestamp, [])
            if images:
                # Return first image as preview
                image_path = images[0].image_path
                # Convert to URL path
                image_url = f"/data/generated_images/{Path(image_path).name}"
                results.append({
                    'index': i,
                    'section': section,
                    'image_url': image_url,
                    'provider': images[0].provider
                })
            else:
                results.append({
                    'index': i,
                    'section': section,
                    'image_url': None,
                    'error': 'No image generated'
                })

        return {
            'status': 'success',
            'previews': results,
            'total': len(results),
            'successful': len([r for r in results if r.get('image_url')])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

@app.post("/api/generate-video")
async def generate_video(
    audio: UploadFile = File(...),
    visual_prompt: str = None,
    quality_tier: str = "professional"
):
    """Main video generation endpoint"""

    if not audio.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    # Save uploaded audio
    task_id = str(uuid.uuid4())
    audio_path = UPLOAD_DIR / f"{task_id}_{audio.filename}"

    with open(audio_path, "wb") as f:
        content = await audio.read()
        f.write(content)

    # Start background task
    task_info = {
        "id": task_id,
        "status": "started",
        "audio_path": str(audio_path),
        "visual_prompt": visual_prompt,
        "quality_tier": quality_tier,
        "progress": "Analyzing audio...",
        "storyboard": [],
        "video_url": None
    }

    active_tasks[task_id] = task_info

    # Start generation pipeline in background
    asyncio.create_task(generate_video_pipeline(task_id, str(audio_path), visual_prompt, quality_tier))

    return {"task_id": task_id, "status": "started"}

async def extract_lyrics_from_audio(audio_path: str) -> Dict:
    """
    Extract lyrics from audio using OpenAI Whisper
    """
    try:
        # Ensure FFmpeg is in PATH (winget installs it but doesn't always add to PATH)
        ffmpeg_paths = [
            r"C:\Users\craig\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin",
            r"C:\ffmpeg\bin",
            r"C:\Program Files\FFmpeg\bin",
        ]
        for ffmpeg_path in ffmpeg_paths:
            if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")
                print(f"[LYRICS] Added FFmpeg to PATH: {ffmpeg_path}")
                break

        import whisper

        print(f"[LYRICS] Loading Whisper model...")
        # Use base model for good accuracy/speed balance
        model = whisper.load_model("base")

        print(f"[LYRICS] Transcribing audio: {audio_path}")
        # Transcribe with word-level timestamps
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"  # Assume English for now
        )

        # Extract lyrics text
        lyrics_text = result.get("text", "").strip()

        # Analyze lyrics content for themes and mood
        lyrics_analysis = analyze_lyrics_content(lyrics_text)

        print(f"[LYRICS] Extracted {len(lyrics_text)} characters of lyrics")
        print(f"[LYRICS] Detected themes: {lyrics_analysis.get('themes', [])}")

        return {
            "has_lyrics": len(lyrics_text) > 0,
            "lyrics_text": lyrics_text,
            "word_segments": result.get("segments", []),
            "language": result.get("language", "en"),
            "lyrics_analysis": lyrics_analysis
        }

    except Exception as e:
        print(f"[LYRICS ERROR] Failed to extract lyrics: {e}")
        return {
            "has_lyrics": False,
            "lyrics_text": "",
            "word_segments": [],
            "language": "unknown",
            "lyrics_analysis": {},
            "error": str(e)
        }

def analyze_lyrics_content(lyrics_text: str) -> Dict:
    """
    Analyze lyrics content to extract themes, mood, and emotional content
    """
    if not lyrics_text:
        return {}

    lyrics_lower = lyrics_text.lower()

    # Detect lyrical themes
    themes = []
    theme_keywords = {
        "love": ["love", "heart", "romance", "kiss", "together", "forever"],
        "loss": ["lost", "gone", "missing", "empty", "alone", "goodbye"],
        "family": ["father", "mother", "dad", "mom", "family", "home", "parents"],
        "nostalgia": ["remember", "memories", "past", "yesterday", "childhood", "time"],
        "hope": ["hope", "dream", "future", "believe", "tomorrow", "light"],
        "struggle": ["fight", "battle", "hard", "difficult", "pain", "struggle"],
        "freedom": ["free", "escape", "break", "fly", "run", "liberation"],
        "celebration": ["party", "dance", "celebrate", "joy", "happy", "fun"]
    }

    for theme, keywords in theme_keywords.items():
        if any(keyword in lyrics_lower for keyword in keywords):
            themes.append(theme)

    # Detect emotional tone
    emotional_indicators = {
        "positive": ["happy", "joy", "love", "good", "great", "amazing", "wonderful"],
        "negative": ["sad", "pain", "hurt", "bad", "terrible", "awful", "hate"],
        "nostalgic": ["remember", "past", "used to", "back then", "memories"],
        "energetic": ["go", "run", "fast", "loud", "power", "energy", "strong"],
        "peaceful": ["calm", "quiet", "peace", "rest", "gentle", "soft"]
    }

    emotional_tone = []
    for tone, keywords in emotional_indicators.items():
        if any(keyword in lyrics_lower for keyword in keywords):
            emotional_tone.append(tone)

    return {
        "themes": themes,
        "emotional_tone": emotional_tone,
        "lyrical_complexity": "simple" if len(lyrics_text.split()) < 50 else "complex",
        "word_count": len(lyrics_text.split())
    }

@app.post("/api/analyze-audio")
async def analyze_audio(audio: UploadFile = File(...)):
    """Analyze audio file and return song structure without generating video"""

    if not audio.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        # Save uploaded audio temporarily
        task_id = str(uuid.uuid4())
        audio_path = UPLOAD_DIR / f"temp_{task_id}_{audio.filename}"

        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)

        # Analyze audio structure and extract lyrics
        from src.audio.analyzer import MusicAnalyzer
        analyzer = MusicAnalyzer()
        music_data = analyzer.analyze_song(str(audio_path))

        # Extract lyrics using Whisper
        lyrics_data = await extract_lyrics_from_audio(str(audio_path))

        # Convert music analysis to song structure format
        duration = music_data['duration']
        segments = music_data.get('segments', [])

        # Generate song structure based on actual analysis
        if segments and len(segments) > 0:
            # Use detected segments to create structure
            song_structure = []
            section_names = ['Intro', 'Verse 1', 'Chorus 1', 'Verse 2', 'Chorus 2', 'Bridge', 'Verse 3', 'Chorus 3 (Final)', 'Outro']

            for i, segment in enumerate(segments[:len(section_names)]):
                song_structure.append({
                    'name': section_names[i],
                    'start': segment['start_time'],
                    'end': segment['end_time']
                })

            # If we have fewer segments than expected, create the rest proportionally
            if len(segments) < len(section_names):
                remaining_duration = duration - segments[-1]['end_time'] if segments else duration
                remaining_sections = len(section_names) - len(segments)
                section_duration = remaining_duration / remaining_sections if remaining_sections > 0 else 0

                current_time = segments[-1]['end_time'] if segments else 0
                for i in range(len(segments), len(section_names)):
                    song_structure.append({
                        'name': section_names[i],
                        'start': current_time,
                        'end': min(current_time + section_duration, duration)
                    })
                    current_time += section_duration
        else:
            # Fallback: create proportional structure if no segments detected
            section_count = 9
            section_duration = duration / section_count
            section_names = ['Intro', 'Verse 1', 'Chorus 1', 'Verse 2', 'Chorus 2', 'Bridge', 'Verse 3', 'Chorus 3 (Final)', 'Outro']

            song_structure = []
            for i, name in enumerate(section_names):
                start_time = i * section_duration
                end_time = min((i + 1) * section_duration, duration)
                song_structure.append({
                    'name': name,
                    'start': start_time,
                    'end': end_time
                })

        # Keep audio file for later video generation - create a task entry
        # Rename from temp_ to keep it permanently for this session
        permanent_path = UPLOAD_DIR / f"{task_id}_{audio.filename}"
        try:
            audio_path.rename(permanent_path)
            audio_path = permanent_path
        except Exception as e:
            print(f"Could not rename audio file: {e}")
            # Keep original path if rename fails

        # Create task entry for video generation
        task_info = {
            "id": task_id,
            "status": "analyzed",
            "audio_path": str(audio_path),
            "duration": duration,
            "song_structure": song_structure,
            "progress": "Audio analyzed, ready for storyboard generation",
            "storyboard": [],
            "video_url": None
        }
        active_tasks[task_id] = task_info

        return {
            "status": "success",
            "task_id": task_id,  # Return task_id for frontend to use
            "audio_path": str(audio_path),  # Return audio path for reference
            "duration": duration,
            "song_structure": song_structure,
            "lyrics_data": lyrics_data,
            "analysis_data": {
                "tempo": music_data.get('tempo', 120),
                "overall_energy": music_data.get('overall_energy', 0.5),
                "overall_mood": music_data.get('overall_mood', 'neutral'),
                "segments_detected": len(segments),
                "lyrics_detected": lyrics_data.get('has_lyrics', False)
            }
        }

    except Exception as e:
        # Clean up temporary file on error
        try:
            audio_path.unlink()
        except:
            pass

        print(f"Error analyzing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")

@app.websocket("/ws/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """Real-time progress updates with enhanced scene regeneration events"""
    await websocket.accept()

    try:
        while True:
            if task_id not in active_tasks:
                await websocket.send_json({"error": "Task not found"})
                break

            task_info = active_tasks[task_id]

            # Send enhanced progress updates with generation error info
            progress_data = {
                "task_id": task_id,
                "status": task_info.get("status", "unknown"),
                "progress": task_info.get("progress", ""),
                "storyboard": task_info.get("storyboard", []),
                "video_url": task_info.get("video_url"),
                "timestamp": asyncio.get_event_loop().time(),
                # Generation statistics for error visibility
                "generation_stats": {
                    "successful_scenes": task_info.get("successful_scenes", 0),
                    "failed_scenes": task_info.get("failed_scenes", 0),
                    "total_scenes": task_info.get("total_scenes", 0),
                },
                "generation_errors": task_info.get("generation_errors", []),
            }

            # Add scene regeneration specific events
            if "regenerating_scene" in task_info:
                progress_data["scene_regeneration"] = {
                    "scene_index": task_info["regenerating_scene"],
                    "status": task_info.get("regeneration_status", "in_progress"),
                    "provider": task_info.get("regeneration_provider", "auto")
                }

            await websocket.send_json(progress_data)

            if task_info["status"] in ["complete", "error"]:
                break

            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/api/download/{video_id}")
async def download_video(video_id: str):
    """Download generated video"""
    video_path = OUTPUT_DIR / f"{video_id}.mp4"

    # Check standard path first, then fall back to task's stored output_path
    if not video_path.exists():
        # Strip _animation suffix to find the task ID
        task_id = video_id.replace("_animation", "")
        task = active_tasks.get(task_id) or active_tasks.get(video_id)
        if task and task.get("output_path"):
            output_path = Path(task["output_path"])
            if output_path.exists():
                return FileResponse(
                    str(output_path),
                    media_type="video/mp4",
                    filename=f"beatcanvas_{video_id}.mp4"
                )
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(video_path, media_type="video/mp4", filename=f"beatcanvas_{video_id}.mp4")

@app.get("/api/references")
async def get_references():
    """Get information about uploaded references"""
    try:
        from src.assets.reference_manager import ReferenceManager

        ref_manager = ReferenceManager()
        return ref_manager.get_reference_info()

    except Exception as e:
        return {"error": f"Failed to get references: {str(e)}"}

class RegenerateSceneRequest(BaseModel):
    task_id: str
    scene_index: int
    new_description: str
    provider: str = "auto"
    effects: List[str] = []

class CulturalProcessingRequest(BaseModel):
    task_id: str
    cultural_standard: str  # "european", "american", "conservative"
    scene_contexts: List[str] = []  # Optional context for each scene
    require_user_approval: bool = True

class CulturalAnalysisRequest(BaseModel):
    image_path: str
    cultural_standard: str = "american"
    scene_context: str = ""

@app.post("/api/regenerate-scene")
async def regenerate_scene(request: RegenerateSceneRequest):
    """Regenerate images for a specific scene with new prompt"""

    if request.task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[request.task_id]

    if "storyboard" not in task or not isinstance(task["storyboard"], list):
        raise HTTPException(status_code=400, detail="No storyboard found for task")

    if request.scene_index < 0 or request.scene_index >= len(task["storyboard"]):
        raise HTTPException(status_code=400, detail="Invalid scene index")

    # Start regeneration in background to avoid blocking
    asyncio.create_task(regenerate_scene_pipeline(request.task_id, request.scene_index, request.new_description, request.provider, request.effects))

    return {
        "task_id": request.task_id,
        "scene_index": request.scene_index,
        "status": "regenerating",
        "message": f"Scene {request.scene_index + 1} regeneration started"
    }

async def regenerate_scene_pipeline(task_id: str, scene_index: int, new_description: str, provider: str, effects: list):
    """Background pipeline for scene regeneration with WebSocket updates"""
    try:
        from src.assets.generator import MultiProviderImageGenerator

        task = active_tasks[task_id]
        scene = task["storyboard"][scene_index]
        original_description = scene.get("description", "")

        # Update WebSocket status
        task["regenerating_scene"] = scene_index
        task["regeneration_status"] = "started"
        task["regeneration_provider"] = provider
        task["progress"] = f"Regenerating scene {scene_index + 1} with new prompt..."

        # Update scene in storyboard
        scene["description"] = new_description
        scene["image_prompt"] = new_description
        scene["effects"] = effects

        # Generate new images for this scene
        task["regeneration_status"] = "generating"
        task["progress"] = f"Generating new images for scene {scene_index + 1}..."

        image_generator = MultiProviderImageGenerator()
        timestamp = scene["timestamp_start"]

        # Use the existing regenerate function
        new_images = await image_generator.regenerate_scene_image(
            timestamp,
            new_description,
            provider
        )

        if new_images:
            # Update scene with new image paths
            scene["images"] = [img.image_path for img in new_images]
            scene["selected_image"] = 0  # Default to first new image

            # Update task status
            task["storyboard"][scene_index] = scene
            task["regeneration_status"] = "complete"
            task["progress"] = f"Scene {scene_index + 1} regenerated successfully"

            # Calculate estimated cost
            provider_costs = {"dalle": 0.08, "novelai": 0.06, "nano_banana": 0.04, "auto": 0.04}
            estimated_cost = provider_costs.get(provider, 0.04)

            # Store regeneration result for API response
            task["last_regeneration"] = {
                "scene_index": scene_index,
                "status": "complete",
                "new_images": [img.image_path for img in new_images],
                "provider_used": new_images[0].provider if new_images else provider,
                "estimated_cost": estimated_cost,
                "updated_scene": scene
            }

            print(f"Scene {scene_index} regenerated successfully for task {task_id}")

        else:
            # Restore original description if generation failed
            scene["description"] = original_description
            scene["image_prompt"] = original_description
            task["regeneration_status"] = "error"
            task["progress"] = f"Failed to regenerate scene {scene_index + 1}"

    except Exception as e:
        # Restore original scene data on error
        task = active_tasks.get(task_id, {})
        if "storyboard" in task and scene_index < len(task["storyboard"]):
            scene = task["storyboard"][scene_index]
            if "original_description" in locals():
                scene["description"] = original_description
                scene["image_prompt"] = original_description

        task["regeneration_status"] = "error"
        task["progress"] = f"Scene regeneration error: {str(e)}"
        print(f"Scene regeneration error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up regeneration status
        if "regenerating_scene" in task:
            del task["regenerating_scene"]

@app.get("/api/regeneration-status/{task_id}")
async def get_regeneration_status(task_id: str):
    """Get the status of the last scene regeneration"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]

    # Check if regeneration is in progress
    if "regenerating_scene" in task:
        return {
            "task_id": task_id,
            "status": "in_progress",
            "scene_index": task["regenerating_scene"],
            "regeneration_status": task.get("regeneration_status", "started"),
            "provider": task.get("regeneration_provider", "auto"),
            "progress": task.get("progress", "Processing...")
        }

    # Check for completed regeneration result
    if "last_regeneration" in task:
        result = task["last_regeneration"]
        # Clear the result after returning it
        del task["last_regeneration"]
        return {
            "task_id": task_id,
            "status": "complete",
            **result
        }

    return {
        "task_id": task_id,
        "status": "no_regeneration",
        "message": "No recent regeneration activity"
    }

@app.post("/api/analyze-cultural-content")
async def analyze_cultural_content(request: CulturalAnalysisRequest):
    """Analyze image content for cultural sensitivity"""

    try:
        from src.content.cultural_processor import CulturalContentProcessor, CulturalStandard

        processor = CulturalContentProcessor()

        # Convert string to enum
        standard = CulturalStandard(request.cultural_standard)

        # Analyze the image
        analysis = await processor.analyze_scene_content(request.image_path)

        # Determine if modification is needed
        needs_modification = processor._should_modify_content(
            analysis, standard, request.scene_context
        )

        return {
            "analysis": {
                "has_content_to_modify": analysis.has_clothing_to_modify,
                "confidence": analysis.confidence,
                "suggested_modification": analysis.suggested_modification.value,
                "regions": analysis.regions,
                "description": analysis.description
            },
            "cultural_standard": request.cultural_standard,
            "needs_modification": needs_modification,
            "scene_context": request.scene_context
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cultural analysis failed: {str(e)}")

@app.post("/api/process-cultural-content")
async def process_cultural_content(request: CulturalProcessingRequest):
    """Process entire storyboard for cultural compliance"""

    if request.task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[request.task_id]

    if "storyboard" not in task:
        raise HTTPException(status_code=400, detail="No storyboard found for task")

    try:
        from src.content.cultural_processor import CulturalContentProcessor, CulturalStandard

        processor = CulturalContentProcessor()
        standard = CulturalStandard(request.cultural_standard)

        # Collect image paths from storyboard
        storyboard = task["storyboard"]
        image_paths = []

        for scene in storyboard:
            if "images" in scene and scene["images"]:
                # Use selected image or first image
                selected_idx = scene.get("selected_image", 0)
                if selected_idx < len(scene["images"]):
                    image_paths.append(scene["images"][selected_idx])
                else:
                    image_paths.append(scene["images"][0])
            else:
                # Skip scenes without images
                continue

        if not image_paths:
            raise HTTPException(status_code=400, detail="No images found in storyboard")

        # Process all images
        results = await processor.batch_process_storyboard(
            image_paths,
            standard,
            request.scene_contexts
        )

        # Generate processing report
        report = processor.generate_modification_report(results)

        # Update storyboard with modified images if not requiring user approval
        if not request.require_user_approval:
            scene_idx = 0
            for i, scene in enumerate(storyboard):
                if "images" in scene and scene["images"] and scene_idx < len(results):
                    result = results[scene_idx]

                    # Update with modified image path
                    if result.modified_path != result.original_path:
                        scene["cultural_modified_image"] = result.modified_path
                        scene["cultural_standard"] = request.cultural_standard

                    scene_idx += 1

        return {
            "task_id": request.task_id,
            "cultural_standard": request.cultural_standard,
            "processing_report": report,
            "results": [
                {
                    "original_path": r.original_path,
                    "modified_path": r.modified_path,
                    "modifications_applied": [m.value for m in r.modifications_applied],
                    "confidence": r.analysis.confidence,
                    "description": r.analysis.description,
                    "user_approval_required": request.require_user_approval and "no_change" not in [m.value for m in r.modifications_applied]
                }
                for r in results
            ],
            "user_approval_required": request.require_user_approval and report["user_approval_required"] > 0,
            "message": f"Processed {len(results)} scenes for {request.cultural_standard} standards"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cultural processing failed: {str(e)}")

@app.post("/api/approve-cultural-modifications")
async def approve_cultural_modifications(task_id: str, approved_scenes: List[int]):
    """Apply approved cultural modifications to storyboard"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]
    storyboard = task.get("storyboard", [])

    try:
        applied_count = 0

        for scene_idx in approved_scenes:
            if scene_idx < len(storyboard):
                scene = storyboard[scene_idx]

                # Apply cultural modification if available
                if "cultural_modified_image" in scene:
                    # Backup original
                    if "images" in scene and scene["images"]:
                        scene["original_images"] = scene["images"].copy()

                    # Replace with modified image
                    scene["images"] = [scene["cultural_modified_image"]]
                    scene["selected_image"] = 0
                    scene["cultural_approved"] = True

                    applied_count += 1

        return {
            "task_id": task_id,
            "approved_scenes": approved_scenes,
            "applied_modifications": applied_count,
            "message": f"Applied cultural modifications to {applied_count} scenes"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply modifications: {str(e)}")

@app.post("/api/rebuild-video")
async def rebuild_video_with_changes(task_id: str):
    """Rebuild video after scene changes"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]

    if "storyboard" not in task:
        raise HTTPException(status_code=400, detail="No storyboard found for task")

    try:
        # Start video rebuild in background
        asyncio.create_task(rebuild_video_pipeline(task_id))

        return {
            "task_id": task_id,
            "status": "rebuilding",
            "message": "Video rebuild started in background"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start video rebuild: {str(e)}")

# Background pipeline functions
async def analyze_and_storyboard_pipeline(task_id: str, audio_path: str, content_prompt: str, style_prompt: str, quality_tier: str):
    """Background task for audio analysis and storyboard creation only"""
    try:
        from src.audio.analyzer import MusicAnalyzer
        from src.storyboard.conceptor import ConceptGenerator
        from src.storyboard.generator import StoryboardGenerator

        task = active_tasks[task_id]

        # Phase 1: Audio Analysis
        task["progress"] = "Analyzing music structure and extracting features..."
        analyzer = MusicAnalyzer()
        music_data = analyzer.analyze_song(audio_path)
        await asyncio.sleep(1)  # Allow UI update

        # Phase 2: Concept Generation
        task["progress"] = "Generating visual concept based on music and prompts..."
        conceptor = ConceptGenerator()

        # Combine content and style prompts
        combined_prompt = f"{content_prompt}. Visual style: {style_prompt}"
        visual_concept = conceptor.generate_concept(music_data, combined_prompt)
        await asyncio.sleep(1)

        # Phase 3: Storyboard Creation
        task["progress"] = "Creating detailed scene-by-scene storyboard..."
        storyboard_gen = StoryboardGenerator()

        # Determine scene count based on quality tier
        scene_counts = {"basic": 12, "professional": 24, "cinematic": 48}
        target_scenes = scene_counts.get(quality_tier, 24)

        # Get optimal scene timings
        scene_timings = analyzer.get_scene_timings(music_data, target_scenes)

        # Generate storyboard
        storyboard_scenes = storyboard_gen.create_storyboard(music_data, visual_concept, scene_timings)
        storyboard_dict = storyboard_gen.scenes_to_dict_list(storyboard_scenes)

        # Complete analysis phase
        task["status"] = "storyboard_ready"
        task["progress"] = f"Storyboard created with {len(storyboard_dict)} scenes. Ready for review."
        task["storyboard"] = storyboard_dict
        task["music_data"] = music_data  # Store for later use

        print(f"Analysis and storyboard completed for task {task_id}")

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Analysis error: {str(e)}"
        print(f"Analysis pipeline error: {e}")
        import traceback
        traceback.print_exc()

async def generate_images_and_video_pipeline(task_id: str, approved_storyboard: List[dict]):
    """Background task for image generation and video assembly"""
    try:
        from src.assets.generator import MultiProviderImageGenerator
        from src.video.assembler import VideoAssembler

        task = active_tasks[task_id]
        audio_path = task["audio_path"]

        # Phase 1: Image Generation
        task["progress"] = "Generating AI images for each scene..."
        task["total_scenes"] = len(approved_storyboard)
        image_generator = MultiProviderImageGenerator()

        # Generate images for all scenes
        scene_assets = await image_generator.generate_all_scenes(approved_storyboard, "auto")

        # Track generation statistics for frontend visibility
        successful_scenes = 0
        failed_scenes = 0
        generation_errors = []

        # Update storyboard with image URLs and track errors
        for i, scene_dict in enumerate(approved_storyboard):
            timestamp = scene_dict['timestamp_start']
            if timestamp in scene_assets:
                images = scene_assets[timestamp]
                if images:
                    scene_dict['images'] = [img.image_path for img in images]
                    scene_dict['selected_image'] = 0
                    successful_scenes += 1
                else:
                    scene_dict['images'] = []
                    failed_scenes += 1
                    generation_errors.append({
                        "scene_index": i,
                        "timestamp": timestamp,
                        "section": scene_dict.get('section', 'Scene'),
                        "error": "No images generated"
                    })
            else:
                scene_dict['images'] = []
                failed_scenes += 1

        # Update task with generation statistics
        task["storyboard"] = approved_storyboard
        task["successful_scenes"] = successful_scenes
        task["failed_scenes"] = failed_scenes
        task["generation_errors"] = generation_errors

        total_images = sum(len(assets) for assets in scene_assets.values())
        if failed_scenes > 0:
            task["progress"] = f"Generated {total_images} images ({successful_scenes}/{len(approved_storyboard)} scenes, {failed_scenes} failed)"
        else:
            task["progress"] = f"Generated {total_images} images for {successful_scenes} scenes"
        await asyncio.sleep(1)

        # Phase 2: Video Assembly
        task["progress"] = "Assembling final video with music synchronization..."
        assembler = VideoAssembler()

        # Create final video
        video_path = assembler.create_video(audio_path, scene_assets, approved_storyboard, task_id)

        # Complete
        task["status"] = "complete"
        task["progress"] = "Video generation complete! Ready to download."
        task["video_url"] = f"/api/download/{task_id}"

        print(f"Video generation completed successfully: {video_path}")

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Generation error: {str(e)}"
        print(f"Generation pipeline error: {e}")
        import traceback
        traceback.print_exc()

async def generate_video_pipeline(task_id: str, audio_path: str, visual_prompt: str, quality_tier: str):
    """Background task for video generation pipeline (original endpoint)"""
    try:
        from src.audio.analyzer import MusicAnalyzer
        from src.storyboard.conceptor import ConceptGenerator
        from src.storyboard.generator import StoryboardGenerator
        from src.assets.generator import MultiProviderImageGenerator
        from src.video.assembler import VideoAssembler

        task = active_tasks[task_id]

        # Phase 1: Audio Analysis
        task["progress"] = "Analyzing music structure and extracting features..."
        analyzer = MusicAnalyzer()
        music_data = analyzer.analyze_song(audio_path)
        await asyncio.sleep(1)  # Allow UI update

        # Phase 2: Concept Generation
        task["progress"] = "Generating visual concept based on music and prompt..."
        conceptor = ConceptGenerator()
        visual_concept = conceptor.generate_concept(music_data, visual_prompt)
        await asyncio.sleep(1)

        # Phase 3: Storyboard Creation
        task["progress"] = "Creating detailed scene-by-scene storyboard..."
        storyboard_gen = StoryboardGenerator()

        # Determine scene count based on quality tier
        scene_counts = {"basic": 12, "professional": 24, "cinematic": 48}
        target_scenes = scene_counts.get(quality_tier, 24)

        # Get optimal scene timings
        scene_timings = analyzer.get_scene_timings(music_data, target_scenes)

        # Generate storyboard
        storyboard_scenes = storyboard_gen.create_storyboard(music_data, visual_concept, scene_timings)
        storyboard_dict = storyboard_gen.scenes_to_dict_list(storyboard_scenes)

        task["storyboard"] = storyboard_dict
        await asyncio.sleep(1)

        # Phase 4: Video/Image Generation
        if USE_ANIMATEDIFF:
            print(f"[DEBUG] Phase 4: AnimateDiff mode enabled, {len(storyboard_dict)} scenes")
            task["progress"] = "Generating AnimateDiff videos for each scene..."
            task["total_scenes"] = len(storyboard_dict)
            from src.video.animatediff_pipeline import AnimateDiffPipeline

            print(f"[DEBUG] Initializing AnimateDiffPipeline (fps=8, interpolate=False - no blur)")
            video_pipeline = AnimateDiffPipeline(
                # Use defaults: 8 FPS, no interpolation for clearer frames
                heartbeat_callback=None
            )

            # Generate video clips for all scenes
            print(f"[DEBUG] Starting generate_all_scenes() for {len(storyboard_dict)} scenes")
            video_results = video_pipeline.generate_all_scenes(storyboard_dict)
            print(f"[DEBUG] generate_all_scenes() complete, got {len(video_results)} results")
            print(f"[DEBUG] Cleaning up pipeline resources")
            video_pipeline.cleanup()

            # Create video_clips_map for enhanced assembler (timestamp -> video_path)
            print(f"[DEBUG] Building video_clips_map from {len(video_results)} results")
            video_clips_map = {}
            for i, scene_dict in enumerate(storyboard_dict):
                timestamp = scene_dict['timestamp_start']
                if i in video_results and 'video_path' in video_results[i]:
                    video_clips_map[timestamp] = video_results[i]['video_path']
                    print(f"[DEBUG]   Scene {i}: {timestamp:.2f}s -> {video_results[i]['video_path']}")
                else:
                    print(f"[DEBUG]   Scene {i}: MISSING video result")

            print(f"[DEBUG] video_clips_map has {len(video_clips_map)} entries")
            # Empty scene_assets since we're using pure video (no images)
            scene_assets = {}

        else:
            task["progress"] = "Generating AI images for each scene..."
            task["total_scenes"] = len(storyboard_dict)
            image_generator = MultiProviderImageGenerator()

            # Generate images for all scenes (legacy)
            scene_assets = await image_generator.generate_all_scenes(storyboard_dict, "auto")

            # No video clips in legacy mode
            video_clips_map = {}

        # Track generation statistics for frontend visibility
        successful_scenes = 0
        failed_scenes = 0
        generation_errors = []

        # Update storyboard with image URLs
        for i, scene_dict in enumerate(storyboard_dict):
            timestamp = scene_dict['timestamp_start']
            if timestamp in scene_assets:
                images = scene_assets[timestamp]
                if images:
                    scene_dict['images'] = [img.image_path for img in images]
                    scene_dict['selected_image'] = 0
                    successful_scenes += 1
                else:
                    scene_dict['images'] = []
                    failed_scenes += 1
                    generation_errors.append({
                        "scene_index": i,
                        "timestamp": timestamp,
                        "section": scene_dict.get('section', 'Scene'),
                        "error": "No images generated"
                    })
            else:
                scene_dict['images'] = []
                failed_scenes += 1

        task["storyboard"] = storyboard_dict
        task["successful_scenes"] = successful_scenes
        task["failed_scenes"] = failed_scenes
        task["generation_errors"] = generation_errors

        total_images = sum(len(assets) for assets in scene_assets.values())
        if failed_scenes > 0:
            task["progress"] = f"Generated {total_images} images ({successful_scenes}/{len(storyboard_dict)} scenes, {failed_scenes} failed)"
        else:
            task["progress"] = f"Generated {total_images} images for all {successful_scenes} scenes"
        await asyncio.sleep(1)

        # Phase 5: Video Assembly
        print(f"[DEBUG] Phase 5: Starting video assembly")
        task["progress"] = "Assembling final video with music synchronization..."
        assembler = VideoAssembler()

        # Create final video
        if USE_ANIMATEDIFF:
            print(f"[DEBUG] Using create_video_enhanced with {len(video_clips_map)} video clips")
            # Use enhanced assembler for video clips
            video_path = assembler.create_video_enhanced(
                audio_path,
                scene_assets,
                video_clips_map,
                storyboard_dict,
                task_id
            )
            print(f"[DEBUG] create_video_enhanced complete: {video_path}")
        else:
            # Legacy: static images with Ken Burns effects
            video_path = assembler.create_video(audio_path, scene_assets, storyboard_dict, task_id)

        # Complete
        task["status"] = "complete"
        task["progress"] = "Video generation complete! Ready to download."
        task["video_url"] = f"/api/download/{task_id}"

        print(f"Video generation completed successfully: {video_path}")

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Error: {str(e)}"
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()

async def rebuild_video_pipeline(task_id: str):
    """Background task for rebuilding video after scene changes"""
    try:
        from src.video.assembler import VideoAssembler

        task = active_tasks[task_id]
        audio_path = task["audio_path"]
        storyboard = task["storyboard"]

        # Update task status
        task["status"] = "rebuilding"
        task["progress"] = "Rebuilding video with updated scenes..."

        # Create scene assets dict from updated storyboard
        scene_assets = {}
        for scene in storyboard:
            timestamp = scene["timestamp_start"]
            if "images" in scene and scene["images"]:
                # Create mock GeneratedImage objects for existing images
                from src.assets.generator import GeneratedImage
                images = []
                for i, image_path in enumerate(scene["images"]):
                    if os.path.exists(image_path):
                        generated_img = GeneratedImage(
                            scene_timestamp=timestamp,
                            image_path=image_path,
                            provider="unknown",
                            prompt=scene.get("description", ""),
                            variation_index=i
                        )
                        images.append(generated_img)
                scene_assets[timestamp] = images

        # Assemble video with updated scenes
        assembler = VideoAssembler()
        video_path = assembler.create_video(audio_path, scene_assets, storyboard, f"{task_id}_updated")

        # Complete
        task["status"] = "complete"
        task["progress"] = "Video rebuild complete!"
        task["video_url"] = f"/api/download/{task_id}_updated"

        print(f"Video rebuild completed successfully: {video_path}")

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Rebuild error: {str(e)}"
        print(f"Video rebuild error: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/export-davinci/{task_id}")
async def export_davinci_project(task_id: str):
    """Export DaVinci Resolve project file for professional post-processing"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = active_tasks[task_id]

    if task_info.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Video generation not complete")

    try:
        from src.video.assembler import VideoAssembler
        assembler = VideoAssembler()

        # Get the required data
        storyboard_dict = task_info.get("storyboard", [])
        scene_assets = task_info.get("scene_assets", {})
        audio_path = task_info.get("audio_file")

        # Create DaVinci project
        project_file = assembler.create_davinci_project(storyboard_dict, scene_assets, audio_path, task_id)

        return {
            "task_id": task_id,
            "project_file": project_file,
            "download_url": f"/api/download-project/{task_id}",
            "message": "DaVinci Resolve project exported successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/download-project/{task_id}")
async def download_project(task_id: str):
    """Download DaVinci Resolve project file"""
    project_file = Path("output") / f"{task_id}_davinci.json"

    if not project_file.exists():
        raise HTTPException(status_code=404, detail="Project file not found")

    return FileResponse(
        path=str(project_file),
        filename=f"BeatCanvas_{task_id}_DaVinci.json",
        media_type="application/json"
    )

class CinematicModeRequest(BaseModel):
    enabled: bool = True
    film_grain: float = 0.5  # 0.0 to 1.0
    color_grade_intensity: float = 0.7  # 0.0 to 1.0
    vignette_strength: float = 0.3  # 0.0 to 1.0

class StoryboardExportRequest(BaseModel):
    task_id: str
    format: str = "json"  # "json" or "markdown"
    include_images: bool = False  # Whether to include image paths

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get current status of a generation task (for debugging without WebSocket)"""
    if task_id in active_tasks:
        task = active_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.get("status", "unknown"),
            "progress": task.get("progress", ""),
            "storyboard_scenes": len(task.get("storyboard", [])),
            "video_url": task.get("video_url"),
            "error": task.get("error")
        }
    return {"error": "Task not found", "task_id": task_id}

@app.get("/api/export-storyboard/{task_id}")
async def export_storyboard(task_id: str, format: str = "json", include_images: bool = False):
    """
    Export storyboard data as JSON (for re-import) or Markdown (for customers).

    JSON format includes:
    - Original narrative/concept
    - Song structure and timing
    - Section breakdown with prompts
    - Style notes for each scene
    - Metadata for re-import

    Markdown format provides:
    - Human-readable document for customers
    - Can be converted to PDF/Word
    """
    from datetime import datetime

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]
    storyboard = task.get("storyboard", [])

    if not storyboard:
        raise HTTPException(status_code=400, detail="No storyboard found for this task")

    # Build export data structure
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "task_id": task_id,
        "metadata": {
            "audio_file": Path(task.get("audio_path", "")).name if task.get("audio_path") else None,
            "duration": task.get("duration", 0),
            "quality_tier": task.get("quality_tier", "professional"),
            "total_scenes": len(storyboard),
        },
        "narrative": {
            "user_concept": task.get("content_prompt", task.get("visual_prompt", "")),
            "style_prompt": task.get("style_prompt", ""),
        },
        "song_structure": task.get("song_structure", []),
        "scenes": []
    }

    # Build scene data
    for i, scene in enumerate(storyboard):
        scene_data = {
            "index": i,
            "section": scene.get("section", f"Scene {i+1}"),
            "timestamp_start": scene.get("timestamp_start", 0),
            "timestamp_end": scene.get("timestamp_end", 0),
            "prompt": scene.get("image_prompt", scene.get("description", "")),
            "visual_style": scene.get("visual_style", ""),
            "mood": scene.get("mood", ""),
            "lighting": scene.get("lighting", ""),
            "color_palette": scene.get("color_palette", ""),
            "style_notes": scene.get("style_notes", ""),
        }

        if include_images and scene.get("images"):
            scene_data["images"] = scene.get("images", [])
            scene_data["selected_image"] = scene.get("selected_image", 0)

        export_data["scenes"].append(scene_data)

    if format.lower() == "markdown":
        # Generate Markdown document
        md_content = _generate_storyboard_markdown(export_data)

        # Return as downloadable markdown file
        from fastapi.responses import Response
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="storyboard_{task_id[:8]}.md"'
            }
        )
    else:
        # Return JSON (default)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f'attachment; filename="storyboard_{task_id[:8]}.json"'
            }
        )

def _generate_storyboard_markdown(export_data: dict) -> str:
    """Generate a human-readable Markdown document from storyboard data."""

    lines = []

    # Title and header
    lines.append("# BeatCanvas Music Video Storyboard")
    lines.append("")
    lines.append(f"**Generated:** {export_data['exported_at']}")

    if export_data['metadata'].get('audio_file'):
        lines.append(f"**Audio:** {export_data['metadata']['audio_file']}")

    duration = export_data['metadata'].get('duration', 0)
    if duration:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        lines.append(f"**Duration:** {minutes}:{seconds:02d}")

    lines.append(f"**Total Scenes:** {export_data['metadata']['total_scenes']}")
    lines.append("")

    # Original Narrative/Concept
    lines.append("---")
    lines.append("")
    lines.append("## Original Narrative")
    lines.append("")

    user_concept = export_data['narrative'].get('user_concept', '')
    if user_concept:
        lines.append(f"> {user_concept}")
    else:
        lines.append("*No narrative concept provided*")
    lines.append("")

    style_prompt = export_data['narrative'].get('style_prompt', '')
    if style_prompt:
        lines.append(f"**Visual Style:** {style_prompt}")
        lines.append("")

    # Song Structure Overview
    if export_data.get('song_structure'):
        lines.append("---")
        lines.append("")
        lines.append("## Song Structure")
        lines.append("")
        lines.append("| Section | Start | End | Duration |")
        lines.append("|---------|-------|-----|----------|")

        for section in export_data['song_structure']:
            start = section.get('start', 0)
            end = section.get('end', 0)
            duration = end - start

            start_str = f"{int(start//60)}:{int(start%60):02d}"
            end_str = f"{int(end//60)}:{int(end%60):02d}"
            dur_str = f"{duration:.1f}s"

            lines.append(f"| {section.get('name', 'Unknown')} | {start_str} | {end_str} | {dur_str} |")

        lines.append("")

    # Scene-by-Scene Breakdown
    lines.append("---")
    lines.append("")
    lines.append("## Scene-by-Scene Breakdown")
    lines.append("")

    current_section = None
    for scene in export_data['scenes']:
        section = scene.get('section', '')

        # Add section header if changed
        if section != current_section:
            current_section = section
            lines.append(f"### {section}")
            lines.append("")

        # Scene timing
        start = scene.get('timestamp_start', 0)
        end = scene.get('timestamp_end', 0)
        start_str = f"{int(start//60)}:{int(start%60):02d}"
        end_str = f"{int(end//60)}:{int(end%60):02d}"

        lines.append(f"**Scene {scene['index'] + 1}** ({start_str} - {end_str})")
        lines.append("")

        # Scene prompt
        prompt = scene.get('prompt', '')
        if prompt:
            lines.append(f"> {prompt}")
            lines.append("")

        # Visual details in a compact format
        details = []
        if scene.get('mood'):
            details.append(f"**Mood:** {scene['mood']}")
        if scene.get('lighting'):
            details.append(f"**Lighting:** {scene['lighting']}")
        if scene.get('color_palette'):
            details.append(f"**Colors:** {scene['color_palette']}")

        if details:
            lines.append(" | ".join(details))
            lines.append("")

        if scene.get('style_notes'):
            lines.append(f"*{scene['style_notes']}*")
            lines.append("")

        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by BeatCanvas - AI-Powered Music Video Creation*")
    lines.append("")

    return "\n".join(lines)

@app.post("/api/import-storyboard")
async def import_storyboard(storyboard_json: dict):
    """
    Import a previously exported storyboard JSON to recreate a video project.

    This allows users to:
    1. Re-use their carefully crafted prompts with different audio
    2. Continue editing a previous project
    3. Share storyboard templates with others
    """

    # Validate the import format
    if "version" not in storyboard_json or "scenes" not in storyboard_json:
        raise HTTPException(status_code=400, detail="Invalid storyboard format. Must be a BeatCanvas export file.")

    # Create a new task for this imported storyboard
    task_id = str(uuid.uuid4())

    # Reconstruct the storyboard from the import
    imported_scenes = []
    for scene_data in storyboard_json.get("scenes", []):
        scene = {
            "timestamp_start": scene_data.get("timestamp_start", 0),
            "timestamp_end": scene_data.get("timestamp_end", 0),
            "section": scene_data.get("section", "Scene"),
            "description": scene_data.get("prompt", ""),
            "image_prompt": scene_data.get("prompt", ""),
            "visual_style": scene_data.get("visual_style", "cinematic"),
            "mood": scene_data.get("mood", ""),
            "lighting": scene_data.get("lighting", ""),
            "color_palette": scene_data.get("color_palette", ""),
            "style_notes": scene_data.get("style_notes", ""),
            "images": [],  # Will need to regenerate images
            "selected_image": 0
        }
        imported_scenes.append(scene)

    # Create task entry
    task_info = {
        "id": task_id,
        "status": "imported",
        "audio_path": None,  # User will need to provide audio
        "content_prompt": storyboard_json.get("narrative", {}).get("user_concept", ""),
        "style_prompt": storyboard_json.get("narrative", {}).get("style_prompt", ""),
        "quality_tier": storyboard_json.get("metadata", {}).get("quality_tier", "professional"),
        "duration": storyboard_json.get("metadata", {}).get("duration", 0),
        "song_structure": storyboard_json.get("song_structure", []),
        "progress": "Storyboard imported. Upload audio to generate video.",
        "storyboard": imported_scenes,
        "video_url": None,
        "imported_from": storyboard_json.get("task_id", "unknown"),
        "imported_at": storyboard_json.get("exported_at", "")
    }

    active_tasks[task_id] = task_info

    return {
        "task_id": task_id,
        "status": "imported",
        "scenes_imported": len(imported_scenes),
        "original_task": storyboard_json.get("task_id"),
        "narrative": task_info["content_prompt"][:100] + "..." if len(task_info["content_prompt"]) > 100 else task_info["content_prompt"],
        "message": f"Successfully imported {len(imported_scenes)} scenes. Upload audio to continue."
    }

@app.post("/api/set-cinematic-mode/{task_id}")
async def set_cinematic_mode(task_id: str, settings: CinematicModeRequest):
    """Configure cinematic post-processing settings"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    # Store cinematic settings for this task
    active_tasks[task_id]["cinematic_settings"] = settings.dict()

    return {
        "task_id": task_id,
        "cinematic_mode": settings.enabled,
        "settings": settings.dict(),
        "message": "Cinematic processing settings updated"
    }

# ============================================================================
# RunPod Hybrid WAN + SkyReels API Endpoints (Phase 9)
# These endpoints run ON the RunPod pod, not locally
# ============================================================================

class GenerateWANSceneRequest(BaseModel):
    prompt: str
    scene_index: int
    audio_segment: Optional[str] = None
    resolution: str = "720p"
    fps: int = 24
    duration: float = 5.0

class StitchSkyReelsRequest(BaseModel):
    scene_urls: List[str]
    audio_url: str
    method: str = "diffusion_forcing"
    output_fps: int = 24

@app.post("/api/generate-wan")
async def generate_wan_scene(request: GenerateWANSceneRequest):
    """
    Generate single scene with WAN 2.6 (RunPod endpoint).
    This endpoint runs ON the RunPod pod, not locally.
    """
    try:
        from src.cinematography.wan26_cloud_generator import WAN26CloudGenerator

        generator = WAN26CloudGenerator()

        # Generate scene video
        video_path = await generator.generate_scene(
            prompt=request.prompt,
            scene_index=request.scene_index,
            audio_segment=request.audio_segment,
            resolution=request.resolution,
            fps=request.fps,
            duration=request.duration
        )

        # Return video URL (accessible via RunPod proxy)
        return {
            "video_url": f"/videos/{Path(video_path).name}",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WAN generation failed: {str(e)}")

@app.post("/api/stitch-skyreels")
async def stitch_skyreels(request: StitchSkyReelsRequest):
    """
    Stitch scenes into seamless video using SkyReels V2 DF (RunPod endpoint).
    This endpoint runs ON the RunPod pod, not locally.
    """
    try:
        from src.cinematography.skyreels_df_generator import SkyReelsDFGenerator

        generator = SkyReelsDFGenerator()

        # Convert URLs to local paths (assuming videos are already on RunPod)
        scene_paths = [url.replace("/videos/", "output/") for url in request.scene_urls]
        audio_path = request.audio_url.replace("/audio/", "data/uploads/")

        # Generate stitched video
        output_path = f"output/stitched_{uuid.uuid4().hex}.mp4"
        final_video = generator.stitch_videos(
            video_clips=scene_paths,
            output_path=output_path,
            audio_path=audio_path,
            target_fps=request.output_fps
        )

        # Return final video URL
        return {
            "final_video_url": f"/videos/{Path(final_video).name}",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SkyReels stitching failed: {str(e)}")

@app.post("/api/upload-audio")
async def upload_audio(audio: UploadFile = File(...)):
    """
    Upload audio file to RunPod for hybrid pipeline.
    This endpoint runs ON the RunPod pod, not locally.
    """
    try:
        # Save uploaded audio
        audio_filename = f"audio_{uuid.uuid4().hex}{Path(audio.filename).suffix}"
        audio_path = UPLOAD_DIR / audio_filename

        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)

        return {
            "audio_url": f"/audio/{audio_filename}",
            "path": str(audio_path),
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio upload failed: {str(e)}")

# Serve generated images
app.mount("/data/generated_images", StaticFiles(directory=str(GENERATED_DIR)), name="generated_images")

# Serve React frontend static files
frontend_build_path = Path("../frontend/build")
if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build_path / "static")), name="static")

    @app.get("/")
    async def serve_frontend():
        """Serve the React frontend"""
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        # Fallback to test-ui.html
        test_ui_path = Path(__file__).parent.parent / "frontend" / "test-ui.html"
        if test_ui_path.exists():
            return FileResponse(str(test_ui_path))

        return {"message": "Frontend not built. Run 'npm run build' in frontend directory."}

    @app.get("/{path:path}")
    async def catch_all(path: str):
        """Catch all routes and serve React frontend for client-side routing"""
        # Don't serve the frontend for API routes
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        # Fallback to test-ui.html for all routes
        test_ui_path = Path(__file__).parent.parent / "frontend" / "test-ui.html"
        if test_ui_path.exists():
            return FileResponse(str(test_ui_path))

        return {"message": "Frontend not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=False)

# ============================================================================
# Animation Workflow Endpoints (Generic for ANY music video)
# ============================================================================

from pydantic import BaseModel
class AnimationProjectRequest(BaseModel):
    task_id: str
    audio_path: str
    animation_style: str
    protagonist_lora: Optional[str] = None
    supporting_loras: Optional[List[str]] = None
    scene_loras: Optional[List[str]] = None
    style_lora: Optional[str] = None
    quality_tier: str = "professional"
    use_stock_footage: bool = False
    fps: int = 24
    width: int = 1024
    height: int = 1024

@app.get("/api/animation/styles")
async def list_animation_styles():
    """List all 16 animation styles"""
    from src.animation.rotoscope_generator import ANIMATION_STYLES

    STYLE_CATEGORIES = {
        "tropical": ["watercolor", "impressionist", "synthwave", "ghibli", "paper_cutout", "oil_painting"],
        "rock": ["comic_book", "graffiti", "cel_shaded", "pencil_sketch", "neon"],
        "electronic": ["neon", "synthwave", "pixel_art", "pop_art"],
        "jazz_classical": ["art_deco", "oil_painting", "impressionist", "ukiyo_e"],
        "world_indie": ["ukiyo_e", "ghibli", "watercolor", "paper_cutout", "pencil_sketch"],
        "pop": ["cartoon", "pop_art", "cel_shaded", "comic_book"],
    }

    styles = []
    for name, config in ANIMATION_STYLES.items():
        styles.append({
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "description": config["prompt_suffix"],
            "best_for": config.get("best_for", "Various genres"),
            "guidance_scale": config.get("guidance_scale", 7.5),
            "conditioning_scale": config.get("controlnet_conditioning_scale", 0.75),
        })

    return {"styles": styles, "total": len(styles), "categories": STYLE_CATEGORIES}

@app.get("/api/animation/loras")
async def list_character_loras():
    """List available character LoRAs"""
    import yaml
    registry_path = Path("config/loras.yaml")
    
    if not registry_path.exists():
        return {"character_loras": [], "scene_loras": [], "style_loras": []}
    
    with open(registry_path, 'r') as f:
        registry = yaml.safe_load(f)
    
    character_loras = []
    scene_loras = []
    style_loras = []
    
    for name, config in registry.items():
        if not config.get('enabled', False):
            continue
        
        triggers = config.get("triggers", [])
        lora_info = {
            "name": name,
            "display_name": name.replace("-", " ").replace("_", " ").title(),
            "type": config.get("type"),
            "description": config.get("description", ""),
            "file": config.get("file", ""),
            "trigger": triggers[0] if triggers else None,
            "default_weight": config.get("default_weight", 0.8),
        }
        
        if config.get("type") == "character":
            character_loras.append(lora_info)
        elif config.get("type") == "scene":
            scene_loras.append(lora_info)
        elif config.get("type") == "style":
            style_loras.append(lora_info)
    
    return {
        "character_loras": character_loras,
        "scene_loras": scene_loras,
        "style_loras": style_loras
    }

@app.post("/api/animation/generate")
async def generate_animation_video(request: AnimationProjectRequest):
    """Generate animated music video"""
    try:
        from src.animation.animation_workflow import AnimationWorkflow, AnimationProjectConfig
        
        config = AnimationProjectConfig(
            project_name=f"project_{request.task_id[:8]}",
            audio_path=request.audio_path,
            animation_style=request.animation_style,
            quality_tier=request.quality_tier,
            protagonist_lora=request.protagonist_lora,
            supporting_loras=request.supporting_loras,
            scene_loras=request.scene_loras,
            style_lora=request.style_lora,
            use_stock_footage=request.use_stock_footage,
            fps=request.fps,
            width=request.width,
            height=request.height
        )
        
        # Run workflow in background
        asyncio.create_task(run_animation_workflow_bg(request.task_id, config))
        
        return {
            "task_id": request.task_id,
            "status": "started",
            "animation_style": request.animation_style
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_animation_workflow_bg(task_id: str, config):
    """Background animation workflow"""
    from src.animation.animation_workflow import AnimationWorkflow
    
    try:
        if task_id not in active_tasks:
            active_tasks[task_id] = {"id": task_id, "status": "animating"}
        
        task = active_tasks[task_id]
        task["progress"] = "Running animation workflow..."
        
        workflow = AnimationWorkflow()
        result = await workflow.run_workflow(config)
        
        if result.success:
            task["status"] = "complete"
            task["video_url"] = f"/api/download/{task_id}_animation"
            task["output_path"] = result.output_video_path
        else:
            task["status"] = "error"
            task["progress"] = f"Error: {result.error}"
    
    except Exception as e:
        active_tasks[task_id]["status"] = "error"
        active_tasks[task_id]["progress"] = str(e)

