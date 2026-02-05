#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

from backend.src.storyboard.narrative_analyzer import analyze_narrative_concept

# Test the exact same call that the API makes
user_concept = """
80s-themed music video with a nostalgic journey through different eras. The story follows a group of friends who discover a magical portal that takes them from the gritty streets of the 1970s to a dystopian future, and finally to a peaceful beach party in the present day. The characters wear period-appropriate clothing, and the visual style should reflect the mood and aesthetics of each era they visit.
"""

song_structure = [
    {"name": "Intro", "start": 0, "end": 15, "energy": "low", "function": "setup"},
    {"name": "Verse 1", "start": 15, "end": 45, "energy": "building", "function": "development"},
    {"name": "Chorus 1", "start": 45, "end": 75, "energy": "high", "function": "hook"},
    {"name": "Verse 2", "start": 75, "end": 105, "energy": "medium", "function": "development"},
    {"name": "Chorus 2", "start": 105, "end": 135, "energy": "high", "function": "hook"},
    {"name": "Bridge", "start": 135, "end": 165, "energy": "dynamic", "function": "transition"},
    {"name": "Verse 3", "start": 165, "end": 195, "energy": "building", "function": "development"},
    {"name": "Chorus 3", "start": 195, "end": 225, "energy": "peak", "function": "climax"},
    {"name": "Outro", "start": 225, "end": 240, "energy": "resolving", "function": "conclusion"}
]

def test_api_function():
    print("Testing analyze_narrative_concept() directly...")
    print("=" * 60)

    try:
        recommendations = analyze_narrative_concept(user_concept, song_structure)

        print(f"Generated {len(recommendations)} recommendations")
        print()

        # Check the chorus recommendations specifically
        for rec in recommendations:
            if "Chorus" in rec["section_name"]:
                print(f"{rec['section_name']}:")
                print(f"  Visual Prompt: {rec['visual_prompt']}")
                print(f"  Mood: {rec['mood']}")
                print()

        # Compare Chorus 1 vs Chorus 2 vs Chorus 3
        choruses = [rec for rec in recommendations if "Chorus" in rec["section_name"]]
        if len(choruses) >= 3:
            print("COMPARISON:")
            print("-" * 40)
            c1_prompt = choruses[0]['visual_prompt']
            c2_prompt = choruses[1]['visual_prompt']
            c3_prompt = choruses[2]['visual_prompt']

            print(f"Chorus 1: {c1_prompt}")
            print(f"Chorus 2: {c2_prompt}")
            print(f"Chorus 3: {c3_prompt}")

            if c1_prompt == c2_prompt == c3_prompt:
                print("\nPROBLEM: All choruses are identical!")
            elif c1_prompt != c2_prompt and c2_prompt != c3_prompt:
                print("\nSUCCESS: All choruses are different!")
            else:
                print("\nPARTIAL: Some choruses are different, others the same")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_function()