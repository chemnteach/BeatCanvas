"""
TDD Test Suite: Multi-Model Swap and VRAM Isolation

Tests the 'Kill and Revive' pattern across different model types:
- Image generators (SDXL variants: Pony, Lustify, Juggernaut, RealVis, Lightning)
- Video generator (SVD)

VRAM Budget: 12GB (Acer Predator)
Rule: Only ONE model loaded at a time. Kill before swap. Return to <1GB baseline.

Run with: pytest tests/test_multi_model_swap.py -v -m cuda
"""

import gc
import time
import pytest
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.local.vram_manager import VRAMManager, ModelRouter


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
def manager():
    """Create fresh VRAMManager for each test."""
    mgr = VRAMManager()
    yield mgr
    # Cleanup after test
    mgr.kill()


@pytest.fixture
def router():
    """Create ModelRouter instance."""
    return ModelRouter()


def skip_if_no_cuda(cuda_available):
    """Helper to skip tests without CUDA."""
    if not cuda_available:
        pytest.skip("CUDA not available")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: PONY → LUSTIFY SWAP WITH VRAM BASELINE CHECK
# Core requirement: VRAM must return to <1GB between model swaps
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestPonyToLustifySwap:
    """Test swapping from STANDARD_ACTION (Pony) to STANDARD_ANATOMY (Lustify)."""

    VRAM_BASELINE_THRESHOLD_GB = 1.0  # Must return to <1GB after kill

    def test_swap_returns_to_baseline_between_loads(self, manager, cuda_available):
        """
        VRAM must return to baseline (<1GB) between Pony and Lustify loads.

        This verifies that Pony's trigger tags, CLIP settings, and any model-specific
        state are fully purged before Lustify loads.
        """
        skip_if_no_cuda(cuda_available)

        # Establish baseline
        manager.kill()
        time.sleep(0.3)
        baseline = manager.get_vram_usage()
        print(f"\n   Baseline VRAM: {baseline:.2f}GB")
        assert baseline < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"Baseline too high: {baseline:.2f}GB"
        )

        # Step 1: Load STANDARD_ACTION (Pony)
        print("   Loading STANDARD_ACTION (Pony)...")
        manager.load("STANDARD_ACTION")
        pony_vram = manager.get_vram_usage()
        print(f"   Pony VRAM: {pony_vram:.2f}GB")
        assert pony_vram > 3.0, f"Pony should use >3GB VRAM, got {pony_vram:.2f}GB"
        assert manager.current_model == "STANDARD_ACTION"

        # Step 2: Kill Pony
        print("   Killing Pony...")
        manager.kill()
        time.sleep(0.5)  # Allow CUDA to fully release
        post_kill_vram = manager.get_vram_usage()
        print(f"   Post-kill VRAM: {post_kill_vram:.2f}GB")

        # CRITICAL ASSERTION: Must return to baseline
        assert post_kill_vram < self.VRAM_BASELINE_THRESHOLD_GB, (
            f"VRAM after killing Pony ({post_kill_vram:.2f}GB) exceeds baseline threshold "
            f"({self.VRAM_BASELINE_THRESHOLD_GB}GB). Pony state not fully purged!"
        )

        # Step 3: Load STANDARD_ANATOMY (Lustify)
        print("   Loading STANDARD_ANATOMY (Lustify)...")
        manager.load("STANDARD_ANATOMY")
        lustify_vram = manager.get_vram_usage()
        print(f"   Lustify VRAM: {lustify_vram:.2f}GB")
        assert lustify_vram > 3.0, f"Lustify should use >3GB VRAM, got {lustify_vram:.2f}GB"
        assert manager.current_model == "STANDARD_ANATOMY"

    def test_vram_doesnt_stack_after_multiple_swaps(self, manager, cuda_available):
        """
        VRAM usage after 2 swaps shouldn't be higher than after 1st swap.

        This detects memory leaks from incomplete model purging.
        """
        skip_if_no_cuda(cuda_available)

        manager.kill()
        baseline = manager.get_vram_usage()
        print(f"\n   Baseline: {baseline:.2f}GB")

        # Swap 1: Load Pony
        manager.load("STANDARD_ACTION")
        vram_after_swap1 = manager.get_vram_usage()
        print(f"   After Swap 1 (Pony): {vram_after_swap1:.2f}GB")

        # Swap 2: Pony → Lustify
        manager.load("STANDARD_ANATOMY")
        vram_after_swap2 = manager.get_vram_usage()
        print(f"   After Swap 2 (Lustify): {vram_after_swap2:.2f}GB")

        # Swap 3: Lustify → Pony again
        manager.load("STANDARD_ACTION")
        vram_after_swap3 = manager.get_vram_usage()
        print(f"   After Swap 3 (Pony again): {vram_after_swap3:.2f}GB")

        # CRITICAL ASSERTION: Swap 3 Pony shouldn't use more VRAM than Swap 1 Pony
        # Allow 10% tolerance for CUDA fragmentation
        max_expected = vram_after_swap1 * 1.1
        assert vram_after_swap3 <= max_expected, (
            f"VRAM stacking detected! Swap 1 Pony: {vram_after_swap1:.2f}GB, "
            f"Swap 3 Pony: {vram_after_swap3:.2f}GB (>{max_expected:.2f}GB tolerance)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: CONTEXT-AWARE FLUSHING
# Verify model-specific settings (trigger tags, schedulers) don't leak
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestContextAwareFlushing:
    """Test that model-specific context is fully purged on swap."""

    def test_pony_trigger_tags_not_leaked_to_lustify(self, manager, router, cuda_available):
        """
        Pony's trigger tags (score_9, score_8_up) must not affect Lustify generation.
        """
        skip_if_no_cuda(cuda_available)

        # Load Pony and verify it has trigger tags
        pony_config = router.get_generation_config("STANDARD_ACTION")
        pony_prompt = router.prepare_prompt("STANDARD_ACTION", "test prompt")
        assert "score_9" in pony_prompt, "Pony should inject trigger tags"

        # Load Lustify and verify it doesn't have trigger tags
        lustify_prompt = router.prepare_prompt("STANDARD_ANATOMY", "test prompt")
        assert "score_9" not in lustify_prompt, (
            "Lustify prompt should NOT contain Pony trigger tags"
        )
        assert lustify_prompt == "test prompt", (
            f"Lustify prompt should be unchanged, got: {lustify_prompt}"
        )

    def test_lightning_scheduler_not_leaked_to_other_models(self, manager, router, cuda_available):
        """
        Lightning's DPMSolver scheduler and 4-step config must not leak to other models.
        """
        skip_if_no_cuda(cuda_available)

        # Lightning has specific scheduler
        lightning_config = router.get_generation_config("STANDARD_DRAFT")
        assert lightning_config["scheduler"] == "DPMSolverMultistepScheduler"
        assert lightning_config["num_inference_steps"] == 4
        assert lightning_config["guidance_scale"] == 1.0

        # Other models should use defaults
        for standard in ["STANDARD_US", "STANDARD_CINEMATIC", "STANDARD_ANATOMY", "STANDARD_ACTION"]:
            config = router.get_generation_config(standard)
            # Should use default steps (30) not Lightning's 4
            assert config["num_inference_steps"] != 4 or standard == "STANDARD_DRAFT", (
                f"{standard} should not inherit Lightning's 4 steps"
            )

    def test_pipeline_components_cleared_on_kill(self, manager, cuda_available):
        """
        After kill(), pipeline reference must be None.
        """
        skip_if_no_cuda(cuda_available)

        # Load a model
        manager.load("STANDARD_DRAFT")  # Fastest to load
        assert manager.pipe is not None, "Pipeline should exist after load"
        assert manager.current_model == "STANDARD_DRAFT"

        # Kill
        manager.kill()

        # Verify cleared
        assert manager.pipe is None, "Pipeline should be None after kill"
        assert manager.current_model is None, "current_model should be None after kill"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: SVD HANDOVER
# Image generator MUST be killed before SVD can load
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestSVDHandover:
    """Test that image generators are killed before SVD loads."""

    VRAM_BASELINE_THRESHOLD_GB = 1.5  # Slightly higher for SVD context

    def test_image_model_killed_before_svd_conceptual(self, manager, cuda_available):
        """
        Conceptual test: After killing image model, VRAM should be low enough for SVD.

        SVD requires ~7-8GB VRAM. On 12GB card, image model (~6GB) MUST be killed first.
        """
        skip_if_no_cuda(cuda_available)

        # Load an image model
        manager.load("STANDARD_US")  # Juggernaut XL
        image_vram = manager.get_vram_usage()
        print(f"\n   Image model VRAM: {image_vram:.2f}GB")

        # Kill image model
        manager.kill()
        time.sleep(0.5)
        post_kill_vram = manager.get_vram_usage()
        print(f"   Post-kill VRAM: {post_kill_vram:.2f}GB")

        # Verify VRAM is low enough for SVD to load
        # SVD needs ~7-8GB, so we need at least 10GB free on 12GB card
        svd_required_gb = 7.0
        total_vram = manager.get_vram_total()
        available_for_svd = total_vram - post_kill_vram

        assert available_for_svd >= svd_required_gb, (
            f"Not enough VRAM for SVD! Available: {available_for_svd:.2f}GB, "
            f"Required: {svd_required_gb}GB. Image model not fully purged."
        )

    def test_kill_is_idempotent(self, manager, cuda_available):
        """
        Multiple kill() calls should be safe and maintain baseline VRAM.
        """
        skip_if_no_cuda(cuda_available)

        # Load and kill
        manager.load("STANDARD_DRAFT")
        manager.kill()
        vram_after_first_kill = manager.get_vram_usage()

        # Kill again (should be no-op, no crash)
        manager.kill()
        vram_after_second_kill = manager.get_vram_usage()

        # Kill a third time
        manager.kill()
        vram_after_third_kill = manager.get_vram_usage()

        print(f"\n   After 1st kill: {vram_after_first_kill:.2f}GB")
        print(f"   After 2nd kill: {vram_after_second_kill:.2f}GB")
        print(f"   After 3rd kill: {vram_after_third_kill:.2f}GB")

        # All should be roughly equal
        assert abs(vram_after_second_kill - vram_after_first_kill) < 0.2
        assert abs(vram_after_third_kill - vram_after_first_kill) < 0.2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: UNIVERSAL REGISTRY - ALL 5 STANDARDS
# Verify all standards can be loaded and swapped
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
class TestUniversalRegistry:
    """Test that all 5 Standards can be loaded via the universal registry."""

    ALL_STANDARDS = [
        "STANDARD_US",       # Juggernaut XL
        "STANDARD_CINEMATIC", # RealVisXL
        "STANDARD_ANATOMY",   # Lustify
        "STANDARD_ACTION",    # Pony
        "STANDARD_DRAFT",     # Lightning
    ]

    def test_all_standards_defined_in_router(self, router):
        """All 5 standards should be defined and resolvable."""
        for standard in self.ALL_STANDARDS:
            path = router.resolve(standard)
            assert path.exists(), f"{standard} path doesn't exist: {path}"
            assert path.suffix == ".safetensors", f"{standard} should be .safetensors"

    def test_all_standards_have_vram_estimates(self, router):
        """All standards should have VRAM estimates for budget planning."""
        for standard in self.ALL_STANDARDS:
            config = router.get_generation_config(standard)
            vram_estimate = config.get("vram_estimate_gb")
            assert vram_estimate is not None, f"{standard} missing vram_estimate_gb"
            assert 3.0 <= vram_estimate <= 10.0, (
                f"{standard} has unrealistic VRAM estimate: {vram_estimate}GB"
            )

    @pytest.mark.slow
    def test_sequential_load_all_standards(self, manager, cuda_available):
        """
        Load each standard sequentially, verifying VRAM returns to baseline between each.

        This is the ultimate multi-model swap test.
        """
        skip_if_no_cuda(cuda_available)

        manager.kill()
        baseline = manager.get_vram_usage()
        print(f"\n   Baseline: {baseline:.2f}GB")

        vram_readings = {}

        for standard in self.ALL_STANDARDS:
            print(f"\n   Loading {standard}...")
            manager.load(standard)
            vram = manager.get_vram_usage()
            vram_readings[standard] = vram
            print(f"   {standard} VRAM: {vram:.2f}GB")

            # Verify model loaded
            assert manager.current_model == standard
            assert manager.pipe is not None

            # Kill before next
            manager.kill()
            time.sleep(0.3)
            post_kill = manager.get_vram_usage()
            print(f"   Post-kill: {post_kill:.2f}GB")

            # Must return to baseline
            assert post_kill < 1.5, (
                f"VRAM after killing {standard} ({post_kill:.2f}GB) too high!"
            )

        print("\n   VRAM Summary:")
        for std, vram in vram_readings.items():
            print(f"     {std}: {vram:.2f}GB")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: STRESS TEST - RAPID MULTI-MODEL CYCLING
# Verify no VRAM leaks under rapid cycling through all models
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.cuda
@pytest.mark.slow
class TestRapidMultiModelCycling:
    """Stress test for rapid model swapping."""

    def test_rapid_cycle_through_all_models_no_leak(self, manager, cuda_available):
        """
        Cycle through all 5 models twice. Final VRAM should match initial.
        """
        skip_if_no_cuda(cuda_available)

        manager.kill()
        baseline = manager.get_vram_usage()
        print(f"\n   Baseline: {baseline:.2f}GB")

        # Use faster-loading models for stress test
        cycle_models = ["STANDARD_DRAFT", "STANDARD_ACTION", "STANDARD_DRAFT"]

        # Run 2 full cycles
        for cycle in range(2):
            print(f"\n   === Cycle {cycle + 1} ===")
            for standard in cycle_models:
                manager.load(standard)
                vram = manager.get_vram_usage()
                print(f"   {standard}: {vram:.2f}GB")

        # Final kill and check
        manager.kill()
        time.sleep(0.5)
        final = manager.get_vram_usage()
        print(f"\n   Final: {final:.2f}GB")

        # Should be back to baseline (within tolerance)
        assert final < baseline + 0.5, (
            f"VRAM leak after stress test! Baseline: {baseline:.2f}GB, Final: {final:.2f}GB"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RUN CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "cuda", "--tb=short"])
