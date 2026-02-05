"""
Prompt Composer - Pure functions for cinematography prompt construction.

ALL FUNCTIONS ARE PURE: No side effects, same input = same output.
This module is 100% unit testable without mocks.

CLIP-OPTIMIZED Template Order (STYLE TRIGGERS FIRST for max impact):
    [DIRECTOR_INJECT] + [SUBJECT] + [QUALITY] + [CAMERA] + [FILM]

NOTE: CLIP tokenizer has 77-token limit. Tokens beyond ~75 get truncated.
Priority order ensures style triggers always make it into the prompt.
"""

from dataclasses import dataclass
from typing import Optional, List


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# CLIP token limit (conservative to avoid truncation)
CLIP_TOKEN_LIMIT = 75

# MANDATORY quality tokens - always included for human subjects
MANDATORY_QUALITY_TOKENS = "detailed skin, realistic skin texture"

# ACTION FRAMING tokens - prevents limbs from moving out of frame during video
# Used for high-velocity action styles to give SVD tracking headroom
ACTION_FRAMING_TOKENS = "wide medium shot, fists contained within frame, generous lead room"

# Styles that require action framing to prevent edge tracking failure
ACTION_STYLE_NAMES = frozenset([
    "STYLE_HIGH_VELOCITY_ACTION",
    "HIGH_VELOCITY_ACTION",
    "action",
    "combat",
    "fight",
])


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - Immutable value objects
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class OpticsProfile:
    """
    Immutable optics configuration for a scene.

    All fields are optional - compose_prompt handles missing values gracefully.
    """

    camera: Optional[str] = None
    film_stock: Optional[str] = None
    lighting: Optional[str] = None
    motion: Optional[str] = None


@dataclass(frozen=True)
class ComposedPrompt:
    """
    Immutable result of prompt composition.

    Contains the full prompt plus individual components for debugging/logging.
    """

    full_prompt: str
    subject: str
    style_prefix: str
    director_inject: str
    camera_tokens: str
    film_tokens: str
    lighting_tokens: str
    motion_tokens: str
    quality_tokens: str
    estimated_tokens: int

    def __str__(self) -> str:
        return self.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# PURE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def inject_action_framing(subject: str, style_name: str = "") -> str:
    """
    Inject wide-shot framing tokens for action styles.

    PURE FUNCTION: Prepends framing tokens to prevent limb edge-tracking failure.
    When arms/fists move near frame boundaries, SVD loses tracking and causes
    distortion. Wide framing ensures motion stays contained.

    Args:
        subject: Original subject description
        style_name: Style name (e.g., "STYLE_HIGH_VELOCITY_ACTION")

    Returns:
        Subject with framing tokens prepended if action style, else unchanged
    """
    # Normalize style name for matching
    style_lower = style_name.lower().replace("_", " ") if style_name else ""

    # Check if this is an action style requiring framing
    needs_framing = (
        style_name in ACTION_STYLE_NAMES
        or any(keyword in style_lower for keyword in ["action", "combat", "fight", "velocity"])
    )

    if needs_framing:
        return f"{ACTION_FRAMING_TOKENS}, {subject}"
    return subject


def estimate_tokens(text: str) -> int:
    """
    Estimate CLIP token count for a prompt string.

    PURE FUNCTION: Rough estimation based on word/punctuation count.
    CLIP tokenizer typically produces ~1.3 tokens per word.

    Args:
        text: Prompt string

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Split on spaces and common separators
    words = text.replace(",", " ").replace("(", " ").replace(")", " ").split()
    # Rough estimate: ~1.3 tokens per word, plus punctuation
    return int(len(words) * 1.3) + text.count("(") + text.count(")")


def truncate_to_token_limit(
    parts: List[str],
    limit: int = CLIP_TOKEN_LIMIT,
) -> List[str]:
    """
    Truncate prompt parts to fit within CLIP token limit.

    PURE FUNCTION: Preserves early parts (highest priority).
    Parts are processed in order; later parts may be dropped.

    Args:
        parts: List of prompt components in priority order
        limit: Maximum token estimate (default: 75)

    Returns:
        Truncated list of parts that fit within limit
    """
    result = []
    current_tokens = 0

    for part in parts:
        part_tokens = estimate_tokens(part)
        if current_tokens + part_tokens <= limit:
            result.append(part)
            current_tokens += part_tokens
        else:
            # Try to fit a truncated version
            remaining = limit - current_tokens
            if remaining > 5:  # Only if meaningful space left
                # Truncate by words
                words = part.split()
                truncated = []
                for word in words:
                    if estimate_tokens(" ".join(truncated + [word])) <= remaining:
                        truncated.append(word)
                    else:
                        break
                if truncated:
                    result.append(" ".join(truncated))
            break  # No more room

    return result


def compose_prompt(
    subject: str,
    style_prefix: str = "",
    director_inject: str = "",
    camera_tokens: str = "",
    film_tokens: str = "",
    lighting_tokens: str = "",
    motion_tokens: str = "",
    quality_tokens: str = MANDATORY_QUALITY_TOKENS,
    include_photo_of: bool = True,
    max_tokens: int = CLIP_TOKEN_LIMIT,
) -> ComposedPrompt:
    """
    Compose a cinematography prompt from components.

    PURE FUNCTION: Same inputs always produce same output.

    ANATOMY SHIELD Template order (quality_tokens protected):
        [DIRECTOR_INJECT] + [QUALITY_TOKENS] + [SUBJECT] + [CAMERA] + [FILM] + [LIGHTING] + [MOTION]

    CRITICAL: quality_tokens ("detailed skin") comes IMMEDIATELY after director_inject
    to ensure it's NEVER truncated, even with long explicit content.

    Truncation happens from the RIGHT (end), so optics tokens may be lost
    but anatomy shield and subject are always preserved.

    Args:
        subject: Main subject description (e.g., "woman walking through rain")
        style_prefix: Style descriptor (e.g., "cinematic", "dramatic")
        director_inject: HIGH PRIORITY style triggers from YAML (comes FIRST)
        camera_tokens: Camera/sensor tokens (e.g., "shot on ARRI ALEXA 65")
        film_tokens: Film stock tokens (e.g., "Kodak Portra 160")
        lighting_tokens: Lighting tokens (e.g., "dramatic rim lighting")
        motion_tokens: Camera motion tokens (e.g., "handheld camera movement")
        quality_tokens: Quality tokens (default: mandatory skin detail) - PROTECTED
        include_photo_of: Whether to include "photo of" in template
        max_tokens: Maximum token estimate (default: 75 for CLIP safety)

    Returns:
        ComposedPrompt with full_prompt and all components

    Example:
        >>> result = compose_prompt(
        ...     subject="man in leather jacket",
        ...     director_inject="score_9, raw street beef",
        ...     camera_tokens="shot on ARRI ALEXA 65",
        ... )
        >>> "detailed skin" in result.full_prompt  # Always preserved
        True
    """
    # Build parts list in PRIORITY ORDER
    # ANATOMY SHIELD: quality_tokens comes IMMEDIATELY after director_inject
    parts: List[str] = []

    # [1] DIRECTOR_INJECT - HIGHEST PRIORITY (score tags, style triggers)
    if director_inject:
        parts.append(director_inject)

    # [2] QUALITY_TOKENS - ANATOMY SHIELD (must never be truncated)
    if quality_tokens:
        parts.append(quality_tokens)

    # [3] SUBJECT with optional style prefix
    if style_prefix:
        if include_photo_of:
            parts.append(f"{style_prefix} photo of {subject}")
        else:
            parts.append(f"{style_prefix} {subject}")
    else:
        if include_photo_of:
            parts.append(f"photo of {subject}")
        else:
            parts.append(subject)

    # [4] CAMERA - Important for aesthetic (can be truncated if needed)
    if camera_tokens:
        parts.append(camera_tokens)

    # [5] FILM - Color science (can be truncated if needed)
    if film_tokens:
        parts.append(film_tokens)

    # [6] LIGHTING - Lower priority (often truncated)
    if lighting_tokens:
        parts.append(lighting_tokens)

    # [7] MOTION - Lowest priority (often truncated)
    if motion_tokens:
        parts.append(motion_tokens)

    # Truncate from RIGHT to fit CLIP limit (preserves high-priority tokens)
    truncated_parts = truncate_to_token_limit(parts, max_tokens)

    # Join with ", " separator
    full_prompt = ", ".join(truncated_parts)
    estimated = estimate_tokens(full_prompt)

    return ComposedPrompt(
        full_prompt=full_prompt,
        subject=subject,
        style_prefix=style_prefix,
        director_inject=director_inject,
        camera_tokens=camera_tokens,
        film_tokens=film_tokens,
        lighting_tokens=lighting_tokens,
        motion_tokens=motion_tokens,
        quality_tokens=quality_tokens,
        estimated_tokens=estimated,
    )


def merge_negative_prompts(*prompts: str) -> str:
    """
    Merge multiple negative prompt strings, removing duplicates.

    PURE FUNCTION: Deterministic output for same inputs.

    Args:
        *prompts: Variable number of negative prompt strings

    Returns:
        Single merged prompt string with duplicates removed

    Example:
        >>> merge_negative_prompts("blurry, low quality", "low quality, bad anatomy")
        'blurry, low quality, bad anatomy'
    """
    seen = set()
    result = []

    for prompt in prompts:
        if not prompt:
            continue
        # Split by comma, strip whitespace
        tokens = [t.strip() for t in prompt.split(",")]
        for token in tokens:
            if token and token.lower() not in seen:
                seen.add(token.lower())
                result.append(token)

    return ", ".join(result)


def build_adetailer_prompt(
    subject: str,
    detail_level: str = "medium",
) -> str:
    """
    Build aDetailer prompt for face/hand repair.

    PURE FUNCTION: Used for post-processing repair prompts.

    Args:
        subject: Subject description for context
        detail_level: "low", "medium", or "high"

    Returns:
        aDetailer-compatible prompt string
    """
    base = "detailed face, realistic eyes, natural skin texture"

    if detail_level == "high":
        return f"{base}, (sharp facial features:1.2), perfect skin pores"
    elif detail_level == "low":
        return base
    else:  # medium
        return f"{base}, natural lighting on face"


def extract_subject_keywords(subject: str) -> List[str]:
    """
    Extract keywords from subject for style matching.

    PURE FUNCTION: Used by style_logic.detect_style().

    Args:
        subject: Subject description string

    Returns:
        List of lowercase keywords
    """
    # Simple word tokenization
    words = subject.lower().replace(",", " ").replace(".", " ").split()
    # Filter very short words
    return [w for w in words if len(w) > 2]
