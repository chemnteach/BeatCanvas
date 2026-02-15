"""
Pexels Image Collector for LoRA Training Datasets

Downloads images from Pexels API by search query for LoRA training.
Handles pagination, deduplication, and quality filtering.

Usage:
    python tools/pexels_collector.py "tiki bar interior" --count 30
    python tools/pexels_collector.py "beach sunset tropical" --count 50 --orientation landscape
    python tools/pexels_collector.py "boat deck ocean" --count 30 --min-width 1024

Requires PEXELS_API_KEY in ~/.claude/.env or environment.
Free tier: 200 requests/hour, 20,000 requests/month.
All Pexels images are free to use (Pexels License).
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional

# Environment loading
from dotenv import load_dotenv
global_env = Path.home() / ".claude" / ".env"
if global_env.exists():
    load_dotenv(dotenv_path=global_env, override=False)
load_dotenv(override=True)

PEXELS_API_URL = "https://api.pexels.com/v1/search"
MIN_IMAGE_WIDTH = 1024
MIN_IMAGE_HEIGHT = 768
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def get_api_key() -> str:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        print("ERROR: PEXELS_API_KEY not found.")
        print("Get a free key at https://www.pexels.com/api/")
        print("Add to ~/.claude/.env: PEXELS_API_KEY=your_key_here")
        sys.exit(1)
    return key


def search_pexels(
    query: str,
    api_key: str,
    page: int = 1,
    per_page: int = 40,
    orientation: Optional[str] = None,
) -> Dict:
    """Search Pexels API for images."""
    params = f"query={urllib.parse.quote(query)}&page={page}&per_page={per_page}"
    if orientation:
        params += f"&orientation={orientation}"

    url = f"{PEXELS_API_URL}?{params}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", api_key)

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            return search_pexels(query, api_key, page, per_page, orientation)
        raise


def download_image(url: str, output_path: Path) -> bool:
    """Download a single image."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "BeatCanvas-LoRA-Collector/1.0")
        with urllib.request.urlopen(req) as response:
            data = response.read()
        output_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  Failed to download: {e}")
        return False


def content_hash(filepath: Path) -> str:
    """SHA256 hash for deduplication."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()[:16]


def collect_images(
    query: str,
    output_dir: Path,
    target_count: int = 30,
    orientation: Optional[str] = None,
    min_width: int = MIN_IMAGE_WIDTH,
    min_height: int = MIN_IMAGE_HEIGHT,
) -> List[Path]:
    """
    Collect images from Pexels for a LoRA training dataset.

    Returns list of downloaded image paths.
    """
    api_key = get_api_key()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track what we've already downloaded (for resume support)
    manifest_path = output_dir / "_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"query": query, "downloaded": {}, "rejected": []}

    downloaded = []
    seen_hashes = set(manifest["downloaded"].values())
    page = 1
    attempts = 0
    max_pages = 20  # Pexels returns max 80 pages, but 20 is plenty

    print(f"Collecting {target_count} images for: '{query}'")
    print(f"Output: {output_dir}")
    print(f"Min resolution: {min_width}x{min_height}")
    print()

    while len(downloaded) < target_count and page <= max_pages:
        print(f"  Fetching page {page}...")
        results = search_pexels(query, api_key, page=page, orientation=orientation)

        photos = results.get("photos", [])
        if not photos:
            print("  No more results from Pexels.")
            break

        for photo in photos:
            if len(downloaded) >= target_count:
                break

            photo_id = str(photo["id"])
            width = photo["width"]
            height = photo["height"]

            # Skip if already downloaded
            if photo_id in manifest["downloaded"]:
                continue

            # Quality filter
            if width < min_width or height < min_height:
                manifest["rejected"].append(
                    {"id": photo_id, "reason": f"too_small_{width}x{height}"}
                )
                continue

            # Download the "large2x" version (best quality without watermark)
            img_url = photo["src"].get("large2x") or photo["src"].get("original")
            ext = ".jpg"  # Pexels serves JPEG
            filename = f"img_{len(downloaded)+1:03d}{ext}"
            filepath = output_dir / filename

            print(f"  [{len(downloaded)+1}/{target_count}] Downloading {filename} ({width}x{height})...")
            if download_image(img_url, filepath):
                # Dedup check
                file_hash = content_hash(filepath)
                if file_hash in seen_hashes:
                    print(f"    Duplicate detected, skipping.")
                    filepath.unlink()
                    continue

                seen_hashes.add(file_hash)
                manifest["downloaded"][photo_id] = file_hash
                downloaded.append(filepath)

                # Save attribution (Pexels license requires it)
                meta = {
                    "pexels_id": photo_id,
                    "photographer": photo.get("photographer", ""),
                    "photographer_url": photo.get("photographer_url", ""),
                    "pexels_url": photo.get("url", ""),
                    "width": width,
                    "height": height,
                }
                meta_path = filepath.with_suffix(".meta.json")
                meta_path.write_text(json.dumps(meta, indent=2))

            attempts += 1
            time.sleep(RATE_LIMIT_DELAY)

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    # Save manifest for resume support
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print()
    print(f"Done! Downloaded {len(downloaded)} images to {output_dir}")
    print(f"  Total API pages fetched: {page - 1}")
    print(f"  Images rejected (too small): {len(manifest['rejected'])}")

    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Download images from Pexels for LoRA training datasets"
    )
    parser.add_argument("query", help="Search query (e.g., 'tiki bar interior')")
    parser.add_argument(
        "--count", type=int, default=30, help="Number of images to download (default: 30)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: datasets/<query-slug>/)",
    )
    parser.add_argument(
        "--orientation",
        choices=["landscape", "portrait", "square"],
        default="landscape",
        help="Image orientation filter (default: landscape)",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        default=MIN_IMAGE_WIDTH,
        help=f"Minimum image width (default: {MIN_IMAGE_WIDTH})",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        default=MIN_IMAGE_HEIGHT,
        help=f"Minimum image height (default: {MIN_IMAGE_HEIGHT})",
    )

    args = parser.parse_args()

    # Generate output directory from query if not specified
    if args.output:
        output_dir = Path(args.output)
    else:
        slug = args.query.lower().replace(" ", "-").replace("/", "-")
        # Keep only alphanumeric and hyphens
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        output_dir = Path("datasets") / slug

    collect_images(
        query=args.query,
        output_dir=output_dir,
        target_count=args.count,
        orientation=args.orientation,
        min_width=args.min_width,
        min_height=args.min_height,
    )


if __name__ == "__main__":
    import urllib.parse
    main()
