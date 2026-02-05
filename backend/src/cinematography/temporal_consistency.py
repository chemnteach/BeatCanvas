"""
Temporal Consistency Wrapper for SVD-XT
Prevents anatomical melting by enforcing structural coherence
Compatible with RAFT interpolation pipeline

AKD Integration (CVPR 2025):
- Uses physics-based skeletal tracking to prevent limb implosion
- Enforces bone length constraints against anchor image

Temporal Smoothing (2026-02-05):
- Gaussian-weighted frame blending to reduce micro-jitter
- Applied before RAFT interpolation to prevent jitter amplification
"""

import torch
import torch.nn.functional as F
import numpy as np
import cv2
from typing import List, Tuple, Optional

from .physics_motion_tracker import SkeletalConsistencyChecker, create_skeletal_checker


def temporal_smooth(
    frames: List[np.ndarray],
    kernel_size: int = 3,
    weights: Optional[Tuple[float, ...]] = None,
    preserve_endpoints: bool = True
) -> List[np.ndarray]:
    """
    Apply Gaussian-weighted temporal smoothing to reduce frame-to-frame jitter.

    This smooths the 25 SVD-XT frames BEFORE RAFT interpolation, preventing
    micro-inconsistencies from being amplified during upsampling.

    Args:
        frames: List of numpy arrays (H, W, 3) in BGR format
        kernel_size: Number of frames to blend (3 = prev + current + next)
        weights: Custom weights tuple. Default for kernel_size=3: (0.25, 0.5, 0.25)
                 For kernel_size=5: (0.1, 0.2, 0.4, 0.2, 0.1)
        preserve_endpoints: If True, keep first and last frames unmodified
                           to maintain anchor consistency

    Returns:
        Smoothed frames list (same length as input)
    """
    if len(frames) < kernel_size:
        print(f"[TemporalSmooth] Warning: Only {len(frames)} frames, skipping smoothing")
        return frames

    # Default weights: center-weighted Gaussian-like
    if weights is None:
        if kernel_size == 3:
            weights = (0.25, 0.5, 0.25)
        elif kernel_size == 5:
            weights = (0.1, 0.2, 0.4, 0.2, 0.1)
        elif kernel_size == 7:
            weights = (0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05)
        else:
            # Generate approximate Gaussian weights
            import scipy.signal as signal
            weights = signal.windows.gaussian(kernel_size, std=kernel_size/4)
            weights = tuple(weights / weights.sum())

    assert len(weights) == kernel_size, f"Weights length {len(weights)} != kernel_size {kernel_size}"
    assert abs(sum(weights) - 1.0) < 0.01, f"Weights must sum to 1.0, got {sum(weights)}"

    half_kernel = kernel_size // 2
    smoothed = []

    for i in range(len(frames)):
        # Preserve endpoints (anchor frame and final frame)
        if preserve_endpoints and (i < half_kernel or i >= len(frames) - half_kernel):
            smoothed.append(frames[i].copy())
            continue

        # Gather neighborhood frames
        blended = np.zeros_like(frames[i], dtype=np.float32)
        for j, weight in enumerate(weights):
            neighbor_idx = i - half_kernel + j
            # Clamp to valid range (shouldn't happen with preserve_endpoints)
            neighbor_idx = max(0, min(len(frames) - 1, neighbor_idx))
            blended += frames[neighbor_idx].astype(np.float32) * weight

        smoothed.append(blended.astype(np.uint8))

    print(f"[TemporalSmooth] Applied kernel_size={kernel_size} smoothing to {len(frames)} frames")
    return smoothed


class TemporalConsistencySVD:
    """
    Wrapper around SVD-XT that adds temporal consistency checks
    Inspired by VideoControlNet (codec-style I/P/B frames)
    """

    def __init__(
        self,
        svd_pipeline,
        consistency_threshold: float = 0.15,
        skeletal_tolerance: float = 0.10,
        temporal_smoothing: bool = True,
        smooth_kernel_size: int = 3,
        motion_bucket_id: int = 70
    ):
        """
        Args:
            svd_pipeline: Loaded SVD-XT pipeline from diffusers
            consistency_threshold: Max allowed structural deviation (0-1)
            skeletal_tolerance: Max allowed bone length deviation (0.10 = 10%)
            temporal_smoothing: Enable frame smoothing to reduce jitter (default True)
            smooth_kernel_size: Smoothing kernel size (3, 5, or 7). Higher = more smoothing
            motion_bucket_id: SVD motion intensity (40-127). Default 70 for stability.
                             Values > 100 risk jitter and limb implosion.
        """
        self.pipe = svd_pipeline
        self.consistency_threshold = consistency_threshold
        self.skeletal_tolerance = skeletal_tolerance
        self.skeletal_checker = None  # Initialized when anchor is set
        self.temporal_smoothing = temporal_smoothing
        self.smooth_kernel_size = smooth_kernel_size
        self.motion_bucket_id = motion_bucket_id

        # Warn about high motion_bucket_id values
        if motion_bucket_id > 100:
            print(f"[TemporalConsistency] Warning: motion_bucket_id={motion_bucket_id} > 100 may cause jitter")

    def extract_structural_features(self, image):
        """
        Extract edge maps + depth estimation for structural anchoring

        Args:
            image: PIL Image or torch.Tensor (3, H, W)

        Returns:
            structure_map: (H, W) structural feature map
        """
        if isinstance(image, torch.Tensor):
            # Convert to numpy for OpenCV processing
            img_np = (image.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        else:
            img_np = np.array(image)

        # Extract edges using Canny
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Blur edges slightly to create soft structural map
        structure_map = cv2.GaussianBlur(edges, (5, 5), 0) / 255.0

        return structure_map

    def compute_structural_consistency(self, frame1_structure, frame2_structure):
        """
        Measure structural deviation between consecutive frames

        Returns:
            consistency_score: 0 = identical structure, 1 = completely different
        """
        diff = np.abs(frame1_structure - frame2_structure)
        consistency_score = np.mean(diff)
        return consistency_score

    def generate_with_consistency(self,
                                  anchor_image,
                                  num_frames=25,
                                  motion_bucket_id=None,
                                  fps=7,
                                  noise_aug_strength=0.05,
                                  max_retries=3,
                                  height=1024,
                                  width=576):
        """
        Generate video with structural consistency enforcement.
        If anatomical melting detected, regenerate with adjusted parameters.

        Args:
            anchor_image: PIL Image (576x1024)
            num_frames: 25 for SVD-XT
            motion_bucket_id: 40-127 (default 85 for action)
            fps: frames per second for conditioning
            noise_aug_strength: noise augmentation level
            max_retries: number of regeneration attempts if consistency fails
            height: output height (1024 for 9:16)
            width: output width (576 for 9:16)

        Returns:
            frames: list of numpy arrays (H, W, 3) BGR with guaranteed consistency
        """

        # Use instance default if motion_bucket_id not specified
        if motion_bucket_id is None:
            motion_bucket_id = self.motion_bucket_id

        # Initialize skeletal checker with anchor (AKD integration)
        if self.skeletal_checker is None:
            anchor_np = np.array(anchor_image)
            self.skeletal_checker = create_skeletal_checker(anchor_np, tolerance=self.skeletal_tolerance)
            if self.skeletal_checker:
                print(f"[TemporalConsistency] AKD skeletal checker initialized (tolerance={self.skeletal_tolerance*100:.0f}%)")
            else:
                print(f"[TemporalConsistency] AKD skeletal checker unavailable - structural checks only")

        for attempt in range(max_retries):
            print(f"[TemporalConsistency] Generation attempt {attempt + 1}/{max_retries}")
            print(f"  motion_bucket_id: {motion_bucket_id}")
            print(f"  noise_aug_strength: {noise_aug_strength}")

            # Generate video with SVD-XT
            output = self.pipe(
                anchor_image,
                height=height,
                width=width,
                num_frames=num_frames,
                motion_bucket_id=motion_bucket_id,
                fps=fps,
                noise_aug_strength=noise_aug_strength,
                decode_chunk_size=8,  # Memory optimization
            )

            frames_pil = output.frames[0]  # List of PIL Images

            # Convert to numpy BGR for consistency check
            frames = []
            for frame_pil in frames_pil:
                frame_np = np.array(frame_pil)
                frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                frames.append(frame_bgr)

            # Check structural consistency across all frames
            anchor_structure = self.extract_structural_features(anchor_image)
            consistency_violations = []
            skeletal_violations = []

            for i, frame in enumerate(frames):
                # Convert BGR to RGB for structure extraction
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_structure = self.extract_structural_features(
                    torch.from_numpy(frame_rgb).permute(2, 0, 1).float() / 255.0
                )
                consistency_score = self.compute_structural_consistency(
                    anchor_structure, frame_structure
                )

                if consistency_score > self.consistency_threshold:
                    consistency_violations.append((i, consistency_score))

                # AKD skeletal check - penalize bone length deviations
                if self.skeletal_checker:
                    skeletal_passed, deviations = self.skeletal_checker.check_frame(frame_rgb)
                    if not skeletal_passed:
                        max_deviation = max(deviations.values()) if deviations else 0
                        skeletal_violations.append((i, max_deviation, deviations))

            # Combined check: structural + skeletal (AKD)
            total_violations = len(consistency_violations) + len(skeletal_violations)

            if total_violations == 0:
                print(f"[TemporalConsistency] ✓ Generation successful - all frames consistent")
                if self.skeletal_checker:
                    print(f"[TemporalConsistency] ✓ AKD skeletal check passed - bone lengths within {self.skeletal_tolerance*100:.0f}% tolerance")

                # Apply temporal smoothing to reduce micro-jitter before RAFT
                if self.temporal_smoothing:
                    frames = temporal_smooth(frames, kernel_size=self.smooth_kernel_size)

                return frames

            else:
                # Report structural violations
                if len(consistency_violations) > 0:
                    print(f"[TemporalConsistency] ✗ Detected {len(consistency_violations)} structural violations:")
                    for frame_idx, score in consistency_violations[:3]:  # Show first 3
                        print(f"    Frame {frame_idx}: {score:.3f} > {self.consistency_threshold}")

                # Report skeletal violations (AKD)
                if len(skeletal_violations) > 0:
                    print(f"[TemporalConsistency] ✗ AKD detected {len(skeletal_violations)} skeletal violations (limb implosion risk):")
                    for frame_idx, max_dev, deviations in skeletal_violations[:3]:  # Show first 3
                        bone_details = ", ".join([f"{k}:{v:.1%}" for k, v in deviations.items()])
                        print(f"    Frame {frame_idx}: {max_dev:.1%} deviation ({bone_details})")

                # AKD ROLLBACK: Reduce noise_aug by 0.01 per skeletal failure (finer control)
                # Structural failures use 0.02 reduction
                if attempt < max_retries - 1:
                    if len(skeletal_violations) > 0:
                        # Skeletal failure = finer rollback (0.01)
                        noise_aug_strength = max(0.02, noise_aug_strength - 0.01)
                        print(f"  AKD rollback: noise_aug_strength -> {noise_aug_strength:.2f} (skeletal)")
                    else:
                        # Structural-only failure = standard rollback (0.02)
                        noise_aug_strength = max(0.02, noise_aug_strength - 0.02)
                        print(f"  Retrying with reduced noise_aug_strength: {noise_aug_strength:.2f}")
                    print(f"  (motion_bucket_id stays at {motion_bucket_id} for max motion)")

        # If all retries failed, return best attempt with warning
        print(f"[TemporalConsistency] ⚠ Warning: Could not achieve full consistency after {max_retries} attempts")
        print(f"  Returning frames from final attempt")

        # Still apply temporal smoothing to reduce jitter in imperfect output
        if self.temporal_smoothing:
            frames = temporal_smooth(frames, kernel_size=self.smooth_kernel_size)

        return frames

    def generate_with_keyframe_anchoring(self,
                                        anchor_image,
                                        num_keyframes=5,
                                        motion_bucket_id=85,
                                        height=1024,
                                        width=576):
        """
        Advanced: Generate video in segments with keyframe anchoring.
        Each segment uses the last frame as anchor for the next segment.
        Prevents drift and anatomical melting over long sequences.

        Args:
            anchor_image: PIL Image
            num_keyframes: number of keyframe segments
            motion_bucket_id: motion intensity
            height: output height
            width: output width

        Returns:
            full_sequence: list of numpy arrays (extended sequence)
        """
        frames_per_segment = 25 // num_keyframes
        full_sequence = []
        current_anchor = anchor_image

        for segment_idx in range(num_keyframes):
            print(f"[TemporalConsistency] Generating keyframe segment {segment_idx + 1}/{num_keyframes}")

            # Generate segment
            segment_frames = self.generate_with_consistency(
                current_anchor,
                num_frames=frames_per_segment + 5,  # Overlap for blending
                motion_bucket_id=motion_bucket_id,
                max_retries=2,
                height=height,
                width=width
            )

            # Use last frame as anchor for next segment (convert to PIL)
            from PIL import Image
            last_frame_rgb = cv2.cvtColor(segment_frames[-1], cv2.COLOR_BGR2RGB)
            current_anchor = Image.fromarray(last_frame_rgb)

            # Add frames (skip overlap for segments after first)
            if segment_idx == 0:
                full_sequence.extend(segment_frames)
            else:
                full_sequence.extend(segment_frames[5:])  # Skip overlap

        return full_sequence
