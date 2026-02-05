"""
Unit tests for prompt_composer.py - Pure function tests.

These tests verify the core prompt composition logic without any
external dependencies (no YAML, no network, no state).
"""

import pytest

from src.cinematography.prompt_composer import (
    OpticsProfile,
    ComposedPrompt,
    compose_prompt,
    merge_negative_prompts,
    build_adetailer_prompt,
    extract_subject_keywords,
    estimate_tokens,
    truncate_to_token_limit,
    MANDATORY_QUALITY_TOKENS,
    CLIP_TOKEN_LIMIT,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_prompt - Basic composition
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposePromptBasic:
    """Basic composition tests."""

    def test_subject_only(self):
        """Composing with just subject produces valid prompt."""
        result = compose_prompt(subject="a woman in red dress")

        assert result.subject == "a woman in red dress"
        assert "a woman in red dress" in result.full_prompt
        assert isinstance(result, ComposedPrompt)

    def test_returns_frozen_dataclass(self):
        """Result is an immutable dataclass."""
        result = compose_prompt(subject="test subject")

        assert isinstance(result, ComposedPrompt)
        with pytest.raises(AttributeError):
            result.subject = "modified"  # Should fail - frozen

    def test_str_returns_full_prompt(self):
        """__str__ returns the full prompt."""
        result = compose_prompt(subject="test subject")

        assert str(result) == result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_prompt - Template order
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposePromptTemplateOrder:
    """Verify tokens appear in correct order."""

    def test_template_order_all_components(self):
        """Full prompt follows ANATOMY SHIELD template: [DIRECTOR] + [QUALITY] + [SUBJECT] + [CAMERA] + [FILM] + [LIGHTING] + [MOTION]."""
        result = compose_prompt(
            subject="man in leather jacket",
            style_prefix="cinematic",
            director_inject="score_9, raw action",
            camera_tokens="shot on ARRI",
            film_tokens="Kodak Portra",
            lighting_tokens="rim lighting",
            motion_tokens="handheld",
            quality_tokens="detailed skin",
        )

        prompt = result.full_prompt

        # Find positions of each component
        director_pos = prompt.find("score_9")
        quality_pos = prompt.find("detailed skin")
        style_pos = prompt.find("cinematic photo of")
        subject_pos = prompt.find("man in leather jacket")
        camera_pos = prompt.find("shot on ARRI")
        film_pos = prompt.find("Kodak Portra")
        lighting_pos = prompt.find("rim lighting")
        motion_pos = prompt.find("handheld")

        # All should be present
        assert director_pos >= 0, "Director inject missing"
        assert quality_pos >= 0, "Quality tokens missing (ANATOMY SHIELD)"
        assert style_pos >= 0, "Style prefix missing"
        assert subject_pos >= 0, "Subject missing"
        assert camera_pos >= 0, "Camera tokens missing"
        assert film_pos >= 0, "Film tokens missing"
        assert lighting_pos >= 0, "Lighting tokens missing"
        assert motion_pos >= 0, "Motion tokens missing"

        # ANATOMY SHIELD order: director < quality < subject < camera < film < lighting < motion
        assert director_pos < quality_pos, "Director should come FIRST"
        assert quality_pos < style_pos, "Quality (ANATOMY SHIELD) should come before subject"
        assert style_pos < camera_pos, "Subject should come before camera"
        assert camera_pos < film_pos, "Camera should come before film"
        assert film_pos < lighting_pos, "Film should come before lighting"
        assert lighting_pos < motion_pos, "Lighting should come before motion"

    def test_photo_of_included_by_default(self):
        """'photo of' is included by default."""
        result = compose_prompt(subject="a sunset")

        assert "photo of" in result.full_prompt
        assert "photo of a sunset" in result.full_prompt

    def test_photo_of_can_be_disabled(self):
        """'photo of' can be excluded."""
        result = compose_prompt(subject="a sunset", include_photo_of=False)

        assert "photo of" not in result.full_prompt
        assert "a sunset" in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_prompt - Mandatory "detailed skin"
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetailedSkinMandatory:
    """CRITICAL: 'detailed skin' must always be included for photorealism."""

    def test_detailed_skin_in_default_quality_tokens(self):
        """Default quality_tokens includes 'detailed skin'."""
        assert "detailed skin" in MANDATORY_QUALITY_TOKENS

    def test_detailed_skin_included_by_default(self):
        """Composing without explicit quality_tokens includes 'detailed skin'."""
        result = compose_prompt(subject="person walking")

        assert "detailed skin" in result.full_prompt

    def test_detailed_skin_preserved_with_other_options(self):
        """'detailed skin' present even when other options specified."""
        result = compose_prompt(
            subject="person",
            camera_tokens="ARRI",
            lighting_tokens="soft light",
        )

        assert "detailed skin" in result.full_prompt

    def test_custom_quality_tokens_override(self):
        """Custom quality_tokens can override default (for non-human subjects)."""
        result = compose_prompt(
            subject="car in garage",
            quality_tokens="high detail, metallic surface",
        )

        # Should use custom tokens, not default
        assert "metallic surface" in result.full_prompt
        # Default NOT present when overridden
        assert "detailed skin" not in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_prompt - Deterministic output
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeterministicOutput:
    """Same input must always produce same output."""

    def test_same_input_same_output(self):
        """Identical inputs produce identical outputs."""
        inputs = {
            "subject": "woman in cafe",
            "style_prefix": "cinematic",
            "camera_tokens": "shot on ARRI",
            "film_tokens": "Portra 400",
        }

        result1 = compose_prompt(**inputs)
        result2 = compose_prompt(**inputs)

        assert result1.full_prompt == result2.full_prompt
        assert result1 == result2  # Dataclass equality

    def test_multiple_calls_consistent(self):
        """Multiple calls produce consistent results."""
        results = [
            compose_prompt(subject="test", camera_tokens="ARRI")
            for _ in range(10)
        ]

        first = results[0].full_prompt
        assert all(r.full_prompt == first for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: compose_prompt - Empty optional fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmptyOptionalFields:
    """Empty fields should not produce artifacts."""

    def test_no_double_commas(self):
        """Empty fields don't create ',,' in output."""
        result = compose_prompt(
            subject="test",
            camera_tokens="",
            film_tokens="",
        )

        assert ",," not in result.full_prompt
        assert ", ," not in result.full_prompt

    def test_no_trailing_comma(self):
        """Output doesn't end with comma."""
        result = compose_prompt(subject="test")

        assert not result.full_prompt.endswith(",")
        assert not result.full_prompt.endswith(", ")

    def test_no_leading_comma(self):
        """Output doesn't start with comma."""
        result = compose_prompt(subject="test", style_prefix="")

        assert not result.full_prompt.startswith(",")
        assert not result.full_prompt.startswith(" ,")

    def test_all_empty_except_subject(self):
        """Only subject provided produces clean output."""
        result = compose_prompt(
            subject="a dog",
            style_prefix="",
            camera_tokens="",
            film_tokens="",
            lighting_tokens="",
            motion_tokens="",
            quality_tokens="",
        )

        # Should just be "photo of a dog" (or similar clean output)
        assert result.full_prompt.strip() == "photo of a dog"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: merge_negative_prompts
# ═══════════════════════════════════════════════════════════════════════════════


class TestMergeNegativePrompts:
    """Tests for negative prompt merging."""

    def test_removes_duplicates(self):
        """Duplicate tokens are removed."""
        result = merge_negative_prompts(
            "blurry, low quality",
            "low quality, bad anatomy",
        )

        # Count occurrences of "low quality"
        count = result.lower().count("low quality")
        assert count == 1, f"'low quality' appears {count} times, expected 1"

    def test_case_insensitive_dedup(self):
        """Deduplication is case-insensitive."""
        result = merge_negative_prompts(
            "Blurry, LOW QUALITY",
            "low quality, blurry",
        )

        # Should have 2 unique tokens, not 4
        tokens = [t.strip() for t in result.split(",")]
        assert len(tokens) == 2

    def test_empty_inputs(self):
        """Handles empty strings gracefully."""
        result = merge_negative_prompts("", "blurry", "", "bad anatomy")

        assert "blurry" in result
        assert "bad anatomy" in result
        assert result.count(",,") == 0

    def test_no_inputs(self):
        """No inputs returns empty string."""
        result = merge_negative_prompts()

        assert result == ""

    def test_preserves_order(self):
        """First occurrence order is preserved."""
        result = merge_negative_prompts("first, second", "third, first")

        tokens = [t.strip().lower() for t in result.split(",")]
        assert tokens.index("first") < tokens.index("second")
        assert tokens.index("second") < tokens.index("third")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: build_adetailer_prompt
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildAdetailerPrompt:
    """Tests for aDetailer prompt building."""

    def test_default_medium_level(self):
        """Default detail level is medium."""
        result = build_adetailer_prompt(subject="portrait")

        assert "detailed face" in result
        assert "natural lighting on face" in result

    def test_high_detail_level(self):
        """High detail level adds extra tokens."""
        result = build_adetailer_prompt(subject="portrait", detail_level="high")

        assert "sharp facial features" in result
        assert "skin pores" in result

    def test_low_detail_level(self):
        """Low detail level is minimal."""
        result = build_adetailer_prompt(subject="portrait", detail_level="low")

        assert "detailed face" in result
        assert "natural lighting" not in result
        assert "sharp facial" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: extract_subject_keywords
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractSubjectKeywords:
    """Tests for keyword extraction."""

    def test_extracts_words(self):
        """Extracts words from subject."""
        result = extract_subject_keywords("woman running through city street")

        assert "woman" in result
        assert "running" in result
        assert "city" in result
        assert "street" in result

    def test_lowercase(self):
        """Keywords are lowercase."""
        result = extract_subject_keywords("RUNNING MAN")

        assert "running" in result
        assert "man" in result
        assert "RUNNING" not in result

    def test_filters_short_words(self):
        """Words <= 2 chars are filtered."""
        result = extract_subject_keywords("a man in a car")

        assert "man" in result
        assert "car" in result
        assert "a" not in result
        assert "in" not in result

    def test_handles_punctuation(self):
        """Punctuation is handled."""
        result = extract_subject_keywords("man, woman. running")

        assert "man" in result
        assert "woman" in result
        assert "running" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: OpticsProfile dataclass
# ═══════════════════════════════════════════════════════════════════════════════


class TestOpticsProfile:
    """Tests for OpticsProfile dataclass."""

    def test_all_fields_optional(self):
        """All fields default to None."""
        profile = OpticsProfile()

        assert profile.camera is None
        assert profile.film_stock is None
        assert profile.lighting is None
        assert profile.motion is None

    def test_frozen(self):
        """Profile is immutable."""
        profile = OpticsProfile(camera="ARRI")

        with pytest.raises(AttributeError):
            profile.camera = "RED"

    def test_equality(self):
        """Equal profiles compare equal."""
        p1 = OpticsProfile(camera="ARRI", lighting="soft")
        p2 = OpticsProfile(camera="ARRI", lighting="soft")

        assert p1 == p2

    def test_hashable(self):
        """Profiles can be used in sets/dicts."""
        profile = OpticsProfile(camera="ARRI")

        profiles = {profile}
        assert profile in profiles


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Director Inject (CLIP Priority)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDirectorInject:
    """Tests for director_inject CLIP-priority feature."""

    def test_director_inject_comes_first(self):
        """Director inject should be the FIRST part of the prompt."""
        result = compose_prompt(
            subject="person walking",
            director_inject="score_9, raw street beef",
        )

        assert result.full_prompt.startswith("score_9")

    def test_director_inject_before_subject(self):
        """Director inject comes before subject."""
        result = compose_prompt(
            subject="person walking",
            director_inject="PRIORITY_TOKEN",
            camera_tokens="shot on ARRI",
        )

        prompt = result.full_prompt
        priority_pos = prompt.find("PRIORITY_TOKEN")
        subject_pos = prompt.find("person walking")

        assert priority_pos < subject_pos, "Director inject must come before subject"

    def test_empty_director_inject(self):
        """Empty director inject doesn't cause issues."""
        result = compose_prompt(
            subject="test",
            director_inject="",
        )

        assert not result.full_prompt.startswith(",")
        assert "test" in result.full_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Token Estimation and Truncation
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenEstimation:
    """Tests for CLIP token estimation."""

    def test_estimate_tokens_basic(self):
        """Basic token estimation works."""
        result = estimate_tokens("hello world")

        assert result > 0
        assert result < 10  # Should be roughly 2-3 tokens

    def test_estimate_tokens_empty(self):
        """Empty string returns 0."""
        result = estimate_tokens("")

        assert result == 0

    def test_estimate_tokens_with_weights(self):
        """Weighted tokens (parentheses) add to count."""
        base = estimate_tokens("test")
        weighted = estimate_tokens("(test:1.4)")

        assert weighted >= base  # Parentheses add tokens


class TestTruncation:
    """Tests for token truncation."""

    def test_truncate_fits_within_limit(self):
        """Truncation keeps prompt under limit."""
        parts = ["short", "another short", "yet another"]
        result = truncate_to_token_limit(parts, limit=10)

        # Should have at least one part
        assert len(result) >= 1

    def test_truncate_preserves_priority_order(self):
        """First parts (highest priority) are preserved."""
        parts = ["PRIORITY_ONE", "PRIORITY_TWO", "low priority long text"]
        result = truncate_to_token_limit(parts, limit=15)

        assert "PRIORITY_ONE" in result[0]

    def test_composed_prompt_has_estimated_tokens(self):
        """ComposedPrompt includes token estimate."""
        result = compose_prompt(subject="test subject")

        assert hasattr(result, "estimated_tokens")
        assert result.estimated_tokens > 0

    def test_truncation_under_clip_limit(self):
        """Default composition stays under CLIP limit."""
        result = compose_prompt(
            subject="short subject",
            director_inject="score_9",
            camera_tokens="ARRI",
        )

        assert result.estimated_tokens <= CLIP_TOKEN_LIMIT
