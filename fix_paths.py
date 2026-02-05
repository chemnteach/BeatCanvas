#!/usr/bin/env python3
"""
Quick fix script for path issues in BeatCanvas modules
"""

import os
from pathlib import Path

def fix_file_paths():
    """Fix relative path issues in backend modules"""

    # Files to fix and their path fixes
    fixes = [
        {
            "file": "backend/src/assets/generator.py",
            "old": 'self.output_dir = Path("../data/generated_images")',
            "new": 'self.output_dir = Path("data/generated_images")'
        },
        {
            "file": "backend/src/assets/reference_manager.py",
            "old": 'self.reference_dir = Path("../data/references")',
            "new": 'self.reference_dir = Path("data/references")'
        },
        {
            "file": "backend/src/video/assembler.py",
            "old": 'self.output_dir = Path("../output")',
            "new": 'self.output_dir = Path("output")'
        },
        {
            "file": "backend/main.py",
            "old": 'UPLOAD_DIR = Path("../data/uploads")',
            "new": 'UPLOAD_DIR = Path("data/uploads")'
        },
        {
            "file": "backend/main.py",
            "old": 'OUTPUT_DIR = Path("../output")',
            "new": 'OUTPUT_DIR = Path("output")'
        },
        {
            "file": "backend/main.py",
            "old": 'GENERATED_DIR = Path("../data/generated_images")',
            "new": 'GENERATED_DIR = Path("data/generated_images")'
        }
    ]

    print("Fixing path issues in backend modules...")

    for fix in fixes:
        file_path = Path(fix["file"])

        if not file_path.exists():
            print(f"  [SKIP] {fix['file']} - file not found")
            continue

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply fix
            if fix["old"] in content:
                content = content.replace(fix["old"], fix["new"])

                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  [OK] Fixed paths in {fix['file']}")
            else:
                print(f"  [SKIP] {fix['file']} - pattern not found")

        except Exception as e:
            print(f"  [FAIL] {fix['file']} - {e}")

    print("Path fixes complete!")

if __name__ == "__main__":
    fix_file_paths()