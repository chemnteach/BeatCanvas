#!/usr/bin/env python3
"""Test the new API endpoints directly"""

import sys
import os
sys.path.append('backend')

from pathlib import Path
from src.utils.env_loader import load_global_env

# Load environment
load_global_env()

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from backend.main import app
        print(f"[OK] App imported successfully")

        # Check routes
        routes = [route for route in app.routes if hasattr(route, 'path')]
        style_route = None
        for route in routes:
            if 'style-suggestions' in route.path:
                style_route = route
                break

        if style_route:
            print(f"[OK] Found style-suggestions route: {style_route}")
        else:
            print("[ERROR] style-suggestions route not found")
            print("Available routes:")
            for route in routes:
                if hasattr(route, 'path') and '/api/' in route.path:
                    print(f"  {route.path}")

        return True

    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_concept_generator():
    """Test ConceptGenerator directly"""
    try:
        from backend.src.storyboard.conceptor import ConceptGenerator

        conceptor = ConceptGenerator()
        suggestions = conceptor.suggest_visual_styles("A dancer moving underwater")
        print(f"[OK] ConceptGenerator.suggest_visual_styles works: {suggestions}")
        return True

    except Exception as e:
        print(f"[ERROR] ConceptGenerator error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing New Endpoints ===")

    success = True
    success &= test_imports()
    success &= test_concept_generator()

    if success:
        print("\n[OK] All tests passed!")
    else:
        print("\n[ERROR] Some tests failed!")
        sys.exit(1)