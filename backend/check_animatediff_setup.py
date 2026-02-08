#!/usr/bin/env python3
"""
Check AnimateDiff setup: models, GPU, dependencies.
Diagnoses common issues before running the pipeline.
"""

import sys
import os
from pathlib import Path

print("=" * 80)
print("AnimateDiff Setup Diagnostic")
print("=" * 80)

# Check 1: Python environment
print("\n[CHECK 1] Python Environment")
print(f"Python version: {sys.version}")
print(f"Executable: {sys.executable}")

# Check 2: GPU availability
print("\n[CHECK 2] GPU Availability")
try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU count: {torch.cuda.device_count()}")
        # Test CUDA
        try:
            x = torch.randn(3, 3).cuda()
            print("✓ CUDA test passed (GPU accessible)")
        except Exception as e:
            print(f"✗ CUDA test failed: {e}")
    else:
        print("⚠ WARNING: CUDA not available - will run on CPU (very slow)")
except ImportError as e:
    print(f"✗ PyTorch not installed: {e}")
    sys.exit(1)

# Check 3: Hugging Face cache
print("\n[CHECK 3] Hugging Face Model Cache")
hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
print(f"HF cache directory: {hf_cache}")
print(f"Cache exists: {hf_cache.exists()}")
if hf_cache.exists():
    models = list(hf_cache.glob("models--*"))
    print(f"Cached models: {len(models)}")
    for model in models[:10]:  # Show first 10
        print(f"  - {model.name}")
    if len(models) > 10:
        print(f"  ... and {len(models) - 10} more")
else:
    print("⚠ No HF cache found - models will be downloaded on first run")

# Check 4: AnimateDiff-specific models
print("\n[CHECK 4] AnimateDiff Model Requirements")
expected_models = [
    "ByteDance/AnimateDiff-Lightning",
    "models--ByteDance--AnimateDiff-Lightning",
]
found = []
if hf_cache.exists():
    for expected in expected_models:
        matches = list(hf_cache.glob(f"*{expected.replace('/', '--')}*"))
        if matches:
            found.append(expected)
            print(f"✓ Found: {expected}")

if not found:
    print("⚠ AnimateDiff models not found - will download on first run (~2-4 GB)")
    print("  This may take several minutes depending on network speed")

# Check 5: Output directories
print("\n[CHECK 5] Output Directories")
backend_dir = Path(__file__).parent
data_dir = backend_dir / "data"
video_clips_dir = data_dir / "video_clips"

for dir_path, name in [(data_dir, "data"), (video_clips_dir, "video_clips")]:
    print(f"{name} dir: {dir_path}")
    print(f"  Exists: {dir_path.exists()}")
    if not dir_path.exists():
        print(f"  Creating directory...")
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created")
        except Exception as e:
            print(f"  ✗ Failed to create: {e}")

# Check 6: Critical dependencies
print("\n[CHECK 6] Critical Dependencies")
dependencies = [
    ("diffusers", "Diffusers library"),
    ("transformers", "Transformers library"),
    ("accelerate", "Accelerate library"),
    ("PIL", "Pillow (PIL)"),
    ("cv2", "OpenCV (cv2)"),
]

for module_name, description in dependencies:
    try:
        __import__(module_name)
        print(f"✓ {description} ({module_name})")
    except ImportError:
        print(f"✗ {description} ({module_name}) - NOT INSTALLED")

# Check 7: AnimateDiffGenerator import
print("\n[CHECK 7] AnimateDiffGenerator Import Test")
sys.path.insert(0, str(backend_dir))
try:
    from src.cinematography import AnimateDiffGenerator
    print("✓ AnimateDiffGenerator imports successfully")
except Exception as e:
    print(f"✗ AnimateDiffGenerator import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Diagnostic Complete")
print("=" * 80)
print("\nRecommendations:")
print("1. If CUDA is not available, install CUDA-enabled PyTorch")
print("2. If models are missing, they'll download automatically (may take time)")
print("3. Ensure all dependencies are installed: pip install -r requirements.txt")
print("4. Check that output directories are writable")
print("\nNext step: Run test_animatediff_standalone.py")
