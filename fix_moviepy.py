#!/usr/bin/env python3
"""
Fix MoviePy imports for version 2.x
"""

from pathlib import Path

def fix_moviepy_import():
    """Fix the MoviePy import in video assembler"""

    file_path = Path("backend/src/video/assembler.py")

    if not file_path.exists():
        print(f"[FAIL] {file_path} not found")
        return

    try:
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace the old import with new moviepy 2.x import
        old_import = "from moviepy.editor import *"
        new_import = """# MoviePy 2.x imports
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, TextClip
import moviepy"""

        if old_import in content:
            content = content.replace(old_import, new_import)

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("[OK] Fixed MoviePy imports")
        else:
            print("[SKIP] MoviePy import already updated or not found")

    except Exception as e:
        print(f"[FAIL] Error fixing MoviePy imports: {e}")

if __name__ == "__main__":
    fix_moviepy_import()