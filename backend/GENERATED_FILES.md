# Generated Files for BeatCanvas Local AI Backend

**Date**: 2026-02-01
**Purpose**: Offline AI inference pipeline using GGUF models

## Files Generated

### 1. Model Path Utilities

**`src/utils/model_loader.py`** (2.0 KB)
- Function: `get_model_path(model_type, filename)` - Resolves model paths
- Function: `validate_models()` - Validates all required models are present
- Logic: Navigates from `src` → `backend` → `beatcanvas` → `synterra` → `models/`

### 2. Image Generation

**`src/local/image_generator.py`** (7.2 KB)
- Class: `LocalImageGenerator`
- Backend: Flux GGUF via llama.cpp
- Methods:
  - `generate_image(prompt, width, height)` - Standard image generation
  - `generate_meme(prompt, top_text, bottom_text)` - Meme with text overlay
  - `_add_meme_text()` - White text with black outline (classic meme style)

### 3. Video Generation

**`src/local/video_generator.py`** (7.5 KB)
- Class: `LocalVideoGenerator`
- Backend: Wan 2.1 T2V GGUF (14B Q4_K_M) via llama.cpp
- Methods:
  - `generate_video(image_path, prompt, num_frames, fps)` - Image-to-video
  - `_load_model()` - Lazy model loading
  - `_unload_model()` - **CRITICAL**: Calls `del model` + `gc.collect()` to free VRAM
- **VRAM Safety**: Automatic cleanup in try/finally block

### 4. Prompt Translation

**`src/local/prompt_translator.py`** (6.8 KB)
- Class: `PhiTranslator`
- Backend: Phi-3 mini 4K instruct via llama.cpp
- Methods:
  - `translate_to_danbooru(natural_prompt)` - Natural language → Danbooru tags
  - `translate_with_style(prompt, style, quality_preset)` - With style modifiers
  - `batch_translate(prompts)` - Batch processing
- Output: Comma-separated tags optimized for anime image generation

### 5. Safety & Compliance

**`src/safety/compliance_gate.py`** (5.3 KB)
- Class: `ComplianceGate`
- Features:
  - Keyword-based content filtering
  - Runtime enable/disable via `ENABLE_SAFETY` env var
  - Strict mode for additional checks
- Methods:
  - `check_prompt(prompt)` - Returns (is_safe, reason)
  - `filter_prompt(prompt)` - Replace banned keywords
  - `add_keyword()` / `remove_keyword()` - Dynamic list management

### 6. CLI Pipeline Runner

**`src/private/admin_runner.py`** (13.1 KB)
- Executable CLI script
- Class: `BeatCanvasPipeline` - Full pipeline orchestrator
- Modes:
  - `standard` - Image generation only
  - `meme` - Image with text overlays
  - `video` - Image-to-video from existing image
  - `full` - Complete pipeline (image → video)
- Features:
  - Safety filtering integration
  - Lazy model loading
  - Progress tracking
  - Comprehensive argument parsing

### 7. Package Initialization Files

- `src/__init__.py` - Root package
- `src/utils/__init__.py` - Exports `get_model_path`, `validate_models`
- `src/local/__init__.py` - Exports all generator classes
- `src/safety/__init__.py` - Exports `ComplianceGate`, `get_default_gate`
- `src/private/__init__.py` - Empty (admin tools)

### 8. Documentation

**`src/README.md`** (6.4 KB)
- Complete usage guide
- API reference
- Performance notes
- Troubleshooting section

## Directory Structure

```
beatcanvas/backend/src/
├── __init__.py
├── README.md
├── utils/
│   ├── __init__.py
│   └── model_loader.py
├── local/
│   ├── __init__.py
│   ├── image_generator.py
│   ├── video_generator.py
│   └── prompt_translator.py
├── safety/
│   ├── __init__.py
│   └── compliance_gate.py
└── private/
    ├── __init__.py
    └── admin_runner.py (executable)
```

## Model Dependencies

All files reference models via `get_model_path()`:

| Model Type | File | Purpose |
|-----------|------|---------|
| `flux` | `flux1-schnell-uncensored.gguf` | Image generation (4-step Flux) |
| `wan` | `Wan2.1-T2V-14B_Q4_K_M.gguf` | Video generation (image-to-video) |
| `llm` | `Phi-3-mini-4k-instruct.gguf` | Prompt translation to Danbooru |
| `pony` | `ponyDiffusionV6XL.safetensors` | Reserved for future use |

## Quick Start

```bash
# Navigate to source directory
cd ~/AI_Workspace/synterra/beatcanvas/backend/src

# Validate models are present
python -m utils.model_loader

# Run full pipeline
./private/admin_runner.py --mode full \
  --prompt "a cyberpunk city" \
  --animation "camera pan right"
```

## Key Features Implemented

1. **Model Path Auto-Resolution**: Automatic detection of synterra root
2. **VRAM Management**: Critical cleanup in video generator
3. **Lazy Loading**: Models loaded only when needed
4. **Safety Integration**: Optional content filtering
5. **Meme Support**: Classic white-with-black-outline text
6. **CLI Interface**: Complete argparse-based runner
7. **Python API**: Import and use classes directly
8. **Error Handling**: FileNotFoundError for missing models
9. **Testing**: Each module has `__main__` test block
10. **Documentation**: Comprehensive README with examples

## Technical Notes

### Image Generation
- Uses llama.cpp Python bindings for Flux GGUF
- Placeholder decoding (actual Flux GGUF decoding requires custom implementation)
- Meme text uses PIL ImageDraw with outline rendering

### Video Generation
- Wan 2.1 14B model in Q4_K_M quantization
- **Critical VRAM cleanup** with `del` + `gc.collect()`
- OpenCV for MP4 encoding
- Placeholder frame interpolation (actual Wan decoding requires custom implementation)

### Prompt Translation
- Phi-3 with ChatML format
- System prompt optimized for Danbooru tag generation
- Supports quality presets (low/medium/high/ultra)

### Safety System
- Environment variable: `ENABLE_SAFETY` (default: true)
- Simple keyword matching (placeholder for LlamaGuard integration)
- Runtime enable/disable without restart

## Known Limitations

1. **Flux GGUF Decoding**: Placeholder implementation - actual decoding depends on llama.cpp's Flux support
2. **Wan GGUF Decoding**: Placeholder implementation - actual decoding depends on Wan 2.1 GGUF format
3. **Impact Font**: Fallback to default font if Impact.ttf not found
4. **GPU Required**: Models expect CUDA/ROCm for acceptable performance
5. **Memory Usage**: 14B model requires ~10GB VRAM

## Next Steps

1. **Integrate Real Decoders**: Replace placeholder decoding with actual Flux/Wan GGUF output parsing
2. **Add Progress Callbacks**: Real-time generation progress reporting
3. **Optimize VRAM**: Implement model swapping for multi-stage pipeline
4. **Batch Processing**: Support multiple prompts in single run
5. **Quality Presets**: Pre-configured settings for different use cases
6. **Model Validation**: Check GGUF compatibility on startup
7. **Async Generation**: Non-blocking generation with callbacks
8. **Cloud Integration**: Optional API fallback for unsupported models

## Testing Checklist

- [ ] Model path resolution works from src directory
- [ ] Image generation produces valid PNG files
- [ ] Meme text overlay renders correctly
- [ ] Video generation creates valid MP4 files
- [ ] VRAM is freed after video generation
- [ ] Prompt translation produces comma-separated tags
- [ ] Safety gate blocks banned keywords
- [ ] CLI runner handles all 4 modes
- [ ] Error messages are helpful
- [ ] Models load without errors

## File Sizes Summary

Total code generated: ~48.1 KB across 6 Python modules + documentation

**End of generation summary**
