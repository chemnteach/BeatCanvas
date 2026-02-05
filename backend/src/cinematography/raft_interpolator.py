"""
RAFT-based Frame Interpolation for Project Synterra
No compilation required - uses torchvision.models.optical_flow
Compatible with WSL2/Ubuntu + RTX 3080/4090
"""

import torch
import torch.nn.functional as F
import numpy as np
from torchvision.models.optical_flow import raft_large, Raft_Large_Weights
from torchvision.models.optical_flow import raft_small, Raft_Small_Weights
from torchvision.transforms import functional as TF
from torchvision.utils import flow_to_image
import cv2
from pathlib import Path


class RAFTInterpolator:
    """
    Drop-in replacement for OpenCV optical flow methods.
    Handles anatomical preservation during high-velocity motion.
    """

    def __init__(self, model_size='large', device=None):
        """
        Args:
            model_size: 'large' (best quality) or 'small' (faster)
            device: torch.device or None (auto-detect CUDA)
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        print(f"[RAFTInterpolator] Initializing {model_size} model on {self.device}")

        if model_size == 'large':
            weights = Raft_Large_Weights.DEFAULT
            self.model = raft_large(weights=weights, progress=True).to(self.device)
        else:
            weights = Raft_Small_Weights.DEFAULT
            self.model = raft_small(weights=weights, progress=True).to(self.device)

        self.model.eval()
        print("[RAFTInterpolator] Model ready")

    def preprocess_frame(self, frame):
        """
        Convert numpy BGR frame (H, W, 3) to torch tensor (1, 3, H, W)
        Args:
            frame: numpy array (H, W, 3) in BGR format (OpenCV standard)
        Returns:
            torch.Tensor: (1, 3, H, W) normalized to [-1, 1]
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to torch tensor and normalize
        frame_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float()  # (3, H, W)
        frame_tensor = frame_tensor.unsqueeze(0)  # (1, 3, H, W)

        # Normalize to [-1, 1] as expected by RAFT
        frame_tensor = (frame_tensor / 255.0) * 2.0 - 1.0

        return frame_tensor.to(self.device)

    def postprocess_frame(self, frame_tensor):
        """
        Convert torch tensor back to numpy BGR frame
        Args:
            frame_tensor: torch.Tensor (1, 3, H, W) in [-1, 1]
        Returns:
            numpy array (H, W, 3) in BGR format
        """
        # Denormalize from [-1, 1] to [0, 255]
        frame_np = ((frame_tensor[0].cpu() + 1.0) / 2.0 * 255.0).clamp(0, 255).byte()
        frame_np = frame_np.permute(1, 2, 0).numpy()  # (H, W, 3)

        # Convert RGB to BGR
        frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        return frame_bgr

    @torch.no_grad()
    def compute_flow(self, frame1, frame2, iters=20):
        """
        Compute optical flow between two frames.

        Args:
            frame1: numpy array (H, W, 3) BGR
            frame2: numpy array (H, W, 3) BGR
            iters: RAFT refinement iterations (default 20, range 12-32)

        Returns:
            flow: numpy array (H, W, 2) - dx, dy displacement for each pixel
        """
        img1 = self.preprocess_frame(frame1)
        img2 = self.preprocess_frame(frame2)

        # RAFT returns list of flow predictions (one per iteration)
        # We want the final refined prediction
        flow_predictions = self.model(img1, img2, num_flow_updates=iters)
        flow = flow_predictions[-1]  # (1, 2, H, W)

        # Convert to numpy (H, W, 2)
        flow_np = flow[0].permute(1, 2, 0).cpu().numpy()
        return flow_np

    def warp_frame(self, frame, flow):
        """
        Warp a frame using optical flow.

        Args:
            frame: numpy array (H, W, 3) BGR
            flow: numpy array (H, W, 2) - flow field

        Returns:
            warped_frame: numpy array (H, W, 3) BGR
        """
        h, w = frame.shape[:2]

        # Create coordinate grid
        grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)

        # Apply flow to get destination coordinates
        map_x = (grid_x + flow[:, :, 0]).astype(np.float32)
        map_y = (grid_y + flow[:, :, 1]).astype(np.float32)

        # Remap using OpenCV (handles boundary conditions)
        warped = cv2.remap(frame, map_x, map_y,
                          interpolation=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)
        return warped

    def detect_occlusions(self, flow_forward, flow_backward, threshold=1.0):
        """
        Detect occluded regions using forward-backward consistency check.

        Args:
            flow_forward: (H, W, 2)
            flow_backward: (H, W, 2)
            threshold: consistency threshold in pixels

        Returns:
            occlusion_mask: (H, W) boolean array, True = occluded
        """
        h, w = flow_forward.shape[:2]
        grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)

        # Warp backward flow using forward flow
        map_x = (grid_x + flow_forward[:, :, 0]).astype(np.float32)
        map_y = (grid_y + flow_forward[:, :, 1]).astype(np.float32)

        warped_flow_bw = cv2.remap(flow_backward, map_x, map_y,
                                     interpolation=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=0)

        # Check consistency: flow_fwd + warped_flow_bwd should be ~0
        flow_diff = flow_forward + warped_flow_bw
        consistency_error = np.sqrt(np.sum(flow_diff**2, axis=2))

        occlusion_mask = consistency_error > threshold
        return occlusion_mask

    def interpolate_frames(self, frame1, frame2, num_intermediate=1,
                          occlusion_aware=True, edge_damping=True):
        """
        Generate intermediate frames between frame1 and frame2.

        Args:
            frame1: numpy array (H, W, 3) BGR
            frame2: numpy array (H, W, 3) BGR
            num_intermediate: number of frames to generate (1 = 2x, 2 = 3x, etc.)
            occlusion_aware: use forward-backward consistency check
            edge_damping: reduce flow magnitude near frame boundaries

        Returns:
            list of interpolated frames (numpy arrays)
        """
        # Compute bidirectional flow (AKD: increased iterations 20→32 for skeletal precision)
        flow_forward = self.compute_flow(frame1, frame2, iters=32)
        flow_backward = self.compute_flow(frame2, frame1, iters=32)

        # Optional: detect occlusions
        if occlusion_aware:
            occlusion_mask = self.detect_occlusions(flow_forward, flow_backward, threshold=1.0)
        else:
            occlusion_mask = None

        # Optional: edge damping for boundary artifacts
        if edge_damping:
            flow_forward = self._apply_edge_damping(flow_forward)
            flow_backward = self._apply_edge_damping(flow_backward)

        interpolated_frames = []

        for i in range(1, num_intermediate + 1):
            t = i / (num_intermediate + 1)  # interpolation coefficient

            # Scale flows by t and (1-t)
            flow_fwd_scaled = flow_forward * t
            flow_bwd_scaled = flow_backward * (1 - t)

            # Warp both frames
            warped_frame1 = self.warp_frame(frame1, flow_fwd_scaled)
            warped_frame2 = self.warp_frame(frame2, flow_bwd_scaled)

            # Blend warped frames
            if occlusion_mask is not None:
                # In occluded regions, favor the non-occluded frame
                alpha = np.ones_like(occlusion_mask, dtype=np.float32) * t
                alpha[occlusion_mask] = 1.0 if t > 0.5 else 0.0
                alpha = alpha[:, :, np.newaxis]
            else:
                alpha = t

            interpolated = (1 - alpha) * warped_frame1 + alpha * warped_frame2
            interpolated = interpolated.astype(np.uint8)

            interpolated_frames.append(interpolated)

        return interpolated_frames

    def _apply_edge_damping(self, flow, boundary_width=20, damping_factor=0.5):
        """
        Reduce flow magnitude near frame boundaries to prevent liquid artifacts.

        Args:
            flow: (H, W, 2)
            boundary_width: pixels from edge to apply damping
            damping_factor: multiplier for boundary flow (0.5 = half strength)

        Returns:
            damped_flow: (H, W, 2)
        """
        h, w = flow.shape[:2]
        damping_mask = np.ones((h, w), dtype=np.float32)

        # Top edge
        damping_mask[:boundary_width, :] *= damping_factor
        # Bottom edge
        damping_mask[-boundary_width:, :] *= damping_factor
        # Left edge
        damping_mask[:, :boundary_width] *= damping_factor
        # Right edge
        damping_mask[:, -boundary_width:] *= damping_factor

        flow = flow.copy()
        flow[:, :, 0] *= damping_mask
        flow[:, :, 1] *= damping_mask

        return flow

    def process_video_sequence(self, frames, target_fps_multiplier=2.4):
        """
        Process a sequence of frames (e.g., 25 frames from SVD-XT) to target FPS.

        Args:
            frames: list of numpy arrays (H, W, 3) BGR
            target_fps_multiplier: 2.4 for 25fps -> 60fps

        Returns:
            interpolated_sequence: list of frames at target FPS
        """
        num_intermediate = int(target_fps_multiplier) - 1  # 2.4x ≈ 2, so add 1 frame between each

        output_sequence = [frames[0]]  # Start with first frame

        for i in range(len(frames) - 1):
            print(f"[RAFTInterpolator] Processing frames {i} -> {i+1}")

            intermediate_frames = self.interpolate_frames(
                frames[i],
                frames[i + 1],
                num_intermediate=num_intermediate,
                occlusion_aware=True,
                edge_damping=True
            )

            output_sequence.extend(intermediate_frames)
            output_sequence.append(frames[i + 1])

        return output_sequence
