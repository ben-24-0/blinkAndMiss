import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
import time
import threading
import queue
from spellchecker import SpellChecker
import os

# Try different TTS libraries
TTS_ENGINE = None
TTS_TYPE = None

try:
    # First try Windows SAPI (usually more reliable)
    import win32com.client
    TTS_ENGINE = "sapi"
    TTS_TYPE = "Windows SAPI"
    print("Using Windows SAPI for TTS")
except ImportError:
    try:
        # Fallback to pyttsx3
        import pyttsx3
        TTS_ENGINE = "pyttsx3"
        TTS_TYPE = "pyttsx3"
        print("Using pyttsx3 for TTS")
    except ImportError:
        print("No TTS library available")
        TTS_ENGINE = None

# --- Initialization ---
cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)

# --- Morse Code Dictionary ---
MORSE_CODE_DICT = { '.-':'A', '-...':'B', '-.-.':'C', '-..':'D', '.':'E', '..-.':'F',
                    '--.':'G', '....':'H', '..':'I', '.---':'J', '-.-':'K', '.-..':'L',
                    '--':'M', '-.':'N', '---':'O', '.--.':'P', '--.-':'Q', '.-.':'R',
                    '...':'S', '-':'T', '..-':'U', '...-':'V', '.--':'W', '-..-':'X',
                    '-.--':'Y', '--..':'Z', '-----':'0', '.----':'1', '..---':'2',
                    '...--':'3', '....-':'4', '.....':'5', '-....':'6', '--...':'7',
                    '---..':'8', '----.':'9',
                    '.-.-.-':'.', '--..--':',', '..--..':'?', '-.-.--':'!'}

# --- Parameters for Morse Code Detection ---
# TIMING (in seconds) - *** NEW, MORE PRECISE DEFINITIONS ***
MIN_DOT_DURATION = 0.1          # Min duration for a dot
MAX_DOT_DURATION = 0.4          # Max duration for a dot
MIN_DASH_DURATION = 0.4         # Min duration for a dash
MAX_DASH_DURATION = 1.5         # Max duration for a dash
LETTER_PAUSE = 1.5              # Pause to signify the end of a letter
WORD_PAUSE = 3.0                # Pause to signify a space between words
RESET_DURATION = 5.0            # Hold eyes closed this long to clear the message
FACE_RESET_DURATION = 2.0       # Time without face to reset
COOLDOWN_DURATION = 1.5         # Time after reset where no blinks are detected
ONE_EYE_DELETE_DURATION = 1.5   # Hold with only one eye visible to delete last word

# STABILITY
STABLE_FRAMES = 2               # Consecutive frames eye must be closed/open

# --- Initialize Speech Queue and Spell Checker ---
speech_queue = queue.Queue()
SPEECH_AVAILABLE = TTS_ENGINE is not None

# Clear the message log files at the start of the script
# (This line will be moved after the file paths are defined)

# --- Initialize Text-to-Speech ---
# TTS engine will be initialized in the speech thread based on available library
print(f"TTS Status: {TTS_TYPE if TTS_ENGINE else 'Not Available'}")

# --- Speech Thread Function ---
def speech_thread():
    """Continuous TTS processing thread that handles all speech requests"""
    global SPEECH_AVAILABLE
    
    if not TTS_ENGINE:
        print("No TTS engine available")
        return
    
    try:
        print(f"Initializing {TTS_TYPE} in speech thread...")
        
        if TTS_ENGINE == "sapi":
            # Windows SAPI setup
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # Set speech rate (0-10, default is usually around 3)
            speaker.Rate = 2
            # Set volume (0-100)
            speaker.Volume = 100
            print("Windows SAPI initialized successfully")
            
        elif TTS_ENGINE == "pyttsx3":
            # pyttsx3 setup
            thread_engine = pyttsx3.init()
            thread_engine.setProperty('rate', 150)
            thread_engine.setProperty('volume', 1.0)
            voices = thread_engine.getProperty('voices')
            if voices:
                thread_engine.setProperty('voice', voices[0].id)
            print("pyttsx3 initialized successfully")
        
        while True:
            try:
                text = speech_queue.get(timeout=1)
                if text == "__STOP__":
                    print("Speech thread stopping...")
                    break
                
                if text and not text.isspace():
                    try:
                        print(f"TTS Thread - Speaking: '{text}'")
                        
                        if TTS_ENGINE == "sapi":
                            # Windows SAPI - simpler and more reliable
                            speaker.Speak(text)
                            
                        elif TTS_ENGINE == "pyttsx3":
                            # pyttsx3 with safeguards
                            thread_engine.stop()
                            time.sleep(0.1)
                            thread_engine.say(text)
                            thread_engine.runAndWait()
                            time.sleep(0.2)
                        
                        print(f"TTS Thread - Finished speaking: '{text}'")
                        
                    except Exception as e:
                        print(f"Error during speech: {e}")
                        if TTS_ENGINE == "pyttsx3":
                            # Try to reinitialize pyttsx3 if it fails
                            try:
                                thread_engine = pyttsx3.init()
                                thread_engine.setProperty('rate', 150)
                                thread_engine.setProperty('volume', 1.0)
                            except:
                                SPEECH_AVAILABLE = False
                
                speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in speech thread main loop: {e}")
                
    except Exception as e:
        print(f"Speech thread initialization error: {e}")
        SPEECH_AVAILABLE = False

# Start the speech thread
print("Starting speech thread...")
speech_thread_active = True
speech_thread_instance = threading.Thread(target=speech_thread, daemon=True)
speech_thread_instance.start()
print("Speech thread started")

# Function for direct speech using Windows SAPI
def speak_text_direct(text):
    """Direct speech using Windows SAPI - more reliable than queue system"""
    if not text or text.isspace() or not SPEECH_AVAILABLE:
        return
    
    try:
        if TTS_ENGINE == "sapi":
            print(f"Speaking directly: '{text}'")
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            # Get available voices and use the first one
            voices = speaker.GetVoices()
            if voices.Count > 0:
                speaker.Voice = voices.Item(0)
            
            # Set properties for better audio
            speaker.Rate = 0  # Normal speed
            speaker.Volume = 100  # Maximum volume
            
            # Use synchronous speech and wait for completion
            speaker.Speak(text, 0)  # 0 = SVSFlagsDefault (synchronous, waits)
            print(f"Finished speaking: '{text}'")
        else:
            print(f"TTS not available or unsupported engine: {TTS_ENGINE}")
    except Exception as e:
        print(f"Error in direct speech: {e}")
        # Fallback: try the old pyttsx3 method if available
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            print(f"Fallback TTS successful: '{text}'")
        except Exception as e2:
            print(f"Fallback TTS also failed: {e2}")

# Legacy function to queue speech requests (kept for compatibility)
def queue_speak_text(text):
    """Add text to the speech queue for processing"""
    if text and not text.isspace() and SPEECH_AVAILABLE:
        print(f"Queueing text for speech: '{text}'")
        speech_queue.put(text)  # Add text to the queue for the speech thread
        print(f"Queue size after adding: {speech_queue.qsize()}")
    else:
        print(f"Not queueing text. Text: '{text}', SPEECH_AVAILABLE: {SPEECH_AVAILABLE}")

# --- Initialize Spell Checker ---
spell = SpellChecker()

# Output file paths for saving messages
output_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "morse_messages.txt")
current_word_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_word.txt")

# Clear the message log files at the start of the script
with open(output_file_path, "w") as file:
    file.write("")
with open(current_word_file_path, "w") as file:
    file.write("")

# --- State variables ---
in_blink = False
blink_start_time = 0
last_blink_duration = 0         # For on-screen debugging
stable_counter = 0
last_activity_time = time.time()
current_morse_code = ""
translated_message = ""
space_added = False
reset_feedback_time = 0
last_face_time = time.time()    # Track when we last saw a face
in_cooldown_until = 0           # Timestamp when cooldown ends
delete_feedback_time = 0        # For displaying delete confirmation
one_eye_visible_start = 0       # Time when we first detected only one eye
one_eye_delete_triggered = False # Flag to prevent multiple deletes
last_spoken_text = ""           # Track what text has already been spoken
last_saved_text = ""            # Track what text has been saved to file
speech_active = True           # Enable speech by default
auto_correct_active = True     # Enable auto-correction by default

# --- Function to remove last word ---
def remove_last_word(text):
    if not text:
        return ""
    
    # If there's a space, remove the last word
    if " " in text:
        words = text.split(" ")
        return " ".join(words[:-1]) + " "  # Keep the trailing space
    else:
        # No space, just remove the last character
        return text[:-1]

# --- Function for spell correction ---
def auto_correct_text(text):
    if not text:
        return ""
    
    words = text.split()
    corrected_words = []
    
    for word in words:
        # Keep punctuation separate from the word
        punctuation = ""
        while word and word[-1] in ".!?,;:":
            punctuation = word[-1] + punctuation
            word = word[:-1]
        
        # Only correct words that are at least 2 characters long
        if len(word) >= 2:
            corrected_word = spell.correction(word)
            if corrected_word and corrected_word.lower() != word.lower():
                corrected_words.append(corrected_word + punctuation)
            else:
                corrected_words.append(word + punctuation)
        else:
            corrected_words.append(word + punctuation)
    
    return " ".join(corrected_words)

# --- Function to save text to files ---
def save_to_files(text):
    """Save to both files: append to all_words file, overwrite current_word file"""
    try:
        # 1. Append to the cumulative log file (all words)
        with open(output_file_path, "a") as file:
            file.write(text + "\n")
        
        # 2. Overwrite the current word file (for TTS)
        with open(current_word_file_path, "w") as file:
            file.write(text)
        
        print(f"Word saved to both files: {text}")
        return True
    except Exception as e:
        print(f"Error saving to files: {e}")
        return False

# --- Main Loop ---
print("Starting main loop...")
# Test speech at startup
print("Testing speech at startup...")
speak_text_direct("System ready")

while True:
    success, img = cap.read()
    if not success:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue
    
    img = cv2.resize(img, (640, 480))
    img, faces = detector.findFaceMesh(img, draw=False)

    # --- Track face presence for reset ---
    if faces:
        last_face_time = time.time()
        
        # --- Check for "one eye only" gesture for backspace/delete ---
        face = faces[0]
        
        # Check if only the left eye is visible (right eye is covered/closed)
        # We'll use facial landmarks to detect if one eye area has very different proportions
        # Get left and right eye landmarks
        leftEye = [face[p] for p in [33, 160, 158, 133, 153, 144]]
        rightEye = [face[p] for p in [362, 385, 387, 263, 373, 380]]
        
        # Eye landmarks visualization removed
        
        # Calculate eye aspect ratios
        leftEyeOpen = True
        rightEyeOpen = True
        
        # Simple check - if right side of face is not visible or covered
        rightSideVisible = all(p[0] > 0 and p[1] > 0 for p in rightEye)
        leftSideVisible = all(p[0] > 0 and p[1] > 0 for p in leftEye)
        
        # Check if only one eye is visible or has very different ratio
        only_one_eye_visible = (leftSideVisible and not rightSideVisible) or (rightSideVisible and not leftSideVisible)
        
        if only_one_eye_visible and translated_message and time.time() > in_cooldown_until:
            # Draw a more subtle indicator for one-eye detection
            cvzone.putTextRect(img, "ONE EYE DETECTED", (430, 50), scale=0.7, thickness=1, colorR=(0, 100, 200))
            
            if one_eye_visible_start == 0:
                # Start timing how long they hold this pose
                one_eye_visible_start = time.time()
            elif time.time() - one_eye_visible_start > ONE_EYE_DELETE_DURATION and not one_eye_delete_triggered:
                # They've held the one-eye gesture long enough - delete last word
                translated_message = remove_last_word(translated_message)
                delete_feedback_time = time.time()
                one_eye_delete_triggered = True
                print(f"Deleted last word (one eye gesture). Message now: {translated_message}")
        else:
            # Reset one-eye detection if both eyes visible again
            one_eye_visible_start = 0
            one_eye_delete_triggered = False
    else:
        # Check if face has been missing long enough to trigger reset
        if time.time() - last_face_time > FACE_RESET_DURATION and translated_message:
            # Clear message and enter cooldown
            current_morse_code = ""
            translated_message = ""
            in_blink = False
            stable_counter = 0
            reset_feedback_time = time.time()
            in_cooldown_until = time.time() + COOLDOWN_DURATION
            print("Message cleared: Face not detected")

    # --- Cooldown check (skip all detection logic during cooldown) ---
    cooldown_remaining = in_cooldown_until - time.time()
    if cooldown_remaining > 0:
        # We're in cooldown - show countdown and skip all detection
        seconds_left = round(cooldown_remaining, 1)
        cvzone.putTextRect(img, f"Ready in: {seconds_left}s", (200, 280), 
                          scale=2, thickness=2, colorR=(0, 200, 200))
    elif faces:
        face = faces[0]
        # Using specific landmarks for eye aspect ratio
        leftUp = face[159]
        leftDown = face[23]
        leftLeft = face[130]
        leftRight = face[243]
        
        # Eye detection visualization removed
        
        lengthVert, _ = detector.findDistance(leftUp, leftDown)
        lengthHoriz, _ = detector.findDistance(leftLeft, leftRight)
        
        ratio = (lengthVert / lengthHoriz) * 100
        eye_closed = ratio < 35
        
        # Eye ratio display removed

        # --- Reset Logic ---
        if in_blink and (time.time() - blink_start_time) > RESET_DURATION:
            current_morse_code = ""
            translated_message = ""
            in_blink = False
            stable_counter = 0
            reset_feedback_time = time.time()
            last_activity_time = time.time()
            in_cooldown_until = time.time() + COOLDOWN_DURATION
            print("Message cleared: Long eye closure")

        # --- Blink State Machine --- (only process if not in cooldown)
        # Skip all blink detection if we're in cooldown mode
        if time.time() < in_cooldown_until:
            # Do nothing - we're in cooldown
            pass
        elif eye_closed and not in_blink:
            stable_counter += 1
            if stable_counter >= STABLE_FRAMES:
                in_blink = True
                blink_start_time = time.time()
                last_activity_time = time.time()
                stable_counter = 0
                space_added = False
        elif not eye_closed and in_blink:
            stable_counter += 1
            if stable_counter >= STABLE_FRAMES:
                in_blink = False
                blink_duration = time.time() - blink_start_time
                last_blink_duration = blink_duration # Store for debugging display
                
                # *** NEW, MORE PRECISE BLINK CLASSIFICATION ***
                if MIN_DOT_DURATION < blink_duration < MAX_DOT_DURATION:
                    current_morse_code += "."
                    print(f"Registered DOT. Current code: {current_morse_code}")
                elif MIN_DASH_DURATION < blink_duration < MAX_DASH_DURATION:
                    current_morse_code += "-"
                    print(f"Registered DASH. Current code: {current_morse_code}")
                
                last_activity_time = time.time()
                stable_counter = 0
        else:
            stable_counter = 0

        # --- Translation Logic based on Pauses ---
        time_since_last_activity = time.time() - last_activity_time
        
        # End of Letter
        if time_since_last_activity > LETTER_PAUSE and current_morse_code:
            letter = MORSE_CODE_DICT.get(current_morse_code, '?')
            translated_message += letter
            print(f"Translated '{current_morse_code}' to '{letter}'. Message: {translated_message}")
            current_morse_code = ""
            last_activity_time = time.time() # Reset timer to avoid multiple translations
            space_added = False
            
            # Speak the letter if speech is active - REMOVED to prevent choppy audio
            # if speech_active:
            #     speak_text(letter)

        # End of Word (Space)
        elif time_since_last_activity > WORD_PAUSE and not current_morse_code and not space_added and translated_message:
            if not translated_message.endswith(" "):
                
                # --- New, more robust speech and save logic ---
                # 1. Get the message before adding a space
                current_words = translated_message.strip().split()
                if not current_words: continue # Skip if empty

                # 2. Auto-correct the last word (if enabled)
                last_word = current_words[-1]
                if auto_correct_active:
                    corrected_word = spell.correction(last_word)
                    
                    if corrected_word and corrected_word.lower() != last_word.lower():
                        print(f"Auto-corrected: '{last_word}' to '{corrected_word}'")
                        current_words[-1] = corrected_word
                    else:
                        print(f"Word kept as: '{last_word}' (no correction needed)")
                else:
                    print(f"Word kept as: '{last_word}' (auto-correct disabled)")
                
                # 3. Rebuild the message and add a space
                translated_message = " ".join(current_words) + " "
                
                # 4. Save to both files and speak the word
                save_to_files(current_words[-1])
                
                if speech_active:
                    # Just speak the last corrected word using direct method
                    speak_text_direct(current_words[-1])
                
                # 5. Reset the translated_message for word-by-word mode
                translated_message = ""
                
                # Mark that a space has been added to prevent this from running in a loop
                space_added = True


    # --- UI Display ---
    # Display the translated message
    cvzone.putTextRect(img, f"Message: {translated_message}", (50, 50), scale=1.5, thickness=2)
    # Display the current morse code being input
    cvzone.putTextRect(img, f"Input: {current_morse_code}", (50, 100), scale=1.5, thickness=2)
    # *** NEW: Display last blink duration for debugging ***
    cvzone.putTextRect(img, f"Last Blink: {last_blink_duration:.2f}s", (50, 150), scale=1.5, thickness=2)
    
    # Show eye state indicator
    if 'eye_closed' in locals():
        eye_state = "CLOSED" if eye_closed else "OPEN"
        eye_color = (0, 0, 255) if eye_closed else (0, 255, 0)  # Red if closed, green if open
        cvzone.putTextRect(img, f"Eye: {eye_state}", (50, 200), scale=1.5, thickness=2, colorR=eye_color)
    
    # Display reset feedback
    if time.time() - reset_feedback_time < 1.5:
        cvzone.putTextRect(img, "MESSAGE CLEARED", (150, 240), scale=2, thickness=2, colorR=(0,0,255))
    
    # Display delete feedback
    if time.time() - delete_feedback_time < 1.5:
        cvzone.putTextRect(img, "WORD DELETED", (150, 200), scale=2, thickness=2, colorR=(0,150,255))
    
    # Add UI controls for text-to-speech and auto-correction
    speech_status = "ON" if speech_active else "OFF"
    speech_color = (0, 200, 0) if speech_active else (0, 0, 200)
    cvzone.putTextRect(img, f"S:Speech: {speech_status}", (450, 430), 
                      scale=1, thickness=2, colorR=speech_color)
    
    autocorrect_status = "ON" if auto_correct_active else "OFF"
    autocorrect_color = (0, 200, 0) if auto_correct_active else (0, 0, 200)
    cvzone.putTextRect(img, f"A:Auto-Correct: {autocorrect_status}", (450, 400), 
                      scale=1, thickness=2, colorR=autocorrect_color)
    
    # Add a help text for keyboard controls - simplified
    cvzone.putTextRect(img, "W: save word or speak current", (50, 430), 
                      scale=0.8, thickness=1)

    cv2.imshow("Morse Code Blinker", img)
    key = cv2.waitKey(25) & 0xFF
    
    # Handle keyboard inputs
    if key == ord('q'):
        break
    elif key == ord('s'):  # Toggle speech
        speech_active = not speech_active
        status = "enabled" if speech_active else "disabled"
        print(f"Speech {status}")
        if speech_active:
            speak_text_direct("Speech enabled")
        else:
            speak_text_direct("Speech disabled")
    elif key == ord('a'):  # Toggle auto-correction
        auto_correct_active = not auto_correct_active
        status = "enabled" if auto_correct_active else "disabled"
        print(f"Auto-correction {status}")
        speak_text_direct(f"Auto correction {status}")
    elif key == ord('w'):  # Save to file manually and speak from file
        if translated_message.strip():
            # Get current word and save it
            current_word = translated_message.strip()
            save_to_files(current_word)
            speak_text_direct(current_word)
            print("Current word saved and spoken")
        else:
            # Read from current_word file and speak
            try:
                with open(current_word_file_path, "r") as file:
                    file_content = file.read().strip()
                    if file_content:
                        speak_text_direct(file_content)
                        print(f"Speaking from file: {file_content}")
                    else:
                        print("Current word file is empty")
            except Exception as e:
                print(f"Error reading current word file: {e}")

cap.release()
cv2.destroyAllWindows()