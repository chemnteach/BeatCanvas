#!/usr/bin/env python3

import requests
import json

# Test data - same as the user provided
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

def test_intelligent_recommendations():
    """Test the intelligent narrative analysis system"""

    url = "http://127.0.0.1:8002/api/generate-section-recommendations"

    payload = {
        "user_concept": user_concept,
        "song_structure": song_structure
    }

    try:
        print("Testing intelligent narrative analysis system...")
        print("=" * 60)

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            recommendations = response.json()

            print(f"Generated {len(recommendations)} recommendations")
            print()
            print("Response format check:")
            print(f"Type: {type(recommendations)}")
            if isinstance(recommendations, list) and len(recommendations) > 0:
                print(f"First item: {recommendations[0]}")
            else:
                print(f"Content: {recommendations}")
            print()

            # Handle different response formats
            if isinstance(recommendations, list):
                chorus_recs = [rec for rec in recommendations if isinstance(rec, dict) and "Chorus" in rec.get("section_name", "")]
            else:
                # If it's a dict, it might have a different structure
                print("Response is not a list - investigating structure...")
                print(json.dumps(recommendations, indent=2))
                return True

            print("CHORUS ANALYSIS:")
            print("=" * 40)

            for i, chorus in enumerate(chorus_recs, 1):
                print(f"\n{chorus['section_name']}:")
                print(f"  Visual Prompt: {chorus['visual_prompt']}")
                print(f"  Mood: {chorus['mood']}")
                print(f"  Color Palette: {chorus['color_palette']}")

            # Check if recommendations are different
            if len(chorus_recs) >= 3:
                chorus1_prompt = chorus_recs[0]['visual_prompt']
                chorus2_prompt = chorus_recs[1]['visual_prompt']
                chorus3_prompt = chorus_recs[2]['visual_prompt']

                print("\n" + "=" * 60)
                print("PROGRESSION TEST:")

                if chorus1_prompt != chorus2_prompt and chorus2_prompt != chorus3_prompt:
                    print("SUCCESS: All choruses have different recommendations!")
                    print("   The intelligent system is working correctly.")
                else:
                    print("FAIL: Choruses have identical recommendations.")
                    print("   This suggests hardcoded functions are still being used.")

                # Check for specific narrative progression
                if "urban decay" not in chorus2_prompt.lower() and "hope" in chorus2_prompt.lower():
                    print("SUCCESS: Chorus 2 shows emotional transition phase!")
                else:
                    print("ISSUE: Chorus 2 still shows urban decay instead of hope emerging.")

            return True

        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    test_intelligent_recommendations()