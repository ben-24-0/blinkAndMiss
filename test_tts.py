import pyttsx3

def test_tts():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # Set speech rate
        engine.setProperty('volume', 1.0)  # Set volume to maximum
        engine.say("This is a test of the text-to-speech system.")
        engine.runAndWait()
        print("TTS test completed successfully.")
    except Exception as e:
        print(f"Error during TTS test: {e}")

if __name__ == "__main__":
    test_tts()
