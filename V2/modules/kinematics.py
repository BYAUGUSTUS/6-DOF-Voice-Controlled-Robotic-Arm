import cv2
import numpy as np
import math

class ArmKinematics:
    def __init__(self):
        # Default 4-point homography calibration (Pixel -> Millimeters relative to arm base)
        # Update these values during workspace calibration
        self.src_pts = np.float32([
            [100, 100],   # Top-left pixel
            [540, 100],   # Top-right pixel
            [540, 420],   # Bottom-right pixel
            [100, 420]    # Bottom-left pixel
        ])
        
        self.dst_pts = np.float32([
            [-100, 250],  # Top-left workspace (X mm, Y mm)
            [100, 250],   # Top-right workspace
            [100, 120],   # Bottom-right workspace
            [-100, 120]   # Bottom-left workspace
        ])
        
        self.homography_matrix = cv2.getPerspectiveTransform(self.src_pts, self.dst_pts)

    def update_calibration(self, src_pixels, dst_world_mm):
        """Recalculates the homography transformation matrix."""
        self.src_pts = np.float32(src_pixels)
        self.dst_pts = np.float32(dst_world_mm)
        self.homography_matrix = cv2.getPerspectiveTransform(self.src_pts, self.dst_pts)

    def pixel_to_world(self, u: int, v: int):
        """Converts pixel coordinate (u, v) to physical table coordinate (X, Y) in mm."""
        pt = np.array([[[u, v]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self.homography_matrix)
        x_mm, y_mm = transformed[0][0]
        return float(x_mm), float(y_mm)

    def solve_base_angle(self, x_mm: float, y_mm: float):
        """
        Calculates the required Base servo angle (0-180 deg) where:
        - 90 degrees points straight forward along the +Y axis.
        """
        # Angle relative to positive Y axis
        angle_rad = math.atan2(x_mm, y_mm)
        angle_deg = 90.0 + math.degrees(angle_rad)
        return max(0.0, min(180.0, angle_deg))