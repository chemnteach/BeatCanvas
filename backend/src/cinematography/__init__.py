"""
Cinematography Engine - Photorealistic prompt composition.

Based on "Creating Photorealistic Images" guide.
Provides style-driven optics selection and prompt templating.

Example:
    from src.cinematography import CinematographyEngine

    engine = CinematographyEngine()
    composed = engine.compose(
        subject="woman walking through rain",
        style="STYLE_URBAN_LUXURY"
    )
    print(composed.full_prompt)
"""

from src.cinematography.prompt_composer import (
    OpticsProfile,
    ComposedPrompt,
    compose_prompt,
    merge_negative_prompts,
)
from src.cinematography.optics import OpticsCatalog
from src.cinematography.style_logic import (
    STYLE_HIGH_VELOCITY_ACTION,
    STYLE_URBAN_LUXURY,
    STYLE_PHYSICAL_DRAMA,
    detect_style,
    get_style_optics,
    get_director_inject,
)
from src.cinematography.engine import CinematographyEngine
from src.cinematography.raft_interpolator import RAFTInterpolator
from src.cinematography.temporal_consistency import TemporalConsistencySVD
from src.cinematography.animatediff_generator import AnimateDiffGenerator
from src.cinematography.physics_motion_tracker import (
    HumanSkeleton,
    LightweightPoseEstimator,
    SkeletalConsistencyChecker,
    create_skeletal_checker,
)

__all__ = [
    # Data classes
    "OpticsProfile",
    "ComposedPrompt",
    # Pure functions
    "compose_prompt",
    "merge_negative_prompts",
    # Catalog
    "OpticsCatalog",
    # Style constants
    "STYLE_HIGH_VELOCITY_ACTION",
    "STYLE_URBAN_LUXURY",
    "STYLE_PHYSICAL_DRAMA",
    "detect_style",
    "get_style_optics",
    "get_director_inject",
    # Facade
    "CinematographyEngine",
    # Video Generation
    "RAFTInterpolator",
    "TemporalConsistencySVD",
    "AnimateDiffGenerator",
    # AKD Physics Tracking
    "HumanSkeleton",
    "LightweightPoseEstimator",
    "SkeletalConsistencyChecker",
    "create_skeletal_checker",
]
