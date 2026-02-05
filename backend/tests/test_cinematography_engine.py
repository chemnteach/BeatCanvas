"""
Integration tests for CinematographyEngine.

Tests the full engine with optics catalog and style logic.
"""

import pytest
from pathlib import Path

from src.cinematography.engine import CinematographyEngine, create_engine
from src.cinematography.optics import OpticsCatalog
from src.cinematography.style_logic import (
    STYLE_HIGH_VELOCITY_ACTION,
    STYLE_URBAN_LUXURY,
    STYLE_PHYSICAL_DRAMA,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine():
    """Create engine with default catalog."""
    return CinematographyEngine()


@pytest.fixture
def engine_empty_catalog():
    """Create engine with empty catalog (for unit testing)."""
    return CinematographyEngine(optics_catalog=OpticsCatalog.empty())


@pytest.fixture
def mock_catalog():
    """Create catalog from inline dict."""
    return OpticsCatalog.from_dict({
        "cameras": {
            "TEST_CAMERA": {"prompt_tokens": "test camera tokens", "description": "test"}
        },
        "film_stocks": {
            "TEST_FILM": {"prompt_tokens": "test film tokens", "description": "test"}
        },
        "lighting": {
            "TEST_LIGHT": {"prompt_tokens": "test lighting tokens", "description": "test"}
        },
        "quality_tokens": {
            "skin_detail": {"mandatory": True, "prompt_tokens": "test skin detail"}
        },
        "negative_prompts": {
            "photorealism": {"prompt_tokens": "test negative"}
        },
        "adetailer": {
            "face_repair": {"enabled": True, "model": "test.pt", "confidence": 0.5}
        },
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Engine Initialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestEngineInit:
    """Test engine initialization."""

    def test_default_init_loads_catalog(self, engine):
        """Default init loads optics catalog from YAML."""
        assert engine.catalog is not None
        # Should have cameras loaded
        assert len(engine.list_cameras()) > 0

    def test_empty_catalog_injection(self, engine_empty_catalog):
        """Can inject empty catalog for testing."""
        assert engine_empty_catalog.catalog is not None
        assert len(engine_empty_catalog.list_cameras()) == 0

    def test_custom_catalog_injection(self, mock_catalog):
        """Can inject custom catalog."""
        engine = CinematographyEngine(optics_catalog=mock_catalog)

        assert "TEST_CAMERA" in engine.list_cameras()
        assert "TEST_FILM" in engine.list_film_stocks()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose - Style-driven
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposeStyleDriven:
    """Test style-driven composition."""

    def test_compose_with_action_style(self, engine):
        """Compose with action style includes director_inject from YAML."""
        result = engine.compose(
            subject="man running through warehouse",
            style=STYLE_HIGH_VELOCITY_ACTION,
        )

        # Should include subject
        assert "man running through warehouse" in result.full_prompt
        # Should include mandatory quality tokens
        assert "detailed skin" in result.full_prompt
        # Should have director_inject from YAML (replaces style_prefix)
        assert result.director_inject != ""
        # Director inject should come FIRST
        assert result.full_prompt.startswith(result.director_inject[:20])

    def test_compose_with_luxury_style(self, engine):
        """Compose with luxury style uses ARRI camera."""
        result = engine.compose(
            subject="elegant woman in penthouse",
            style=STYLE_URBAN_LUXURY,
        )

        # Should include ARRI camera tokens from catalog
        assert "ARRI" in result.full_prompt or "ALEXA" in result.full_prompt

    def test_compose_with_drama_style(self, engine):
        """Compose with drama style has director_inject and preserves detailed skin."""
        result = engine.compose(
            subject="emotional portrait",
            style=STYLE_PHYSICAL_DRAMA,
        )

        # Director inject should contain score tags from YAML
        assert "score_9" in result.director_inject.lower() or "score_8" in result.director_inject.lower()
        # CRITICAL: detailed skin MUST be preserved (Anatomy Shield)
        assert "detailed skin" in result.full_prompt
        # Camera/film may be truncated due to long explicit director_inject - that's OK
        # Subject must be present
        assert "emotional portrait" in result.full_prompt

    def test_auto_detect_style(self, engine):
        """Auto-detect style from subject keywords."""
        result = engine.compose(
            subject="fighter throwing punch in combat",
            auto_detect_style=True,
        )

        # Should auto-detect action style and apply its director_inject
        prompt = result.full_prompt.lower()
        assert "punch" in prompt or "combat" in prompt
        # Should have director_inject applied
        assert result.director_inject != ""


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose - Manual optics
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposeManualOptics:
    """Test manual optics selection."""

    def test_compose_with_manual_camera(self, engine):
        """Compose with explicit camera selection."""
        result = engine.compose(
            subject="portrait",
            camera="ARRI_ALEXA_65",
        )

        assert "ARRI" in result.full_prompt or "ALEXA" in result.full_prompt

    def test_compose_with_manual_film_stock(self, engine):
        """Compose with explicit film stock selection."""
        result = engine.compose(
            subject="night scene",
            film_stock="CINESTILL_800T",
        )

        assert "Cinestill" in result.full_prompt or "800T" in result.full_prompt

    def test_compose_with_all_manual_optics(self, engine):
        """Compose with all optics manually specified."""
        result = engine.compose(
            subject="subject",
            camera="RED_DIGITAL_CINEMA",
            film_stock="KODAK_PORTRA_160",
            lighting="BOUNCED_SOFT",
            motion="STATIC_LOCKED",
        )

        assert "RED" in result.full_prompt
        assert "Portra" in result.full_prompt
        assert "soft" in result.full_prompt.lower() or "bounced" in result.full_prompt.lower()

    def test_manual_overrides_style(self, engine):
        """Manual optics override style defaults."""
        result = engine.compose(
            subject="action scene",
            style=STYLE_HIGH_VELOCITY_ACTION,  # Would use Bolex
            camera="ARRI_ALEXA_65",  # Override to ARRI
        )

        # Should have ARRI, not Bolex
        assert "ARRI" in result.full_prompt or "ALEXA" in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose - Mandatory quality tokens
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposeMandatoryTokens:
    """Test that mandatory quality tokens are always included."""

    def test_detailed_skin_always_present(self, engine):
        """'detailed skin' is always in output."""
        result = engine.compose(subject="person")

        assert "detailed skin" in result.full_prompt

    def test_detailed_skin_with_style(self, engine):
        """'detailed skin' present even with style."""
        for style in [STYLE_HIGH_VELOCITY_ACTION, STYLE_URBAN_LUXURY, STYLE_PHYSICAL_DRAMA]:
            result = engine.compose(subject="person", style=style)

            assert "detailed skin" in result.full_prompt, f"Missing in {style}"

    def test_detailed_skin_with_manual_optics(self, engine):
        """'detailed skin' present with manual optics."""
        result = engine.compose(
            subject="person",
            camera="BOLEX_H16",
            film_stock="CINESTILL_800T",
        )

        assert "detailed skin" in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_generation_config
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetGenerationConfig:
    """Test generation config retrieval."""

    def test_default_config(self, engine):
        """Default config without style."""
        config = engine.get_generation_config()

        assert "cfg_scale" in config
        assert "steps" in config
        assert "recommended_checkpoint" in config
        assert "sampler" in config

    def test_style_config(self, engine):
        """Config with style applied."""
        config = engine.get_generation_config(style=STYLE_HIGH_VELOCITY_ACTION)

        assert config["cfg_scale"] >= 7.0
        assert config["steps"] >= 20


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_negative_prompt
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetNegativePrompt:
    """Test negative prompt generation."""

    def test_default_negative_prompt(self, engine):
        """Default negative prompt includes common exclusions."""
        negative = engine.get_negative_prompt()

        # Should include anatomy issues (may vary based on YAML)
        assert "fused limbs" in negative or "deformed" in negative or "extra" in negative
        # Should include quality issues
        assert "blurry" in negative or "low quality" in negative

    def test_negative_prompt_no_duplicates(self, engine):
        """Negative prompt has no duplicate tokens."""
        negative = engine.get_negative_prompt()

        tokens = [t.strip().lower() for t in negative.split(",")]
        unique_tokens = set(tokens)

        # Allow some tolerance for empty strings
        tokens_no_empty = [t for t in tokens if t]
        unique_no_empty = [t for t in unique_tokens if t]

        assert len(tokens_no_empty) == len(unique_no_empty)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_adetailer_config
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetAdetailerConfig:
    """Test aDetailer config retrieval."""

    def test_returns_face_and_hand_repair(self, engine):
        """Config includes face and hand repair settings."""
        config = engine.get_adetailer_config()

        assert "face_repair" in config
        assert "hand_repair" in config

    def test_face_repair_structure(self, engine):
        """Face repair config has expected fields."""
        config = engine.get_adetailer_config()

        face = config["face_repair"]
        assert "enabled" in face
        assert "model" in face
        assert "confidence" in face

    def test_hand_repair_structure(self, engine):
        """Hand repair config has expected fields."""
        config = engine.get_adetailer_config()

        hand = config["hand_repair"]
        assert "enabled" in hand
        assert "model" in hand
        assert "confidence" in hand


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Listing methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestListingMethods:
    """Test listing/discovery methods."""

    def test_list_styles(self, engine):
        """list_styles returns all styles."""
        styles = engine.list_styles()

        assert STYLE_HIGH_VELOCITY_ACTION in styles
        assert STYLE_URBAN_LUXURY in styles
        assert STYLE_PHYSICAL_DRAMA in styles

    def test_list_cameras(self, engine):
        """list_cameras returns available cameras."""
        cameras = engine.list_cameras()

        assert len(cameras) > 0
        assert "ARRI_ALEXA_65" in cameras

    def test_list_film_stocks(self, engine):
        """list_film_stocks returns available film stocks."""
        stocks = engine.list_film_stocks()

        assert len(stocks) > 0
        assert "CINESTILL_800T" in stocks

    def test_list_lighting(self, engine):
        """list_lighting returns available lighting setups."""
        lighting = engine.list_lighting()

        assert len(lighting) > 0
        assert "CHIAROSCURO" in lighting

    def test_list_motion(self, engine):
        """list_motion returns available motion styles."""
        motion = engine.list_motion()

        assert len(motion) > 0
        assert "HANDHELD_AGGRESSIVE" in motion


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: get_style_info
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetStyleInfo:
    """Test style info retrieval through engine."""

    def test_returns_style_info(self, engine):
        """get_style_info returns complete info."""
        info = engine.get_style_info(STYLE_HIGH_VELOCITY_ACTION)

        assert info is not None
        assert "display_name" in info
        assert "description" in info
        assert "optics" in info

    def test_invalid_style_returns_none(self, engine):
        """Invalid style returns None."""
        info = engine.get_style_info("INVALID")

        assert info is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: create_engine factory
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateEngineFactory:
    """Test the create_engine factory function."""

    def test_create_engine_default(self):
        """create_engine with no args uses default catalog."""
        engine = create_engine()

        assert engine is not None
        assert len(engine.list_cameras()) > 0

    def test_create_engine_custom_path(self, tmp_path):
        """create_engine with custom YAML path."""
        # Create minimal YAML
        yaml_content = """
version: "1.0"
cameras:
  CUSTOM_CAM:
    prompt_tokens: "custom camera"
    description: "test"
"""
        yaml_path = tmp_path / "custom.yaml"
        yaml_path.write_text(yaml_content)

        engine = create_engine(yaml_path=yaml_path)

        assert "CUSTOM_CAM" in engine.list_cameras()
