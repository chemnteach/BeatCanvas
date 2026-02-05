#!/usr/bin/env python3
"""
End-to-end BeatCanvas workflow test
Tests the complete pipeline from audio upload to video generation
"""

import requests
import json
import time
import os
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
AUDIO_FILE = "data/uploads/WrapAroundMeVoxLoop-10Bar_keyC#min_88bpm.wav"
VISUAL_PROMPT = "Abstract colorful patterns flowing in rhythm with music, geometric shapes dancing"
QUALITY_TIER = "basic"  # 12 scenes for cost control
PROVIDER_PREFERENCE = "dalle"

def test_audio_upload_and_generation():
    """Test the complete video generation workflow"""

    print("[MUSIC] BeatCanvas End-to-End Test")
    print("=" * 50)

    # Check if audio file exists
    if not Path(AUDIO_FILE).exists():
        print(f"[ERROR] Audio file not found: {AUDIO_FILE}")
        return False

    print(f"[FILE] Audio file: {Path(AUDIO_FILE).name}")
    print(f"[PROMPT] Prompt: {VISUAL_PROMPT}")
    print(f"[QUALITY] Quality: {QUALITY_TIER}")
    print()

    # Prepare file upload
    try:
        with open(AUDIO_FILE, 'rb') as f:
            files = {'audio': f}
            data = {
                'visual_prompt': VISUAL_PROMPT,
                'quality_tier': QUALITY_TIER,
                'provider_preference': PROVIDER_PREFERENCE
            }

            print("[START] Starting video generation...")
            response = requests.post(
                f"{API_BASE}/api/generate-video",
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                task_id = result.get('task_id')
                print(f"[OK] Generation started! Task ID: {task_id}")

                # Monitor progress (simplified - in real app would use WebSocket)
                print("\n[PROGRESS] Monitoring progress...")
                return monitor_generation(task_id)

            else:
                print(f"[ERROR] Failed to start generation: {response.status_code}")
                print(f"Response: {response.text}")
                return False

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return False

def monitor_generation(task_id):
    """Monitor the generation progress (simplified polling)"""
    max_wait_time = 600  # 10 minutes max
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        time.sleep(10)  # Check every 10 seconds

        # In a real implementation, we'd use WebSocket
        # For now, just check if output file exists
        output_file = f"output/{task_id}.mp4"
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            print(f"[SUCCESS] Video generated successfully!")
            print(f"[FILE] Output: {output_file}")
            print(f"[SIZE] Size: {file_size / (1024*1024):.2f} MB")
            return True

        elapsed = time.time() - start_time
        print(f"[WAIT] Waiting... ({elapsed:.0f}s elapsed)")

    print(f"[TIMEOUT] Timeout after {max_wait_time/60:.1f} minutes")
    return False

def main():
    """Run the end-to-end test"""

    # Check server is running
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code != 200:
            print("[ERROR] Server not responding")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to server. Is it running on port 8000?")
        return False

    print("[OK] Server is running")
    print()

    # Run the test
    success = test_audio_upload_and_generation()

    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] END-TO-END TEST PASSED!")
        print("BeatCanvas pipeline is working correctly.")
    else:
        print("[ERROR] END-TO-END TEST FAILED!")
        print("Check the output above for details.")

    return success

if __name__ == "__main__":
    main()