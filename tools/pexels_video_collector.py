"""
Pexels Video Collector for Music Video Production

Downloads video clips from Pexels API by search query for rotoscope animation
or stock footage for music videos.

Usage:
    # Single scene
    python tools/pexels_video_collector.py "beach sunset" --count 5 --duration 10-20

    # Multiple scenes for a music video
    python tools/pexels_video_collector.py "Island Girl" \
        --scenes "beach sunset,couple dancing,tropical woman,ocean waves,bonfire" \
        --clips-per-scene 3 \
        --output datasets/island-girl-footage/

    # Specific quality/orientation
    python tools/pexels_video_collector.py "beach walking" \
        --count 10 --orientation landscape --min-width 1920 --min-duration 10

Requires PEXELS_API_KEY in ~/.claude/.env or environment.
Free tier: 200 requests/hour, 20,000 requests/month.
All Pexels videos are free to use (Pexels License).
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
from typing import List, Dict, Optional, Tuple

# Environment loading
from dotenv import load_dotenv
global_env = Path.home() / ".claude" / ".env"
if global_env.exists():
    load_dotenv(dotenv_path=global_env, override=False)
load_dotenv(override=True)

PEXELS_VIDEO_API_URL = "https://api.pexels.com/videos/search"
MIN_VIDEO_WIDTH = 1920
MIN_VIDEO_HEIGHT = 1080
MIN_DURATION = 5  # seconds
MAX_DURATION = 30  # seconds
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def get_api_key() -> str:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        print("ERROR: PEXELS_API_KEY not found.")
        print("Get a free key at https://www.pexels.com/api/")
        print("Add to ~/.claude/.env: PEXELS_API_KEY=your_key_here")
        sys.exit(1)
    return key


def parse_duration_range(duration_str: str) -> Tuple[int, int]:
    """Parse duration string like '10-20' into (min, max) tuple."""
    if "-" in duration_str:
        min_dur, max_dur = duration_str.split("-")
        return int(min_dur), int(max_dur)
    else:
        dur = int(duration_str)
        return dur, dur + 10  # Default range


def search_pexels_videos(
    query: str,
    api_key: str,
    page: int = 1,
    per_page: int = 30,
    orientation: Optional[str] = None,
    min_width: int = MIN_VIDEO_WIDTH,
    min_height: int = MIN_VIDEO_HEIGHT,
) -> Dict:
    """Search Pexels API for videos."""
    params = f"query={urllib.parse.quote(query)}&page={page}&per_page={per_page}"
    if orientation:
        params += f"&orientation={orientation}"
    if min_width:
        params += f"&min_width={min_width}"
    if min_height:
        params += f"&min_height={min_height}"

    url = f"{PEXELS_VIDEO_API_URL}?{params}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", api_key)
    req.add_header("User-Agent", "BeatCanvas-Video-Collector/1.0")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            return search_pexels_videos(
                query, api_key, page, per_page, orientation, min_width, min_height
            )
        raise


def download_video(url: str, output_path: Path, show_progress: bool = True) -> bool:
    """Download a single video with progress indicator."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "BeatCanvas-Video-Collector/1.0")

        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('content-length', 0))
            data = bytearray()
            chunk_size = 8192
            downloaded = 0

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data.extend(chunk)
                downloaded += len(chunk)

                if show_progress and total_size > 0:
                    percent = (downloaded / total_size) * 100
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"\r    Downloading: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)", end="")

            if show_progress:
                print()  # New line after progress

        output_path.write_bytes(bytes(data))
        return True
    except Exception as e:
        print(f"\n  Failed to download: {e}")
        return False


def content_hash(filepath: Path) -> str:
    """SHA256 hash for deduplication."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()[:16]


def get_best_video_file(video_files: List[Dict]) -> Optional[Dict]:
    """
    Select the best video file from available quality options.
    Prioritizes HD/FHD, then falls back to SD if needed.
    """
    if not video_files:
        return None

    # Prefer hd, then sd
    for quality in ["hd", "sd"]:
        for vf in video_files:
            if vf.get("quality") == quality:
                return vf

    # Fallback to first available
    return video_files[0]


def collect_videos(
    query: str,
    output_dir: Path,
    target_count: int = 5,
    orientation: Optional[str] = None,
    min_width: int = MIN_VIDEO_WIDTH,
    min_height: int = MIN_VIDEO_HEIGHT,
    duration_range: Tuple[int, int] = (MIN_DURATION, MAX_DURATION),
) -> List[Path]:
    """
    Collect videos from Pexels for rotoscope or stock footage.

    Returns list of downloaded video paths.
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
    max_pages = 10  # Pexels video search is more limited

    min_dur, max_dur = duration_range
    print(f"Collecting {target_count} videos for: '{query}'")
    print(f"Output: {output_dir}")
    print(f"Min resolution: {min_width}x{min_height}")
    print(f"Duration: {min_dur}-{max_dur} seconds")
    print()

    while len(downloaded) < target_count and page <= max_pages:
        print(f"  Fetching page {page}...")
        results = search_pexels_videos(
            query, api_key, page=page, orientation=orientation,
            min_width=min_width, min_height=min_height
        )

        videos = results.get("videos", [])
        if not videos:
            print("  No more results from Pexels.")
            break

        for video in videos:
            if len(downloaded) >= target_count:
                break

            video_id = str(video["id"])
            width = video["width"]
            height = video["height"]
            duration = video.get("duration", 0)

            # Skip if already downloaded
            if video_id in manifest["downloaded"]:
                continue

            # Duration filter
            if duration < min_dur or duration > max_dur:
                manifest["rejected"].append(
                    {"id": video_id, "reason": f"duration_{duration}s"}
                )
                continue

            # Get best quality video file
            video_file = get_best_video_file(video.get("video_files", []))
            if not video_file:
                manifest["rejected"].append(
                    {"id": video_id, "reason": "no_video_files"}
                )
                continue

            video_url = video_file.get("link")
            if not video_url:
                continue

            # Determine file extension from URL
            ext = ".mp4"  # Pexels typically serves MP4
            filename = f"video_{len(downloaded)+1:03d}{ext}"
            filepath = output_dir / filename

            quality = video_file.get("quality", "unknown")
            file_mb = video_file.get("width", 0) * video_file.get("height", 0) / (1024 * 1024)

            print(f"  [{len(downloaded)+1}/{target_count}] {filename} ({width}x{height}, {duration}s, {quality})")

            if download_video(video_url, filepath):
                # Dedup check
                file_hash = content_hash(filepath)
                if file_hash in seen_hashes:
                    print(f"    Duplicate detected, skipping.")
                    filepath.unlink()
                    continue

                seen_hashes.add(file_hash)
                manifest["downloaded"][video_id] = file_hash
                downloaded.append(filepath)

                # Save attribution (Pexels license requires it)
                meta = {
                    "pexels_id": video_id,
                    "user": video.get("user", {}).get("name", ""),
                    "user_url": video.get("user", {}).get("url", ""),
                    "pexels_url": video.get("url", ""),
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "quality": quality,
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
    print(f"Done! Downloaded {len(downloaded)} videos to {output_dir}")
    print(f"  Total API pages fetched: {page - 1}")
    print(f"  Videos rejected (duration/quality): {len(manifest['rejected'])}")

    # Calculate total size
    total_mb = sum(f.stat().st_size for f in downloaded) / (1024 * 1024)
    print(f"  Total size: {total_mb:.1f}MB")

    return downloaded


def collect_multi_scene(
    project_name: str,
    scenes: List[str],
    output_dir: Path,
    clips_per_scene: int = 3,
    **kwargs
) -> Dict[str, List[Path]]:
    """
    Collect videos for multiple scenes in a music video project.

    Returns dict mapping scene names to downloaded video paths.
    """
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Multi-Scene Video Collection: {project_name}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Scenes: {len(scenes)}")
    print(f"  Clips per scene: {clips_per_scene}")
    print()

    results = {}

    for i, scene in enumerate(scenes, 1):
        scene_slug = scene.lower().replace(" ", "-").replace("/", "-")
        scene_slug = "".join(c for c in scene_slug if c.isalnum() or c == "-")
        scene_dir = output_dir / scene_slug

        print(f"[{i}/{len(scenes)}] Scene: '{scene}'")
        print(f"          Output: {scene_dir}")
        print()

        videos = collect_videos(
            query=scene,
            output_dir=scene_dir,
            target_count=clips_per_scene,
            **kwargs
        )

        results[scene] = videos
        print()

    # Summary
    total_videos = sum(len(v) for v in results.values())
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Collection Complete!")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Total videos: {total_videos}")
    print(f"  Output: {output_dir}")
    print()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Download videos from Pexels for music video production"
    )
    parser.add_argument("query", help="Search query or project name")
    parser.add_argument(
        "--count", type=int, default=5,
        help="Number of videos to download per scene (default: 5)"
    )
    parser.add_argument(
        "--scenes", type=str, default=None,
        help="Comma-separated scene queries for multi-scene collection"
    )
    parser.add_argument(
        "--clips-per-scene", type=int, default=3,
        help="Videos per scene in multi-scene mode (default: 3)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output directory (default: datasets/<query-slug>/)"
    )
    parser.add_argument(
        "--orientation",
        choices=["landscape", "portrait", "square"],
        default="landscape",
        help="Video orientation filter (default: landscape)"
    )
    parser.add_argument(
        "--min-width", type=int, default=MIN_VIDEO_WIDTH,
        help=f"Minimum video width (default: {MIN_VIDEO_WIDTH})"
    )
    parser.add_argument(
        "--min-height", type=int, default=MIN_VIDEO_HEIGHT,
        help=f"Minimum video height (default: {MIN_VIDEO_HEIGHT})"
    )
    parser.add_argument(
        "--duration", type=str, default=f"{MIN_DURATION}-{MAX_DURATION}",
        help=f"Duration range in seconds, e.g. '10-20' (default: {MIN_DURATION}-{MAX_DURATION})"
    )
    parser.add_argument(
        "--min-duration", type=int, default=None,
        help="Minimum duration in seconds (overrides --duration)"
    )
    parser.add_argument(
        "--max-duration", type=int, default=None,
        help="Maximum duration in seconds (overrides --duration)"
    )

    args = parser.parse_args()

    # Generate output directory from query if not specified
    if args.output:
        output_dir = Path(args.output)
    else:
        slug = args.query.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        output_dir = Path("datasets") / slug

    # Parse duration
    if args.min_duration and args.max_duration:
        duration_range = (args.min_duration, args.max_duration)
    else:
        duration_range = parse_duration_range(args.duration)

    # Multi-scene or single scene mode
    if args.scenes:
        scene_list = [s.strip() for s in args.scenes.split(",")]
        collect_multi_scene(
            project_name=args.query,
            scenes=scene_list,
            output_dir=output_dir,
            clips_per_scene=args.clips_per_scene,
            orientation=args.orientation,
            min_width=args.min_width,
            min_height=args.min_height,
            duration_range=duration_range,
        )
    else:
        collect_videos(
            query=args.query,
            output_dir=output_dir,
            target_count=args.count,
            orientation=args.orientation,
            min_width=args.min_width,
            min_height=args.min_height,
            duration_range=duration_range,
        )


if __name__ == "__main__":
    import urllib.parse
    main()
