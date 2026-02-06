"""
Style Logic - Three style abstractions for cinematography.

YAML-DRIVEN: Loads director_inject (additional_triggers/prompt_tokens) from
the production_styles section of optics_presets.yaml.

Styles:
- STYLE_HIGH_VELOCITY_ACTION: Bolex H16 + Cinestill 800T + Hard Light
- STYLE_URBAN_LUXURY: ARRI ALEXA 65 + Kodak Vision3 + Neon Noir
- STYLE_PHYSICAL_DRAMA: RED + Kodak Portra 160 + Bounced Soft Light
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from src.cinematography.prompt_composer import (
    OpticsProfile,
    ComposedPrompt,
    compose_prompt,
    extract_subject_keywords,
)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

STYLE_HIGH_VELOCITY_ACTION = "STYLE_HIGH_VELOCITY_ACTION"
STYLE_URBAN_LUXURY = "STYLE_URBAN_LUXURY"
STYLE_PHYSICAL_DRAMA = "STYLE_PHYSICAL_DRAMA"
STYLE_BEACH_CASUAL = "STYLE_BEACH_CASUAL"

ALL_STYLES = [STYLE_HIGH_VELOCITY_ACTION, STYLE_URBAN_LUXURY, STYLE_PHYSICAL_DRAMA, STYLE_BEACH_CASUAL]


# ═══════════════════════════════════════════════════════════════════════════════
# YAML LOADING
# ═══════════════════════════════════════════════════════════════════════════════

_YAML_PATH = Path(__file__).parent.parent.parent / "library" / "optics_presets.yaml"
_YAML_CACHE: Optional[Dict[str, Any]] = None


def _load_yaml() -> Dict[str, Any]:
    """Load and cache YAML data."""
    global _YAML_CACHE
    if _YAML_CACHE is None:
        if _YAML_PATH.exists():
            with open(_YAML_PATH, "r") as f:
                _YAML_CACHE = yaml.safe_load(f) or {}
        else:
            _YAML_CACHE = {}
    return _YAML_CACHE


def _get_production_style(style_name: str) -> Dict[str, Any]:
    """Get production style config from YAML."""
    data = _load_yaml()
    return data.get("production_styles", {}).get(style_name, {})


def get_director_inject(style_name: str) -> str:
    """
    Get director_inject (additional_triggers or prompt_tokens) from YAML.

    This is the HIGH PRIORITY content that goes FIRST in the prompt.
    """
    style_config = _get_production_style(style_name)

    # Check for prompt_tokens first (used by PHYSICAL_DRAMA)
    if "prompt_tokens" in style_config:
        return style_config["prompt_tokens"].strip()

    # Fall back to additional_triggers (used by ACTION and LUXURY)
    if "additional_triggers" in style_config:
        return style_config["additional_triggers"].strip()

    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class StyleDefinition:
    """Complete style definition with optics and metadata."""

    name: str
    display_name: str
    description: str
    optics: OpticsProfile
    style_prefix: str
    trigger_keywords: frozenset
    cfg_scale: float = 7.0
    steps: int = 30
    recommended_checkpoint: str = "STANDARD_CINEMATIC"


# Base style definitions (optics from YAML, trigger keywords hardcoded)
_BASE_DEFINITIONS: Dict[str, StyleDefinition] = {
    STYLE_HIGH_VELOCITY_ACTION: StyleDefinition(
        name=STYLE_HIGH_VELOCITY_ACTION,
        display_name="High Velocity Action",
        description="Raw action sequences - fights, chases, sports, explosions",
        optics=OpticsProfile(
            camera="BOLEX_H16",
            film_stock="CINESTILL_800T",
            lighting="HARD_LIGHT",
            motion="HANDHELD_AGGRESSIVE",
        ),
        style_prefix="",  # Director inject replaces this
        trigger_keywords=frozenset([
            "action", "fight", "chase", "explosion", "sports", "running",
            "combat", "battle", "crash", "impact", "velocity", "speed",
            "punch", "kick", "jump", "fall", "gunfight", "attack",
        ]),
        cfg_scale=8.0,
        steps=30,
        recommended_checkpoint="STANDARD_CINEMATIC",
    ),
    STYLE_URBAN_LUXURY: StyleDefinition(
        name=STYLE_URBAN_LUXURY,
        display_name="Urban Luxury",
        description="High-end urban aesthetic - fashion, nightlife, elegance",
        optics=OpticsProfile(
            camera="ARRI_ALEXA_65",
            film_stock="KODAK_VISION3_500T",
            lighting="NEON_NOIR",  # Updated from YAML
            motion="STEADICAM_SMOOTH",
        ),
        style_prefix="",  # Director inject replaces this
        trigger_keywords=frozenset([
            "luxury", "fashion", "elegant", "urban", "night", "city",
            "glamour", "sophisticated", "expensive", "haute", "couture",
            "penthouse", "rooftop", "limousine", "champagne", "designer",
            "model", "runway", "nightclub", "upscale", "exclusive",
        ]),
        cfg_scale=7.0,
        steps=30,
        recommended_checkpoint="STANDARD_CINEMATIC",
    ),
    STYLE_PHYSICAL_DRAMA: StyleDefinition(
        name=STYLE_PHYSICAL_DRAMA,
        display_name="Physical Drama",
        description="Intimate physical moments - portraits, drama, connection",
        optics=OpticsProfile(
            camera="RED_DIGITAL_CINEMA",
            film_stock="KODAK_PORTRA_160",
            lighting="BOUNCED_SOFT",
            motion="STATIC_LOCKED",
        ),
        style_prefix="",  # Director inject replaces this
        trigger_keywords=frozenset([
            "drama", "emotional", "intimate", "portrait", "close",
            "tears", "crying", "embrace", "hug", "love", "tender",
            "vulnerable", "confession", "heartbreak", "reunion",
            "conversation", "quiet", "reflection", "contemplation",
        ]),
        cfg_scale=6.5,
        steps=35,
        recommended_checkpoint="STANDARD_CINEMATIC",
    ),
    STYLE_BEACH_CASUAL: StyleDefinition(
        name=STYLE_BEACH_CASUAL,
        display_name="Beach Casual",
        description="Relaxed beach scenes - walking, dancing, singing, natural movement",
        optics=OpticsProfile(
            camera="SONY_VENICE",
            film_stock="KODAK_PORTRA_400",
            lighting="BOUNCED_SOFT",
            motion="STEADICAM_SMOOTH",
        ),
        style_prefix="",  # Director inject replaces this
        trigger_keywords=frozenset([
            "beach", "ocean", "sand", "walking", "dancing", "singing",
            "casual", "relaxed", "natural", "sunset", "golden hour",
            "waves", "shore", "seaside", "coastal", "summer",
        ]),
        cfg_scale=7.5,
        steps=30,
        recommended_checkpoint="STANDARD_CINEMATIC",
    ),
}

# Alias for backward compatibility
STYLE_DEFINITIONS = _BASE_DEFINITIONS


# ═══════════════════════════════════════════════════════════════════════════════
# PURE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def detect_style(prompt: str) -> Optional[str]:
    """
    Auto-detect style from prompt keywords.

    PURE FUNCTION: Examines prompt for trigger keywords and returns
    matching style name, or None if no clear match.

    Args:
        prompt: Subject/prompt text to analyze

    Returns:
        Style name (e.g., STYLE_HIGH_VELOCITY_ACTION) or None

    Example:
        >>> detect_style("man running through explosion")
        'STYLE_HIGH_VELOCITY_ACTION'
        >>> detect_style("random scene with no keywords")
        None
    """
    keywords = set(extract_subject_keywords(prompt))

    best_match: Optional[str] = None
    best_score = 0

    for style_name, definition in STYLE_DEFINITIONS.items():
        # Count matching keywords
        matches = keywords & definition.trigger_keywords
        score = len(matches)

        if score > best_score:
            best_score = score
            best_match = style_name

    # Require at least 1 match to return a style
    return best_match if best_score >= 1 else None


def get_style_optics(style_name: str) -> Optional[OpticsProfile]:
    """
    Get optics profile for a style.

    PURE FUNCTION: Returns the curated optics profile for the given style.

    Args:
        style_name: Style constant (e.g., STYLE_HIGH_VELOCITY_ACTION)

    Returns:
        OpticsProfile or None if style not found
    """
    definition = STYLE_DEFINITIONS.get(style_name)
    return definition.optics if definition else None


def get_style_definition(style_name: str) -> Optional[StyleDefinition]:
    """
    Get full style definition.

    Args:
        style_name: Style constant

    Returns:
        StyleDefinition or None if not found
    """
    return STYLE_DEFINITIONS.get(style_name)


def get_style_prefix(style_name: str) -> str:
    """
    Get style prefix for prompt composition.

    NOTE: For YAML-driven styles, this returns empty string.
    Use get_director_inject() instead for the style triggers.

    Args:
        style_name: Style constant

    Returns:
        Style prefix string or empty string
    """
    definition = STYLE_DEFINITIONS.get(style_name)
    return definition.style_prefix if definition else ""


def get_style_generation_config(style_name: str) -> Dict[str, Any]:
    """
    Get generation config for a style.

    Args:
        style_name: Style constant

    Returns:
        Dict with cfg_scale, steps, recommended_checkpoint
    """
    definition = STYLE_DEFINITIONS.get(style_name)
    if not definition:
        return {}

    return {
        "cfg_scale": definition.cfg_scale,
        "steps": definition.steps,
        "recommended_checkpoint": definition.recommended_checkpoint,
    }


def compose_with_style(
    subject: str,
    style_name: str,
    camera_tokens: str = "",
    film_tokens: str = "",
    lighting_tokens: str = "",
    motion_tokens: str = "",
) -> ComposedPrompt:
    """
    Compose prompt using style's optics profile.

    PURE FUNCTION: Combines subject with style's curated optics.
    Explicit token parameters override style defaults.

    Args:
        subject: Main subject description
        style_name: Style constant
        camera_tokens: Override camera (empty = use style default)
        film_tokens: Override film stock (empty = use style default)
        lighting_tokens: Override lighting (empty = use style default)
        motion_tokens: Override motion (empty = use style default)

    Returns:
        ComposedPrompt with style-appropriate optics

    Example:
        >>> result = compose_with_style(
        ...     subject="man in leather jacket",
        ...     style_name=STYLE_HIGH_VELOCITY_ACTION
        ... )
        >>> "Bolex H16" in result.full_prompt or "16mm" in result.full_prompt
        True
    """
    definition = STYLE_DEFINITIONS.get(style_name)

    if not definition:
        # Fallback: compose without style
        return compose_prompt(
            subject=subject,
            camera_tokens=camera_tokens,
            film_tokens=film_tokens,
            lighting_tokens=lighting_tokens,
            motion_tokens=motion_tokens,
        )

    # Get director inject from YAML
    director_inject = get_director_inject(style_name)

    # Use provided tokens or fall back to style defaults
    # Note: We need actual token strings here, not preset names
    # The engine will resolve preset names to tokens
    return compose_prompt(
        subject=subject,
        style_prefix=definition.style_prefix,
        director_inject=director_inject,
        camera_tokens=camera_tokens,
        film_tokens=film_tokens,
        lighting_tokens=lighting_tokens,
        motion_tokens=motion_tokens,
    )


def list_styles() -> List[str]:
    """List all available style names."""
    return list(STYLE_DEFINITIONS.keys())


def get_style_info(style_name: str) -> Optional[Dict[str, Any]]:
    """
    Get human-readable style info for display.

    Args:
        style_name: Style constant

    Returns:
        Dict with display_name, description, trigger_keywords, optics
    """
    definition = STYLE_DEFINITIONS.get(style_name)
    if not definition:
        return None

    return {
        "name": definition.name,
        "display_name": definition.display_name,
        "description": definition.description,
        "trigger_keywords": list(definition.trigger_keywords)[:10],  # Top 10
        "director_inject": get_director_inject(style_name),  # From YAML
        "optics": {
            "camera": definition.optics.camera,
            "film_stock": definition.optics.film_stock,
            "lighting": definition.optics.lighting,
            "motion": definition.optics.motion,
        },
        "generation": {
            "cfg_scale": definition.cfg_scale,
            "steps": definition.steps,
        },
    }
