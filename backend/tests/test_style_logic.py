"""
Unit tests for style_logic.py - Style detection and composition.

Tests the three style abstractions:
- STYLE_HIGH_VELOCITY_ACTION
- STYLE_URBAN_LUXURY
- STYLE_PHYSICAL_DRAMA
"""

import pytest

from src.cinematography.style_logic import (
    STYLE_HIGH_VELOCITY_ACTION,
    STYLE_URBAN_LUXURY,
    STYLE_PHYSICAL_DRAMA,
    ALL_STYLES,
    STYLE_DEFINITIONS,
    detect_style,
    get_style_optics,
    get_style_prefix,
    get_director_inject,
    get_style_generation_config,
    get_style_definition,
    compose_with_style,
    list_styles,
    get_style_info,
)
from src.cinematography.prompt_composer import OpticsProfile


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Style Constants
# ═══════════════════════════════════════════════════════════════════════════════


class TestStyleConstants:
    """Verify style constants are properly defined."""

    def test_all_styles_list(self):
        """ALL_STYLES contains all three styles."""
        assert STYLE_HIGH_VELOCITY_ACTION in ALL_STYLES
        assert STYLE_URBAN_LUXURY in ALL_STYLES
        assert STYLE_PHYSICAL_DRAMA in ALL_STYLES
        assert len(ALL_STYLES) == 3

    def test_style_definitions_exist(self):
        """Each style has a definition."""
        for style in ALL_STYLES:
            assert style in STYLE_DEFINITIONS
            assert STYLE_DEFINITIONS[style] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: detect_style - Action keywords
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectsActionStyle:
    """Tests for detecting STYLE_HIGH_VELOCITY_ACTION."""

    @pytest.mark.parametrize("prompt", [
        "man running through explosion",
        "fighter throwing a punch",
        "car chase through city streets",
        "combat scene in warehouse",
        "athlete in full sprint action shot",
        "martial arts kick mid-air",
    ])
    def test_action_keywords_trigger(self, prompt):
        """Action keywords trigger STYLE_HIGH_VELOCITY_ACTION."""
        result = detect_style(prompt)

        assert result == STYLE_HIGH_VELOCITY_ACTION, f"Expected action style for: {prompt}"

    def test_multiple_action_keywords(self):
        """Multiple action keywords still detect correctly."""
        result = detect_style("explosion during chase with combat")

        assert result == STYLE_HIGH_VELOCITY_ACTION


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: detect_style - Luxury keywords
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectsLuxuryStyle:
    """Tests for detecting STYLE_URBAN_LUXURY."""

    @pytest.mark.parametrize("prompt", [
        "luxury penthouse at night",
        "fashion model on runway",
        "elegant woman in city nightclub",
        "sophisticated man with champagne",
        "glamorous rooftop party scene",
        "designer dress in urban setting",
    ])
    def test_luxury_keywords_trigger(self, prompt):
        """Luxury keywords trigger STYLE_URBAN_LUXURY."""
        result = detect_style(prompt)

        assert result == STYLE_URBAN_LUXURY, f"Expected luxury style for: {prompt}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: detect_style - Drama keywords
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectsDramaStyle:
    """Tests for detecting STYLE_PHYSICAL_DRAMA."""

    @pytest.mark.parametrize("prompt", [
        "emotional portrait of woman crying",
        "intimate embrace between lovers",
        "dramatic confession scene",
        "tender moment of reunion",
        "vulnerable close-up portrait",
        "quiet contemplation by window",
    ])
    def test_drama_keywords_trigger(self, prompt):
        """Drama keywords trigger STYLE_PHYSICAL_DRAMA."""
        result = detect_style(prompt)

        assert result == STYLE_PHYSICAL_DRAMA, f"Expected drama style for: {prompt}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: detect_style - No match
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectStyleNoMatch:
    """Tests for prompts with no clear style match."""

    @pytest.mark.parametrize("prompt", [
        "random scene with trees",
        "the quick brown fox",
        "generic landscape view",
        "abstract pattern",
    ])
    def test_no_keywords_returns_none(self, prompt):
        """Prompts without trigger keywords return None."""
        result = detect_style(prompt)

        assert result is None, f"Expected None for: {prompt}"

    def test_empty_prompt(self):
        """Empty prompt returns None."""
        result = detect_style("")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_style_optics - Correct optics applied
# ═══════════════════════════════════════════════════════════════════════════════


class TestStyleOpticsApplied:
    """Tests that styles apply correct optics profiles."""

    def test_action_style_optics(self):
        """STYLE_HIGH_VELOCITY_ACTION uses Bolex H16 + Cinestill 800T."""
        optics = get_style_optics(STYLE_HIGH_VELOCITY_ACTION)

        assert optics is not None
        assert optics.camera == "BOLEX_H16"
        assert optics.film_stock == "CINESTILL_800T"
        assert optics.lighting == "HARD_LIGHT"
        assert optics.motion == "HANDHELD_AGGRESSIVE"

    def test_luxury_style_optics(self):
        """STYLE_URBAN_LUXURY uses ARRI ALEXA 65 + Kodak Vision3 + Neon Noir."""
        optics = get_style_optics(STYLE_URBAN_LUXURY)

        assert optics is not None
        assert optics.camera == "ARRI_ALEXA_65"
        assert optics.film_stock == "KODAK_VISION3_500T"
        assert optics.lighting == "NEON_NOIR"  # Updated to match YAML
        assert optics.motion == "STEADICAM_SMOOTH"

    def test_drama_style_optics(self):
        """STYLE_PHYSICAL_DRAMA uses RED + Kodak Portra 160."""
        optics = get_style_optics(STYLE_PHYSICAL_DRAMA)

        assert optics is not None
        assert optics.camera == "RED_DIGITAL_CINEMA"
        assert optics.film_stock == "KODAK_PORTRA_160"
        assert optics.lighting == "BOUNCED_SOFT"
        assert optics.motion == "STATIC_LOCKED"

    def test_invalid_style_returns_none(self):
        """Invalid style name returns None."""
        optics = get_style_optics("INVALID_STYLE")

        assert optics is None

    def test_optics_is_frozen_profile(self):
        """Returned optics is a frozen OpticsProfile."""
        optics = get_style_optics(STYLE_HIGH_VELOCITY_ACTION)

        assert isinstance(optics, OpticsProfile)
        with pytest.raises(AttributeError):
            optics.camera = "different"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_director_inject (replaces style_prefix for YAML-driven styles)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetDirectorInject:
    """Tests for director_inject retrieval from YAML."""

    def test_action_style_director_inject(self):
        """Action style has director inject from YAML additional_triggers."""
        inject = get_director_inject(STYLE_HIGH_VELOCITY_ACTION)

        # Should contain raw street/action keywords from YAML
        assert "street beef" in inject.lower() or "gunfight" in inject.lower()

    def test_luxury_style_director_inject(self):
        """Luxury style has director inject from YAML additional_triggers."""
        inject = get_director_inject(STYLE_URBAN_LUXURY)

        # Should contain jewelry/luxury keywords from YAML
        assert "jewelry" in inject.lower() or "diamond" in inject.lower()

    def test_drama_style_director_inject(self):
        """Drama style has director inject from YAML prompt_tokens."""
        inject = get_director_inject(STYLE_PHYSICAL_DRAMA)

        # Should contain score_9 and explicit keywords from YAML
        assert "score_9" in inject.lower() or "score_8" in inject.lower()

    def test_invalid_style_empty_string(self):
        """Invalid style returns empty string."""
        inject = get_director_inject("INVALID_STYLE")

        assert inject == ""


class TestGetStylePrefix:
    """Tests for legacy style_prefix (now empty for YAML-driven styles)."""

    def test_style_prefix_is_empty_for_yaml_styles(self):
        """YAML-driven styles have empty style_prefix (use director_inject instead)."""
        for style in ALL_STYLES:
            prefix = get_style_prefix(style)
            # Style prefix is now empty - director_inject replaces it
            assert prefix == "", f"Style {style} should have empty style_prefix"

    def test_invalid_style_empty_string(self):
        """Invalid style returns empty string."""
        prefix = get_style_prefix("INVALID_STYLE")

        assert prefix == ""


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_style_generation_config
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetStyleGenerationConfig:
    """Tests for generation config retrieval."""

    def test_action_style_config(self):
        """Action style has higher cfg_scale for adherence."""
        config = get_style_generation_config(STYLE_HIGH_VELOCITY_ACTION)

        assert "cfg_scale" in config
        assert config["cfg_scale"] >= 7.0  # Should be higher for action
        assert "steps" in config
        assert "recommended_checkpoint" in config

    def test_drama_style_config(self):
        """Drama style has more steps for detail."""
        config = get_style_generation_config(STYLE_PHYSICAL_DRAMA)

        assert config["steps"] >= 30  # More steps for emotional detail

    def test_invalid_style_empty_dict(self):
        """Invalid style returns empty dict."""
        config = get_style_generation_config("INVALID_STYLE")

        assert config == {}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_with_style
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposeWithStyle:
    """Tests for style-based prompt composition."""

    def test_compose_with_action_style(self):
        """Composing with action style includes director_inject from YAML."""
        result = compose_with_style(
            subject="man in leather jacket",
            style_name=STYLE_HIGH_VELOCITY_ACTION,
        )

        assert "man in leather jacket" in result.full_prompt
        # Director inject should be present (from YAML additional_triggers)
        assert result.director_inject != ""
        # Director inject should come FIRST in the prompt
        assert result.full_prompt.startswith(result.director_inject[:20])

    def test_compose_with_invalid_style(self):
        """Invalid style falls back to basic composition."""
        result = compose_with_style(
            subject="test subject",
            style_name="INVALID_STYLE",
        )

        # Should still produce a valid prompt
        assert "test subject" in result.full_prompt
        assert result.director_inject == ""

    def test_explicit_tokens_override_style(self):
        """Explicit token params override style defaults."""
        result = compose_with_style(
            subject="person",
            style_name=STYLE_HIGH_VELOCITY_ACTION,
            camera_tokens="shot on RED camera",  # Override Bolex
        )

        assert "shot on RED camera" in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: list_styles
# ═══════════════════════════════════════════════════════════════════════════════


class TestListStyles:
    """Tests for style listing."""

    def test_list_styles_returns_all(self):
        """list_styles returns all style names."""
        styles = list_styles()

        assert STYLE_HIGH_VELOCITY_ACTION in styles
        assert STYLE_URBAN_LUXURY in styles
        assert STYLE_PHYSICAL_DRAMA in styles
        assert len(styles) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_style_info
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetStyleInfo:
    """Tests for style info retrieval."""

    def test_returns_complete_info(self):
        """get_style_info returns all expected fields."""
        info = get_style_info(STYLE_HIGH_VELOCITY_ACTION)

        assert info is not None
        assert "name" in info
        assert "display_name" in info
        assert "description" in info
        assert "trigger_keywords" in info
        assert "optics" in info
        assert "generation" in info

    def test_optics_info_structure(self):
        """Optics info has camera, film, lighting, motion."""
        info = get_style_info(STYLE_URBAN_LUXURY)

        optics = info["optics"]
        assert "camera" in optics
        assert "film_stock" in optics
        assert "lighting" in optics
        assert "motion" in optics

    def test_invalid_style_returns_none(self):
        """Invalid style returns None."""
        info = get_style_info("INVALID_STYLE")

        assert info is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Style Definition Completeness
# ═══════════════════════════════════════════════════════════════════════════════


class TestStyleDefinitionCompleteness:
    """Verify all style definitions are complete."""

    @pytest.mark.parametrize("style_name", ALL_STYLES)
    def test_style_has_all_required_fields(self, style_name):
        """Each style definition has all required fields."""
        definition = get_style_definition(style_name)

        assert definition is not None
        assert definition.name == style_name
        assert definition.display_name != ""
        assert definition.description != ""
        assert definition.optics is not None
        # style_prefix is now empty - director_inject from YAML replaces it
        director_inject = get_director_inject(style_name)
        assert director_inject != "", f"Style {style_name} must have director_inject in YAML"
        assert len(definition.trigger_keywords) > 0
        assert definition.cfg_scale > 0
        assert definition.steps > 0
        assert definition.recommended_checkpoint != ""

    @pytest.mark.parametrize("style_name", ALL_STYLES)
    def test_style_optics_complete(self, style_name):
        """Each style's optics profile has all components."""
        optics = get_style_optics(style_name)

        assert optics.camera is not None
        assert optics.film_stock is not None
        assert optics.lighting is not None
        assert optics.motion is not None
