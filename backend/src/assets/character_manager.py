"""
Character Manager - Multi-Character Support for BeatCanvas

This module manages character definitions and reference images for consistent
character appearance across video scenes. Supports family videos and musicians
who want to appear in their own videos.

Key concepts:
- User input is the primary source for character count
- Reference images validate/inform character definitions
- Per-scene character subsets allow different characters in different scenes

Usage:
    manager = CharacterManager()
    manager.add_character("alice", "Young woman with red hair", "path/to/alice.jpg")
    manager.add_character("bob", "Middle-aged man with glasses")

    # For a scene with both characters
    prompt = manager.build_prompt_with_characters(
        base_prompt="Walking through park at sunset",
        character_names=["alice", "bob"]
    )
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHARACTER CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAX_CHARACTERS_PER_SCENE = 2  # AI video works best with 1-2 characters
MAX_TOTAL_CHARACTERS = 6      # Reasonable limit for consistency

REFERENCE_IMAGE_DIR = Path("data/references/characters")


@dataclass
class Character:
    """Definition of a character for video generation"""
    name: str                           # Unique identifier (e.g., "alice")
    description: str                    # Visual description for prompts
    reference_image_path: Optional[str] = None  # Path to reference image
    silhouette_keywords: List[str] = field(default_factory=list)  # Distinct visual features
    color_palette: List[str] = field(default_factory=list)  # Character's color scheme

    def to_prompt_fragment(self) -> str:
        """Generate prompt fragment describing this character"""
        parts = [self.description]
        if self.silhouette_keywords:
            parts.append(f"distinctive features: {', '.join(self.silhouette_keywords)}")
        if self.color_palette:
            parts.append(f"wearing colors: {', '.join(self.color_palette)}")
        return ", ".join(parts)


class CharacterManager:
    """
    Manages characters and their reference images for video generation.

    Design principles:
    - User input is primary source for character count (API request)
    - Reference images validate/enhance but don't override user intent
    - Support per-scene character subsets (not everyone in every scene)
    """

    def __init__(self):
        self.characters: Dict[str, Character] = {}
        REFERENCE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def add_character(
        self,
        name: str,
        description: str,
        reference_image_path: Optional[str] = None,
        silhouette_keywords: Optional[List[str]] = None,
        color_palette: Optional[List[str]] = None
    ) -> Character:
        """
        Add a character definition.

        Args:
            name: Unique identifier (lowercase, no spaces recommended)
            description: Visual description for AI prompts
            reference_image_path: Optional path to reference photo
            silhouette_keywords: Distinctive features for recognition
            color_palette: Character's typical colors

        Returns:
            Created Character object
        """
        if len(self.characters) >= MAX_TOTAL_CHARACTERS:
            logger.warning(f"Character limit ({MAX_TOTAL_CHARACTERS}) reached")
            raise ValueError(f"Maximum {MAX_TOTAL_CHARACTERS} characters allowed")

        character = Character(
            name=name.lower().strip(),
            description=description,
            reference_image_path=reference_image_path,
            silhouette_keywords=silhouette_keywords or [],
            color_palette=color_palette or []
        )

        self.characters[character.name] = character
        logger.info(f"Added character: {character.name}")
        return character

    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name"""
        return self.characters.get(name.lower().strip())

    def list_characters(self) -> List[str]:
        """List all character names"""
        return list(self.characters.keys())

    def remove_character(self, name: str) -> bool:
        """Remove a character definition"""
        name = name.lower().strip()
        if name in self.characters:
            del self.characters[name]
            return True
        return False

    def build_prompt_with_characters(
        self,
        base_prompt: str,
        character_names: List[str],
        max_characters: int = MAX_CHARACTERS_PER_SCENE
    ) -> str:
        """
        Build an image/video prompt that includes character descriptions.

        Args:
            base_prompt: The scene description
            character_names: Which characters appear in this scene
            max_characters: Maximum characters to include (AI limit)

        Returns:
            Enhanced prompt with character descriptions
        """
        if not character_names:
            return base_prompt

        # Limit characters per scene for AI quality
        selected = character_names[:max_characters]
        if len(character_names) > max_characters:
            logger.warning(
                f"Scene has {len(character_names)} characters, "
                f"limiting to {max_characters} for AI quality"
            )

        # Build character descriptions
        char_descriptions = []
        for name in selected:
            char = self.get_character(name)
            if char:
                char_descriptions.append(char.to_prompt_fragment())

        if not char_descriptions:
            return base_prompt

        # Combine: "Scene description, featuring Character A (description), Character B (description)"
        char_text = ", ".join(char_descriptions)
        return f"{base_prompt}, featuring {char_text}"

    def validate_against_references(self) -> Dict[str, bool]:
        """
        Validate that reference images exist for characters that have them.

        Returns:
            Dict mapping character name to whether reference is valid
        """
        results = {}
        for name, char in self.characters.items():
            if char.reference_image_path:
                results[name] = os.path.exists(char.reference_image_path)
            else:
                results[name] = True  # No reference required
        return results

    def get_reference_images(self, character_names: List[str]) -> Dict[str, str]:
        """
        Get reference image paths for specified characters.

        Args:
            character_names: List of character names

        Returns:
            Dict mapping name to image path (only for those with references)
        """
        refs = {}
        for name in character_names:
            char = self.get_character(name)
            if char and char.reference_image_path:
                if os.path.exists(char.reference_image_path):
                    refs[name] = char.reference_image_path
        return refs

    def infer_characters_from_prompt(self, user_prompt: str) -> List[str]:
        """
        Try to infer which characters should appear based on user prompt.

        This is a simple heuristic - user input should be primary source.

        Args:
            user_prompt: The user's video concept prompt

        Returns:
            List of character names mentioned
        """
        prompt_lower = user_prompt.lower()
        mentioned = []
        for name in self.characters:
            if name in prompt_lower:
                mentioned.append(name)
        return mentioned

    def to_dict(self) -> Dict:
        """Serialize all characters for JSON storage"""
        return {
            name: {
                'name': char.name,
                'description': char.description,
                'reference_image_path': char.reference_image_path,
                'silhouette_keywords': char.silhouette_keywords,
                'color_palette': char.color_palette
            }
            for name, char in self.characters.items()
        }

    def from_dict(self, data: Dict) -> None:
        """Load characters from JSON data"""
        self.characters.clear()
        for name, char_data in data.items():
            self.add_character(
                name=char_data['name'],
                description=char_data['description'],
                reference_image_path=char_data.get('reference_image_path'),
                silhouette_keywords=char_data.get('silhouette_keywords', []),
                color_palette=char_data.get('color_palette', [])
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCENE CHARACTER ASSIGNMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def assign_characters_to_scenes(
    storyboard: List[Dict],
    character_manager: CharacterManager,
    strategy: str = "rotate"
) -> List[Dict]:
    """
    Assign characters to scenes based on a strategy.

    Strategies:
    - "all": All characters in every scene (limited by MAX_CHARACTERS_PER_SCENE)
    - "rotate": Rotate through characters scene by scene
    - "solo": One character per scene, rotating
    - "narrative": Based on scene description (attempts to match)

    Args:
        storyboard: List of scene dicts
        character_manager: CharacterManager with defined characters
        strategy: Assignment strategy

    Returns:
        Updated storyboard with 'characters_in_scene' field
    """
    char_names = character_manager.list_characters()
    if not char_names:
        return storyboard

    for i, scene in enumerate(storyboard):
        if strategy == "all":
            scene['characters_in_scene'] = char_names[:MAX_CHARACTERS_PER_SCENE]
        elif strategy == "rotate":
            # Cycle through pairs
            start_idx = (i * 2) % len(char_names)
            selected = []
            for j in range(min(2, len(char_names))):
                selected.append(char_names[(start_idx + j) % len(char_names)])
            scene['characters_in_scene'] = selected
        elif strategy == "solo":
            scene['characters_in_scene'] = [char_names[i % len(char_names)]]
        elif strategy == "narrative":
            # Try to match from scene description
            mentioned = character_manager.infer_characters_from_prompt(
                scene.get('description', '')
            )
            if mentioned:
                scene['characters_in_scene'] = mentioned[:MAX_CHARACTERS_PER_SCENE]
            else:
                # Fallback to rotate
                scene['characters_in_scene'] = [char_names[i % len(char_names)]]
        else:
            scene['characters_in_scene'] = []

    return storyboard


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FAMILY VIDEO PRESETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_family_preset(family_members: List[Dict]) -> CharacterManager:
    """
    Create a CharacterManager preset for family videos.

    Args:
        family_members: List of dicts with 'name', 'description', 'reference_image'

    Example:
        members = [
            {'name': 'mom', 'description': 'Woman in her 40s with brown hair'},
            {'name': 'dad', 'description': 'Tall man with beard'},
            {'name': 'kid1', 'description': 'Young girl, about 8 years old'},
            {'name': 'kid2', 'description': 'Young boy, about 5 years old'}
        ]
        manager = create_family_preset(members)

    Returns:
        Configured CharacterManager
    """
    manager = CharacterManager()

    for member in family_members:
        manager.add_character(
            name=member.get('name', 'unknown'),
            description=member.get('description', 'Person'),
            reference_image_path=member.get('reference_image'),
            silhouette_keywords=member.get('silhouette_keywords', []),
            color_palette=member.get('color_palette', [])
        )

    return manager
