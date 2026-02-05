# BeatCanvas Backend - Local AI Inference

Complete offline AI generation system using GGUF models via llama.cpp.

## Architecture

```
src/
├── utils/
│   ├── __init__.py
│   └── model_loader.py         # Model path resolution
├── local/
│   ├── __init__.py
│   ├── image_generator.py      # Flux GGUF image generation
│   ├── video_generator.py      # Wan 2.1 video generation
│   └── prompt_translator.py    # Phi-3 prompt translation
├── safety/
│   ├── __init__.py
│   └── compliance_gate.py      # Content safety filtering
└── private/
    ├── __init__.py
    └── admin_runner.py          # CLI pipeline runner
```

## Model Requirements

The system expects models in `synterra/models/`:

```
synterra/models/
├── flux/
│   └── flux1-schnell-uncensored.gguf      # Image generation
├── wan/
│   └── Wan2.1-T2V-14B_Q4_K_M.gguf        # Video generation
├── llm/
│   └── Phi-3-mini-4k-instruct.gguf       # Prompt translation
└── pony/
    └── ponyDiffusionV6XL.safetensors      # (Reserved for future use)
```

## Installation

```bash
# Install dependencies
pip install llama-cpp-python Pillow opencv-python numpy

# Optional: Install with GPU support (CUDA)
pip install llama-cpp-python --force-reinstall --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

## Usage

### Validate Models

```bash
cd beatcanvas/backend/src
python -m utils.model_loader
```

### CLI Pipeline Runner

The `admin_runner.py` provides a complete CLI interface:

#### Standard Image Generation

```bash
./private/admin_runner.py --mode standard --prompt "a cyberpunk city at night"
```

#### Meme Generation

```bash
./private/admin_runner.py --mode meme \
  --prompt "confused cat" \
  --top "WHEN YOU REALIZE" \
  --bottom "IT'S ALREADY MONDAY"
```

#### Video Generation

```bash
./private/admin_runner.py --mode video \
  --image /path/to/image.png \
  --prompt "smooth zoom in with particles"
```

#### Full Pipeline (Image → Video)

```bash
./private/admin_runner.py --mode full \
  --prompt "a magical forest" \
  --animation "gentle swaying trees"
```

### Advanced Options

```bash
# Disable prompt translation
--no-translate

# Disable safety filtering
--no-safety

# Custom dimensions
--width 768 --height 768

# Video parameters
--frames 24 --fps 12

# Custom output directory
--output-dir /path/to/output
```

## Python API

### Image Generation

```python
from local.image_generator import LocalImageGenerator

# Initialize generator
generator = LocalImageGenerator()

# Generate standard image
image = generator.generate_image(
    prompt="a beautiful sunset",
    width=512,
    height=512
)
image.save("output.png")

# Generate meme
meme = generator.generate_meme(
    prompt="confused cat",
    top_text="WHEN YOU",
    bottom_text="REALIZE IT'S MONDAY"
)
meme.save("meme.png")
```

### Video Generation

```python
from local.video_generator import LocalVideoGenerator

# Initialize generator
generator = LocalVideoGenerator()

# Generate video (automatically frees VRAM after completion)
video_path = generator.generate_video(
    image_path="input.png",
    prompt="smooth zoom in",
    num_frames=16,
    fps=8
)
```

**IMPORTANT**: The video generator automatically calls `del model` and `gc.collect()` to free VRAM after generation.

### Prompt Translation

```python
from local.prompt_translator import PhiTranslator

# Initialize translator
translator = PhiTranslator()

# Translate natural language to Danbooru tags
tags = translator.translate_to_danbooru(
    "A girl with long purple hair in a school uniform"
)
print(tags)
# Output: masterpiece, high_quality, 1girl, long_hair, purple_hair, school_uniform

# With style modifiers
styled_tags = translator.translate_with_style(
    "a magical forest",
    style="anime",
    quality_preset="ultra"
)
```

### Safety Filtering

```python
from safety.compliance_gate import ComplianceGate

# Initialize gate
gate = ComplianceGate(enable_safety=True)

# Check prompt
is_safe, reason = gate.check_prompt("your prompt here")
if not is_safe:
    print(f"Blocked: {reason}")

# Or filter instead of blocking
filtered = gate.filter_prompt("prompt with banned words")

# Disable safety at runtime
gate.disable()
```

## Environment Variables

```bash
# Safety toggle (default: true)
export ENABLE_SAFETY=false  # Disable content filtering
```

## Model Path Resolution

The `model_loader` automatically finds models by navigating from `src` to `synterra/models/`:

```
src (current file)
  → backend
    → beatcanvas
      → synterra
        → models/
```

All generators use this utility for consistent path resolution.

## Performance Notes

### Memory Requirements

- **Flux (Image)**: ~4-6 GB VRAM
- **Wan 2.1 (Video)**: ~8-10 GB VRAM
- **Phi-3 (LLM)**: ~2-3 GB VRAM

### VRAM Management

The video generator includes critical VRAM cleanup:

```python
def generate_video(...):
    try:
        self._load_model()
        # ... generation logic ...
        return output_path
    finally:
        self._unload_model()  # Always frees VRAM
```

This ensures VRAM is released even if generation fails.

### GPU Acceleration

All models use `n_gpu_layers=-1` to offload to GPU by default. For CPU-only:

```python
model = Llama(
    model_path=path,
    n_gpu_layers=0  # CPU only
)
```

## Troubleshooting

### Model Not Found

```
FileNotFoundError: Model not found: /path/to/synterra/models/flux/flux1-schnell-uncensored.gguf
```

**Solution**: Verify the model exists and the symlink is correct:

```bash
ls -la synterra/models/flux/
```

### VRAM Out of Memory

**Solution**: Run video generation in isolation or reduce batch size:

```bash
# The video generator automatically cleans up VRAM
# If still failing, close other GPU applications
```

### Import Errors

```
ModuleNotFoundError: No module named 'llama_cpp'
```

**Solution**: Install dependencies:

```bash
pip install llama-cpp-python
```

## Testing

Each module includes a `__main__` block for standalone testing:

```bash
# Test model loader
python -m utils.model_loader

# Test image generation
python -m local.image_generator

# Test video generation
python -m local.video_generator

# Test prompt translation
python -m local.prompt_translator

# Test safety gate
python -m safety.compliance_gate
```

## License

Part of the Synterra suite.
