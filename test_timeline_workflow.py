#!/usr/bin/env python3
"""
Interactive Timeline and Scene Editing - End-to-End Test Script

This script tests the complete workflow:
1. Video generation with storyboard
2. Timeline component integration
3. Scene editing and regeneration
4. Video rebuilding after changes

Usage:
    python test_timeline_workflow.py

Requirements:
    - Backend server running on localhost:8000
    - Frontend running on localhost:3000
    - Valid API keys in ~/.claude/.env
    - Test audio file in data/uploads/
"""

import os
import json
import time
import requests
import asyncio
import websocket
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add backend to path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

from src.utils.env_loader import load_environment_variables
load_environment_variables()

class TimelineWorkflowTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.test_audio_path = "data/uploads/test_song.mp3"
        self.task_id = None
        self.storyboard = None
        self.video_url = None

    def setup_test_environment(self):
        """Prepare test environment and validate dependencies"""
        print("🔧 Setting up test environment...")

        # Check if backend is running
        try:
            response = requests.get(f"{self.base_url}/")
            print(f"✅ Backend running at {self.base_url}")
        except requests.exceptions.ConnectionError:
            print(f"❌ Backend not running at {self.base_url}")
            print("   Start with: cd backend && uvicorn main:app --reload")
            return False

        # Check if frontend is accessible
        try:
            response = requests.get(self.frontend_url)
            print(f"✅ Frontend accessible at {self.frontend_url}")
        except requests.exceptions.ConnectionError:
            print(f"⚠️  Frontend not running at {self.frontend_url}")
            print("   Start with: cd frontend && npm start")

        # Check for test audio file
        if not os.path.exists(self.test_audio_path):
            print(f"❌ Test audio file not found: {self.test_audio_path}")
            print("   Add a test MP3 file to data/uploads/")
            return False
        print(f"✅ Test audio file found: {self.test_audio_path}")

        # Check API keys
        required_keys = ["OPENAI_API_KEY"]
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        if missing_keys:
            print(f"❌ Missing API keys: {missing_keys}")
            print("   Add to ~/.claude/.env")
            return False
        print("✅ API keys configured")

        return True

    def test_video_generation(self) -> bool:
        """Test initial video generation with storyboard"""
        print("\n🎬 Testing video generation...")

        # Prepare generation request
        generation_data = {
            "user_prompt": "A romantic couple walking through a magical forest at sunset",
            "quality_tier": "professional",  # 24 scenes
            "music_style": "romantic",
            "visual_style": "cinematic",
            "effects": ["fade_in", "zoom_in", "pan_left"]
        }

        # Upload audio file
        with open(self.test_audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = generation_data

            response = requests.post(
                f"{self.base_url}/api/generate-video",
                files=files,
                data=data
            )

        if response.status_code != 200:
            print(f"❌ Video generation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False

        result = response.json()
        self.task_id = result.get("task_id")

        if not self.task_id:
            print("❌ No task_id returned from generation")
            return False

        print(f"✅ Video generation started with task_id: {self.task_id}")

        # Monitor generation progress via WebSocket
        return self.monitor_generation_progress()

    def monitor_generation_progress(self) -> bool:
        """Monitor video generation via WebSocket"""
        print("📡 Monitoring generation progress...")

        # Simple WebSocket monitoring (synchronous for testing)
        max_wait_time = 600  # 10 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Check status via REST API
            response = requests.get(f"{self.base_url}/api/status/{self.task_id}")
            if response.status_code == 200:
                status = response.json()
                current_step = status.get("current_step", "unknown")
                progress = status.get("progress", 0)

                print(f"   Step: {current_step}, Progress: {progress}%")

                if status.get("status") == "completed":
                    self.storyboard = status.get("storyboard", [])
                    self.video_url = status.get("video_url")
                    print(f"✅ Video generation completed!")
                    print(f"   Storyboard scenes: {len(self.storyboard)}")
                    print(f"   Video URL: {self.video_url}")
                    return True
                elif status.get("status") == "failed":
                    print(f"❌ Video generation failed: {status.get('error', 'Unknown error')}")
                    return False

            time.sleep(10)  # Check every 10 seconds

        print(f"❌ Video generation timed out after {max_wait_time} seconds")
        return False

    def test_timeline_integration(self) -> bool:
        """Test timeline component functionality"""
        print("\n⏰ Testing timeline integration...")

        if not self.storyboard:
            print("❌ No storyboard available for timeline testing")
            return False

        # Validate storyboard structure for timeline
        required_fields = ["timestamp_start", "timestamp_end", "description", "mood"]
        for i, scene in enumerate(self.storyboard):
            for field in required_fields:
                if field not in scene:
                    print(f"❌ Scene {i} missing required field: {field}")
                    return False

        print(f"✅ Storyboard structure valid for timeline ({len(self.storyboard)} scenes)")

        # Calculate timeline segments
        total_duration = max(scene["timestamp_end"] for scene in self.storyboard)
        print(f"   Total video duration: {total_duration:.2f} seconds")

        # Test scene timing calculations
        scene_durations = []
        for i, scene in enumerate(self.storyboard):
            duration = scene["timestamp_end"] - scene["timestamp_start"]
            scene_durations.append(duration)
            print(f"   Scene {i+1}: {scene['timestamp_start']:.2f}s - {scene['timestamp_end']:.2f}s ({duration:.2f}s)")

        avg_duration = sum(scene_durations) / len(scene_durations)
        print(f"   Average scene duration: {avg_duration:.2f}s")

        # Validate timeline requirements
        if len(self.storyboard) < 12:
            print(f"⚠️  Fewer scenes than expected: {len(self.storyboard)} < 12")
        if any(d < 1.0 for d in scene_durations):
            print("⚠️  Some scenes are very short (< 1 second)")

        print("✅ Timeline integration test passed")
        return True

    def test_scene_editing(self) -> bool:
        """Test scene editing and regeneration functionality"""
        print("\n✏️ Testing scene editing...")

        if not self.storyboard or len(self.storyboard) == 0:
            print("❌ No storyboard available for scene editing")
            return False

        # Select middle scene for editing
        scene_index = len(self.storyboard) // 2
        original_scene = self.storyboard[scene_index]

        print(f"   Editing scene {scene_index + 1}/{len(self.storyboard)}")
        print(f"   Original description: {original_scene['description']}")

        # Prepare scene edit request
        edit_request = {
            "task_id": self.task_id,
            "scene_index": scene_index,
            "new_description": "Two characters sharing a romantic kiss under moonlight",
            "provider": "nano_banana",  # Cheaper for testing
            "effects": ["fade_in", "zoom_in"]
        }

        # Test scene regeneration endpoint
        response = requests.post(
            f"{self.base_url}/api/regenerate-scene",
            json=edit_request
        )

        if response.status_code != 200:
            print(f"❌ Scene regeneration failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False

        result = response.json()
        print(f"✅ Scene regeneration started")
        print(f"   Estimated cost: ${result.get('estimated_cost', 'unknown')}")

        # Monitor scene regeneration progress
        max_wait_time = 120  # 2 minutes for single scene
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            response = requests.get(f"{self.base_url}/api/status/{self.task_id}")
            if response.status_code == 200:
                status = response.json()

                # Check for scene regeneration completion
                if "scene_regeneration_complete" in status.get("events", []):
                    print("✅ Scene regeneration completed")
                    return True

            time.sleep(5)  # Check every 5 seconds

        print(f"❌ Scene regeneration timed out after {max_wait_time} seconds")
        return False

    def test_video_rebuilding(self) -> bool:
        """Test video rebuilding after scene changes"""
        print("\n🔄 Testing video rebuilding...")

        rebuild_request = {
            "task_id": self.task_id,
            "rebuild_type": "full"  # or "preview" for faster testing
        }

        response = requests.post(
            f"{self.base_url}/api/rebuild-video",
            json=rebuild_request
        )

        if response.status_code != 200:
            print(f"❌ Video rebuild failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False

        print("✅ Video rebuild started")

        # Monitor rebuild progress
        max_wait_time = 300  # 5 minutes for video rebuild
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            response = requests.get(f"{self.base_url}/api/status/{self.task_id}")
            if response.status_code == 200:
                status = response.json()

                # Check for video rebuild completion
                if "video_update_available" in status.get("events", []):
                    new_video_url = status.get("video_url")
                    print(f"✅ Video rebuild completed")
                    print(f"   New video URL: {new_video_url}")
                    return True

            time.sleep(10)  # Check every 10 seconds

        print(f"❌ Video rebuild timed out after {max_wait_time} seconds")
        return False

    def test_frontend_integration(self) -> bool:
        """Test frontend component integration"""
        print("\n🖥️ Testing frontend integration...")

        # Check if timeline component files exist
        timeline_component = Path("frontend/src/components/InteractiveTimeline.tsx")
        scene_modal_component = Path("frontend/src/components/SceneEditModal.tsx")
        video_preview_component = Path("frontend/src/components/VideoPreview.tsx")

        components = [
            ("InteractiveTimeline", timeline_component),
            ("SceneEditModal", scene_modal_component),
            ("VideoPreview", video_preview_component)
        ]

        all_exist = True
        for name, path in components:
            if path.exists():
                print(f"✅ {name} component exists")
            else:
                print(f"❌ {name} component missing: {path}")
                all_exist = False

        if not all_exist:
            return False

        # Check TypeScript interfaces
        video_generator = Path("frontend/src/components/VideoGenerator.tsx")
        if video_generator.exists():
            with open(video_generator, 'r', encoding='utf-8') as f:
                content = f.read()
                if "handleSceneEdit" in content and "handleSceneRegenerate" in content:
                    print("✅ VideoGenerator has scene editing integration")
                else:
                    print("❌ VideoGenerator missing scene editing functions")
                    return False
        else:
            print("❌ VideoGenerator component missing")
            return False

        print("✅ Frontend integration test passed")
        return True

    def generate_test_report(self, results: Dict[str, bool]):
        """Generate comprehensive test report"""
        print("\n📊 Test Results Summary")
        print("=" * 50)

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")

        print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if all(results.values()):
            print("\n🎉 All tests passed! Interactive timeline workflow is ready.")
            print("\nNext steps:")
            print("1. Test in browser at http://localhost:3000")
            print("2. Generate a video and verify timeline functionality")
            print("3. Try editing a scene and regenerating")
            print("4. Verify video updates after scene changes")
        else:
            print("\n⚠️  Some tests failed. Check the errors above.")
            print("\nTroubleshooting:")
            print("- Ensure backend and frontend are running")
            print("- Verify API keys are configured")
            print("- Check component files exist and are properly integrated")

    def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 Interactive Timeline Workflow Test Suite")
        print("=" * 50)

        if not self.setup_test_environment():
            print("❌ Test environment setup failed")
            return

        results = {}

        # Run tests in sequence
        test_methods = [
            ("Environment Setup", lambda: True),  # Already passed
            ("Video Generation", self.test_video_generation),
            ("Timeline Integration", self.test_timeline_integration),
            ("Scene Editing", self.test_scene_editing),
            ("Video Rebuilding", self.test_video_rebuilding),
            ("Frontend Integration", self.test_frontend_integration)
        ]

        for test_name, test_method in test_methods:
            if test_name == "Environment Setup":
                results[test_name] = True
                continue

            try:
                results[test_name] = test_method()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False

            # Stop on critical failures
            if test_name in ["Video Generation", "Timeline Integration"] and not results[test_name]:
                print(f"💥 Critical test failed: {test_name}. Stopping test suite.")
                break

        self.generate_test_report(results)

if __name__ == "__main__":
    tester = TimelineWorkflowTester()
    tester.run_all_tests()