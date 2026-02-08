#!/usr/bin/env python3
"""
Quick script to verify API keys are loaded correctly.
Run this after setting up ~/.claude/.env
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("API Key Verification")
print("=" * 80)

# Load environment
from src.utils.env_loader import load_global_env
print("\n[STEP 1] Loading environment variables...")
success = load_global_env()

# Check required keys
print("\n[STEP 2] Checking API keys...")
print("-" * 80)

required_keys = {
    "OPENAI_API_KEY": "Required for GPT-4 and DALL-E 3",
}

optional_keys = {
    "GOOGLE_AI_API_KEY": "Optional - Nano Banana (Gemini)",
    "NOVELAI_API_KEY": "Optional - Artistic image generation",
    "REPLICATE_API_TOKEN": "Optional - Stable Diffusion/Flux",
    "MIDJOURNEY_API_KEY": "Optional - Future integration",
    "HUGGINGFACE_TOKEN": "Optional - Model downloads",
    "CIVITAI_API_KEY": "Optional - Model downloads",
}

# Check required
all_required_present = True
for key, description in required_keys.items():
    value = os.getenv(key)
    if value and value != f"your_{key.lower()}":
        # Mask the key for security
        masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        print(f"✓ {key:25s} {masked:20s} ({description})")
    else:
        print(f"✗ {key:25s} NOT SET          ({description})")
        all_required_present = False

print()

# Check optional
optional_present = []
for key, description in optional_keys.items():
    value = os.getenv(key)
    if value and value != f"your_{key.lower()}":
        masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        print(f"✓ {key:25s} {masked:20s} ({description})")
        optional_present.append(key)
    else:
        print(f"  {key:25s} not set          ({description})")

print("-" * 80)

# Summary
print("\n[SUMMARY]")
if all_required_present:
    print("✅ All required API keys are configured")
    print(f"✅ {len(optional_present)} optional API keys configured")
    print("\n✨ BeatCanvas is ready to use!")
    print("\nNext steps:")
    print("1. Start backend: conda run -n beatcanvas uvicorn main:app --reload")
    print("2. Test API: curl -X POST http://localhost:8000/api/generate-video \\")
    print("     -F 'audio=@data/uploads/test_audio.mp3' \\")
    print("     -F 'visual_prompt=beach sunset' \\")
    print("     -F 'quality_tier=basic'")
    sys.exit(0)
else:
    print("❌ Missing required API keys")
    print("\nPlease edit ~/.claude/.env and add your OPENAI_API_KEY")
    print("Then run this script again to verify.")
    sys.exit(1)
