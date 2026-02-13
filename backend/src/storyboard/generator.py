from anthropic import Anthropic
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import os
import json
from .conceptor import VisualConcept

# Load environment variables (must happen before API client init)
from src.utils import env_loader

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MOTION PROMPT CONFIGURATION - Image-to-Video Upgrade
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Motion prompt guidance for GPT-4 (calibrated to energy level)
MOTION_PROMPT_SYSTEM = """
Generate a motion description for AI video animation. Be specific about:
- Camera movement (slow push in, gentle pan left, static, handheld drift)
- Subject motion (hair flowing, eyes blinking, fabric rippling)
- Environmental motion (leaves falling, smoke rising, light shifting)
- Tempo (match the song energy level provided)

TEMPO GUIDELINES:
- Low energy (0.0-0.4): Static camera, minimal subject motion, slow environmental drift
- Medium energy (0.4-0.7): Slow dolly/pan, subtle subject motion, moderate environment
- High energy (0.7-1.0): Dynamic camera push, active subject elements, energetic environment

Keep prompts under 50 words. Avoid:
- Scene changes or teleportation
- Impossible physics (flying, transforming)
- Complex character actions (walking, running, dancing)
- Multiple sequential movements

EXAMPLES:
Low energy: "Static wide shot, gentle mist drifts across frame, soft light flickers on subject's face"
Medium energy: "Slow camera push-in, wind ripples through fabric, golden light shifts across scene"
High energy: "Dynamic handheld drift, hair and fabric billow dramatically, particles swirl through frame"
"""

# Character design guidance for consistent animation
CHARACTER_GUIDANCE = """
For consistent character animation:
- Maximum 1-2 characters per scene
- Use distinct silhouettes and solid colors
- Prefer medium shots (waist-up) over full body
- Focus on environment and mood, not complex action
"""

# Style anchor for visual consistency
DEFAULT_STYLE_ANCHOR = "cinematic, 35mm film grain, consistent warm lighting"
DEFAULT_NEGATIVE_PROMPT = "cartoon, anime, oversaturated, morphing faces, scene changes"


@dataclass
class StoryboardScene:
    timestamp_start: float
    timestamp_end: float
    description: str
    visual_style: str
    mood: str
    camera_direction: str
    image_prompt: str
    effects: List[str]
    # New fields for image-to-video upgrade
    motion_prompt: str = ""
    style_anchor: str = DEFAULT_STYLE_ANCHOR
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT
    scene_type: str = "standard"  # 'hero' or 'standard'
    energy: float = 0.5
    characters_in_scene: List[str] = field(default_factory=list)

class StoryboardGenerator:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = Anthropic(api_key=api_key)

    def create_storyboard(self, music_data: Dict, concept: VisualConcept, scene_timings: List[tuple] = None) -> List[StoryboardScene]:
        """Generate detailed scene-by-scene storyboard"""

        if not scene_timings:
            # Use music segments as scene timings
            scene_timings = [(seg['start_time'], seg['end_time']) for seg in music_data['segments']]

        scenes = []
        total_scenes = len(scene_timings)

        for i, (start_time, end_time) in enumerate(scene_timings):
            # Find corresponding music segment for this timing
            segment = self._find_segment_for_time(music_data['segments'], start_time)

            scene = self._generate_scene(
                start_time, end_time, segment, concept, i, total_scenes,
                music_data['tempo'], music_data['overall_energy']
            )
            scenes.append(scene)

        return scenes

    def _find_segment_for_time(self, segments: List[Dict], target_time: float) -> Dict:
        """Find the music segment that contains the target time"""
        for segment in segments:
            if segment['start_time'] <= target_time <= segment['end_time']:
                return segment

        # Fallback to closest segment
        closest_segment = min(segments,
                            key=lambda s: abs(s['start_time'] - target_time))
        return closest_segment

    def _generate_scene(self, start_time: float, end_time: float, segment: Dict,
                       concept: VisualConcept, scene_num: int, total_scenes: int,
                       overall_tempo: float, overall_energy: float) -> StoryboardScene:
        """Generate a single scene description"""

        # Determine mood progression
        progress = scene_num / max(total_scenes - 1, 1)
        if progress < 0.33:
            concept_mood = concept.mood_progression[0] if concept.mood_progression else "building"
        elif progress < 0.67:
            concept_mood = concept.mood_progression[1] if len(concept.mood_progression) > 1 else "climax"
        else:
            concept_mood = concept.mood_progression[2] if len(concept.mood_progression) > 2 else "resolution"

        # Determine scene type based on energy
        energy = segment.get('energy', 0.5)
        scene_type = self._classify_scene_type(energy, scene_num, total_scenes, segment)

        system_prompt = f"""You are a music video director creating detailed scene descriptions.
Create vivid, specific scenes that match the music's energy and emotion.
{MOTION_PROMPT_SYSTEM}
{CHARACTER_GUIDANCE}
Respond only with valid JSON in the exact format specified."""

        prompt = f"""
        Create a detailed scene for a music video:

        Scene {scene_num+1} of {total_scenes}
        Timeframe: {start_time:.1f}s to {end_time:.1f}s (duration: {end_time - start_time:.1f}s)
        Music Segment Energy: {energy:.2f}
        Music Segment Mood: {segment.get('mood', 'neutral')}
        Overall Concept Mood: {concept_mood}
        Beat Strength: {segment.get('beat_strength', 0.5):.2f}
        Scene Type: {scene_type} ({"will be animated as video" if scene_type == "hero" else "will use Ken Burns effect"})

        Visual Concept Context:
        - Style: {concept.overall_style}
        - Color Palette: {', '.join(concept.color_palette)}
        - Key Themes: {', '.join(concept.key_visual_themes)}
        - Camera Style: {concept.camera_style}

        Respond with JSON only:
        {{
            "description": "Detailed visual description of what's happening in the scene",
            "camera_direction": "specific camera instruction (close-up/wide shot/movement/angle)",
            "image_prompt": "precise AnimateDiff video prompt: front-lit, well-lit faces, visible facial features, bright daylight, colorful clothing, photorealistic. AVOID: silhouettes, backlighting, dark shadows, sunset backlighting",
            "motion_prompt": "AI video motion description matching energy level {energy:.2f}",
            "effects": ["effect1", "effect2"]
        }}

        Make the scene match the music energy level and maintain visual consistency.
        For motion_prompt: Low energy (static camera, minimal motion), Medium (slow dolly/pan), High (dynamic camera, active elements).
        """

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_content = response.content[0].text.strip()

            # Extract JSON from response
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()
            elif "```" in response_content:
                json_start = response_content.find("```") + 3
                json_end = response_content.find("```", json_start)
                response_content = response_content[json_start:json_end].strip()

            scene_data = json.loads(response_content)

            return StoryboardScene(
                timestamp_start=start_time,
                timestamp_end=end_time,
                description=scene_data.get('description', f'Scene {scene_num+1}'),
                visual_style=concept.overall_style,
                mood=segment.get('mood', 'neutral'),
                camera_direction=scene_data.get('camera_direction', 'medium shot'),
                image_prompt=scene_data.get('image_prompt', self._create_fallback_prompt(concept, segment, scene_num)),
                effects=scene_data.get('effects', []),
                # New fields for image-to-video upgrade
                motion_prompt=scene_data.get('motion_prompt', self._create_fallback_motion_prompt(energy)),
                style_anchor=DEFAULT_STYLE_ANCHOR,
                negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                scene_type=scene_type,
                energy=energy,
                characters_in_scene=[]
            )

        except (json.JSONDecodeError, Exception) as e:
            print(f"Error generating scene {scene_num}: {e}")
            return self._create_fallback_scene(start_time, end_time, concept, segment, scene_num)

    def _classify_scene_type(self, energy: float, scene_num: int, total_scenes: int, segment: Dict) -> str:
        """
        Classify scene as 'hero' (gets video treatment) or 'standard' (Ken Burns).

        Hero criteria:
        - High energy (>0.7)
        - Climax position (last 25% of song)
        - Chorus/hook sections
        """
        progress = scene_num / max(total_scenes - 1, 1)
        is_climax = progress > 0.75
        is_high_energy = energy > 0.7
        is_chorus = segment.get('label', '').lower() in ['chorus', 'hook', 'drop', 'climax']

        if is_climax or is_high_energy or is_chorus:
            return "hero"
        return "standard"

    def _create_fallback_motion_prompt(self, energy: float) -> str:
        """Create fallback motion prompt based on energy level"""
        if energy < 0.4:
            return "Static wide shot, gentle mist drifts across frame, soft ambient light"
        elif energy < 0.7:
            return "Slow camera push-in, subtle environmental motion, light shifts gradually"
        else:
            return "Dynamic handheld drift, hair and fabric billow, particles swirl through frame"

    def _create_fallback_prompt(self, concept: VisualConcept, segment: Dict, scene_num: int) -> str:
        """Create fallback image prompt if JSON parsing fails"""
        energy_desc = "high energy" if segment.get('energy', 0.5) > 0.6 else "calm"
        mood_desc = segment.get('mood', 'neutral')

        return f"""
        {concept.overall_style} style scene, {energy_desc} {mood_desc} mood,
        featuring {', '.join(concept.key_visual_themes[:2])},
        color palette: {', '.join(concept.color_palette[:3])},
        {concept.camera_style} camera work,
        professional cinematography, 16:9 aspect ratio, high quality
        """

    def _create_fallback_scene(self, start_time: float, end_time: float,
                              concept: VisualConcept, segment: Dict, scene_num: int) -> StoryboardScene:
        """Create fallback scene if generation fails"""
        energy = segment.get('energy', 0.5)

        return StoryboardScene(
            timestamp_start=start_time,
            timestamp_end=end_time,
            description=f"Visual scene with {concept.overall_style} style, {segment.get('mood', 'neutral')} mood",
            visual_style=concept.overall_style,
            mood=segment.get('mood', 'neutral'),
            camera_direction="medium shot",
            image_prompt=self._create_fallback_prompt(concept, segment, scene_num),
            effects=["fade_in"] if scene_num == 0 else [],
            # New fields for image-to-video upgrade
            motion_prompt=self._create_fallback_motion_prompt(energy),
            style_anchor=DEFAULT_STYLE_ANCHOR,
            negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            scene_type="standard",
            energy=energy,
            characters_in_scene=[]
        )

    def scenes_to_dict_list(self, scenes: List[StoryboardScene]) -> List[Dict]:
        """Convert list of scenes to list of dictionaries for JSON serialization"""
        return [
            {
                'timestamp_start': scene.timestamp_start,
                'timestamp_end': scene.timestamp_end,
                'description': scene.description,
                'visual_style': scene.visual_style,
                'mood': scene.mood,
                'camera_direction': scene.camera_direction,
                'image_prompt': scene.image_prompt,
                'effects': scene.effects,
                # New fields for image-to-video upgrade
                'motion_prompt': scene.motion_prompt,
                'style_anchor': scene.style_anchor,
                'negative_prompt': scene.negative_prompt,
                'scene_type': scene.scene_type,
                'energy': scene.energy,
                'characters_in_scene': scene.characters_in_scene
            }
            for scene in scenes
        ]