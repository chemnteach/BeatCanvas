#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Island Girl - Footage Collection Script
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Collects stock video footage from Pexels for "Island Girl" music video.
# Downloads 3-5 clips per scene type, organized by lyric section.
#
# Usage:
#   bash tools/collect_island_girl_footage.sh
#
# Output:
#   datasets/island-girl-footage/
#     ├── airport/           # Intro: "Hello, American Airlines"
#     ├── beach-solo/        # Verse 1: Walking alone
#     ├── tropical-woman/    # Chorus: Island Girl
#     ├── couple-beach/      # Verse 2: "Vamanos a la playa"
#     ├── bonfire-night/     # Verse 2: Beach bonfire
#     ├── sunset-overhead/   # Bridge: "Cloudless sky"
#     ├── couple-dancing/    # Final Chorus: Dancing together
#     └── ocean-waves/       # B-roll/transitions
#
# Requires: PEXELS_API_KEY in ~/.claude/.env
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Scene definitions matching lyrics
# Format: "search query|clips|duration range"
SCENES=(
    "airport terminal modern|3|5-10"
    "beach walking alone sunset man|4|10-15"
    "tropical woman beach smiling|5|8-15"
    "couple on beach tropical|5|10-20"
    "beach bonfire night flames|3|8-15"
    "beach overhead aerial cloudless|3|10-20"
    "couple dancing beach sunset|5|10-20"
    "ocean waves tropical beach|4|8-15"
    "palm trees swaying wind|3|8-12"
    "sunset golden hour beach|4|10-15"
)

# Folder names (clean slugs)
FOLDERS=(
    "airport"
    "beach-solo"
    "tropical-woman"
    "couple-beach"
    "bonfire-night"
    "sunset-overhead"
    "couple-dancing"
    "ocean-waves"
    "palm-trees"
    "sunset"
)

OUTPUT_BASE="datasets/island-girl-footage"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Island Girl - Footage Collection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  This will collect ~35-40 video clips from Pexels."
echo "  Estimated size: 300-500MB"
echo "  Estimated time: 5-10 minutes"
echo ""
echo "  Output: $OUTPUT_BASE/"
echo ""

# Check for API key
if [ -z "$PEXELS_API_KEY" ]; then
    echo "ERROR: PEXELS_API_KEY not found in environment."
    echo "Add it to ~/.claude/.env:"
    echo "  PEXELS_API_KEY=your_key_here"
    exit 1
fi

cd "$PROJECT_DIR"

# Collect each scene type
for i in "${!SCENES[@]}"; do
    IFS='|' read -r query clips duration <<< "${SCENES[$i]}"
    folder="${FOLDERS[$i]}"
    output_dir="$OUTPUT_BASE/$folder"

    echo ""
    echo "[$((i+1))/${#SCENES[@]}] Collecting: $folder"
    echo "    Query: $query"
    echo "    Clips: $clips"
    echo "    Duration: ${duration}s"
    echo ""

    python tools/pexels_video_collector.py "$query" \
        --count "$clips" \
        --output "$output_dir" \
        --duration "$duration" \
        --orientation landscape \
        --min-width 1920

    echo ""
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Collection Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Calculate totals
total_videos=$(find "$OUTPUT_BASE" -name "video_*.mp4" 2>/dev/null | wc -l)
total_size=$(du -sh "$OUTPUT_BASE" 2>/dev/null | cut -f1)

echo "  Total videos: $total_videos"
echo "  Total size: $total_size"
echo "  Output: $OUTPUT_BASE/"
echo ""
echo "Next steps:"
echo "  1. Review footage in $OUTPUT_BASE/"
echo "  2. Delete any clips you don't want to use"
echo "  3. When you have the MP3, run rotoscope processing"
echo ""
