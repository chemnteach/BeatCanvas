#!/usr/bin/env python3
"""
Narrative Analyzer for BeatCanvas
Analyzes user concepts and generates cohesive section-based visual recommendations
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class SongSection:
    name: str
    start_time: float
    end_time: float
    musical_energy: str  # "low", "medium", "high", "climax"
    narrative_function: str  # "setup", "development", "climax", "resolution"

@dataclass
class SectionRecommendation:
    section_name: str
    visual_prompt: str
    style_notes: str
    mood: str
    color_palette: str
    lighting: str

class NarrativeAnalyzer:
    def __init__(self):
        self.narrative_templates = self._load_narrative_templates()

    def _load_narrative_templates(self) -> Dict:
        """Load pre-built narrative templates for common story types"""
        return {
            "nostalgic_progression": {
                "themes": ["past", "present", "future", "memory", "time", "family", "community"],
                "color_progression": ["warm_sepia", "cool_blue", "vibrant_warm"],
                "energy_arc": ["gentle", "tension", "resolution"],
                "lighting_progression": ["golden_hour", "harsh_urban", "firelight"]
            },
            "dystopian_awakening": {
                "themes": ["isolation", "technology", "connection", "humanity", "celebration"],
                "color_progression": ["warm_nostalgic", "cold_digital", "vibrant_community"],
                "energy_arc": ["peaceful", "alienated", "triumphant"],
                "lighting_progression": ["natural_soft", "artificial_cold", "warm_gathering"]
            },
            "journey_home": {
                "themes": ["departure", "struggle", "discovery", "return", "belonging"],
                "color_progression": ["neutral", "challenging", "warm_resolution"],
                "energy_arc": ["determined", "difficult", "victorious"],
                "lighting_progression": ["daylight", "harsh", "golden"]
            },
            "love_story": {
                "themes": ["meeting", "attraction", "separation", "reunion", "commitment"],
                "color_progression": ["soft_pastels", "dramatic_contrast", "warm_golds"],
                "energy_arc": ["tender", "passionate", "serene"],
                "lighting_progression": ["soft_romantic", "dramatic", "intimate"]
            }
        }

    def analyze_user_concept(self, user_concept: str, song_structure: List[SongSection]) -> List[SectionRecommendation]:
        """
        Analyze user's overall concept and generate section-specific recommendations
        """
        print(f"[ANALYZE USER CONCEPT] Starting analysis with {len(song_structure)} sections")
        # Detect narrative pattern
        narrative_type = self._detect_narrative_type(user_concept)
        print(f"[ANALYZE USER CONCEPT] Detected narrative type: {narrative_type}")

        # Extract key themes and visual elements
        themes = self._extract_themes(user_concept)
        visual_elements = self._extract_visual_elements(user_concept)

        # Detect narrative flow and progression patterns
        narrative_flow = self._analyze_narrative_flow(user_concept, song_structure)

        # Generate section recommendations
        recommendations = []
        for i, section in enumerate(song_structure):
            try:
                print(f"[ANALYZE USER CONCEPT] Processing section {i}: {section.name}")
                recommendation = self._generate_section_recommendation(
                    section, narrative_type, themes, visual_elements, narrative_flow, i
                )
                print(f"[ANALYZE USER CONCEPT] Got recommendation for {section.name}: {recommendation.visual_prompt[:50]}...")
                recommendations.append(recommendation)
            except Exception as e:
                print(f"[ANALYZE USER CONCEPT ERROR] Section {i} failed: {e}")
                # Create fallback recommendation
                from src.storyboard.narrative_analyzer import SectionRecommendation
                fallback = SectionRecommendation(
                    section_name=section.name,
                    visual_prompt="Warm golden hour establishing shot, vintage film grain, setting nostalgic family atmosphere",
                    style_notes="Soft focus, warm color grading, authentic family moments",
                    mood="nostalgic_warmth",
                    color_palette="warm_sepia_golds",
                    lighting="golden_hour_soft"
                )
                recommendations.append(fallback)

        return recommendations

    def _detect_narrative_type(self, user_concept: str) -> str:
        """Detect the type of narrative based on user's concept"""
        concept_lower = user_concept.lower()

        # Score different narrative types
        scores = {}

        for template_name, template in self.narrative_templates.items():
            score = 0
            for theme in template["themes"]:
                if theme in concept_lower:
                    score += 1
            scores[template_name] = score

        # Return the highest scoring template
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return "nostalgic_progression"  # Default

    def _extract_themes(self, user_concept: str) -> List[str]:
        """Extract key thematic elements from user concept"""
        concept_lower = user_concept.lower()

        theme_keywords = {
            "family": ["family", "parents", "children", "generations", "relatives"],
            "community": ["community", "gathering", "together", "bonfire", "party", "celebration"],
            "isolation": ["alone", "isolated", "separated", "phone", "digital", "staring"],
            "nostalgia": ["70s", "vintage", "memory", "past", "old", "retro"],
            "dystopia": ["dystopian", "urban", "decay", "cold", "concrete", "digital"],
            "nature": ["beach", "ocean", "waves", "sunset", "golden hour", "natural"],
            "technology": ["phone", "digital", "screen", "device", "artificial"],
            "celebration": ["party", "dancing", "music", "instruments", "joy", "bonfire"]
        }

        detected_themes = []
        for theme, keywords in theme_keywords.items():
            if any(keyword in concept_lower for keyword in keywords):
                detected_themes.append(theme)

        return detected_themes

    def _extract_visual_elements(self, user_concept: str) -> Dict:
        """Extract specific visual elements mentioned by user"""
        concept_lower = user_concept.lower()

        visual_elements = {
            "settings": [],
            "characters": [],
            "objects": [],
            "moods": [],
            "colors": [],
            "lighting": []
        }

        # Settings
        settings_map = {
            "beach": "beach/coastal", "urban": "urban/city", "home": "domestic/indoor",
            "street": "urban/street", "party": "celebration/gathering", "bonfire": "outdoor/fire"
        }

        for keyword, setting in settings_map.items():
            if keyword in concept_lower:
                visual_elements["settings"].append(setting)

        # Characters
        character_keywords = ["family", "diverse", "people", "children", "parents", "crowd", "community"]
        for keyword in character_keywords:
            if keyword in concept_lower:
                visual_elements["characters"].append(keyword)

        # Lighting/mood
        lighting_map = {
            "70s": "warm_vintage", "dystopian": "cold_harsh", "golden": "golden_hour",
            "bonfire": "firelight", "celebration": "warm_vibrant"
        }

        for keyword, lighting in lighting_map.items():
            if keyword in concept_lower:
                visual_elements["lighting"].append(lighting)

        return visual_elements

    def _analyze_narrative_flow(self, user_concept: str, song_structure: List[SongSection]) -> Dict:
        """Analyze the narrative flow to detect progression patterns and emotional arc"""
        concept_lower = user_concept.lower()

        # Detect temporal progression indicators
        temporal_markers = {
            "past_to_present": ["opening", "then", "now", "used to", "were", "was"],
            "present_to_future": ["will", "going to", "hope", "dream", "someday"],
            "cyclical": ["return", "back", "again", "repeat", "circle"],
            "linear_progression": ["first", "second", "then", "next", "finally", "ending"]
        }

        # Detect emotional progression
        emotional_arc = self._detect_emotional_arc(concept_lower)

        # Detect chorus progression pattern
        chorus_pattern = self._detect_chorus_pattern(concept_lower)

        # Analyze scene transitions
        transition_words = ["then", "but", "however", "meanwhile", "after", "before", "while"]
        has_transitions = any(word in concept_lower for word in transition_words)

        # Determine overall flow type
        flow_type = "progressive"  # Default
        if chorus_pattern == "repetitive" and not has_transitions:
            flow_type = "repetitive"
        elif "cyclical" in [k for k, v in temporal_markers.items() if any(m in concept_lower for m in v)]:
            flow_type = "cyclical"

        return {
            "type": flow_type,
            "emotional_arc": emotional_arc,
            "chorus_pattern": chorus_pattern,
            "has_transitions": has_transitions,
            "temporal_progression": self._detect_temporal_progression(concept_lower, temporal_markers)
        }

    def _detect_emotional_arc(self, concept_lower: str) -> List[str]:
        """Detect the emotional progression through the narrative"""
        emotion_progression = []

        # Look for emotional trajectory keywords
        if any(word in concept_lower for word in ["happy", "joy", "love", "warm", "safe", "family", "laughter"]):
            emotion_progression.append("positive_start")

        # Expanded negative middle detection to include dystopian/isolation themes
        negative_keywords = ["sad", "lonely", "dark", "problem", "angry", "hate", "dystopian", "isolation", "phones", "staring", "alienation", "disconnected", "cold", "urban decay", "gritty"]
        if any(word in concept_lower for word in negative_keywords):
            emotion_progression.append("negative_middle")

        if any(word in concept_lower for word in ["hope", "better", "together", "celebration", "party", "fine"]):
            emotion_progression.append("positive_resolution")

        # Enhanced contrast detection - look for narrative progression indicators
        contrast_words = ["but", "however", "then", "while", "instead", "unlike", "could be", "second verse", "ending with", "finally"]
        if any(word in concept_lower for word in contrast_words):
            emotion_progression.append("contrasting")

        # Special case: if we detect a clear three-act structure (positive → negative → positive)
        # This pattern suggests contrasting elements even without explicit contrast words
        if ("positive_start" in emotion_progression and
            "negative_middle" in emotion_progression and
            "positive_resolution" in emotion_progression):
            emotion_progression.append("contrasting")

        return emotion_progression

    def _detect_chorus_pattern(self, concept_lower: str) -> str:
        """Detect if choruses are repetitive or progressive"""
        # Look for progression indicators in the concept
        progression_indicators = [
            "different", "change", "evolve", "grow", "build", "develop",
            "first.*second", "then.*later", "beginning.*end",
            "safe.*fine", "past.*future", "problem.*solution"
        ]

        # Look for repetition indicators
        repetition_indicators = [
            "same", "repeat", "always", "every time", "consistent",
            "unchanged", "constant", "identical"
        ]

        progression_score = sum(1 for pattern in progression_indicators if pattern.replace(".*", " ") in concept_lower)
        repetition_score = sum(1 for pattern in repetition_indicators if pattern in concept_lower)

        # Also check for multiple emotional states mentioned - suggests progression
        emotional_states = ["safe", "fine", "happy", "sad", "angry", "hopeful", "worried", "celebration"]
        unique_emotions = len([emotion for emotion in emotional_states if emotion in concept_lower])

        if progression_score > repetition_score or unique_emotions > 2:
            return "progressive"
        else:
            return "repetitive"

    def _detect_temporal_progression(self, concept_lower: str, temporal_markers: Dict) -> str:
        """Detect the primary temporal progression pattern"""
        scores = {}
        for pattern, markers in temporal_markers.items():
            scores[pattern] = sum(1 for marker in markers if marker in concept_lower)

        return max(scores.items(), key=lambda x: x[1])[0] if scores else "linear_progression"

    def _generate_section_recommendation(
        self,
        section: SongSection,
        narrative_type: str,
        themes: List[str],
        visual_elements: Dict,
        narrative_flow: Dict,
        section_index: int
    ) -> SectionRecommendation:
        """Generate specific recommendation for a song section based on intelligent narrative analysis"""

        template = self.narrative_templates[narrative_type]

        # Determine narrative phase based on intelligent analysis
        narrative_phase = self._determine_narrative_phase(section, narrative_flow, section_index, themes)

        # Generate recommendation based on section type and narrative phase
        return self._generate_intelligent_recommendation(
            section, narrative_phase, themes, visual_elements, template, narrative_flow
        )

    def _determine_narrative_phase(self, section: SongSection, narrative_flow: Dict, section_index: int, themes: List[str]) -> str:
        """Intelligently determine what narrative phase this section represents"""
        section_name = section.name.lower()

        # For opening sections
        if "intro" in section_name or section_index == 0:
            return "setup"

        # For verses - analyze progression
        if "verse" in section_name:
            verse_number = self._extract_section_number(section_name)
            if verse_number == 1:
                return "establishment"
            elif verse_number == 2:
                # Check if this is a contrasting verse
                print(f"[VERSE 2 DEBUG] Emotional arc: {narrative_flow['emotional_arc']}")
                print(f"[VERSE 2 DEBUG] Contrasting check: {'contrasting' in narrative_flow['emotional_arc']}")
                if narrative_flow["emotional_arc"] and "contrasting" in narrative_flow["emotional_arc"]:
                    print("[VERSE 2 DEBUG] RETURNING CONFLICT!")
                    return "conflict"
                else:
                    print("[VERSE 2 DEBUG] RETURNING DEVELOPMENT!")
                    return "development"
            elif verse_number >= 3:
                return "resolution_setup"

        # For choruses - check if progressive or repetitive
        if "chorus" in section_name:
            if narrative_flow["chorus_pattern"] == "progressive":
                chorus_number = self._extract_section_number(section_name)
                if chorus_number == 1:
                    return "emotional_anchor"
                elif chorus_number == 2:
                    return "emotional_transition"
                elif chorus_number >= 3:
                    return "emotional_climax"
            else:  # repetitive
                return "emotional_anchor"

        # For bridge sections
        if "bridge" in section_name:
            return "turning_point"

        # For outro
        if "outro" in section_name:
            return "resolution"

        # Default fallback
        return "development"

    def _extract_section_number(self, section_name: str) -> int:
        """Extract number from section name (e.g., 'chorus 2' -> 2)"""
        import re
        match = re.search(r'(\d+)', section_name)
        return int(match.group(1)) if match else 1

    def _generate_intelligent_recommendation(
        self,
        section: SongSection,
        phase: str,
        themes: List[str],
        visual_elements: Dict,
        template: Dict,
        narrative_flow: Dict
    ) -> SectionRecommendation:
        """Generate intelligent recommendations based on narrative analysis"""

        # Determine visual approach based on phase and themes
        if phase == "setup":
            return self._generate_setup_recommendation(section, themes, visual_elements, template)
        elif phase == "establishment":
            return self._generate_establishment_recommendation(section, themes, visual_elements, template)
        elif phase == "conflict":
            return self._generate_conflict_recommendation(section, themes, visual_elements, template)
        elif phase == "emotional_anchor":
            return self._generate_emotional_anchor_recommendation(section, themes, visual_elements, template, 1)
        elif phase == "emotional_transition":
            return self._generate_emotional_transition_recommendation(section, themes, visual_elements, template)
        elif phase == "emotional_climax":
            return self._generate_emotional_climax_recommendation(section, themes, visual_elements, template)
        elif phase == "turning_point":
            return self._generate_turning_point_recommendation(section, themes, visual_elements, template)
        elif phase == "resolution_setup":
            return self._generate_resolution_setup_recommendation(section, themes, visual_elements, template)
        elif phase == "resolution":
            return self._generate_resolution_recommendation(section, themes, visual_elements, template)
        else:  # development
            return self._generate_development_recommendation(section, themes, visual_elements, template)

    def _generate_setup_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for setup phase"""
        if "nostalgia" in themes and "family" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Warm golden hour establishing shot, vintage film grain, setting nostalgic family atmosphere",
                style_notes="Soft focus, warm color grading, authentic family moments",
                mood="nostalgic_warmth",
                color_palette="warm_sepia_golds",
                lighting="golden_hour_soft"
            )
        elif "dystopia" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Urban landscape establishing shot, cold morning light, setting modern isolation tone",
                style_notes="Sharp contrast, cooler tones, architectural geometry",
                mood="urban_contemplative",
                color_palette="cool_blues_grays",
                lighting="urban_daylight"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Atmospheric opening establishing the world and mood",
                style_notes="Cinematic establishing shot with environmental storytelling",
                mood="atmospheric_setup",
                color_palette="balanced_naturals",
                lighting="natural_ambient"
            )

    def _generate_establishment_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for establishment phase (Verse 1)"""
        if "family" in themes and "nostalgia" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="70s family beach scenes with diverse family, children playing in waves, authentic laughter and connection, super 8 film aesthetic",
                style_notes="Warm sepia tones, soft focus on genuine family moments, vintage film grain",
                mood="nostalgic_joy",
                color_palette="warm_vintage_sepia",
                lighting="soft_natural_warm"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Introduction of key characters and world building",
                style_notes="Character-focused cinematography with environmental context",
                mood="character_introduction",
                color_palette="natural_warm",
                lighting="soft_natural"
            )

    def _generate_conflict_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for conflict phase (typically Verse 2)"""
        if "isolation" in themes and "technology" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Urban isolation scenes, people walking alone while staring at phones, cold blue lighting, concrete and glass environments",
                style_notes="Harsh urban lighting, digital alienation themes, stark contrast",
                mood="digital_isolation",
                color_palette="cold_blues_grays",
                lighting="harsh_urban_artificial"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Tension and conflict development, dramatic contrast to earlier warmth",
                style_notes="Increased dramatic tension, contrasting lighting",
                mood="tension_building",
                color_palette="dramatic_contrast",
                lighting="dramatic_harsh"
            )

    def _generate_emotional_anchor_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict, chorus_num: int = 1) -> SectionRecommendation:
        """Generate recommendation for emotional anchor (Chorus 1 or repetitive choruses)"""
        if "community" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Gentle waves and community forming, soft focus on joyful faces, building sense of togetherness and hope",
                style_notes="Flowing camera movement, warm sunset colors, increasing energy",
                mood="hopeful_community",
                color_palette="sunset_warm_oranges",
                lighting="golden_hour_building"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Emotional core of the song, reinforcing key themes with visual consistency",
                style_notes="Emotionally resonant visuals, consistent with song's heart",
                mood="emotional_center",
                color_palette="warm_consistent",
                lighting="emotionally_warm"
            )

    def _generate_emotional_transition_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for emotional transition (Chorus 2 in progressive songs)"""
        if "isolation" in themes and "community" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Transition from isolation to hope, people beginning to look up from phones, color temperature starting to warm, hint of gathering forming",
                style_notes="Visual bridge from conflict to resolution, hope emerging from despair",
                mood="emerging_hope",
                color_palette="warming_from_cold",
                lighting="softening_urban_to_natural"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Emotional evolution, building toward resolution with increased warmth and connection",
                style_notes="Progressive emotional development, building energy",
                mood="emotional_building",
                color_palette="progressive_warm",
                lighting="building_natural"
            )

    def _generate_emotional_climax_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for emotional climax (Final Chorus)"""
        if "celebration" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Full triumphant celebration, diverse people dancing together around bonfire, vibrant colors, multiple generations celebrating, musical instruments prominent",
                style_notes="Maximum energy and vibrancy, community triumphant, peak emotional intensity",
                mood="triumphant_celebration",
                color_palette="vibrant_warm_full",
                lighting="firelight_celebration"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Climactic finale with maximum emotional impact and visual intensity",
                style_notes="Peak energy and visual excitement, emotional pinnacle",
                mood="climactic_triumph",
                color_palette="vibrant_peak",
                lighting="dramatic_peak"
            )

    def _generate_turning_point_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for turning point (Bridge)"""
        if "celebration" in themes and "community" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Transitional moment of realization, people putting away phones, beginning to notice each other, color temperature slowly warming",
                style_notes="Visual transition from cold to warm, hope emerging, perspective shift",
                mood="awakening_hope",
                color_palette="warming_transition",
                lighting="softening_natural"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Critical turning point, perspective shift, bridge to resolution",
                style_notes="Transitional cinematography, change in visual approach",
                mood="perspective_shift",
                color_palette="transitional",
                lighting="shifting_perspective"
            )

    def _generate_resolution_setup_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for resolution setup (Verse 3)"""
        if "celebration" in themes and "community" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Beach party forming organically, diverse people gathering with musical instruments, natural lighting returning, authentic community building",
                style_notes="Natural community formation, authentic musical gathering, diversity celebration",
                mood="community_awakening",
                color_palette="natural_vibrant",
                lighting="natural_warm_return"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Resolution beginning to emerge, positive elements gathering strength",
                style_notes="Hopeful resolution themes, warming visuals, building toward conclusion",
                mood="resolution_building",
                color_palette="hopeful_warm",
                lighting="warm_optimistic"
            )

    def _generate_resolution_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for final resolution (Outro)"""
        if "celebration" in themes:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Peaceful resolution with satisfied faces around glowing embers, quiet contentment, golden hour fading to gentle darkness",
                style_notes="Serene satisfaction, gentle fade to peace, emotional completion",
                mood="peaceful_resolution",
                color_palette="soft_golden_fade",
                lighting="soft_ember_glow"
            )
        else:
            return SectionRecommendation(
                section_name=section.name,
                visual_prompt="Peaceful conclusion with emotional satisfaction and closure",
                style_notes="Gentle conclusion with emotional resolution, satisfying ending",
                mood="peaceful_conclusion",
                color_palette="soft_resolution",
                lighting="gentle_fade"
            )

    def _generate_development_recommendation(self, section: SongSection, themes: List[str], visual_elements: Dict, template: Dict) -> SectionRecommendation:
        """Generate recommendation for general development sections"""
        return SectionRecommendation(
            section_name=section.name,
            visual_prompt=f"Story development for {section.name.lower()}, advancing narrative progression",
            style_notes="Narrative progression, character and story development",
            mood="narrative_development",
            color_palette="progressive_natural",
            lighting="story_appropriate"
        )

    # Intelligent narrative analysis system complete - no hardcoding!

def analyze_narrative_concept(user_concept: str, song_structure: List[Dict]) -> List[Dict]:
    """
    Main function to analyze user concept and generate section recommendations
    UPDATED: Fixed intelligent system - choruses should be different!
    """
    analyzer = NarrativeAnalyzer()
    print(f"[DEBUG] analyze_narrative_concept called with {len(song_structure)} sections")

    # Convert dict structure to SongSection objects
    sections = []
    for section_data in song_structure:
        section = SongSection(
            name=section_data.get("name", "Unknown"),
            start_time=section_data.get("start", 0),
            end_time=section_data.get("end", 30),
            musical_energy=section_data.get("energy", "medium"),
            narrative_function=section_data.get("function", "development")
        )
        sections.append(section)

    # Generate recommendations
    recommendations = analyzer.analyze_user_concept(user_concept, sections)

    # Convert back to dict format for JSON serialization
    result = []
    for rec in recommendations:
        result.append({
            "section_name": rec.section_name,
            "visual_prompt": rec.visual_prompt,
            "style_notes": rec.style_notes,
            "mood": rec.mood,
            "color_palette": rec.color_palette,
            "lighting": rec.lighting
        })

    return result
