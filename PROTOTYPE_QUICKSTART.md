# Prototype Engine Quickstart

Local AI video generation using Flux.1-schnell + LTX-Video on NVIDIA GPU.

## Requirements

- NVIDIA GPU with 16GB+ VRAM
- Python 3.10+
- CUDA 11.8 or 12.1

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 2. Install PyTorch with CUDA (pick your version)
# CUDA 12.1:
pip install torch --index-url https://download.pytorch.org/whl/cu121
# CUDA 11.8:
pip install torch --index-url https://download.pytorch.org/whl/cu118

# 3. Install dependencies
pip install -r requirements_prototype.txt
```

## Run

```bash
python prototype_engine.py
```

First run downloads ~25GB of model weights (cached for future runs).

## Output

| File | Description |
|------|-------------|
| `test_image.png` | Generated image (1024x576) |
| `test_render.mp4` | Final video (768x512, 5 sec, 24fps) |

## Customize Prompts

Edit `prototype_engine.py` and modify these variables in `main()`:

```python
image_prompt = "Your image description here..."
motion_prompt = "Your motion/camera description here..."
seed = 42  # Change for variations
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CUDA not available | Verify GPU drivers and PyTorch CUDA version match |
| Out of memory | Close other GPU apps, or reduce `num_frames` to 97 (4 sec) |
| Slow download | Models cache to `~/.cache/huggingface/` |
