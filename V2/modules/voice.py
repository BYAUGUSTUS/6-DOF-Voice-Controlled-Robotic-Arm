import os
import json
import pyaudio
import vosk
import threading
import queue

class VoiceListener:
    def __init__(self, model_path="models/vosk-model-small-en-us-0.15", sample_rate=16000, chunk_size=4096):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Vosk model not found at path: '{model_path}'")
        
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.command_queue = queue.Queue()

    def start(self):
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        self.stream.start_stream()
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("[VOICE] Listening stream started.")

    def _listen_loop(self):
        while self.running:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        print(f"[VOICE RAW] Heard: \"{text}\"")
                        self.command_queue.put(text)
            except Exception as e:
                print(f"[VOICE ERROR] {e}")
                break

    def get_transcript(self, block=False, timeout=None):
        try:
            return self.command_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        print("[VOICE] Listening stream stopped.")