#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

from backend.src.storyboard.narrative_analyzer import analyze_narrative_concept

# Use the EXACT same data that the API test script sends
user_concept = """
80s-themed music video with a nostalgic journey through different eras. The story follows a group of friends who discover a magical portal that takes them from the gritty streets of the 1970s to a dystopian future, and finally to a peaceful beach party in the present day. The characters wear period-appropriate clothing, and the visual style should reflect the mood and aesthetics of each era they visit.
"""

# This is the exact song_structure from the API test
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

def test_exact_api_call():
    print("Testing analyze_narrative_concept with EXACT API data...")
    print("=" * 60)

    try:
        # This is the exact call the API makes
        recommendations = analyze_narrative_concept(user_concept, song_structure)

        print(f"Generated {len(recommendations)} recommendations")
        print()

        # Look at choruses specifically
        for rec in recommendations:
            if "Chorus" in rec["section_name"]:
                print(f"{rec['section_name']}:")
                print(f"  Visual Prompt: {rec['visual_prompt'][:80]}...")
                print(f"  Mood: {rec['mood']}")
                print()

        # Check the specific issue: are choruses identical to verses?
        verse1 = next(rec for rec in recommendations if rec["section_name"] == "Verse 1")
        chorus1 = next(rec for rec in recommendations if rec["section_name"] == "Chorus 1")

        print("COMPARISON CHECK:")
        print(f"Verse 1 prompt: {verse1['visual_prompt']}")
        print(f"Chorus 1 prompt: {chorus1['visual_prompt']}")

        if verse1['visual_prompt'] == chorus1['visual_prompt']:
            print("BUG CONFIRMED: Verse 1 and Chorus 1 have identical prompts!")
        else:
            print("SUCCESS: Verse 1 and Chorus 1 have different prompts!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exact_api_call()