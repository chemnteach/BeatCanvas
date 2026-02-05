#!/usr/bin/env python3
"""
Manual Timeline Testing Script

Quick verification script for interactive timeline functionality.
Run this after implementing the timeline components to verify basic functionality.

Usage:
    python test_timeline_manual.py
"""

import os
import requests
from pathlib import Path

def test_component_files():
    """Verify all component files exist"""
    print("📁 Checking component files...")

    required_files = [
        ("InteractiveTimeline", "frontend/src/components/InteractiveTimeline.tsx"),
        ("SceneEditModal", "frontend/src/components/SceneEditModal.tsx"),
        ("VideoPreview", "frontend/src/components/VideoPreview.tsx"),
        ("VideoGenerator", "frontend/src/components/VideoGenerator.tsx")
    ]

    all_exist = True
    for name, path in required_files:
        if Path(path).exists():
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ {name}: {path} - MISSING")
            all_exist = False

    return all_exist

def test_backend_endpoints():
    """Test if backend endpoints are available"""
    print("\n🔗 Checking backend endpoints...")

    base_url = "http://localhost:8000"
    endpoints = [
        ("/", "Root"),
        ("/docs", "API Documentation"),
    ]

    backend_running = False
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: {base_url}{endpoint}")
                backend_running = True
            else:
                print(f"⚠️  {name}: {base_url}{endpoint} - Status {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"❌ {name}: {base_url}{endpoint} - Connection failed")

    return backend_running

def test_frontend_build():
    """Check if frontend can be built"""
    print("\n🏗️  Testing frontend build...")

    package_json = Path("frontend/package.json")
    if not package_json.exists():
        print("❌ package.json not found in frontend/")
        return False

    print("✅ package.json found")

    # Check if node_modules exists (dependencies installed)
    node_modules = Path("frontend/node_modules")
    if node_modules.exists():
        print("✅ node_modules found (dependencies installed)")
    else:
        print("⚠️  node_modules not found - run 'npm install' in frontend/")

    return True

def test_timeline_integration():
    """Verify timeline integration in VideoGenerator"""
    print("\n⏰ Checking timeline integration...")

    video_generator = Path("frontend/src/components/VideoGenerator.tsx")
    if not video_generator.exists():
        print("❌ VideoGenerator.tsx not found")
        return False

    with open(video_generator, 'r', encoding='utf-8') as f:
        content = f.read()

    required_integrations = [
        ("InteractiveTimeline import", "InteractiveTimeline"),
        ("SceneEditModal import", "SceneEditModal"),
        ("Scene editing state", "editingSceneIndex"),
        ("Scene edit handler", "handleSceneEdit"),
        ("Scene regenerate handler", "handleSceneRegenerate")
    ]

    all_integrated = True
    for check_name, search_term in required_integrations:
        if search_term in content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} - '{search_term}' not found")
            all_integrated = False

    return all_integrated

def test_api_structure():
    """Check if new API endpoints are implemented in main.py"""
    print("\n🔌 Checking API endpoints...")

    main_py = Path("backend/main.py")
    if not main_py.exists():
        print("❌ backend/main.py not found")
        return False

    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()

    required_endpoints = [
        ("Regenerate Scene", "/api/regenerate-scene"),
        ("Rebuild Video", "/api/rebuild-video"),
        ("RegenerateSceneRequest", "RegenerateSceneRequest"),
        ("RebuildVideoRequest", "RebuildVideoRequest")
    ]

    all_implemented = True
    for endpoint_name, search_term in required_endpoints:
        if search_term in content:
            print(f"✅ {endpoint_name}")
        else:
            print(f"❌ {endpoint_name} - '{search_term}' not found")
            all_implemented = False

    return all_implemented

def print_manual_test_guide():
    """Print manual testing instructions"""
    print("\n📋 Manual Testing Guide")
    print("=" * 50)
    print("""
After running this verification script, manually test:

1. START SERVERS:
   cd backend && uvicorn main:app --reload
   cd frontend && npm start

2. GENERATE VIDEO:
   - Go to http://localhost:3000
   - Upload test audio file
   - Generate video with professional tier (24 scenes)
   - Wait for completion

3. TEST TIMELINE:
   - Video should show with timeline below
   - Timeline should have colored scene segments
   - Click a segment → video should seek to that scene
   - Hover segments → tooltip should show scene details

4. TEST SCENE EDITING:
   - Double-click a timeline segment
   - Scene edit modal should open
   - Modify scene description
   - Select effects and AI provider
   - Click "Regenerate Scene"
   - Wait for regeneration and video rebuild

5. VERIFY CHANGES:
   - Updated video should reflect scene changes
   - Timeline should update with new scene data
   - Download should work for updated video

6. CHECK COST TRANSPARENCY:
   - Scene edit modal should show cost estimates
   - Different providers should show different costs
   - User should confirm before regeneration

If any step fails, check console errors and server logs.
""")

def main():
    """Run all verification tests"""
    print("🧪 Interactive Timeline Manual Test Script")
    print("=" * 50)

    tests = [
        ("Component Files", test_component_files),
        ("Backend Endpoints", test_backend_endpoints),
        ("Frontend Build", test_frontend_build),
        ("Timeline Integration", test_timeline_integration),
        ("API Structure", test_api_structure)
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results[test_name] = False

    # Summary
    print("\n📊 Verification Summary")
    print("=" * 30)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} checks passed ({passed/total*100:.1f}%)")

    if all(results.values()):
        print("\n🎉 All verification checks passed!")
        print("Ready for manual testing.")
    else:
        print("\n⚠️  Some checks failed. Fix issues before manual testing.")

    print_manual_test_guide()

if __name__ == "__main__":
    main()