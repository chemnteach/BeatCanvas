#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

from backend.src.storyboard.narrative_analyzer import NarrativeAnalyzer, SongSection

# Test data
user_concept = """
Opening verse of 70s film-filter family beach scenes with diverse family. Second verse could be borderline dystopian scenes of people walking around staring at their phones, with the song ending with a growing beach party with people of all colors, dancing and playing musical instruments and drinking and gathering around a bonfire.
"""

def debug_narrative_analysis():
    """Debug the narrative analysis step by step"""
    analyzer = NarrativeAnalyzer()

    # Create test sections
    verse1 = SongSection(
        name="Verse 1",
        start_time=15,
        end_time=45,
        musical_energy="building",
        narrative_function="development"
    )

    chorus1 = SongSection(
        name="Chorus 1",
        start_time=45,
        end_time=75,
        musical_energy="high",
        narrative_function="hook"
    )

    verse2 = SongSection(
        name="Verse 2",
        start_time=75,
        end_time=105,
        musical_energy="medium",
        narrative_function="development"
    )

    chorus2 = SongSection(
        name="Chorus 2",
        start_time=105,
        end_time=135,
        musical_energy="high",
        narrative_function="hook"
    )

    sections = [verse1, chorus1, verse2, chorus2]

    print("=== DEBUGGING NARRATIVE ANALYSIS ===")
    print(f"User concept: {user_concept[:100]}...")
    print()

    # Step 1: Analyze narrative type
    narrative_type = analyzer._detect_narrative_type(user_concept)
    print(f"Detected narrative type: {narrative_type}")

    # Step 2: Extract themes
    themes = analyzer._extract_themes(user_concept)
    print(f"Extracted themes: {themes}")

    # Step 3: Extract visual elements
    visual_elements = analyzer._extract_visual_elements(user_concept)
    print(f"Visual elements: {visual_elements}")

    # Step 4: Analyze narrative flow
    narrative_flow = analyzer._analyze_narrative_flow(user_concept, sections)
    print(f"Narrative flow: {narrative_flow}")

    print()
    print("=== SECTION-BY-SECTION ANALYSIS ===")

    # Test each section individually
    for i, section in enumerate(sections):
        print(f"\n--- {section.name} ---")

        # Determine narrative phase
        phase = analyzer._determine_narrative_phase(section, narrative_flow, i + 1, themes)
        print(f"Narrative phase: {phase}")

        # Generate recommendation
        recommendation = analyzer._generate_section_recommendation(section, narrative_type, themes, visual_elements, narrative_flow, i)
        print(f"Visual prompt: {recommendation.visual_prompt}")
        print(f"Mood: {recommendation.mood}")

if __name__ == "__main__":
    debug_narrative_analysis()