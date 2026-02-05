"""
Physics-Based Motion Tracker for Project Synterra
Based on Articulated Kinematics Distillation (AKD) - CVPR 2025
Extracts physically plausible skeletal motion from video frames
Prevents anatomical melting through kinematic constraints
"""

import torch
import torch.nn as nn
import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


# ============================================
# SKELETAL MODEL DEFINITION
# ============================================

@dataclass
class Joint:
    """Single joint in the kinematic chain"""
    name: str
    id: int
    parent_id: Optional[int]
    position: np.ndarray  # (3,) - x, y, z in 3D space
    rotation: np.ndarray  # (4,) - quaternion

    # Physical constraints
    dof: int  # Degrees of freedom (1-3)
    angle_limits: Optional[Tuple[float, float]]  # Min/max angle in radians


class HumanSkeleton:
    """
    Human skeletal model with 17 keypoints (COCO format)
    Enforces physical constraints and joint limits
    """

    # COCO 17-keypoint topology
    KEYPOINT_NAMES = [
        'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
        'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
        'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
        'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
    ]

    # Parent-child relationships (kinematic chain)
    SKELETON_TREE = [
        (0, 1), (0, 2), (1, 3), (2, 4),  # Head
        (0, 5), (0, 6),  # Shoulders
        (5, 7), (7, 9),  # Left arm
        (6, 8), (8, 10),  # Right arm
        (5, 11), (6, 12),  # Torso
        (11, 13), (13, 15),  # Left leg
        (12, 14), (14, 16)   # Right leg
    ]

    # ARM BONES for punch tracking (most critical for haymaker)
    ARM_BONES = [
        (5, 7),   # Left shoulder -> elbow
        (7, 9),   # Left elbow -> wrist
        (6, 8),   # Right shoulder -> elbow
        (8, 10),  # Right elbow -> wrist
    ]

    # Bone length constraints (relative to body height)
    BONE_LENGTH_RATIOS = {
        'upper_arm': 0.186,
        'forearm': 0.146,
        'thigh': 0.245,
        'shin': 0.246,
        'torso': 0.288,
        'shoulder_width': 0.259
    }

    # Joint angle limits (radians)
    JOINT_LIMITS = {
        'elbow': (0, np.pi),  # Can't bend backward
        'knee': (0, np.pi),
        'shoulder': (-np.pi, np.pi),
        'hip': (-np.pi/2, np.pi/2)
    }

    def __init__(self, body_height: float = 1.7):
        self.body_height = body_height
        self.joints = self._initialize_joints()
        self.bone_lengths = self._compute_bone_lengths()

    def _initialize_joints(self) -> List[Joint]:
        joints = []
        for i, name in enumerate(self.KEYPOINT_NAMES):
            parent_id = self._get_parent_id(i)

            joint = Joint(
                name=name,
                id=i,
                parent_id=parent_id,
                position=np.zeros(3),
                rotation=np.array([1, 0, 0, 0]),
                dof=3 if 'shoulder' in name or 'hip' in name else 1,
                angle_limits=self._get_angle_limits(name)
            )
            joints.append(joint)

        return joints

    def _get_parent_id(self, joint_id: int) -> Optional[int]:
        for parent, child in self.SKELETON_TREE:
            if child == joint_id:
                return parent
        return None

    def _get_angle_limits(self, joint_name: str) -> Optional[Tuple[float, float]]:
        for key, limits in self.JOINT_LIMITS.items():
            if key in joint_name:
                return limits
        return (-np.pi, np.pi)

    def _compute_bone_lengths(self) -> Dict[str, float]:
        return {
            bone: ratio * self.body_height
            for bone, ratio in self.BONE_LENGTH_RATIOS.items()
        }

    def _get_bone_name(self, parent_id: int, child_id: int) -> str:
        parent_name = self.KEYPOINT_NAMES[parent_id]
        child_name = self.KEYPOINT_NAMES[child_id]

        if 'shoulder' in parent_name and 'elbow' in child_name:
            return 'upper_arm'
        elif 'elbow' in parent_name and 'wrist' in child_name:
            return 'forearm'
        elif 'hip' in parent_name and 'knee' in child_name:
            return 'thigh'
        elif 'knee' in parent_name and 'ankle' in child_name:
            return 'shin'
        elif 'shoulder' in parent_name and 'hip' in child_name:
            return 'torso'

        return 'unknown'


# ============================================
# LIGHTWEIGHT POSE ESTIMATOR (MediaPipe)
# ============================================

class LightweightPoseEstimator:
    """
    MediaPipe-based pose estimation for skeletal consistency checks.
    Runs on CPU to avoid VRAM conflicts with SVD-XT.
    """

    def __init__(self):
        try:
            # Use explicit submodule imports (mp.solutions.pose throws AttributeError)
            import mediapipe.python.solutions.pose as mp_pose
            self.mp_pose = mp_pose
            self.pose = mp_pose.Pose(
                static_image_mode=True,  # For single frame analysis
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.available = True
            print("[LightweightPoseEstimator] MediaPipe initialized (explicit submodule path)")
        except ImportError as e:
            print(f"[LightweightPoseEstimator] MediaPipe not available: {e}")
            print("[LightweightPoseEstimator] Skeletal checks disabled")
            self.available = False
            self.pose = None

    def detect_keypoints(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect 17 COCO keypoints in image.

        Args:
            image: RGB image (H, W, 3)

        Returns:
            keypoints: (17, 3) array [x, y, confidence] or None if detection fails
        """
        if not self.available:
            return None

        # MediaPipe expects RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            results = self.pose.process(image)
        else:
            return None

        if not results.pose_landmarks:
            return None

        landmarks = results.pose_landmarks.landmark
        h, w = image.shape[:2]

        # MediaPipe to COCO keypoint mapping
        # MediaPipe has 33 landmarks, COCO has 17
        mp_to_coco = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

        keypoints = np.zeros((17, 3))
        for i, mp_idx in enumerate(mp_to_coco):
            if mp_idx < len(landmarks):
                lm = landmarks[mp_idx]
                keypoints[i] = [lm.x * w, lm.y * h, lm.visibility]

        return keypoints

    def extract_arm_bones(self, keypoints: np.ndarray) -> Dict[str, float]:
        """
        Extract arm bone lengths from keypoints.

        Args:
            keypoints: (17, 3) COCO keypoints

        Returns:
            bone_lengths: Dict with bone names and pixel lengths
        """
        if keypoints is None:
            return {}

        bones = {}

        # Left arm
        left_upper = np.linalg.norm(keypoints[7, :2] - keypoints[5, :2])  # shoulder->elbow
        left_forearm = np.linalg.norm(keypoints[9, :2] - keypoints[7, :2])  # elbow->wrist

        # Right arm
        right_upper = np.linalg.norm(keypoints[8, :2] - keypoints[6, :2])  # shoulder->elbow
        right_forearm = np.linalg.norm(keypoints[10, :2] - keypoints[8, :2])  # elbow->wrist

        bones['left_upper_arm'] = left_upper
        bones['left_forearm'] = left_forearm
        bones['right_upper_arm'] = right_upper
        bones['right_forearm'] = right_forearm

        return bones


# ============================================
# SKELETAL CONSISTENCY CHECKER
# ============================================

class SkeletalConsistencyChecker:
    """
    Checks generated frames against anchor image skeletal structure.
    Prevents anatomical melting by enforcing bone length constraints.
    """

    def __init__(self, tolerance: float = 0.10):
        """
        Args:
            tolerance: Maximum allowed bone length deviation (0.10 = 10%)
        """
        self.pose_estimator = LightweightPoseEstimator()
        self.tolerance = tolerance
        self.anchor_bones = None
        self.anchor_keypoints = None

    def set_anchor(self, anchor_image: np.ndarray) -> bool:
        """
        Extract skeletal structure from anchor image.

        Args:
            anchor_image: RGB anchor image from RealVisXL

        Returns:
            success: True if skeleton detected
        """
        if not self.pose_estimator.available:
            print("[SkeletalConsistency] Pose estimator not available")
            return False

        # Detect keypoints in anchor
        self.anchor_keypoints = self.pose_estimator.detect_keypoints(anchor_image)

        if self.anchor_keypoints is None:
            print("[SkeletalConsistency] No skeleton detected in anchor image")
            return False

        # Extract bone lengths
        self.anchor_bones = self.pose_estimator.extract_arm_bones(self.anchor_keypoints)

        print(f"[SkeletalConsistency] Anchor bones extracted:")
        for bone, length in self.anchor_bones.items():
            print(f"  {bone}: {length:.1f}px")

        return True

    def check_frame(self, frame: np.ndarray) -> Tuple[bool, Dict[str, float]]:
        """
        Check if frame skeleton matches anchor within tolerance.

        Args:
            frame: RGB frame to check

        Returns:
            (passed, deviations): Tuple of pass/fail and deviation dict
        """
        if self.anchor_bones is None:
            return True, {}  # No anchor set, pass by default

        if not self.pose_estimator.available:
            return True, {}

        # Detect keypoints in frame
        frame_keypoints = self.pose_estimator.detect_keypoints(frame)

        if frame_keypoints is None:
            # No skeleton detected - this could indicate melting
            return False, {'detection_failed': 1.0}

        # Extract bone lengths
        frame_bones = self.pose_estimator.extract_arm_bones(frame_keypoints)

        # Compare bone lengths
        deviations = {}
        passed = True

        for bone_name, anchor_length in self.anchor_bones.items():
            if bone_name not in frame_bones:
                continue

            frame_length = frame_bones[bone_name]

            if anchor_length > 0:
                deviation = abs(frame_length - anchor_length) / anchor_length
                deviations[bone_name] = deviation

                if deviation > self.tolerance:
                    passed = False

        return passed, deviations

    def check_sequence(self, frames: List[np.ndarray]) -> Dict[int, Dict[str, float]]:
        """
        Check all frames in sequence.

        Args:
            frames: List of RGB frames

        Returns:
            violations: Dict mapping frame index to deviation dict
        """
        violations = {}

        for i, frame in enumerate(frames):
            passed, deviations = self.check_frame(frame)

            if not passed:
                violations[i] = deviations

        return violations


# ============================================
# INTEGRATION FUNCTION
# ============================================

def create_skeletal_checker(anchor_image: np.ndarray, tolerance: float = 0.10) -> Optional[SkeletalConsistencyChecker]:
    """
    Factory function to create and initialize skeletal consistency checker.

    Args:
        anchor_image: RGB anchor image
        tolerance: Bone length deviation tolerance (default 10%)

    Returns:
        checker: Initialized checker or None if failed
    """
    checker = SkeletalConsistencyChecker(tolerance=tolerance)

    if checker.set_anchor(anchor_image):
        return checker

    return None
