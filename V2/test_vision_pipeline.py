import time
import cv2
from modules.vision import VisionDetector
from modules.kinematics import ArmKinematics

def main():
    vision = VisionDetector(model_path="models/yolov8n.pt", camera_index=0)
    kinematics = ArmKinematics()
    vision.start()
    
    print("[TEST] Vision running. Hold a RED or BLUE object in front of the camera. Press 'q' on the preview window to exit.")
    
    try:
        while True:
            if vision.latest_frame is not None:
                cv2.imshow("Robotic Arm Vision", vision.latest_frame)
                
            objects = vision.get_all_locations()
            for color, (u, v) in objects.items():
                x_mm, y_mm = kinematics.pixel_to_world(u, v)
                base_angle = kinematics.solve_base_angle(x_mm, y_mm)
                print(f"[{color.upper()}] Pixel: ({u}, {v}) -> World: ({x_mm:.1f} mm, {y_mm:.1f} mm) -> Target Base Angle: {base_angle:.1f}°")
                
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
            time.sleep(0.1)
    finally:
        vision.stop()

if __name__ == "__main__":
    main()