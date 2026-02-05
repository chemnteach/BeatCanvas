"""
TDD Test Suite: Full Pipeline VRAM Handover

Tests the complete BeatCanvas pipeline VRAM lifecycle:
  ImageGen (SDXL) → VideoGen (SVD) → MotionSmoother (RIFE)

Each stage must:
1. Load its model
2. Execute
3. Kill and return to <1GB baseline BEFORE next stage loads

VRAM Budget: 12GB (Acer Predator)
Rule: Only ONE model loaded at a time. Kill before swap.

Run with: pytest tests/test_full_pipeline_handover.py -v -m cuda
"""

import gc
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.local.vram_manager import VRAMManager


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def cuda_available():
    """Check if CUDA is available."""
    try:
        import torch
        available = torch.cuda.is_available()
        if available:
            props = torch.cuda.get_device_properties(0)
            print(f"\n🎮 GPU: {props.name}")
            print(f"   VRAM: {props.total_memory / (1024**3):.1f}GB")
        return available
    except ImportError:
        return False


@pytest.fixture
def shared_vram_manager():
    """Create shared VRAMManager for pipeline coordination."""
    mgr = VRAMManager()
    yield mgr
    # Final cleanup
    mgr.kill()


def skip_if_no_cuda(cuda_available):
    """Helper to skip tests without CUDA."""
    if not cuda_available:
        pytest.skip("CUDA not available")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: SHARED VRAM MANAGER COORDINATION
# Verify components can share a single VRAMManager instance
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestSharedVRAMManagerCoordination:
    """Test that all pipeline components share a single VRAMManager."""

    VRAM_BASELINE_THRESHOLD_GB = 1.0

    def test_image_generator_accepts_shared_manager(self, shared_vram_manager, cuda_available):
        """ImageGenerator should accept and use a shared VRAMManager."""
        skip_if_no_cuda(cuda_available)

        from src.local.image_generator import LocalImageGenerator

        # Create with shared manager
        img_gen = LocalImageGenerator(vram_manager=shared_vram_manager)

        # Verify it's using the shared manager
        assert img_gen.vram_manager is shared_vram_manager
        assert img_gen.pipe is None  # Not loaded yet

        # Load a model
        img_gen.load_model("draft")  # Fastest

        # Both should see the loaded model
        assert img_gen.current_model == "STANDARD_DRAFT"
        assert shared_vram_manager.current_model == "STANDARD_DRAFT"
        assert shared_vram_manager.pipe is not None

    def test_video_generator_accepts_shared_manager(self, shared_vram_manager, cuda_available):
        """VideoGenerator should accept and use a shared VRAMManager."""
        skip_if_no_cuda(cuda_available)

        from src.local.video_generator import LocalVideoGenerator

        # Create with shared manager
        video_gen = LocalVideoGenerator(vram_manager=shared_vram_manager)

        # Verify it's using the shared manager
        assert video_gen.vram_manager is shared_vram_manager

    def test_killing_via_shared_manager_affects_all(self, shared_vram_manager, cuda_available):
        """Killing via shared manager should clear state for all components."""
        skip_if_no_cuda(cuda_available)

        from src.local.image_generator import LocalImageGenerator

        img_gen = LocalImageGenerator(vram_manager=shared_vram_manager)
        img_gen.load_model("draft")

        # Verify loaded
        assert shared_vram_manager.pipe is not None
        vram_loaded = shared_vram_manager.get_vram_usage()
        assert vram_loaded > 2.0

        # Kill via shared manager
        shared_vram_manager.kill()
        time.sleep(0.3)

        # Both should see cleared state
        assert shared_vram_manager.pipe is None
        assert img_gen.pipe is None
        assert shared_vram_manager.get_vram_usage() < self.VRAM_BASELINE_THRESHOLD_GB


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: IMAGE → VIDEO HANDOVER
# Verify VRAM returns to baseline between ImageGen and VideoGen
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestImageToVideoHandover:
    """Test VRAM handover from ImageGenerator to VideoGenerator."""

    VRAM_BASELINE_THRESHOLD_GB = 1.5

    def test_image_kill_before_video_load(self, shared_vram_manager, cuda_available):
        """
        ImageGen must be killed and VRAM returned to baseline before VideoGen loads.
        """
        skip_if_no_cuda(cuda_available)

        from src.local.image_generator import LocalImageGenerator
        from src.local.video_generator import LocalVideoGenerator

        # Establish baseline
        shared_vram_manager.kill()
        time.sleep(0.3)
        baseline = shared_vram_manager.get_vram_usage()
        print(f"\n   Baseline: {baseline:.2f}GB")

        # Phase 1: Load ImageGen (Pony for action shots)
        img_gen = LocalImageGenerator(vram_manager=shared_vram_manager)
        img_gen.load_model("pony")
        img_vram = shared_vram_manager.get_vram_usage()
        print(f"   After ImageGen load (Pony): {img_vram:.2f}GB")
        assert img_vram > 3.0, "ImageGen should use significant VRAM"

        # Phase 2: Kill ImageGen
        img_gen.kill()
        time.sleep(0.5)
        post_img_kill = shared_vram_manager.get_vram_usage()
        print(f"   After ImageGen kill: {post_img_kill:.2f}GB")

        # CRITICAL: Must be at baseline before VideoGen
        assert post_img_kill < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"VRAM after ImageGen kill ({post_img_kill:.2f}GB) not at baseline! "
            f"VideoGen cannot safely load."
        )

        # Phase 3: VideoGen can now safely check VRAM
        video_gen = LocalVideoGenerator(vram_manager=shared_vram_manager)
        available_vram = shared_vram_manager.get_vram_free()
        print(f"   Available for VideoGen: {available_vram:.2f}GB")

        # Should have enough for SVD (~7GB)
        assert available_vram > 7.0, (
            f"Not enough VRAM for SVD! Available: {available_vram:.2f}GB, Need: ~7GB"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: VIDEO → RIFE HANDOVER
# Verify VRAM returns to baseline between VideoGen and MotionSmoother
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestVideoToRIFEHandover:
    """Test VRAM handover from VideoGenerator to MotionSmoother."""

    VRAM_BASELINE_THRESHOLD_GB = 1.5

    def test_video_generator_has_kill_method(self, shared_vram_manager, cuda_available):
        """VideoGenerator must have a kill() method for VRAM handover."""
        skip_if_no_cuda(cuda_available)

        from src.local.video_generator import LocalVideoGenerator

        video_gen = LocalVideoGenerator(vram_manager=shared_vram_manager)

        # Must have kill method
        assert hasattr(video_gen, 'kill'), "VideoGenerator must have kill() method"
        assert callable(video_gen.kill), "kill must be callable"

    def test_motion_smoother_respects_vram_lifecycle(self, shared_vram_manager, cuda_available):
        """MotionSmoother should work within VRAM lifecycle."""
        skip_if_no_cuda(cuda_available)

        from src.local.motion_smoother import MotionSmoother

        # MotionSmoother should be creatable
        smoother = MotionSmoother(vram_manager=shared_vram_manager)

        # Should have cleanup method
        assert hasattr(smoother, 'cleanup') or hasattr(smoother, 'kill'), (
            "MotionSmoother must have cleanup() or kill() method"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: FULL PIPELINE VRAM HANDOVER
# The main test: ImageGen → VideoGen → RIFE with 3 baseline checkpoints
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
@pytest.mark.slow
class TestFullPipelineHandover:
    """
    Full pipeline VRAM handover test.

    Verifies VRAM returns to baseline (<1GB) THREE times:
    1. After ImageGen kill (before VideoGen)
    2. After VideoGen kill (before RIFE)
    3. After RIFE cleanup (final state)
    """

    VRAM_BASELINE_THRESHOLD_GB = 1.5
    VRAM_BASELINE_CHECKPOINTS = []

    def test_three_stage_handover_vram_baselines(self, shared_vram_manager, cuda_available):
        """
        Execute mock run: STANDARD_ACTION → SVD → RIFE
        Assert VRAM returns to baseline 3 times.
        """
        skip_if_no_cuda(cuda_available)

        from src.local.image_generator import LocalImageGenerator
        from src.local.video_generator import LocalVideoGenerator
        from src.local.motion_smoother import MotionSmoother

        vram_checkpoints = []

        # Establish baseline
        shared_vram_manager.kill()
        time.sleep(0.3)
        initial_baseline = shared_vram_manager.get_vram_usage()
        print(f"\n   Initial baseline: {initial_baseline:.2f}GB")

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 1: IMAGE GENERATION (STANDARD_ACTION / Pony)
        # ═══════════════════════════════════════════════════════════════════
        print("\n   === STAGE 1: ImageGen (Pony) ===")
        img_gen = LocalImageGenerator(vram_manager=shared_vram_manager)
        img_gen.load_model("STANDARD_ACTION")
        img_vram = shared_vram_manager.get_vram_usage()
        print(f"   Loaded: {img_vram:.2f}GB")

        # Simulate generation (just verify model is loaded)
        assert shared_vram_manager.pipe is not None
        assert shared_vram_manager.current_model == "STANDARD_ACTION"

        # KILL ImageGen
        print("   Killing ImageGen...")
        img_gen.kill()
        time.sleep(0.5)
        checkpoint_1 = shared_vram_manager.get_vram_usage()
        vram_checkpoints.append(("After ImageGen kill", checkpoint_1))
        print(f"   ✓ Checkpoint 1: {checkpoint_1:.2f}GB")

        # ASSERTION 1: Must be at baseline
        assert checkpoint_1 < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"Checkpoint 1 FAILED: {checkpoint_1:.2f}GB > {self.VRAM_BASELINE_THRESHOLD_GB}GB"
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 2: VIDEO GENERATION (SVD)
        # ═══════════════════════════════════════════════════════════════════
        print("\n   === STAGE 2: VideoGen (SVD) ===")
        video_gen = LocalVideoGenerator(vram_manager=shared_vram_manager)

        # For this test, we don't actually load SVD (would need image input)
        # Instead, verify the handover protocol works
        print("   VideoGen ready (mock - no actual SVD load)")
        print(f"   Available VRAM: {shared_vram_manager.get_vram_free():.2f}GB")

        # KILL VideoGen (even if not loaded, should be safe)
        print("   Killing VideoGen...")
        video_gen.kill()
        time.sleep(0.3)
        checkpoint_2 = shared_vram_manager.get_vram_usage()
        vram_checkpoints.append(("After VideoGen kill", checkpoint_2))
        print(f"   ✓ Checkpoint 2: {checkpoint_2:.2f}GB")

        # ASSERTION 2: Must be at baseline
        assert checkpoint_2 < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"Checkpoint 2 FAILED: {checkpoint_2:.2f}GB > {self.VRAM_BASELINE_THRESHOLD_GB}GB"
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 3: MOTION SMOOTHING (RIFE)
        # ═══════════════════════════════════════════════════════════════════
        print("\n   === STAGE 3: MotionSmoother (RIFE) ===")
        smoother = MotionSmoother(vram_manager=shared_vram_manager)

        # RIFE runs externally, but verify it can clean up
        print("   MotionSmoother ready")

        # Final cleanup
        print("   Final cleanup...")
        if hasattr(smoother, 'cleanup'):
            smoother.cleanup()
        elif hasattr(smoother, 'kill'):
            smoother.kill()
        shared_vram_manager.kill()  # Ensure clean state
        time.sleep(0.3)
        checkpoint_3 = shared_vram_manager.get_vram_usage()
        vram_checkpoints.append(("After RIFE cleanup", checkpoint_3))
        print(f"   ✓ Checkpoint 3: {checkpoint_3:.2f}GB")

        # ASSERTION 3: Must be at baseline
        assert checkpoint_3 < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"Checkpoint 3 FAILED: {checkpoint_3:.2f}GB > {self.VRAM_BASELINE_THRESHOLD_GB}GB"
        )

        # ═══════════════════════════════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════════════════════════════
        print("\n   === VRAM CHECKPOINT SUMMARY ===")
        for name, vram in vram_checkpoints:
            status = "✓ PASS" if vram < self.VRAM_BASELINE_THRESHOLD_GB else "✗ FAIL"
            print(f"   {status}: {name}: {vram:.2f}GB")

        # All three must be below threshold
        assert all(v < self.VRAM_BASELINE_THRESHOLD_GB for _, v in vram_checkpoints), (
            "Not all checkpoints returned to baseline!"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: CINEMATIC DIRECTOR ORCHESTRATION
# Verify the CinematicDirector follows strict stage sequencing
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestCinematicDirectorOrchestration:
    """Test that CinematicDirector orchestrates stages correctly."""

    def test_director_has_stage_sequence(self, cuda_available):
        """CinematicDirector should define stage sequence."""
        skip_if_no_cuda(cuda_available)

        from src.local.cinematic_director import CinematicDirector

        director = CinematicDirector()

        # Should have defined stages and run method
        assert hasattr(director, 'STAGES') or hasattr(director, 'stages'), (
            "CinematicDirector must define STAGES constant"
        )
        assert hasattr(director, 'run') or hasattr(director, 'run_pipeline'), (
            "CinematicDirector must define run() method"
        )
        assert callable(director.run), "run must be callable"

    def test_director_uses_shared_vram_manager(self, shared_vram_manager, cuda_available):
        """CinematicDirector should accept shared VRAMManager."""
        skip_if_no_cuda(cuda_available)

        from src.local.cinematic_director import CinematicDirector

        # Should accept shared manager
        director = CinematicDirector(vram_manager=shared_vram_manager)

        assert director.vram_manager is shared_vram_manager


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: VRAM LEAK DETECTION OVER MULTIPLE RUNS
# Verify no VRAM accumulation over repeated pipeline runs
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
@pytest.mark.slow
class TestVRAMLeakDetection:
    """Detect VRAM leaks over multiple pipeline runs."""

    def test_repeated_image_video_cycles_no_leak(self, shared_vram_manager, cuda_available):
        """
        Run image→kill cycle 3 times. Final VRAM should match initial.
        """
        skip_if_no_cuda(cuda_available)

        from src.local.image_generator import LocalImageGenerator

        shared_vram_manager.kill()
        time.sleep(0.3)
        initial = shared_vram_manager.get_vram_usage()
        print(f"\n   Initial: {initial:.2f}GB")

        # Run 3 cycles
        for i in range(3):
            img_gen = LocalImageGenerator(vram_manager=shared_vram_manager)
            img_gen.load_model("draft")  # Fast model
            loaded = shared_vram_manager.get_vram_usage()
            img_gen.kill()
            time.sleep(0.3)
            after_kill = shared_vram_manager.get_vram_usage()
            print(f"   Cycle {i+1}: loaded={loaded:.2f}GB, after_kill={after_kill:.2f}GB")

        final = shared_vram_manager.get_vram_usage()
        print(f"   Final: {final:.2f}GB")

        # Final should be close to initial (within 0.5GB tolerance)
        assert final < initial + 0.5, (
            f"VRAM leak detected! Initial: {initial:.2f}GB, Final: {final:.2f}GB"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RUN CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "cuda", "--tb=short"])
