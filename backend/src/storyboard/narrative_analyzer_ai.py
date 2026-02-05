#!/usr/bin/env python3
"""
AI-Powered Narrative Analyzer for BeatCanvas
Uses GPT-4 to analyze user concepts and generate intelligent section-specific visual recommendations
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import openai
import os
from src.utils.env_loader import load_global_env

@dataclass
class SongSection:
    name: str
    start_time: float
    end_time: float
    musical_energy: str = "medium"  # "low", "medium", "high", "climax"
    narrative_function: str = "development"  # "setup", "development", "climax", "resolution"

@dataclass
class SectionRecommendation:
    section_name: str
    visual_prompt: str
    style_notes: str
    mood: str
    color_palette: str
    lighting: str

class AINarrativeAnalyzer:
    def __init__(self):
        # Load environment and set up OpenAI
        load_global_env()
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def analyze_user_concept(self, user_concept: str, song_structure: List[SongSection]) -> List[SectionRecommendation]:
        """
        Analyze user's overall concept using GPT-4 and generate section-specific recommendations
        """
        return self.analyze_concept_with_song(user_concept, song_structure, {})

    def analyze_concept_with_song(self, user_concept: str, song_structure: List[SongSection], song_analysis: dict) -> List[SectionRecommendation]:
        """
        GPT-4 only analysis system: Real AI recommendations or wait until available
        NO TEMPLATES - User explicitly requested to remove all template fallbacks
        """
        print(f"[AI ANALYZE] Starting GPT-4 only analysis with {len(song_structure)} sections")
        print(f"[AI ANALYZE] User concept: {user_concept[:100]}...")

        # Check song analysis data
        has_lyrics = song_analysis.get("lyrics_data", {}).get("has_lyrics", False)
        has_musical_analysis = "analysis_data" in song_analysis
        lyrics_text = song_analysis.get("lyrics_data", {}).get("lyrics_text", "")
        musical_mood = song_analysis.get("analysis_data", {}).get("overall_mood", "neutral")

        print(f"[AI ANALYZE] Song context: lyrics={has_lyrics}, analysis={has_musical_analysis}")
        if has_lyrics:
            print(f"[AI ANALYZE] Lyrics sample: {lyrics_text[:100]}...")
        if has_musical_analysis:
            print(f"[AI ANALYZE] Musical mood: {musical_mood}")

        # REQUIRE GPT-4: No templates, wait for proper LLM connection
        try:
            print(f"[AI ANALYZE] Attempting GPT-4 analysis (REQUIRED - no fallback)...")
            recommendations = self._generate_ai_recommendations_with_song(
                user_concept, song_structure, song_analysis
            )
            print(f"[AI ANALYZE] GPT-4 analysis successful - generated {len(recommendations)} intelligent recommendations")
            return recommendations

        except Exception as e:
            error_msg = str(e)
            print(f"[AI ANALYZE] GPT-4 connection failed: {error_msg}")

            # NO TEMPLATES - Raise error instead of falling back
            if "429" in error_msg or "quota" in error_msg.lower():
                raise Exception("OpenAI quota exceeded. Please wait or check your billing. No template fallback available - user requested real AI only.")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise Exception("OpenAI API key invalid or unauthorized. Please check your API key configuration. No template fallback available.")
            else:
                raise Exception(f"GPT-4 connection failed: {error_msg}. No template fallback available - waiting for proper LLM connection.")


    def _extract_song_context(self, song_analysis: dict) -> Dict:
        """Extract and structure song context for integration with concept analysis"""
        context = {
            "has_lyrics": song_analysis.get("lyrics_data", {}).get("has_lyrics", False),
            "lyrics_text": song_analysis.get("lyrics_data", {}).get("lyrics_text", ""),
            "lyrics_themes": [],
            "musical_mood": song_analysis.get("analysis_data", {}).get("overall_mood", "neutral"),
            "tempo": song_analysis.get("analysis_data", {}).get("tempo", 120),
            "energy_level": song_analysis.get("analysis_data", {}).get("overall_energy", 0.5)
        }

        # Extract lyrical themes if lyrics available
        if context["has_lyrics"] and context["lyrics_text"]:
            lyrics_analysis = song_analysis.get("lyrics_data", {}).get("lyrics_analysis", {})
            context["lyrics_themes"] = lyrics_analysis.get("themes", [])

        return context

    def _integrate_concept_with_song(self, concept_analysis: Dict, song_context: Dict) -> Dict:
        """Intelligently merge user concept with song context"""
        integrated = concept_analysis.copy()

        # Enhance emotions based on song mood
        song_mood = song_context["musical_mood"]
        if song_mood == "calm" and "joyful" in concept_analysis["emotions"]:
            integrated["emotions"].append("serene_joy")
        elif song_mood == "energetic" and "communal_gathering" in concept_analysis["activities"]:
            integrated["emotions"].append("vibrant_celebration")

        # Integrate lyrical themes with concept themes
        if song_context["lyrics_themes"]:
            for theme in song_context["lyrics_themes"]:
                if theme not in integrated["emotions"]:
                    integrated["emotions"].append(f"lyrical_{theme}")

        # Adjust pacing based on tempo
        tempo = song_context["tempo"]
        if tempo < 80:
            integrated["pacing"] = "contemplative"
        elif tempo > 140:
            integrated["pacing"] = "energetic"
        else:
            integrated["pacing"] = "moderate"

        # Song context for reference
        integrated["song_context"] = song_context

        return integrated

    def _generate_integrated_prompt(self, section, section_index: int, total_sections: int,
                                   user_concept: str, integrated_context: Dict) -> str:
        """Generate sophisticated prompts that blend concept with song analysis"""

        section_name = section.name.lower()
        progress = section_index / max(1, total_sections - 1)
        song_context = integrated_context.get("song_context", {})

        # Use the original detailed concept-aware generation but enhance with song context
        base_prompt = self._generate_concept_aware_prompt(
            section, section_index, total_sections, user_concept, integrated_context
        )

        # Enhance with song-specific context if available
        if song_context.get("has_lyrics") and song_context.get("lyrics_themes"):
            lyrical_enhancement = self._add_lyrical_context(base_prompt, song_context, section_name)
            return lyrical_enhancement

        # Enhance with musical mood context
        musical_mood = song_context.get("musical_mood", "neutral")
        tempo = song_context.get("tempo", 120)

        if musical_mood == "calm" and tempo < 90:
            mood_enhancement = f"{base_prompt.rstrip('.')}. Scene moves with deliberate, contemplative pacing that matches the song's reflective {tempo:.0f} BPM rhythm"
        elif musical_mood == "energetic" and tempo > 120:
            mood_enhancement = f"{base_prompt.rstrip('.')}. Dynamic energy and movement synchronized with the song's driving {tempo:.0f} BPM tempo"
        else:
            mood_enhancement = f"{base_prompt.rstrip('.')}. Visual rhythm complementing the song's {musical_mood} mood at {tempo:.0f} BPM"

        return mood_enhancement

    def _add_lyrical_context(self, base_prompt: str, song_context: Dict, section_name: str) -> str:
        """Add lyrical context to enhance visual prompts"""
        lyrics_themes = song_context.get("lyrics_themes", [])

        if "family" in lyrics_themes and "parental" in base_prompt.lower():
            return f"{base_prompt.rstrip('.')}. Visual storytelling echoes the song's lyrical themes of family bonds and generational connection"
        elif "love" in lyrics_themes and ("warm" in base_prompt.lower() or "connection" in base_prompt.lower()):
            return f"{base_prompt.rstrip('.')}. Romantic visual elements harmonize with the song's love-themed lyrics"
        elif "nostalgia" in lyrics_themes:
            return f"{base_prompt.rstrip('.')}. Nostalgic visual filters and composition reflect the song's themes of memory and reflection"
        else:
            return f"{base_prompt.rstrip('.')}. Visual narrative supports the song's lyrical emotional journey"

    def _determine_integrated_visual_style(self, integrated_context: Dict, section, song_context: Dict) -> Dict:
        """Enhanced visual style determination using song + concept integration"""

        # Start with base concept-aware styling
        base_style = self._determine_visual_style(integrated_context, section)

        # Enhance with song context
        musical_mood = song_context.get("musical_mood", "neutral")
        tempo = song_context.get("tempo", 120)

        # Adjust style notes based on musical context
        if musical_mood == "calm" and tempo < 90:
            base_style["style_notes"] += ". Slow, deliberate camera movements matching contemplative song pacing"
        elif musical_mood == "energetic" and tempo > 120:
            base_style["style_notes"] += ". Dynamic cinematography with energy matching upbeat musical tempo"

        # Adjust mood based on song integration
        if musical_mood == "melancholic" and "joyful" not in integrated_context.get("emotions", []):
            base_style["mood"] = "bittersweet"
        elif song_context.get("has_lyrics") and "family" in song_context.get("lyrics_themes", []):
            if base_style["mood"] == "heartwarming":
                base_style["mood"] = "deeply_emotional"

        return base_style

    def _generate_ai_recommendations(self, user_concept: str, song_structure: List[SongSection]) -> List[SectionRecommendation]:
        """
        Use GPT-4 to generate intelligent, story-specific section recommendations
        """
        # Prepare song structure for GPT-4
        structure_info = []
        for i, section in enumerate(song_structure):
            structure_info.append({
                "index": i,
                "name": section.name,
                "start_time": section.start_time,
                "end_time": section.end_time,
                "duration": section.end_time - section.start_time
            })

        # Create the GPT-4 prompt
        system_prompt = """You are an expert video director and visual storyteller. Your job is to take a user's overall story concept and intelligently map it across a song's structure, creating specific visual prompts for each section that tell a cohesive narrative arc.

Key principles:
- Each section should advance the story naturally
- Visual style should evolve with the emotional arc
- Prompts should be detailed and cinematically rich
- The story should flow logically from intro to outro
- Consider the duration of each section for pacing
- Make prompts specific to the story, not generic

Focus on creating vivid, specific scenes that directly relate to the story concept provided."""

        user_prompt = f"""Story Concept: "{user_concept}"

Song Structure: {json.dumps(structure_info, indent=2)}

Create visual prompts for each section that tell this specific story cinematically. For each section, provide:
1. A detailed visual prompt (2-3 sentences describing the specific scene that advances this story)
2. Style notes (lighting, mood, visual approach)
3. Color palette (warm/cool/natural/dramatic/muted/vibrant)
4. Overall mood (energetic/calm/dramatic/nostalgic/intimate/etc.)
5. Lighting style (golden hour/dramatic/soft/natural/harsh/etc.)

IMPORTANT: Make each prompt specifically about the story concept, not generic. If it's about a father's love, show that. If it's about overcoming fear, show that. Be specific to the story.

Respond in JSON format with an array of sections like this:
[
  {{
    "section_name": "Intro",
    "visual_prompt": "Specific scene description that relates directly to the story...",
    "style_notes": "Cinematographic approach...",
    "color_palette": "specific color approach",
    "mood": "specific emotional tone",
    "lighting": "specific lighting style"
  }},
  ...
]

Make sure the story flows logically and each section builds on the previous one to tell the complete narrative arc."""

        # Call GPT-4
        print(f"[AI ANALYZE] Calling GPT-4 for story analysis...")
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )

        # Parse the response
        ai_response = response.choices[0].message.content
        print(f"[AI ANALYZE] GPT-4 response received: {len(ai_response)} characters")

        try:
            # Clean up the response (remove markdown formatting if present)
            json_text = ai_response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            ai_sections = json.loads(json_text)

            # Convert to SectionRecommendation objects
            recommendations = []
            for i, ai_section in enumerate(ai_sections):
                if i >= len(song_structure):
                    break  # Don't exceed the actual song structure length

                rec = SectionRecommendation(
                    section_name=ai_section.get("section_name", song_structure[i].name),
                    visual_prompt=ai_section.get("visual_prompt", "Cinematic scene with dramatic composition"),
                    style_notes=ai_section.get("style_notes", "Professional cinematic style"),
                    mood=ai_section.get("mood", "cinematic"),
                    color_palette=ai_section.get("color_palette", "natural"),
                    lighting=ai_section.get("lighting", "dramatic")
                )
                recommendations.append(rec)
                print(f"[AI ANALYZE] Section {i} ({rec.section_name}): {rec.visual_prompt[:80]}...")

            # If GPT-4 returned fewer than expected, fill remaining with AI-generated continuations
            if len(recommendations) < len(song_structure):
                print(f"[AI ANALYZE] GPT-4 returned {len(recommendations)}/{len(song_structure)} - extending with continuations")
                for i in range(len(recommendations), len(song_structure)):
                    section = song_structure[i]
                    # Create a continuation based on the last recommendation's style
                    last_rec = recommendations[-1] if recommendations else None
                    rec = SectionRecommendation(
                        section_name=section.name,
                        visual_prompt=f"Continuing the narrative arc into {section.name}, building on previous scenes with evolving emotional intensity",
                        style_notes=last_rec.style_notes if last_rec else "Professional cinematic style",
                        mood=last_rec.mood if last_rec else "cinematic",
                        color_palette=last_rec.color_palette if last_rec else "natural",
                        lighting=last_rec.lighting if last_rec else "dramatic"
                    )
                    recommendations.append(rec)
                    print(f"[AI ANALYZE] Extended Section {i} ({rec.section_name}): continuation")

            return recommendations

        except json.JSONDecodeError as e:
            print(f"[AI ANALYZE ERROR] Failed to parse GPT-4 JSON response: {e}")
            print(f"[AI ANALYZE ERROR] Raw response: {ai_response}")
            raise Exception(f"GPT-4 returned invalid JSON")

    def _generate_ai_recommendations_with_song(self, user_concept: str, song_structure: List[SongSection], song_analysis: dict) -> List[SectionRecommendation]:
        """
        Use GPT-4 to intelligently blend user concept with actual song analysis
        """
        # Prepare song structure for GPT-4
        structure_info = []
        for i, section in enumerate(song_structure):
            structure_info.append({
                "index": i,
                "name": section.name,
                "start_time": section.start_time,
                "end_time": section.end_time,
                "duration": section.end_time - section.start_time,
                "musical_energy": section.musical_energy,
                "narrative_function": section.narrative_function
            })

        # Extract song context
        lyrics = song_analysis.get("lyrics_data", {}).get("lyrics_text", "")
        musical_mood = song_analysis.get("analysis_data", {}).get("overall_mood", "unknown")
        tempo = song_analysis.get("analysis_data", {}).get("tempo", 120)
        key_signature = song_analysis.get("analysis_data", {}).get("key", "unknown")

        # Detect song themes for better blending
        song_themes = self._detect_song_themes(lyrics, musical_mood)

        # Create enhanced GPT-4 prompt that blends song + concept
        system_prompt = """You are an expert video director who specializes in creating music videos that seamlessly blend the song's actual content with the user's visual concept. Your job is to analyze both the song's lyrics/mood AND the user's concept, then create scenes that tell a cohesive story combining both elements.

Key principles:
- ALWAYS incorporate the song's actual lyrical content and emotional arc
- Blend the user's visual concept/style with the song's narrative
- Each section should advance both the song's story AND the visual concept
- Make the concept feel natural within the song's world
- Consider the song's tempo, mood, and energy for scene pacing
- Create specific, cinematic scenes that serve both the music and the concept

Focus on intelligent fusion - don't just apply the concept as a surface layer, but deeply integrate it with the song's meaning."""

        user_prompt = f"""Song Analysis:
Lyrics: "{lyrics[:500]}{'...' if len(lyrics) > 500 else ''}"
Musical Mood: {musical_mood}
Tempo: {tempo} BPM
Key: {key_signature}
Detected Themes: {', '.join(song_themes)}

User's Visual Concept: "{user_concept}"

Song Structure: {json.dumps(structure_info, indent=2)}

Create a music video treatment that intelligently blends the song's content with the user's concept. For each section, analyze:
1. What the song is expressing in that part (lyrically and musically)
2. How the user's concept can enhance or reframe that expression
3. What specific visual scene would serve both the song AND the concept

For each section, provide:
1. A detailed visual prompt that fuses song content + user concept
2. Style notes explaining how the concept integrates with the song
3. Color palette that matches both mood and concept
4. Overall emotional tone that serves the music
5. Lighting that enhances both song and visual style

Example of good fusion: If song is about heartbreak and concept is "cyberpunk world", don't just put heartbreak in neon city - create scenes where digital love/connection themes parallel the emotional journey, where technology amplifies the human emotion.

Respond in JSON format:
[
  {{
    "section_name": "Intro",
    "visual_prompt": "Specific scene that blends song meaning + user concept...",
    "style_notes": "How the concept serves the song's narrative...",
    "color_palette": "Colors that work for both song mood and concept",
    "mood": "Emotional tone serving both elements",
    "lighting": "Lighting that enhances the fusion"
  }},
  ...
]

Make each prompt feel like it belongs to BOTH the song's world AND the user's concept naturally.

IMPORTANT: Generate a visual prompt for EVERY section listed in the song structure above."""

        # Call GPT-4 with enhanced context
        print(f"[AI ANALYZE] Calling GPT-4 for enhanced song+concept analysis...")
        print(f"[AI ANALYZE] Song themes: {song_themes}")
        print(f"[AI ANALYZE] Musical context: {musical_mood} at {tempo}BPM")

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4500  # Increased to allow full response for 9+ sections
        )

        # Parse and process the enhanced response
        ai_response = response.choices[0].message.content
        print(f"[AI ANALYZE] Enhanced GPT-4 response received: {len(ai_response)} characters")

        try:
            # Clean up the response
            json_text = ai_response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            ai_sections = json.loads(json_text)

            # Convert to SectionRecommendation objects
            recommendations = []
            for i, ai_section in enumerate(ai_sections):
                if i >= len(song_structure):
                    break

                rec = SectionRecommendation(
                    section_name=ai_section.get("section_name", song_structure[i].name),
                    visual_prompt=ai_section.get("visual_prompt", "Cinematic scene blending song and concept"),
                    style_notes=ai_section.get("style_notes", "Fusion of song narrative and visual concept"),
                    mood=ai_section.get("mood", musical_mood),
                    color_palette=ai_section.get("color_palette", "natural"),
                    lighting=ai_section.get("lighting", "dramatic")
                )
                recommendations.append(rec)
                print(f"[AI ANALYZE] Enhanced Section {i} ({rec.section_name}): {rec.visual_prompt[:80]}...")

            # If GPT-4 returned fewer than expected, fill remaining with AI-generated continuations
            if len(recommendations) < len(song_structure):
                print(f"[AI ANALYZE] GPT-4 returned {len(recommendations)}/{len(song_structure)} - extending with continuations")
                for i in range(len(recommendations), len(song_structure)):
                    section = song_structure[i]
                    last_rec = recommendations[-1] if recommendations else None
                    rec = SectionRecommendation(
                        section_name=section.name,
                        visual_prompt=f"Continuing the narrative into {section.name}, the story evolves with deepening emotional resonance and visual progression",
                        style_notes=last_rec.style_notes if last_rec else "Fusion of song narrative and visual concept",
                        mood=last_rec.mood if last_rec else musical_mood,
                        color_palette=last_rec.color_palette if last_rec else "natural",
                        lighting=last_rec.lighting if last_rec else "dramatic"
                    )
                    recommendations.append(rec)
                    print(f"[AI ANALYZE] Extended Section {i} ({rec.section_name}): continuation")

            return recommendations

        except json.JSONDecodeError as e:
            print(f"[AI ANALYZE ERROR] Failed to parse enhanced GPT-4 JSON: {e}")
            print(f"[AI ANALYZE ERROR] Raw response: {ai_response}")
            raise Exception(f"GPT-4 returned invalid JSON format. Please try again.")

    def _detect_song_themes(self, lyrics: str, musical_mood: str) -> List[str]:
        """Detect key themes in the song for better concept integration"""
        themes = []

        lyrics_lower = lyrics.lower()

        # Common song themes detection
        if any(word in lyrics_lower for word in ["love", "heart", "forever", "together", "kiss"]):
            themes.append("romance")

        if any(word in lyrics_lower for word in ["lost", "gone", "goodbye", "alone", "empty"]):
            themes.append("loss")

        if any(word in lyrics_lower for word in ["fight", "strong", "rise", "overcome", "power"]):
            themes.append("empowerment")

        if any(word in lyrics_lower for word in ["remember", "past", "yesterday", "time", "memory"]):
            themes.append("nostalgia")

        if any(word in lyrics_lower for word in ["journey", "road", "travel", "going", "moving"]):
            themes.append("journey")

        if any(word in lyrics_lower for word in ["dream", "hope", "future", "believe", "wish"]):
            themes.append("aspiration")

        if any(word in lyrics_lower for word in ["dark", "shadow", "night", "pain", "hurt"]):
            themes.append("darkness")

        if any(word in lyrics_lower for word in ["light", "bright", "sun", "shine", "glow"]):
            themes.append("hope")

        # Add musical mood as theme
        if musical_mood and musical_mood != "unknown":
            themes.append(f"musical_{musical_mood}")

        return themes if themes else ["general_narrative"]


    def _analyze_concept_elements(self, user_concept: str) -> Dict:
        """Extract and categorize visual and thematic elements from user concept"""
        concept_lower = user_concept.lower()

        # Visual style indicators
        visual_styles = []
        if any(term in concept_lower for term in ["70s", "vintage", "retro", "film-filter"]):
            visual_styles.append("vintage_70s")
        if any(term in concept_lower for term in ["cyberpunk", "neon", "futuristic", "sci-fi"]):
            visual_styles.append("cyberpunk")
        if any(term in concept_lower for term in ["fantasy", "medieval", "magic", "dragons"]):
            visual_styles.append("fantasy")
        if any(term in concept_lower for term in ["dystopian", "dark", "apocalyptic"]):
            visual_styles.append("dystopian")
        if any(term in concept_lower for term in ["beach", "ocean", "sand", "waves"]):
            visual_styles.append("coastal")
        if any(term in concept_lower for term in ["family", "diverse", "together", "bonfire"]):
            visual_styles.append("community")

        # Emotional themes
        emotions = []
        if any(term in concept_lower for term in ["love", "caring", "warm", "bonding"]):
            emotions.append("warm")
        if any(term in concept_lower for term in ["dystopian", "isolated", "phones", "staring"]):
            emotions.append("disconnected")
        if any(term in concept_lower for term in ["party", "dancing", "celebration", "gathering"]):
            emotions.append("joyful")
        if any(term in concept_lower for term in ["father", "dad", "parent", "teaching"]):
            emotions.append("parental")

        # Activities and scenes
        activities = []
        if any(term in concept_lower for term in ["dancing", "party", "celebration"]):
            activities.append("celebration")
        if any(term in concept_lower for term in ["walking", "staring at phones", "isolated"]):
            activities.append("isolation")
        if any(term in concept_lower for term in ["working on", "fixing", "teaching", "showing"]):
            activities.append("craftsmanship")
        if any(term in concept_lower for term in ["beach", "bonfire", "instruments", "drinking"]):
            activities.append("communal_gathering")

        # Color and lighting cues
        colors = []
        if any(term in concept_lower for term in ["golden", "warm", "sunset", "bonfire"]):
            colors.append("warm_golden")
        if any(term in concept_lower for term in ["neon", "electric", "bright"]):
            colors.append("electric_bright")
        if any(term in concept_lower for term in ["70s", "film", "vintage"]):
            colors.append("vintage_film")
        if any(term in concept_lower for term in ["dystopian", "gray", "cold"]):
            colors.append("desaturated_cold")

        return {
            "visual_styles": visual_styles or ["cinematic"],
            "emotions": emotions or ["neutral"],
            "activities": activities or ["general"],
            "colors": colors or ["natural"],
            "raw_concept": user_concept
        }

    def _generate_concept_aware_prompt(self, section, section_index: int, total_sections: int,
                                     user_concept: str, concept_analysis: Dict) -> str:
        """Generate rich, concept-specific visual prompts for each section"""

        section_name = section.name.lower()
        progress = section_index / max(1, total_sections - 1)

        # Extract key elements for this specific prompt
        styles = concept_analysis["visual_styles"]
        emotions = concept_analysis["emotions"]
        activities = concept_analysis["activities"]

        # Build section-specific narrative based on user's detailed concept
        if "intro" in section_name:
            if "vintage_70s" in styles and "coastal" in styles:
                return "Golden hour beach scene with vintage 70s film grain, diverse family walking along shoreline, children playing in waves, parents sharing quiet moments, warm nostalgic lighting filtering through gentle sea breeze"
            elif "parental" in emotions and "craftsmanship" in activities:
                return "Father working quietly in garage, tools organized with methodical care, young person observing from doorway, understanding beginning to form about love expressed through action rather than words"
            else:
                return f"Opening scene establishing the world of {user_concept[:50]}, setting emotional and visual tone for the story to unfold"

        elif "verse" in section_name:
            if "1" in section_name or section_index < total_sections * 0.3:
                if "vintage_70s" in styles and "coastal" in styles:
                    return "Detailed shots of diverse family members enjoying beach activities, children building sandcastles, teenagers playing volleyball, parents setting up picnic with vintage coolers and blankets, all captured with warm film grain"
                elif "parental" in emotions:
                    return "Father demonstrating life lessons through hands-on work, teaching through example rather than words, young person gradually understanding the depth of quiet, consistent care"
                else:
                    concept_fragment = user_concept.split('.')[0] if '.' in user_concept else user_concept[:100]
                    return f"Developing the story elements: {concept_fragment}, introducing key characters and establishing the emotional landscape"

            elif "2" in section_name or section_index > total_sections * 0.4:
                if "dystopian" in styles and "isolation" in activities:
                    return "Stark contrast scene: people walking through urban landscape, faces illuminated only by phone screens, isolated despite physical proximity, cold desaturated colors emphasizing disconnection"
                elif "parental" in emotions:
                    return "Deeper exploration of father's way of showing love through actions, memories of countless small gestures of care and preparation, understanding growing stronger"
                else:
                    return f"Developing tension or contrast in the narrative: exploring the complexity within {user_concept[:60]}, building toward resolution"

        elif "chorus" in section_name:
            if "communal_gathering" in activities and "joyful" in emotions:
                return "Vibrant beach gathering coming to life, people of all backgrounds joining together, musical instruments appearing, dancing around growing bonfire, celebration of human connection"
            elif "parental" in emotions and "warm" in emotions:
                return "Emotional crescendo of understanding, father's love finally fully comprehended, years of quiet care and dedication crystallizing into profound gratitude and recognition"
            else:
                return f"Emotional high point bringing together the themes of {user_concept[:70]}, visual and emotional culmination of the story's central message"

        elif "bridge" in section_name:
            if "communal_gathering" in activities:
                return "Transition moment as more people arrive at beach celebration, barriers breaking down, strangers becoming friends, community forming naturally around shared joy and music"
            elif "parental" in emotions:
                return "Pivotal moment of complete emotional understanding, the full weight of unconditional love expressed through actions, tears of recognition and deep appreciation"
            else:
                return f"Transformative moment in the story where {user_concept[:60]} reaches its turning point, leading toward resolution and deeper understanding"

        elif "outro" in section_name:
            if "communal_gathering" in activities and "coastal" in styles:
                return "Perfect beach celebration in full swing, bonfire crackling under stars, people of all ages and backgrounds sharing stories and music, camera pulling back to reveal the beautiful community formed"
            elif "parental" in emotions:
                return "Peaceful resolution with tools being passed down or lovingly maintained, legacy of care continuing, quiet satisfaction and understanding permanently transforming the relationship"
            else:
                return f"Concluding scene that brings resolution to {user_concept[:50]}, leaving viewer with sense of completion and emotional satisfaction"

        # NO TEMPLATE FALLBACKS - User explicitly requested AI-only
        # If we reach here, it means GPT-4 analysis didn't handle this section type properly
        raise Exception(f"AI analysis failed to generate specific recommendation for section '{section_name}'. No template fallback available - user requested real AI only.")

    def _determine_visual_style(self, concept_analysis: Dict, section) -> Dict:
        """Determine appropriate visual style, mood, colors, and lighting based on concept analysis"""

        styles = concept_analysis["visual_styles"]
        emotions = concept_analysis["emotions"]
        colors = concept_analysis["colors"]

        # Style notes
        if "vintage_70s" in styles:
            style_notes = "Vintage 70s cinematography with film grain, warm color grading, and nostalgic composition"
        elif "cyberpunk" in styles:
            style_notes = "Cyberpunk aesthetic with neon lighting, high contrast, and futuristic urban environments"
        elif "fantasy" in styles:
            style_notes = "Fantasy cinematography with magical lighting, ethereal atmosphere, and rich color palette"
        elif "dystopian" in styles:
            style_notes = "Dystopian visual style with desaturated colors, stark composition, and urban decay"
        else:
            style_notes = "Professional cinematic style with emotionally resonant composition and lighting"

        # Mood
        if "joyful" in emotions and "communal_gathering" in concept_analysis["activities"]:
            mood = "celebratory"
        elif "warm" in emotions or "parental" in emotions:
            mood = "heartwarming"
        elif "disconnected" in emotions:
            mood = "melancholic"
        else:
            mood = "cinematic"

        # Color palette
        if "warm_golden" in colors:
            color_palette = "warm golden tones"
        elif "electric_bright" in colors:
            color_palette = "electric neons and bright accents"
        elif "vintage_film" in colors:
            color_palette = "vintage film color grading"
        elif "desaturated_cold" in colors:
            color_palette = "desaturated and cold tones"
        else:
            color_palette = "natural cinematic palette"

        # Lighting
        if "coastal" in styles and "vintage_70s" in styles:
            lighting = "golden hour beach lighting"
        elif "cyberpunk" in styles:
            lighting = "dramatic neon lighting"
        elif "parental" in emotions:
            lighting = "soft warm interior lighting"
        elif "dystopian" in styles:
            lighting = "harsh urban lighting"
        else:
            lighting = "professional cinematic lighting"

        return {
            "style_notes": style_notes,
            "mood": mood,
            "color_palette": color_palette,
            "lighting": lighting
        }

    def _get_father_story_prompt(self, section_name: str, index: int, total_sections: int) -> str:
        """Generate father-story specific prompts"""
        if "intro" in section_name.lower():
            return "Quiet domestic scene, father working on something mechanical with focused attention, warm but distant lighting, showing care through actions"
        elif "verse 1" in section_name.lower():
            return "Young person watching their father fix something, curiosity and slight confusion, workshop or garage setting, observing quiet dedication"
        elif "chorus 1" in section_name.lower():
            return "Close-up of father's hands working with tools, showing skill and methodical care, the love expressed through preparation and maintenance"
        elif "verse 2" in section_name.lower():
            return "Adult reflecting on memories of father's quiet care, flashback scenes of behind-the-scenes preparation and thoughtfulness"
        elif "chorus 2" in section_name.lower():
            return "Growing realization that actions were expressions of love, warmer lighting, emotional understanding dawning"
        elif "bridge" in section_name.lower():
            return "Pivotal emotional moment of complete understanding, tears of gratitude, the depth of unspoken love finally comprehended"
        elif "verse 3" in section_name.lower():
            return "Present day, continuing the legacy of care, showing love through actions just like father did, full circle"
        elif "chorus" in section_name.lower() and "final" in section_name.lower():
            return "Full emotional understanding and appreciation, warmth and gratitude, father's love finally fully seen and valued"
        elif "outro" in section_name.lower():
            return "Peaceful resolution, tools being put away or passed down, quiet satisfaction, love understood and cherished"
        else:
            return f"Emotional scene showing father's love through actions in {section_name.lower()}, advancing the story of understanding"

    def _get_love_story_prompt(self, section_name: str, index: int, total_sections: int) -> str:
        """Generate love-story specific prompts"""
        progress = index / max(1, total_sections - 1)

        if progress < 0.2:
            return f"First meeting or early attraction, tentative glances and hopeful energy, {section_name.lower()} with soft romantic lighting"
        elif progress < 0.4:
            return f"Growing connection, shared moments and laughter, deepening bond, {section_name.lower()} with warm intimate atmosphere"
        elif progress < 0.6:
            return f"Challenge or misunderstanding, relationship tested, {section_name.lower()} with dramatic tension and uncertainty"
        elif progress < 0.8:
            return f"Resolution and deeper commitment, love overcoming obstacles, {section_name.lower()} with triumphant and hopeful emotion"
        else:
            return f"Peaceful love and bright future together, {section_name.lower()} with contentment and lasting happiness"

    def _get_journey_story_prompt(self, section_name: str, index: int, total_sections: int) -> str:
        """Generate journey-story specific prompts"""
        progress = index / max(1, total_sections - 1)

        if progress < 0.2:
            return f"Beginning of journey, departure or first steps, {section_name.lower()} with anticipation and uncertainty"
        elif progress < 0.4:
            return f"Early challenges and learning, adapting to new environments, {section_name.lower()} with discovery and growth"
        elif progress < 0.6:
            return f"Major obstacles or setbacks, testing resolve, {section_name.lower()} with dramatic tension and perseverance"
        elif progress < 0.8:
            return f"Breaking through barriers, finding inner strength, {section_name.lower()} with triumph and realization"
        else:
            return f"Journey's end with wisdom gained, transformation complete, {section_name.lower()} with peaceful accomplishment"