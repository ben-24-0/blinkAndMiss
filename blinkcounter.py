import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
import time
from spellchecker import SpellChecker
import os

# Try different TTS libraries
TTS_ENGINE = None

try:
    import win32com.client
    TTS_ENGINE = "sapi"
except ImportError:
    try:
        import pyttsx3
        TTS_ENGINE = "pyttsx3"
    except ImportError:
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

# Function for direct speech using Windows SAPI
def speak_text_direct(text):
    """Direct speech using Windows SAPI"""
    if not text or text.isspace() or not TTS_ENGINE:
        return
    
    try:
        if TTS_ENGINE == "sapi":
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = speaker.GetVoices()
            if voices.Count > 0:
                speaker.Voice = voices.Item(0)
            speaker.Rate = 0
            speaker.Volume = 100
            speaker.Speak(text, 0)
        else:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
    except Exception:
        pass

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
stable_counter = 0
last_activity_time = time.time()
current_morse_code = ""
translated_message = ""
space_added = False
reset_feedback_time = 0
last_face_time = time.time()
in_cooldown_until = 0
delete_feedback_time = 0
one_eye_visible_start = 0
one_eye_delete_triggered = False
speech_active = True
auto_correct_active = True

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
        with open(output_file_path, "a") as file:
            file.write(text + "\n")
        with open(current_word_file_path, "w") as file:
            file.write(text)
        return True
    except Exception:
        return False

# --- Main Loop ---
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
        
        # Get left and right eye landmarks
        leftEye = [face[p] for p in [33, 160, 158, 133, 153, 144]]
        rightEye = [face[p] for p in [362, 385, 387, 263, 373, 380]]
        
        # Simple check - if right side of face is not visible or covered
        rightSideVisible = all(p[0] > 0 and p[1] > 0 for p in rightEye)
        leftSideVisible = all(p[0] > 0 and p[1] > 0 for p in leftEye)
        
        # Check if only one eye is visible or has very different ratio
        only_one_eye_visible = (leftSideVisible and not rightSideVisible) or (rightSideVisible and not leftSideVisible)
        
        if only_one_eye_visible and translated_message and time.time() > in_cooldown_until:
            cvzone.putTextRect(img, "ONE EYE DETECTED", (430, 50), scale=0.7, thickness=1, colorR=(0, 100, 200))
            
            if one_eye_visible_start == 0:
                one_eye_visible_start = time.time()
            elif time.time() - one_eye_visible_start > ONE_EYE_DELETE_DURATION and not one_eye_delete_triggered:
                translated_message = remove_last_word(translated_message)
                delete_feedback_time = time.time()
                one_eye_delete_triggered = True
        else:
            one_eye_visible_start = 0
            one_eye_delete_triggered = False
    else:
        # Check if face has been missing long enough to trigger reset
        if time.time() - last_face_time > FACE_RESET_DURATION and translated_message:
            current_morse_code = ""
            translated_message = ""
            in_blink = False
            stable_counter = 0
            reset_feedback_time = time.time()
            in_cooldown_until = time.time() + COOLDOWN_DURATION

    cooldown_remaining = in_cooldown_until - time.time()
    if cooldown_remaining > 0:
        seconds_left = round(cooldown_remaining, 1)
        cvzone.putTextRect(img, f"Ready in: {seconds_left}s", (200, 280), 
                          scale=2, thickness=2, colorR=(0, 200, 200))
    elif faces:
        face = faces[0]
        leftUp = face[159]
        leftDown = face[23]
        leftLeft = face[130]
        leftRight = face[243]
        
        lengthVert, _ = detector.findDistance(leftUp, leftDown)
        lengthHoriz, _ = detector.findDistance(leftLeft, leftRight)
        
        ratio = (lengthVert / lengthHoriz) * 100
        eye_closed = ratio < 35

        if in_blink and (time.time() - blink_start_time) > RESET_DURATION:
            current_morse_code = ""
            translated_message = ""
            in_blink = False
            stable_counter = 0
            reset_feedback_time = time.time()
            last_activity_time = time.time()
            in_cooldown_until = time.time() + COOLDOWN_DURATION

        # --- Blink State Machine ---
        if time.time() < in_cooldown_until:
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
                
                if MIN_DOT_DURATION < blink_duration < MAX_DOT_DURATION:
                    current_morse_code += "."
                elif MIN_DASH_DURATION < blink_duration < MAX_DASH_DURATION:
                    current_morse_code += "-"
                
                last_activity_time = time.time()
                stable_counter = 0
        else:
            stable_counter = 0

        time_since_last_activity = time.time() - last_activity_time
        
        if time_since_last_activity > LETTER_PAUSE and current_morse_code:
            letter = MORSE_CODE_DICT.get(current_morse_code, '?')
            translated_message += letter
            current_morse_code = ""
            last_activity_time = time.time()
            space_added = False

        elif time_since_last_activity > WORD_PAUSE and not current_morse_code and not space_added and translated_message:
            if not translated_message.endswith(" "):
                current_words = translated_message.strip().split()
                if not current_words: continue

                last_word = current_words[-1]
                if auto_correct_active:
                    corrected_word = spell.correction(last_word)
                    if corrected_word and corrected_word.lower() != last_word.lower():
                        current_words[-1] = corrected_word
                
                translated_message = " ".join(current_words) + " "
                save_to_files(current_words[-1])
                
                if speech_active:
                    speak_text_direct(current_words[-1])
                
                translated_message = ""
                space_added = True


    # --- UI Display ---
    cvzone.putTextRect(img, f"Message: {translated_message}", (50, 50), scale=1.5, thickness=2)
    cvzone.putTextRect(img, f"Input: {current_morse_code}", (50, 100), scale=1.5, thickness=2)
    
    if 'eye_closed' in locals():
        eye_state = "CLOSED" if eye_closed else "OPEN"
        eye_color = (0, 0, 255) if eye_closed else (0, 255, 0)
        cvzone.putTextRect(img, f"Eye: {eye_state}", (50, 150), scale=1.5, thickness=2, colorR=eye_color)
    
    if time.time() - reset_feedback_time < 1.5:
        cvzone.putTextRect(img, "MESSAGE CLEARED", (150, 200), scale=2, thickness=2, colorR=(0,0,255))
    
    if time.time() - delete_feedback_time < 1.5:
        cvzone.putTextRect(img, "WORD DELETED", (150, 240), scale=2, thickness=2, colorR=(0,150,255))
    
    # Add UI controls
    speech_status = "ON" if speech_active else "OFF"
    speech_color = (0, 200, 0) if speech_active else (0, 0, 200)
    cvzone.putTextRect(img, f"S:Speech: {speech_status}", (450, 430), 
                      scale=1, thickness=2, colorR=speech_color)
    
    autocorrect_status = "ON" if auto_correct_active else "OFF"
    autocorrect_color = (0, 200, 0) if auto_correct_active else (0, 0, 200)
    cvzone.putTextRect(img, f"A:Auto-Correct: {autocorrect_status}", (450, 400), 
                      scale=1, thickness=2, colorR=autocorrect_color)
    
    cvzone.putTextRect(img, "W: save word or speak current", (50, 430), 
                      scale=0.8, thickness=1)

    cv2.imshow("Morse Code Blinker", img)
    key = cv2.waitKey(25) & 0xFF
    
    # Handle keyboard inputs
    if key == ord('q'):
        break
    elif key == ord('s'):
        speech_active = not speech_active
        speak_text_direct("Speech enabled" if speech_active else "Speech disabled")
    elif key == ord('a'):
        auto_correct_active = not auto_correct_active
        speak_text_direct(f"Auto correction {'enabled' if auto_correct_active else 'disabled'}")
    elif key == ord('w'):
        if translated_message.strip():
            current_word = translated_message.strip()
            save_to_files(current_word)
            speak_text_direct(current_word)
        else:
            try:
                with open(current_word_file_path, "r") as file:
                    file_content = file.read().strip()
                    if file_content:
                        speak_text_direct(file_content)
            except Exception:
                pass

cap.release()
cv2.destroyAllWindows()
