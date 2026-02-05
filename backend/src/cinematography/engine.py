"""
Cinematography Engine - Orchestration facade for prompt composition.

Combines OpticsCatalog, StyleLogic, and PromptComposer into a single
interface for generating photorealistic prompts.

Example:
    engine = CinematographyEngine()

    # Style-driven composition
    result = engine.compose(
        subject="woman walking through rain",
        style="STYLE_URBAN_LUXURY"
    )

    # Manual optics selection
    result = engine.compose(
        subject="man in leather jacket",
        camera="ARRI_ALEXA_65",
        film_stock="CINESTILL_800T",
        lighting="DRAMATIC_RIM_LIGHTING"
    )
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.cinematography.optics import OpticsCatalog, load_default_catalog, ADetailerConfig
from src.cinematography.prompt_composer import (
    ComposedPrompt,
    OpticsProfile,
    compose_prompt,
    merge_negative_prompts,
    inject_action_framing,
    MANDATORY_QUALITY_TOKENS,
)
from src.cinematography.style_logic import (
    detect_style,
    get_style_optics,
    get_style_prefix,
    get_style_generation_config,
    get_style_definition,
    get_director_inject,
    list_styles,
    STYLE_DEFINITIONS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CINEMATOGRAPHY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class CinematographyEngine:
    """
    Orchestration facade for cinematography prompt composition.

    Combines:
    - OpticsCatalog: Loads presets from YAML
    - StyleLogic: Style detection and optics profiles
    - PromptComposer: Pure function prompt construction

    Supports dependency injection for testing:
        engine = CinematographyEngine(optics_catalog=mock_catalog)
    """

    def __init__(
        self,
        optics_catalog: Optional[OpticsCatalog] = None,
        custom_styles: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the cinematography engine.

        Args:
            optics_catalog: Inject custom catalog (for testing).
                           If None, loads from library/optics_presets.yaml
            custom_styles: Override style definitions (for testing).
                          Keys are style names, values are StyleDefinition-like dicts.
        """
        # Load optics catalog (or use injected mock)
        if optics_catalog is not None:
            self._catalog = optics_catalog
        else:
            try:
                self._catalog = load_default_catalog()
            except FileNotFoundError:
                # Fall back to empty catalog if YAML not found
                self._catalog = OpticsCatalog.empty()

        # Custom style overrides (for testing)
        self._custom_styles = custom_styles or {}

    @property
    def catalog(self) -> OpticsCatalog:
        """Access the optics catalog."""
        return self._catalog

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN COMPOSITION API
    # ═══════════════════════════════════════════════════════════════════════════

    def compose(
        self,
        subject: str,
        style: Optional[str] = None,
        camera: Optional[str] = None,
        film_stock: Optional[str] = None,
        lighting: Optional[str] = None,
        motion: Optional[str] = None,
        auto_detect_style: bool = False,
        include_photo_of: bool = True,
    ) -> ComposedPrompt:
        """
        Compose a cinematography prompt.

        Can work in three modes:
        1. Style-driven: Pass style name, uses curated optics
        2. Manual: Pass individual optics (camera, film_stock, etc.)
        3. Auto-detect: Set auto_detect_style=True to infer from subject

        Explicit optics parameters override style defaults.

        Args:
            subject: Main subject description
            style: Style constant (e.g., STYLE_HIGH_VELOCITY_ACTION)
            camera: Camera preset name (e.g., "ARRI_ALEXA_65")
            film_stock: Film stock preset name (e.g., "CINESTILL_800T")
            lighting: Lighting preset name (e.g., "HARD_LIGHT")
            motion: Motion preset name (e.g., "HANDHELD_AGGRESSIVE")
            auto_detect_style: If True and no style provided, detect from subject
            include_photo_of: Include "photo of" in prompt template

        Returns:
            ComposedPrompt with full_prompt and components
        """
        # Auto-detect style if requested
        if auto_detect_style and not style:
            style = detect_style(subject)

        # Get style optics profile (if style provided)
        style_optics = get_style_optics(style) if style else None
        style_prefix = get_style_prefix(style) if style else ""

        # Get director inject from YAML (HIGH PRIORITY - goes FIRST in prompt)
        director_inject = get_director_inject(style) if style else ""

        # Resolve optics: explicit params > style defaults > empty
        camera_name = camera or (style_optics.camera if style_optics else None)
        film_name = film_stock or (style_optics.film_stock if style_optics else None)
        lighting_name = lighting or (style_optics.lighting if style_optics else None)
        motion_name = motion or (style_optics.motion if style_optics else None)

        # Look up tokens from catalog
        camera_tokens = self._catalog.get_camera_tokens(camera_name) if camera_name else ""
        film_tokens = self._catalog.get_film_tokens(film_name) if film_name else ""
        lighting_tokens = self._catalog.get_lighting_tokens(lighting_name) if lighting_name else ""
        motion_tokens = self._catalog.get_motion_tokens(motion_name) if motion_name else ""

        # Get mandatory quality tokens
        quality_tokens = self._catalog.get_mandatory_quality_tokens()
        if not quality_tokens:
            # Fall back to hardcoded mandatory tokens
            quality_tokens = MANDATORY_QUALITY_TOKENS

        # Inject action framing for high-velocity styles (prevents edge tracking failure)
        framed_subject = inject_action_framing(subject, style or "")

        # Compose using pure function (director_inject goes FIRST for CLIP priority)
        return compose_prompt(
            subject=framed_subject,
            style_prefix=style_prefix,
            director_inject=director_inject,
            camera_tokens=camera_tokens,
            film_tokens=film_tokens,
            lighting_tokens=lighting_tokens,
            motion_tokens=motion_tokens,
            quality_tokens=quality_tokens,
            include_photo_of=include_photo_of,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATION CONFIG
    # ═══════════════════════════════════════════════════════════════════════════

    def get_generation_config(self, style: Optional[str] = None) -> Dict[str, Any]:
        """
        Get generation config for a style.

        Args:
            style: Style constant (optional)

        Returns:
            Dict with:
                - cfg_scale: Guidance scale
                - steps: Inference steps
                - recommended_checkpoint: Model to use
                - sampler: Recommended sampler
                - target_size: SDXL target resolution (width, height)
                - crops_coords_top_left: SDXL crop coordinates (prevents stretching)
                - upcast_vae: Enable VAE upcasting for pixel alignment
        """
        # SDXL Geometry config for 9:16 vertical (Street Rap aesthetic)
        # - target_size prevents model from stretching square to rectangle
        # - crops_coords_top_left (0,0) ensures no offset cropping
        # - upcast_vae maintains pixel proportions during VAE decode
        sdxl_geometry = {
            "target_size": (576, 1024),          # 9:16 vertical
            "crops_coords_top_left": (0, 0),     # No cropping offset
            "original_size": (576, 1024),        # Match target for no rescaling
            "upcast_vae": True,                  # Maintain pixel alignment
        }

        if style:
            config = get_style_generation_config(style)
            if config:
                return {
                    **config,
                    **sdxl_geometry,
                    "sampler": "DPM++ 2M Karras",  # Default good sampler
                }

        # Default config
        return {
            "cfg_scale": 7.0,
            "steps": 30,
            "recommended_checkpoint": "STANDARD_CINEMATIC",
            "sampler": "DPM++ 2M Karras",
            **sdxl_geometry,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # NEGATIVE PROMPTS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_negative_prompt(self, style: Optional[str] = None) -> str:
        """
        Get negative prompt, optionally tailored to style.

        Args:
            style: Style constant (optional)

        Returns:
            Negative prompt string with duplicates removed
        """
        # Get all category negative prompts from catalog
        photorealism = self._catalog.get_negative_prompt("photorealism")
        anatomy = self._catalog.get_negative_prompt("anatomy")
        quality = self._catalog.get_negative_prompt("quality")

        # Style-specific additions could go here
        style_negative = ""
        if style:
            definition = get_style_definition(style)
            # Future: Add style-specific negatives from definition

        return merge_negative_prompts(photorealism, anatomy, quality, style_negative)

    # ═══════════════════════════════════════════════════════════════════════════
    # ADETAILER CONFIG
    # ═══════════════════════════════════════════════════════════════════════════

    def get_adetailer_config(self) -> Dict[str, Any]:
        """
        Get aDetailer post-processing configuration.

        Returns:
            Dict with face_repair and hand_repair configs
        """
        face_config = self._catalog.get_adetailer_config("face_repair")
        hand_config = self._catalog.get_adetailer_config("hand_repair")

        return {
            "face_repair": {
                "enabled": face_config.enabled if face_config else True,
                "model": face_config.model if face_config else "face_yolov8n.pt",
                "confidence": face_config.confidence if face_config else 0.3,
            },
            "hand_repair": {
                "enabled": hand_config.enabled if hand_config else True,
                "model": hand_config.model if hand_config else "hand_yolov8n.pt",
                "confidence": hand_config.confidence if hand_config else 0.5,
            },
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # LISTING / DISCOVERY
    # ═══════════════════════════════════════════════════════════════════════════

    def list_styles(self) -> List[str]:
        """List all available style names."""
        return list_styles()

    def list_cameras(self) -> List[str]:
        """List all available camera names."""
        return self._catalog.list_cameras()

    def list_film_stocks(self) -> List[str]:
        """List all available film stock names."""
        return self._catalog.list_film_stocks()

    def list_lighting(self) -> List[str]:
        """List all available lighting names."""
        return self._catalog.list_lighting()

    def list_motion(self) -> List[str]:
        """List all available motion names."""
        return self._catalog.list_motion()

    def get_style_info(self, style: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed info about a style.

        Args:
            style: Style constant

        Returns:
            Dict with display_name, description, optics, generation config
        """
        from src.cinematography.style_logic import get_style_info

        return get_style_info(style)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FACTORY
# ═══════════════════════════════════════════════════════════════════════════════


def create_engine(yaml_path: Optional[Path] = None) -> CinematographyEngine:
    """
    Factory function to create a CinematographyEngine.

    Args:
        yaml_path: Optional custom YAML path (for testing)

    Returns:
        Configured CinematographyEngine instance
    """
    if yaml_path:
        catalog = OpticsCatalog.from_yaml(yaml_path)
        return CinematographyEngine(optics_catalog=catalog)

    return CinematographyEngine()
