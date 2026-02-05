"""
Local inference modules for BeatCanvas.

Lightweight init - do NOT import heavy modules here.
Import directly from submodules to avoid circular dependencies:

    from src.local.image_generator import LocalImageGenerator
    from src.local.video_generator import LocalVideoGenerator
"""

__all__ = ["image_generator", "video_generator", "motion_smoother", "cinematic_director"]
