import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
import time

# cap = cv2.VideoCapture('blinking.mp4')
# cap = cv2.VideoCapture('rtrd.mp4')
cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)

# --- Morse Code Dictionary ---
MORSE_CODE_DICT = { '.-':'A', '-...':'B', '-.-.':'C', '-..':'D', '.':'E', '..-.':'F',
                    '--.':'G', '....':'H', '..':'I', '.---':'J', '-.-':'K', '.-..':'L',
                    '--':'M', '-.':'N', '---':'O', '.--.':'P', '--.-':'Q', '.-.':'R',
                    '...':'S', '-':'T', '..-':'U', '...-':'V', '.--':'W', '-..-':'X',
                    '-.--':'Y', '--..':'Z', '-----':'0', '.----':'1', '..---':'2',
                    '...--':'3', '....-':'4', '.....':'5', '-....':'6', '--...':'7',
                    '---..':'8', '----.':'9'}

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

# --- Main Loop ---
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

        # End of Word (Space)
        elif time_since_last_activity > WORD_PAUSE and not current_morse_code and not space_added and translated_message:
            if not translated_message.endswith(" "):
                translated_message += " "
                print("Added SPACE.")
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

    cv2.imshow("Morse Code Blinker", img)
    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()