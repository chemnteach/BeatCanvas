#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"[OK] {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_directories():
    """Create necessary directories"""
    print("\nCreating directories...")

    directories = [
        "data/uploads",
        "data/generated_images",
        "data/references",
        "output"
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created {dir_path}")

def setup_environment():
    """Set up environment file"""
    print("\nSetting up environment...")

    if not Path(".env").exists():
        # Copy example file
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("[OK] Created .env file from .env.example")
            print("     Please add your API keys to .env file")
        else:
            print("[FAIL] .env.example not found")
    else:
        print("[OK] .env file already exists")

def check_python_packages():
    """Check if required Python packages can be imported"""
    print("\nChecking Python packages...")

    required_packages = [
        "fastapi",
        "uvicorn",
        "librosa",
        "openai",
        "moviepy"
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[MISSING] {package}")
            missing_packages.append(package)

    return len(missing_packages) == 0

def test_audio_analysis():
    """Test the audio analysis module"""
    print("\nTesting audio analysis...")

    try:
        # Test import
        sys.path.append(str(Path("backend")))
        from src.audio.analyzer import MusicAnalyzer

        analyzer = MusicAnalyzer()
        print("[OK] Audio analyzer imported successfully")
        return True

    except Exception as e:
        print(f"[FAIL] Audio analyzer test failed: {e}")
        return False

def test_api_imports():
    """Test if all backend modules can be imported"""
    print("\nTesting backend module imports...")

    try:
        sys.path.append(str(Path("backend")))

        # Test key imports
        from src.storyboard.conceptor import ConceptGenerator
        print("[OK] Concept generator")

        from src.storyboard.generator import StoryboardGenerator
        print("[OK] Storyboard generator")

        from src.assets.generator import MultiProviderImageGenerator
        print("[OK] Image generator")

        from src.video.assembler import VideoAssembler
        print("[OK] Video assembler")

        return True

    except Exception as e:
        print(f"[FAIL] Module import failed: {e}")
        return False

def main():
    """Main setup function"""
    print("BeatCanvas Setup & Testing")
    print("==========================")

    # Check Python version
    if sys.version_info < (3, 8):
        print("[FAIL] Python 3.8 or higher is required")
        sys.exit(1)

    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor} detected")

    # Setup steps
    setup_directories()
    setup_environment()

    # Test components
    packages_ok = check_python_packages()
    audio_ok = test_audio_analysis()
    imports_ok = test_api_imports()

    print("\nSetup Summary")
    print("=============")
    print(f"[{'OK' if packages_ok else 'FAIL'}] Python packages")
    print(f"[{'OK' if audio_ok else 'FAIL'}] Audio analysis")
    print(f"[{'OK' if imports_ok else 'FAIL'}] Backend modules")

    print("\nNext Steps:")
    if not packages_ok:
        print("1. Install missing packages: pip install fastapi uvicorn librosa openai moviepy")
    else:
        print("1. Add OpenAI API key to .env file")
        print("2. Test: cd backend && python -m src.audio.analyzer")
        print("3. Start backend: cd backend && uvicorn main:app --reload")
        print("4. Start frontend: cd frontend && npm start")

if __name__ == "__main__":
    main()