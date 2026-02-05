#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"✓ {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_backend():
    """Set up Python backend"""
    print("\n🔧 Setting up Backend...")

    backend_dir = Path("backend")

    # Create virtual environment
    if not (backend_dir / "venv").exists():
        run_command("python -m venv venv", cwd=backend_dir)

    # Determine activate script path
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
        pip_path = "venv\\Scripts\\pip"
    else:  # Unix/macOS
        activate_script = "source venv/bin/activate"
        pip_path = "venv/bin/pip"

    # Install dependencies
    run_command(f"{pip_path} install -r requirements.txt", cwd=backend_dir)

    print("✓ Backend setup complete")

def setup_frontend():
    """Set up React frontend"""
    print("\n🔧 Setting up Frontend...")

    frontend_dir = Path("frontend")

    # Check if npm is available
    if run_command("npm --version") is None:
        print("❌ npm not found. Please install Node.js and npm first.")
        return False

    # Install dependencies
    run_command("npm install", cwd=frontend_dir)

    print("✓ Frontend setup complete")
    return True

def setup_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")

    directories = [
        "data/uploads",
        "data/generated_images",
        "data/references",
        "output"
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {dir_path}")

def check_ffmpeg():
    """Check if ffmpeg is available"""
    print("\n🎬 Checking FFmpeg...")

    result = run_command("ffmpeg -version")
    if result:
        print("✓ FFmpeg is available")
        return True
    else:
        print("❌ FFmpeg not found. Please install FFmpeg for video processing.")
        print("   Windows: https://ffmpeg.org/download.html")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        return False

def setup_environment():
    """Set up environment file"""
    print("\n🔐 Setting up environment...")

    if not Path(".env").exists():
        # Copy example file
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✓ Created .env file from .env.example")
            print("   Please add your API keys to .env file")
        else:
            print("❌ .env.example not found")
    else:
        print("✓ .env file already exists")

def main():
    """Main setup function"""
    print("🎵 BeatCanvas Setup")
    print("==================")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

    # Setup steps
    setup_directories()
    setup_environment()
    setup_backend()
    frontend_ok = setup_frontend()
    ffmpeg_ok = check_ffmpeg()

    print("\n🎉 Setup Summary")
    print("================")
    print("✓ Backend: Ready")
    print(f"{'✓' if frontend_ok else '❌'} Frontend: {'Ready' if frontend_ok else 'Failed'}")
    print(f"{'✓' if ffmpeg_ok else '❌'} FFmpeg: {'Available' if ffmpeg_ok else 'Missing'}")

    print("\n🚀 Next Steps:")
    print("1. Add your API keys to .env file")
    print("2. Start backend: cd backend && uvicorn main:app --reload")
    print("3. Start frontend: cd frontend && npm start")
    print("4. Open http://localhost:3000")

    if not ffmpeg_ok:
        print("\n⚠️  Install FFmpeg before generating videos")

if __name__ == "__main__":
    main()