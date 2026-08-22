import pyttsx3
import threading
import queue

class Speaker:
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        # Initialize engine inside the dedicated worker thread (avoids COM threading bugs on Windows)
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        while self.running:
            try:
                text = self.queue.get(timeout=0.5)
                if text is None:
                    break
                engine.say(text)
                engine.runAndWait()
                self.queue.task_done()
            except queue.Empty:
                continue

    def say(self, message: str):
        print(f"[TTS] {message}")
        self.queue.put(message)

    def stop(self):
        self.running = False
        self.queue.put(None)