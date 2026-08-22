import time
from modules.voice import VoiceListener
from modules.parser import parse_transcript
from modules.feedback import Speaker

def main():
    speaker = Speaker()
    speaker.say("Voice system initializing.")
    
    # Adjust path if your folder is named differently inside models/
    listener = VoiceListener(model_path="models/vosk-model-small-en-us-0.15")
    listener.start()
    
    speaker.say("I am ready for commands.")
    print("\n--- Try saying: 'pick up red and put over blue', 'stop', 'save preset home', or 'exit' ---")

    try:
        while True:
            text = listener.get_transcript(block=True, timeout=1.0)
            if text:
                action, params = parse_transcript(text)
                print(f"[PARSER MATCH] Action: {action} | Params: {params}")

                if action == "safety_stop":
                    speaker.say("Emergency stop activated.")
                elif action == "safety_resume":
                    speaker.say("Resuming operations.")
                elif action == "pick_place":
                    speaker.say(f"Picking {params['src']} and placing on {params['dst']}")
                elif action == "save_preset":
                    speaker.say(f"Saving preset {params['name']}")
                elif action == "load_preset":
                    speaker.say(f"Loading preset {params['name']}")
                elif action == "shutdown":
                    speaker.say("Shutting down voice system.")
                    break
                elif action == "unknown":
                    speaker.say("I didn't catch that.")
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        speaker.stop()

if __name__ == "__main__":
    main()