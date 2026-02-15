#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BeatCanvas LoRA Factory - Automated Training Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# End-to-end: collect images → caption → generate config → train
# Run one LoRA or batch the whole Trop Rock library overnight.
#
# Usage:
#   # Single LoRA (all steps):
#   bash tools/train_lora.sh --name tiki-bar-interior --query "tiki bar interior tropical" --type scene
#
#   # Single LoRA (train only, dataset already prepared):
#   bash tools/train_lora.sh --name tiki-bar-interior --train-only
#
#   # Batch all Trop Rock LoRAs (walk away overnight):
#   bash tools/train_lora.sh --batch
#
#   # Character LoRA from local photos:
#   bash tools/train_lora.sh --name artist-rob --type character --trigger "ohwx" --skip-collect
#
# Requirements:
#   - Python 3.10+ with torch, transformers, Pillow
#   - ai-toolkit cloned at: ../ai-toolkit (sibling directory)
#   - PEXELS_API_KEY in ~/.claude/.env (for image collection)
#   - NVIDIA GPU with 8GB+ VRAM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

# ── Configuration ──────────────────────────────────────────────
BEATCANVAS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AI_TOOLKIT_DIR="${BEATCANVAS_DIR}/../ai-toolkit"
DATASETS_DIR="${BEATCANVAS_DIR}/datasets"
CONFIGS_DIR="${BEATCANVAS_DIR}/config/loras"
OUTPUT_DIR="${BEATCANVAS_DIR}/output/loras"
TOOLS_DIR="${BEATCANVAS_DIR}/tools"
VRAM=12  # Default VRAM; override with --vram

# Detect VRAM automatically if nvidia-smi is available
detect_vram() {
    if command -v nvidia-smi &> /dev/null; then
        local vram_mb
        vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$vram_mb" ]; then
            VRAM=$((vram_mb / 1024))
            echo "Detected GPU VRAM: ${VRAM}GB"
        fi
    fi
}

# ── Trop Rock Library Definition ──────────────────────────────
# Each entry: NAME|QUERY|TYPE|TRIGGER|COUNT
TROP_ROCK_LIBRARY=(
    "tiki-bar-interior|tiki bar interior bamboo tropical drinks|scene|tiki_bar|30"
    "beach-sunset|tropical beach sunset ocean golden hour|scene|beach_sunset|30"
    "boat-deck|boat deck ocean sailing yacht|scene|boat_deck|30"
    "ocean-underwater|underwater ocean coral reef tropical fish|scene|ocean_underwater|30"
    "beach-bar-exterior|beach bar exterior tropical palm trees|scene|beach_bar|30"
    "stage-performance|live music stage performance concert lights|scene|stage_performance|30"
    "bonfire-beach|beach bonfire night party flames|scene|bonfire_beach|30"
    "70s-film-retro|1970s vintage film photography family|style|retro_70s|40"
)

# ── Helper Functions ──────────────────────────────────────────

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

log_section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $*"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

check_ai_toolkit() {
    if [ ! -d "$AI_TOOLKIT_DIR" ]; then
        echo "ERROR: ai-toolkit not found at $AI_TOOLKIT_DIR"
        echo ""
        echo "Install it:"
        echo "  cd $(dirname $AI_TOOLKIT_DIR)"
        echo "  git clone https://github.com/ostris/ai-toolkit.git"
        echo "  cd ai-toolkit"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate  # or venv\\Scripts\\activate on Windows"
        echo "  pip install torch torchvision torchaudio"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
}

# ── Pipeline Steps ────────────────────────────────────────────

step_collect() {
    local name="$1" query="$2" count="$3"
    log_section "COLLECT: ${name} (${count} images)"
    python "${TOOLS_DIR}/pexels_collector.py" "$query" \
        --count "$count" \
        --output "${DATASETS_DIR}/${name}" \
        --orientation landscape
}

step_caption() {
    local name="$1" trigger="$2"
    log_section "CAPTION: ${name}"
    local trigger_arg=""
    if [ -n "$trigger" ]; then
        trigger_arg="--trigger ${trigger}"
    fi
    python "${TOOLS_DIR}/auto_caption.py" "${DATASETS_DIR}/${name}" \
        $trigger_arg \
        --model florence2
}

step_generate_config() {
    local name="$1" type="$2" trigger="$3"
    log_section "CONFIG: ${name}"
    python "${TOOLS_DIR}/generate_lora_config.py" "$name" \
        --dataset "${DATASETS_DIR}/${name}" \
        --vram "$VRAM" \
        --type "$type" \
        --trigger "$trigger"
}

step_train() {
    local name="$1"
    local config_path="${CONFIGS_DIR}/${name}.yaml"
    log_section "TRAIN: ${name}"

    if [ ! -f "$config_path" ]; then
        echo "ERROR: Config not found: $config_path"
        echo "Run generate_lora_config.py first."
        return 1
    fi

    check_ai_toolkit

    log "Starting training: ${name}"
    log "Config: ${config_path}"
    log "This will run unattended. Check output/loras/${name}/ for progress."
    echo ""

    cd "$AI_TOOLKIT_DIR"
    python run.py "${config_path}"
    cd "$BEATCANVAS_DIR"

    log "Training complete: ${name}"
    log "Output: output/loras/${name}/"
}

# ── Single LoRA Pipeline ─────────────────────────────────────

run_single() {
    local name="$1" query="$2" type="$3" trigger="$4" count="$5"
    local skip_collect="$6" train_only="$7"

    log_section "LoRA PIPELINE: ${name}"
    local start_time=$(date +%s)

    if [ "$train_only" != "true" ]; then
        # Step 1: Collect (unless skipped)
        if [ "$skip_collect" != "true" ] && [ -n "$query" ]; then
            step_collect "$name" "$query" "$count"
        else
            log "Skipping collection (using existing dataset)"
        fi

        # Step 2: Caption
        step_caption "$name" "$trigger"

        # Step 3: Generate config
        step_generate_config "$name" "$type" "$trigger"
    fi

    # Step 4: Train
    step_train "$name"

    local end_time=$(date +%s)
    local elapsed=$(( (end_time - start_time) / 60 ))
    log "Pipeline complete for ${name} in ${elapsed} minutes"
}

# ── Batch Pipeline ────────────────────────────────────────────

run_batch() {
    log_section "BATCH MODE: Training ${#TROP_ROCK_LIBRARY[@]} LoRAs"
    local total_start=$(date +%s)
    local completed=0
    local failed=0

    for entry in "${TROP_ROCK_LIBRARY[@]}"; do
        IFS='|' read -r name query type trigger count <<< "$entry"

        log "Starting LoRA $((completed + failed + 1))/${#TROP_ROCK_LIBRARY[@]}: ${name}"

        if run_single "$name" "$query" "$type" "$trigger" "$count" "false" "false"; then
            completed=$((completed + 1))
        else
            failed=$((failed + 1))
            log "WARNING: ${name} failed, continuing with next..."
        fi
    done

    local total_end=$(date +%s)
    local total_elapsed=$(( (total_end - total_start) / 60 ))

    log_section "BATCH COMPLETE"
    echo "  Completed: ${completed}/${#TROP_ROCK_LIBRARY[@]}"
    echo "  Failed:    ${failed}"
    echo "  Total time: ${total_elapsed} minutes"
    echo "  Output:    ${OUTPUT_DIR}/"
}

# ── Argument Parsing ──────────────────────────────────────────

NAME=""
QUERY=""
TYPE="scene"
TRIGGER=""
COUNT=30
SKIP_COLLECT=false
TRAIN_ONLY=false
BATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --name) NAME="$2"; shift 2;;
        --query) QUERY="$2"; shift 2;;
        --type) TYPE="$2"; shift 2;;
        --trigger) TRIGGER="$2"; shift 2;;
        --count) COUNT="$2"; shift 2;;
        --vram) VRAM="$2"; shift 2;;
        --skip-collect) SKIP_COLLECT=true; shift;;
        --train-only) TRAIN_ONLY=true; shift;;
        --batch) BATCH=true; shift;;
        --help|-h)
            echo "Usage:"
            echo "  bash tools/train_lora.sh --name NAME --query 'search terms' --type scene"
            echo "  bash tools/train_lora.sh --name NAME --train-only"
            echo "  bash tools/train_lora.sh --batch"
            echo ""
            echo "Options:"
            echo "  --name NAME          LoRA name (required for single mode)"
            echo "  --query 'TERMS'      Pexels search query"
            echo "  --type TYPE          scene|style|character (default: scene)"
            echo "  --trigger WORD       Trigger word for captions"
            echo "  --count N            Number of images to collect (default: 30)"
            echo "  --vram N             GPU VRAM in GB (default: auto-detect)"
            echo "  --skip-collect       Skip image collection (use existing dataset)"
            echo "  --train-only         Skip collect+caption+config, just train"
            echo "  --batch              Train all Trop Rock LoRAs"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1;;
    esac
done

# ── Main ──────────────────────────────────────────────────────

detect_vram

if [ "$BATCH" = true ]; then
    run_batch
elif [ -n "$NAME" ]; then
    if [ -z "$TRIGGER" ]; then
        TRIGGER="$NAME"
    fi
    run_single "$NAME" "$QUERY" "$TYPE" "$TRIGGER" "$COUNT" "$SKIP_COLLECT" "$TRAIN_ONLY"
else
    echo "ERROR: Specify --name for single LoRA or --batch for all."
    echo "Run with --help for usage."
    exit 1
fi
