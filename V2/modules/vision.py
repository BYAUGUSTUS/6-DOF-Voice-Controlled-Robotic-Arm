import cv2
import threading
import numpy as np
from ultralytics import YOLO

class VisionDetector:
    def __init__(self, model_path="models/yolov8n.pt", camera_index=0, conf_threshold=0.4):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index)
        self.conf_threshold = conf_threshold
        self.running = False
        self.lock = threading.Lock()
        
        # Stores target center coordinates: {"red": (u, v), "blue": (u, v)}
        self.detected_objects = {}
        self.latest_frame = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._process_stream, daemon=True)
        self.thread.start()
        print("[VISION] Camera and YOLO inference started.")

    def _get_dominant_color(self, crop):
        """Determines if the cropped box is predominantly red, blue, or other."""
        if crop.size == 0:
            return "unknown"
        
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        # Red has two HSV ranges
        lower_red1, upper_red1 = np.array([0, 70, 50]), np.array([10, 255, 255])
        lower_red2, upper_red2 = np.array([170, 70, 50]), np.array([180, 255, 255])
        
        # Blue range
        lower_blue, upper_blue = np.array([100, 70, 50]), np.array([130, 255, 255])
        
        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        red_count = cv2.countNonZero(mask_red)
        blue_count = cv2.countNonZero(mask_blue)
        
        if red_count > blue_count and red_count > 100:
            return "red"
        elif blue_count > red_count and blue_count > 100:
            return "blue"
        return "unknown"

    def _process_stream(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            results = self.model(frame, verbose=False, conf=self.conf_threshold)
            targets = {}

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    # Crop object to classify color tag
                    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                    color_tag = self._get_dominant_color(crop)
                    
                    if color_tag != "unknown":
                        targets[color_tag] = (cx, cy)
                        # Draw bounding box and label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"{color_tag} ({cx},{cy})", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            with self.lock:
                self.detected_objects = targets
                self.latest_frame = frame.copy()

    def get_location(self, label: str):
        with self.lock:
            return self.detected_objects.get(label.lower(), None)

    def get_all_locations(self):
        with self.lock:
            return dict(self.detected_objects)

    def stop(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        print("[VISION] Vision pipeline stopped.")