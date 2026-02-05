import openai
from typing import Dict, List
from dataclasses import dataclass
import json
import os

@dataclass
class VisualConcept:
    overall_style: str
    color_palette: List[str]
    mood_progression: List[str]
    key_visual_themes: List[str]
    camera_style: str

class ConceptGenerator:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = openai.OpenAI(api_key=api_key)

    def generate_concept(self, music_data: Dict, user_prompt: str) -> VisualConcept:
        """Generate visual concept based on music analysis and user input"""

        system_prompt = """You are a music video director and visual artist.
Create compelling visual concepts that sync with music structure and emotion.
Respond only with valid JSON in the exact format specified."""

        # Prepare music analysis summary for the prompt
        segments_summary = []
        for i, segment in enumerate(music_data['segments']):
            segments_summary.append(f"Segment {i+1}: {segment['start_time']:.1f}-{segment['end_time']:.1f}s, "
                                  f"mood: {segment['mood']}, energy: {segment['energy']:.2f}")

        user_message = f"""
        Music Analysis:
        - Duration: {music_data['duration']:.1f} seconds
        - Tempo: {music_data['tempo']:.1f} BPM
        - Overall Energy: {music_data['overall_energy']:.2f}
        - Segments: {len(music_data['segments'])} sections

        Segment Details:
        {chr(10).join(segments_summary)}

        User's Creative Direction: {user_prompt}

        Create a cohesive visual concept. Respond with JSON only:
        {{
            "overall_style": "photographic/animated/abstract/cinematic/etc",
            "color_palette": ["color1", "color2", "color3", "color4"],
            "mood_progression": ["mood for start", "mood for middle", "mood for end"],
            "key_visual_themes": ["theme1", "theme2", "theme3"],
            "camera_style": "static/dynamic/handheld/cinematic/sweeping/etc"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.8,
                max_tokens=500
            )

            response_content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle potential markdown formatting)
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()
            elif "```" in response_content:
                json_start = response_content.find("```") + 3
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()

            # Parse JSON response into VisualConcept
            concept_data = json.loads(response_content)

            return VisualConcept(
                overall_style=concept_data.get('overall_style', 'cinematic'),
                color_palette=concept_data.get('color_palette', ['blue', 'gold', 'white', 'black']),
                mood_progression=concept_data.get('mood_progression', ['calm', 'building', 'intense']),
                key_visual_themes=concept_data.get('key_visual_themes', ['movement', 'light', 'emotion']),
                camera_style=concept_data.get('camera_style', 'cinematic')
            )

        except json.JSONDecodeError as e:
            # Fallback concept if JSON parsing fails
            print(f"JSON parsing error in concept generation: {e}")
            return self._create_fallback_concept(user_prompt)

        except Exception as e:
            print(f"Error in concept generation: {e}")
            return self._create_fallback_concept(user_prompt)

    def _create_fallback_concept(self, user_prompt: str) -> VisualConcept:
        """Create a fallback concept based on user prompt keywords"""

        prompt_lower = user_prompt.lower() if user_prompt else ""

        # Determine style based on keywords
        if any(word in prompt_lower for word in ['cartoon', 'anime', 'animated']):
            style = "animated"
            palette = ["bright_blue", "pink", "yellow", "purple"]
        elif any(word in prompt_lower for word in ['dark', 'gothic', 'noir']):
            style = "cinematic"
            palette = ["black", "deep_red", "silver", "charcoal"]
        elif any(word in prompt_lower for word in ['nature', 'outdoor', 'forest']):
            style = "photographic"
            palette = ["forest_green", "earth_brown", "sky_blue", "sunlight_gold"]
        else:
            style = "cinematic"
            palette = ["deep_blue", "gold", "white", "charcoal"]

        # Determine themes based on keywords
        if any(word in prompt_lower for word in ['dance', 'movement']):
            themes = ["movement", "rhythm", "energy"]
        elif any(word in prompt_lower for word in ['love', 'romantic']):
            themes = ["romance", "connection", "emotion"]
        elif any(word in prompt_lower for word in ['action', 'dynamic']):
            themes = ["action", "intensity", "power"]
        else:
            themes = ["emotion", "journey", "transformation"]

        return VisualConcept(
            overall_style=style,
            color_palette=palette,
            mood_progression=["building", "climax", "resolution"],
            key_visual_themes=themes,
            camera_style="dynamic"
        )

    def suggest_visual_styles(self, content_prompt: str) -> List[str]:
        """Generate AI-powered visual style suggestions based on content prompt"""

        system_prompt = """You are a creative director specializing in music video aesthetics.
        Based on the user's content description, suggest 4-6 diverse visual styles that would work well.
        Focus on distinct aesthetic approaches that would create different moods and feels.
        Respond with just a JSON array of style strings, no other text."""

        user_message = f"""
        Content Description: {content_prompt}

        Suggest 4-6 distinct visual styles for this content. Each style should be concise but descriptive (2-6 words).
        Examples of good styles:
        - "Photorealistic cinematic"
        - "Animated watercolor"
        - "Neon cyberpunk aesthetic"
        - "Film noir black & white"
        - "Studio Ghibli inspired"
        - "Abstract geometric patterns"

        Respond with JSON array only:
        ["style1", "style2", "style3", "style4", "style5", "style6"]
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.9,
                max_tokens=300
            )

            response_content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle potential markdown formatting)
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()
            elif "```" in response_content:
                json_start = response_content.find("```") + 3
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()

            # Parse JSON response
            suggestions = json.loads(response_content)

            # Ensure it's a list and has reasonable length
            if isinstance(suggestions, list) and 2 <= len(suggestions) <= 8:
                return suggestions[:6]  # Limit to 6 suggestions max
            else:
                return self._create_fallback_style_suggestions(content_prompt)

        except (json.JSONDecodeError, Exception) as e:
            print(f"Error generating style suggestions: {e}")
            return self._create_fallback_style_suggestions(content_prompt)

    def _create_fallback_style_suggestions(self, content_prompt: str) -> List[str]:
        """Create fallback style suggestions based on content keywords"""

        prompt_lower = content_prompt.lower() if content_prompt else ""

        # Base suggestions that work for most content
        base_suggestions = ["Photorealistic cinematic", "Artistic illustration", "Abstract expressionist"]

        # Add contextual suggestions based on keywords
        additional = []

        if any(word in prompt_lower for word in ['dance', 'dancer', 'dancing']):
            additional.extend(["Neon nightclub aesthetic", "Ballet studio elegance"])
        elif any(word in prompt_lower for word in ['nature', 'forest', 'ocean', 'mountain']):
            additional.extend(["National Geographic documentary", "Impressionist painting"])
        elif any(word in prompt_lower for word in ['city', 'urban', 'street']):
            additional.extend(["Cyberpunk neon", "Film noir style"])
        elif any(word in prompt_lower for word in ['fantasy', 'magical', 'mystical']):
            additional.extend(["Studio Ghibli inspired", "Dark fantasy gothic"])
        elif any(word in prompt_lower for word in ['love', 'romantic', 'couple']):
            additional.extend(["Dreamy soft focus", "Vintage film aesthetic"])
        else:
            additional.extend(["Minimalist geometric", "Retro synthwave"])

        # Combine and return up to 6 suggestions
        all_suggestions = base_suggestions + additional
        return all_suggestions[:6]

    def concept_to_dict(self, concept: VisualConcept) -> Dict:
        """Convert VisualConcept to dictionary for JSON serialization"""
        return {
            'overall_style': concept.overall_style,
            'color_palette': concept.color_palette,
            'mood_progression': concept.mood_progression,
            'key_visual_themes': concept.key_visual_themes,
            'camera_style': concept.camera_style
        }