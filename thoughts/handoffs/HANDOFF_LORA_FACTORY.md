# Handoff: LoRA Factory Pipeline Complete

**Date**: 2026-02-15
**Status**: Tools built, ai-toolkit installed on desktop, ready for first training on laptop

## What Was Built

### 4 Automation Scripts (`tools/`)

1. **`pexels_collector.py`** - Downloads training images from Pexels API
   - Handles pagination, SHA256 dedup, quality filtering (min 1024x768)
   - Resume support via manifest file
   - `python tools/pexels_collector.py "tiki bar interior" --count 30 --orientation landscape`

2. **`auto_caption.py`** - Auto-captions images for LoRA training
   - Florence-2 (~4GB VRAM, ~0.5s/image) for scene/style LoRAs
   - Joy-Caption (~8-10GB VRAM) for character LoRAs (better identity details)
   - `python tools/auto_caption.py datasets/beach-sunset/ --trigger beach_sunset --model florence2`

3. **`generate_lora_config.py`** - Generates ai-toolkit YAML configs
   - VRAM-aware profiles: 8GB, 12GB, 16GB, 24GB
   - Type presets: scene (2500 steps), style (2000 steps), character (1500 steps)
   - `python tools/generate_lora_config.py beach-sunset --vram 12 --type scene`

4. **`train_lora.sh`** - End-to-end orchestrator
   - Single: `bash tools/train_lora.sh --name beach-sunset --query "tropical beach sunset" --type scene`
   - Batch: `bash tools/train_lora.sh --batch` (all 8 Trop Rock LoRAs, walk away overnight)

### LoRA Registry (`backend/config/loras.yaml`)
Expanded with full Trop Rock library: 7 scene LoRAs + 2 style LoRAs + character template. All `enabled: false` until trained.

## Hardware Situation (CORRECTED)

| Machine | RAM | VRAM | Role |
|---------|-----|------|------|
| Desktop (Xeon) | 256GB | 4GB (Quadro M2000) | Dataset collection ONLY |
| Laptop | 32GB | 12GB | PRIMARY training machine |

**Important**: Desktop cannot train LoRAs. 4GB VRAM is insufficient even for 8GB profile. Use desktop only for running `pexels_collector.py` (no GPU needed).

## What's Installed on Desktop

- `c:\src\Synterra\ai-toolkit\` - Cloned, venv created, PyTorch 2.6.0+cu124, all deps installed
- Verified: torch, diffusers, transformers, peft, bitsandbytes all import correctly
- BUT: 4GB VRAM means training won't work here

## Laptop Setup Instructions

### Step 1: Clone Repos
```bash
# Clone BeatCanvas (has all tools/ scripts)
cd /path/to/workspace
git clone <your-github-url> BeatCanvas

# Clone ai-toolkit as sibling directory
git clone https://github.com/ostris/ai-toolkit.git
```

### Step 2: Install ai-toolkit
```bash
cd ai-toolkit
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install PyTorch with CUDA (check your CUDA version with nvidia-smi)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install requirements (if scipy fails, install scipy separately first, then --no-deps)
pip install -r requirements.txt

# Verify
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')"
```

### Step 3: Set Up Environment
```bash
# PEXELS_API_KEY should already be in ~/.claude/.env
# Verify:
cat ~/.claude/.env | grep PEXELS
```

### Step 4: First Test - Beach Sunset LoRA
```bash
cd BeatCanvas

# Full pipeline: collect → caption → config → train
bash tools/train_lora.sh --name beach-sunset --query "tropical beach sunset ocean" --type scene --vram 12

# Expected time: ~1-2 hours for 2500 steps on 12GB VRAM
# Output: output/loras/beach-sunset/beach-sunset.safetensors
```

### Step 5: Batch All Trop Rock LoRAs (Overnight)
```bash
bash tools/train_lora.sh --batch
# Trains all 8 LoRAs sequentially. ~8-16 hours total.
```

## Known Issues / Workarounds

1. **scipy 1.12.0 build failure on Python 3.13**: ai-toolkit pins scipy==1.12.0 which needs Fortran compiler. Fix: install scipy separately (pre-built wheel), then `pip install --no-deps -r requirements.txt`

2. **MarkupSafe source build**: If MarkupSafe errors about `_native` module, run `pip install --force-reinstall markupsafe`

3. **PyTorch version**: 2.7.0 not available for cu124 yet. Use 2.6.0.

## File Map

```
tools/
├── pexels_collector.py          # Image collection from Pexels
├── auto_caption.py              # Florence-2 / Joy-Caption
├── generate_lora_config.py      # ai-toolkit YAML generator
└── train_lora.sh                # End-to-end orchestrator

backend/config/
└── loras.yaml                   # LoRA registry (scene/style/character)

datasets/                        # Training datasets (created by pipeline)
config/loras/                    # Generated YAML configs
output/loras/                    # Trained .safetensors output
```

## Next After First Successful Training

1. Validate .safetensors loads correctly
2. Test inference with trained LoRA
3. Run batch overnight for full Trop Rock library
4. Build LoRA Curator module (matches storyboard scenes to LoRA registry)
5. Test with "Love and Saltwater" song - full pipeline with LoRA-enhanced generation
