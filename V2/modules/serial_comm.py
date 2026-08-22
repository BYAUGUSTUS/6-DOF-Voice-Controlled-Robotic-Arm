import serial
import time
import sys

class SerialArmBridge:
    def __init__(self, port="COM3", baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2.0)  # Wait for ESP32 auto-reset
            print(f"[SERIAL] Connected to ESP32 on {self.port} at {self.baudrate} baud.")
            return True
        except serial.SerialException as e:
            print(f"[SERIAL ERROR] Failed to connect on {self.port}: {e}")
            self.ser = None
            return False

    def send_angles(self, base, shoulder, elbow, wrist_rot, wrist_tilt, gripper):
        if not self.ser or not self.ser.is_open:
            print("[SERIAL ERROR] Port not open. Cannot send angles.")
            return False

        # Constrain angles within safe 0 - 180 servo boundaries
        angles = [max(0, min(180, int(a))) for a in (base, shoulder, elbow, wrist_rot, wrist_tilt, gripper)]
        packet = f"<{','.join(map(str, angles))}>\n"

        try:
            self.ser.write(packet.encode('utf-8'))
            response = self.ser.readline().decode('utf-8').strip()
            return response == "ACK"
        except Exception as e:
            print(f"[SERIAL ERROR] Write error: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[SERIAL] Disconnected.")

# Standalone Test Script
if __name__ == "__main__":
    # Change COM3 to your actual ESP32 COM port on Windows (check Device Manager)
    TEST_PORT = "COM3"
    arm = SerialArmBridge(port=TEST_PORT)

    if arm.connect():
        try:
            print("Moving to Home Position (90, 90, 90, 90, 90, 90)...")
            arm.send_angles(90, 90, 90, 90, 90, 90)
            time.sleep(2)

            print("Testing Base Rotation (45 degrees)...")
            arm.send_angles(45, 90, 90, 90, 90, 90)
            time.sleep(2)

            print("Testing Gripper Open (30 degrees)...")
            arm.send_angles(45, 90, 90, 90, 90, 30)
            time.sleep(1)

            print("Returning to Home...")
            arm.send_angles(90, 90, 90, 90, 90, 90)
            time.sleep(2)
        finally:
            arm.close()