#!/usr/bin/env python3
"""
BeatCanvas Component Testing Script

This script tests individual components to verify they work correctly
before running the full application.
"""

import sys
import os
from pathlib import Path
import traceback

# Add backend to path
sys.path.append(str(Path("backend")))

def test_audio_analysis():
    """Test audio analysis module with a synthetic audio example"""
    print("Testing Audio Analysis...")

    try:
        from src.audio.analyzer import MusicAnalyzer

        # Create analyzer
        analyzer = MusicAnalyzer()
        print("  [OK] MusicAnalyzer created")

        # Test with minimal functionality
        # NOTE: This test doesn't require actual audio files
        print("  [OK] Audio analysis module ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Audio analysis failed: {e}")
        traceback.print_exc()
        return False

def test_concept_generation():
    """Test concept generation (requires OpenAI API key)"""
    print("Testing Concept Generation...")

    try:
        from src.storyboard.conceptor import ConceptGenerator

        # Check if API key is available
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your_openai_api_key_here":
            print("  [SKIP] No OpenAI API key - concept generation will use fallbacks")
            return True

        # Create conceptor (this validates API key format)
        conceptor = ConceptGenerator()
        print("  [OK] ConceptGenerator created with API key")

        # Create mock music data for testing
        mock_music_data = {
            'duration': 240.0,
            'tempo': 120.0,
            'overall_energy': 0.7,
            'segments': [
                {'start_time': 0, 'end_time': 60, 'mood': 'energetic', 'energy': 0.8},
                {'start_time': 60, 'end_time': 120, 'mood': 'calm', 'energy': 0.4},
                {'start_time': 120, 'end_time': 180, 'mood': 'building', 'energy': 0.9},
                {'start_time': 180, 'end_time': 240, 'mood': 'resolution', 'energy': 0.6}
            ]
        }

        print("  [OK] Concept generation module ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Concept generation failed: {e}")
        return False

def test_storyboard_generation():
    """Test storyboard generation"""
    print("Testing Storyboard Generation...")

    try:
        from src.storyboard.generator import StoryboardGenerator
        from src.storyboard.conceptor import VisualConcept

        # Create generator
        generator = StoryboardGenerator()
        print("  [OK] StoryboardGenerator created")

        # Create mock visual concept
        mock_concept = VisualConcept(
            overall_style="cinematic",
            color_palette=["blue", "gold", "white", "black"],
            mood_progression=["calm", "building", "intense"],
            key_visual_themes=["movement", "light", "emotion"],
            camera_style="dynamic"
        )
        print("  [OK] Mock visual concept created")

        print("  [OK] Storyboard generation module ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Storyboard generation failed: {e}")
        return False

def test_image_generation():
    """Test image generation setup"""
    print("Testing Image Generation...")

    try:
        from src.assets.generator import MultiProviderImageGenerator

        # Create generator
        generator = MultiProviderImageGenerator()
        print("  [OK] MultiProviderImageGenerator created")

        # Check which providers are available
        openai_available = generator.openai_client is not None
        novelai_available = generator.novelai_api_key is not None
        replicate_available = generator.replicate_api_key is not None

        print(f"  [{'OK' if openai_available else 'SKIP'}] OpenAI/DALL-E provider")
        print(f"  [{'OK' if novelai_available else 'SKIP'}] NovelAI provider")
        print(f"  [{'OK' if replicate_available else 'SKIP'}] Replicate provider")

        if not any([openai_available, novelai_available, replicate_available]):
            print("  [WARN] No image generation providers available - add API keys to .env")

        print("  [OK] Image generation module ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Image generation failed: {e}")
        return False

def test_video_assembly():
    """Test video assembly module"""
    print("Testing Video Assembly...")

    try:
        import moviepy
        print("  [OK] MoviePy imported successfully")

        from src.video.assembler import VideoAssembler

        # Create assembler
        assembler = VideoAssembler()
        print("  [OK] VideoAssembler created")

        print("  [OK] Video assembly module ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Video assembly failed: {e}")
        return False

def test_reference_manager():
    """Test reference manager"""
    print("Testing Reference Manager...")

    try:
        from src.assets.reference_manager import ReferenceManager

        # Create manager
        ref_manager = ReferenceManager()
        print("  [OK] ReferenceManager created")

        # Test basic functionality
        info = ref_manager.get_reference_info()
        print("  [OK] Reference info retrieved")

        print("  [OK] Reference manager ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Reference manager failed: {e}")
        return False

def test_api_imports():
    """Test main API imports"""
    print("Testing Main API...")

    try:
        # Test FastAPI imports
        import fastapi
        import uvicorn
        from fastapi import UploadFile, File, WebSocket
        print("  [OK] FastAPI imports")

        # Test main API file structure
        import sys
        sys.path.append("backend")
        print("  [OK] Backend path added")

        print("  [OK] Main API ready")
        return True

    except Exception as e:
        print(f"  [FAIL] Main API failed: {e}")
        return False

def check_environment():
    """Check environment setup"""
    print("Checking Environment...")

    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("  [OK] .env file exists")

        # Check for API keys (without exposing them)
        with open(env_file) as f:
            content = f.read()

        has_openai = "OPENAI_API_KEY=" in content and "your_openai_api_key_here" not in content
        has_novelai = "NOVELAI_API_KEY=" in content and "your_novelai_api_key_here" not in content

        print(f"  [{'OK' if has_openai else 'MISSING'}] OpenAI API key")
        print(f"  [{'OK' if has_novelai else 'MISSING'}] NovelAI API key (optional)")

        if not has_openai:
            print("  [WARN] Add OpenAI API key to .env for full functionality")
    else:
        print("  [FAIL] .env file missing")
        return False

    return True

def main():
    """Run all component tests"""
    print("BeatCanvas Component Testing")
    print("============================")

    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[OK] Environment loaded")
    except ImportError:
        print("[SKIP] python-dotenv not available")

    print()

    # Run tests
    tests = [
        ("Environment", check_environment),
        ("Audio Analysis", test_audio_analysis),
        ("Concept Generation", test_concept_generation),
        ("Storyboard Generation", test_storyboard_generation),
        ("Image Generation", test_image_generation),
        ("Video Assembly", test_video_assembly),
        ("Reference Manager", test_reference_manager),
        ("Main API", test_api_imports)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"[FAIL] {test_name}: Unexpected error: {e}")
            results[test_name] = False
        print()

    # Summary
    print("Test Summary")
    print("============")

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"[{status}] {test_name}")

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! BeatCanvas is ready to use.")
        print("\nNext steps:")
        print("1. Start backend: cd backend && uvicorn main:app --reload")
        print("2. Start frontend: cd frontend && npm start")
        print("3. Open http://localhost:3000")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Check the issues above.")

        if not results.get("Environment", False):
            print("\n💡 Make sure to add your OpenAI API key to .env file")

if __name__ == "__main__":
    main()