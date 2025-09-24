import time
import pyaudio
import json
import vosk
import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit
from ultralytics import YOLO
import cv2
import pyttsx3
import threading

# Debug Mode Toggle
DEBUG_MODE = True

# ServoKit Setup
kit = ServoKit(channels=16)

# Servo Pin Assignments
BASE_SERVO = 0
SHOULDER_SERVO = 1
ELBOW_SERVO = 2
WRIST_ROTATION_SERVO = 3
WRIST_TILT_SERVO = 4
GRIPPER_SERVO = 5

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# Vosk Voice Recognition Setup
model_path = "vosk-model-small-en-us-0.15"
samplerate = 16000
chunk_size = 1024
vosk_model = vosk.Model(model_path)
rec = vosk.KaldiRecognizer(vosk_model, samplerate)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=samplerate, input=True, frames_per_buffer=chunk_size)
stream.start_stream()

# TTS Engine Setup
engine = pyttsx3.init()

def speak(message):
    engine.say(message)
    engine.runAndWait()

# Debug Function
def debug_log(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

# Smooth Servo Movement
def smooth_move(servo_index, target_angle, delay=0.01):
    current_angle = kit.servo[servo_index].angle or 90
    step = 1 if target_angle > current_angle else -1
    for angle in range(int(current_angle), int(target_angle) + step, step):
        kit.servo[servo_index].angle = angle
        time.sleep(delay)

# Move Arm Function
def move_arm(base_angle, shoulder_angle, elbow_angle, wrist_rotate_angle, wrist_tilt_angle, gripper_angle):
    smooth_move(BASE_SERVO, base_angle)
    smooth_move(SHOULDER_SERVO, shoulder_angle)
    smooth_move(ELBOW_SERVO, elbow_angle)
    smooth_move(WRIST_ROTATION_SERVO, wrist_rotate_angle)
    smooth_move(WRIST_TILT_SERVO, wrist_tilt_angle)
    smooth_move(GRIPPER_SERVO, gripper_angle)
    debug_log(f"Arm Moved -> Base: {base_angle}, Shoulder: {shoulder_angle}, Elbow: {elbow_angle}, Wrist Rotate: {wrist_rotate_angle}, Wrist Tilt: {wrist_tilt_angle}, Gripper: {gripper_angle}")

# Voice Command Function
def get_command():
    debug_log("Listening for command...")
    while True:
        data = stream.read(chunk_size)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            command = result.get("text", "").lower()
            debug_log(f"Detected Command: {command}")
            return command

# Command Parsing
def parse_command(text):
    if text.startswith("save preset"):
        name = text.replace("save preset", "").strip()
        return "save_preset", {"name": name}
    elif text.startswith("load preset"):
        name = text.replace("load preset", "").strip()
        return "load_preset", {"name": name}

    COMMANDS = {
        "pick up {color1} and put over {color2}": "pick_place",
        "rotate {color} 90 degrees": "rotate",
        "place {color1} parallel to {color2}": "parallel",
    }
    for template, action in COMMANDS.items():
        words = template.replace("{color1}", "").replace("{color2}", "").replace("{color}", "").split()
        if all(word in text for word in words):
            for color1 in ["red", "blue"]:
                for color2 in ["red", "blue"]:
                    if color1 in text and color2 in text and color1 != color2:
                        return action, {"color1": color1, "color2": color2}
            if "red" in text or "blue" in text:
                color = "red" if "red" in text else "blue"
                return action, {"color": color}
    return None, {}

# YOLOv8 Object Detection Setup
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

# Object Detection Function
def detect_cubes():
    ret, frame = cap.read()
    results = model(frame)
    cubes = {}
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            x1, y1, x2, y2 = box.xyxy[0]
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            cubes[label] = center
    debug_log(f"Detected Cubes: {cubes}")
    return cubes

# Live Camera Feed Thread
def show_camera():
    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Live Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
camera_thread = threading.Thread(target=show_camera)
camera_thread.start()

# Load or Create Presets Config
CONFIG_FILE = "config.json"
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(presets):
    with open(CONFIG_FILE, "w") as f:
        json.dump(presets, f, indent=4)

motion_presets = load_config()

# Main Loop
while True:
    command = get_command()
    action, params = parse_command(command)

    if not action:
        speak("Sorry, I didn't understand.")
        continue

    if action == "save_preset":
        name = params["name"]
        motion_presets[name] = {
            "base": kit.servo[BASE_SERVO].angle or 90,
            "shoulder": kit.servo[SHOULDER_SERVO].angle or 90,
            "elbow": kit.servo[ELBOW_SERVO].angle or 90,
            "wrist_rotate": kit.servo[WRIST_ROTATION_SERVO].angle or 90,
            "wrist_tilt": kit.servo[WRIST_TILT_SERVO].angle or 90,
            "gripper": kit.servo[GRIPPER_SERVO].angle or 90
        }
        save_config(motion_presets)
        speak(f"Preset {name} saved.")
        continue

    if action == "load_preset":
        name = params["name"]
        if name in motion_presets:
            preset = motion_presets[name]
            move_arm(preset["base"], preset["shoulder"], preset["elbow"], preset["wrist_rotate"], preset["wrist_tilt"], preset["gripper"])
            speak(f"Loaded preset {name}.")
        else:
            speak(f"Preset {name} not found.")
        continue

    speak(f"Executing {action} for {params}")
    cubes = detect_cubes()

    if action == "pick_place":
        move_arm(90, 60, 30, 0, 0, 0)
        time.sleep(1)
        move_arm(90, 60, 30, 0, 0, 30)
        time.sleep(1)
        move_arm(120, 30, 0, 0, 0, 30)
        time.sleep(1)
        move_arm(120, 30, 0, 0, 0, 0)
        speak("Task Completed")

    elif action == "parallel":
        move_arm(90, 50, 20, 0, 0, 30)
        time.sleep(1)
        move_arm(90, 50, 20, 0, 0, 0)
        speak("Cubes placed parallel")

    elif action == "rotate":
        move_arm(90, 60, 30, 0, 0, 30)
        time.sleep(1)
        move_arm(90, 60, 30, 90, 0, 30)
        time.sleep(1)
        move_arm(90, 60, 30, 90, 0, 0)
        speak("Rotation complete")

    elif "exit" in command:
        speak("Shutting down")
        break

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
GPIO.cleanup()
cap.release()
cv2.destroyAllWindows()

#  __  __ _  ___   ___   _ _____ __  __       ____  _______     __
# |  \/  | || \ \ / / | | |___ /|  \/  |     |  _ \| ____\ \   / /
# | |\/| | || |\ V /| |_| | |_ \| |\/| |_____| | | |  _|  \ \ / / 
# | |  | |__   _| | |  _  |___) | |  | |_____| |_| | |___  \ V /  
# |_|  |_|  |_| |_| |_| |_|____/|_|  |_|     |____/|_____|  \_/   
                                                                
