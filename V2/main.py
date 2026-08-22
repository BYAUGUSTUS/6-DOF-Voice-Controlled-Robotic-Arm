import os
import json
import time
import cv2
import threading

from modules.voice import VoiceListener
from modules.parser import parse_transcript
from modules.feedback import Speaker
from modules.vision import VisionDetector
from modules.kinematics import ArmKinematics
from modules.serial_comm import SerialArmBridge

CONFIG_FILE = "config.json"
SERIAL_PORT = "COM3"  # Change to your ESP32 COM port

class RoboticArmSystem:
    def __init__(self):
        self.speaker = Speaker()
        self.listener = VoiceListener(model_path="models/vosk-model-small-en-us-0.15")
        self.vision = VisionDetector(model_path="models/yolov8n.pt", camera_index=0)
        self.kinematics = ArmKinematics()
        self.arm = SerialArmBridge(port=SERIAL_PORT)

        self.config = self.load_config()
        self.running = False
        self.paused = False
        self.is_busy = False

        # Current physical arm state
        self.current_pose = self.config.get("presets", {}).get("home", {
            "base": 90, "shoulder": 90, "elbow": 90,
            "wrist_rot": 90, "wrist_tilt": 90, "gripper": 90
        })

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CONFIG ERROR] Failed to load config: {e}")
        return {"presets": {}, "calibration": {}}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
        print("[CONFIG] Presets saved to disk.")

    def move_to(self, base, shoulder, elbow, wrist_rot, wrist_tilt, gripper, delay_after=1.0):
        """Sends validated joint angles to ESP32."""
        if self.paused:
            print("[MOTION] Skipped - Arm is paused.")
            return False
        
        self.current_pose = {
            "base": base, "shoulder": shoulder, "elbow": elbow,
            "wrist_rot": wrist_rot, "wrist_tilt": wrist_tilt, "gripper": gripper
        }
        success = self.arm.send_angles(base, shoulder, elbow, wrist_rot, wrist_tilt, gripper)
        time.sleep(delay_after)
        return success

    def execute_pick_and_place(self, src_color: str, dst_color: str):
        self.is_busy = True
        self.speaker.say(f"Locating {src_color} and {dst_color}.")

        # Step 1: Detect Source
        src_coords = self.vision.get_location(src_color)
        if not src_coords:
            self.speaker.say(f"Could not find {src_color} block.")
            self.is_busy = False
            return

        # Calculate base angle for source
        src_x, src_y = self.kinematics.pixel_to_world(src_coords[0], src_coords[1])
        src_base = self.kinematics.solve_base_angle(src_x, src_y)

        # Approach and Grip Source
        self.speaker.say(f"Picking up {src_color}.")
        self.move_to(src_base, 90, 90, 90, 90, 30)       # Align Base, open gripper
        self.move_to(src_base, 60, 30, 90, 90, 30)       # Reach down
        self.move_to(src_base, 60, 30, 90, 90, 90)       # Close gripper
        self.move_to(src_base, 90, 90, 90, 90, 90)       # Lift object

        if self.paused:
            self.is_busy = False
            return

        # Step 2: Detect Destination
        dst_coords = self.vision.get_location(dst_color)
        if not dst_coords:
            self.speaker.say(f"Could not locate {dst_color} target. Aborting.")
            self.move_to(90, 90, 90, 90, 90, 90)
            self.is_busy = False
            return

        dst_x, dst_y = self.kinematics.pixel_to_world(dst_coords[0], dst_coords[1])
        dst_base = self.kinematics.solve_base_angle(dst_x, dst_y)

        # Move to Destination and Release
        self.speaker.say(f"Placing on {dst_color}.")
        self.move_to(dst_base, 90, 90, 90, 90, 90)      # Rotate to destination
        self.move_to(dst_base, 60, 30, 90, 90, 90)      # Lower
        self.move_to(dst_base, 60, 30, 90, 90, 30)      # Release
        self.move_to(dst_base, 90, 90, 90, 90, 90)      # Return up
        self.move_to(90, 90, 90, 90, 90, 90)            # Home

        self.speaker.say("Pick and place completed.")
        self.is_busy = False

    def execute_rotate(self, target_color: str, angle: int):
        self.is_busy = True
        coords = self.vision.get_location(target_color)
        if not coords:
            self.speaker.say(f"Target {target_color} not detected.")
            self.is_busy = False
            return

        x, y = self.kinematics.pixel_to_world(coords[0], coords[1])
        base = self.kinematics.solve_base_angle(x, y)

        self.speaker.say(f"Rotating {target_color} by {angle} degrees.")
        self.move_to(base, 60, 30, 90, 90, 90)           # Grip
        self.move_to(base, 60, 30, min(180, 90 + angle), 90, 90) # Rotate wrist
        self.move_to(base, 60, 30, min(180, 90 + angle), 90, 30) # Release
        self.move_to(90, 90, 90, 90, 90, 90)            # Reset
        self.speaker.say("Rotation complete.")
        self.is_busy = False

    def handle_command(self, action: str, params: dict):
        if action == "safety_stop":
            self.paused = True
            self.speaker.say("Emergency stop enabled. Actions frozen.")

        elif action == "safety_resume":
            self.paused = False
            self.speaker.say("System resumed.")

        elif action == "save_preset":
            name = params.get("name")
            self.config.setdefault("presets", {})[name] = self.current_pose
            self.save_config()
            self.speaker.say(f"Preset {name} saved successfully.")

        elif action == "load_preset":
            name = params.get("name")
            preset = self.config.get("presets", {}).get(name)
            if preset:
                self.speaker.say(f"Moving to preset {name}.")
                self.move_to(
                    preset["base"], preset["shoulder"], preset["elbow"],
                    preset["wrist_rot"], preset["wrist_tilt"], preset["gripper"]
                )
            else:
                self.speaker.say(f"Preset {name} not found.")

        elif action == "pick_place":
            if self.is_busy:
                self.speaker.say("Arm is currently executing a task.")
            else:
                threading.Thread(
                    target=self.execute_pick_and_place,
                    args=(params["src"], params["dst"]),
                    daemon=True
                ).start()

        elif action == "rotate":
            if self.is_busy:
                self.speaker.say("Arm is currently busy.")
            else:
                angle = int(params.get("angle", 90))
                threading.Thread(
                    target=self.execute_rotate,
                    args=(params["target"], angle),
                    daemon=True
                ).start()

        elif action == "shutdown":
            self.speaker.say("Shutting down the system.")
            self.running = False

    def run(self):
        print("[SYSTEM] Connecting to ESP32...")
        if not self.arm.connect():
            print("[WARN] Running in simulation mode (No hardware response).")

        self.vision.start()
        self.listener.start()
        self.running = True
        self.speaker.say("6-D O F Robotic Arm system online and ready.")

        try:
            while self.running:
                # 1. Vision GUI Render
                if self.vision.latest_frame is not None:
                    cv2.imshow("Robot Arm Vision Feed", self.vision.latest_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # 2. Check for Voice Commands
                transcript = self.listener.get_transcript(block=False)
                if transcript:
                    action, params = parse_transcript(transcript)
                    if action and action != "unknown":
                        self.handle_command(action, params)

                time.sleep(0.02)
        finally:
            self.listener.stop()
            self.vision.stop()
            self.arm.close()
            self.speaker.stop()
            cv2.destroyAllWindows()
            print("[SYSTEM] Offline.")

if __name__ == "__main__":
    system = RoboticArmSystem()
    system.run()