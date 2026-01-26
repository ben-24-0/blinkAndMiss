import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
import mediapipe as mp
import time

# Initialize the face mesh detector
cap = cv2.VideoCapture('blinking.mp4')
detector = FaceMeshDetector(maxFaces=1)

# Blink detection variables
blink_counter = 0
ratio_list = []
blink_threshold = 0.35  # Adjust this value for sensitivity

# Simple blink duration tracking
is_blinking = False
blink_start_time = None

# Eye landmarks indices for mediapipe
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

def get_eye_aspect_ratio(face_landmarks, eye_indices):
    """Calculate the eye aspect ratio for blink detection"""
    # Get eye landmarks
    eye_points = []
    for idx in eye_indices:
        x, y = face_landmarks[idx]
        eye_points.append([x, y])
    
    # Calculate vertical distances
    vertical_1 = abs(eye_points[1][1] - eye_points[5][1])
    vertical_2 = abs(eye_points[2][1] - eye_points[4][1])
    
    # Calculate horizontal distance
    horizontal = abs(eye_points[0][0] - eye_points[3][0])
    
    # Calculate eye aspect ratio
    if horizontal > 0:
        ratio = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ratio
    return 0

while True:
    # Loop the video
    if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        blink_counter = 0  # Reset counter when video loops

    success, img = cap.read()
    if not success:
        break
        
    # Detect face mesh
    img, faces = detector.findFaceMesh(img, draw=False)
    
    if faces:
        face = faces[0]  # Get the first face
        
        # Calculate eye aspect ratio for both eyes
        left_ratio = get_eye_aspect_ratio(face, LEFT_EYE)
        right_ratio = get_eye_aspect_ratio(face, RIGHT_EYE)
        
        # Average the ratios
        avg_ratio = (left_ratio + right_ratio) / 2
        ratio_list.append(avg_ratio)
        
        # Keep only last 5 ratios for smoothing
        if len(ratio_list) > 5:
            ratio_list.pop(0)
        
        # Simple blink detection using peaks
        eye_closed = avg_ratio < blink_threshold
        
        # Start timing when blink begins
        if eye_closed and not is_blinking:
            is_blinking = True
            blink_start_time = time.time()
            
        # End timing when blink finishes
        elif not eye_closed and is_blinking:
            is_blinking = False
            if blink_start_time:
                blink_duration = time.time() - blink_start_time
                
                # Classify and log the blink
                if blink_duration < 0.4:  # Less than 0.4 seconds
                    print(f"SHORT blink - Duration: {blink_duration:.2f}s")
                else:  # 0.4 seconds or more
                    print(f"LONG blink - Duration: {blink_duration:.2f}s")
                
                blink_counter += 1
            
        # Check for blink (original logic for counting)
        if len(ratio_list) >= 3:
            if avg_ratio < blink_threshold and all(r < blink_threshold for r in ratio_list[-3:]):
                if len(ratio_list) >= 5 and any(r > blink_threshold for r in ratio_list[-5:-2]):
                    ratio_list.clear()  # Clear to avoid double counting
        
        # Draw eye landmarks
        for idx in LEFT_EYE + RIGHT_EYE:
            x, y = face[idx]
            cv2.circle(img, (x, y), 2, (0, 255, 0), -1)
    
    # Display information
    cv2.putText(img, f'Blinks: {blink_counter}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    if faces:
        cv2.putText(img, f'Eye Ratio: {avg_ratio:.2f}', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f'Threshold: {blink_threshold}', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Resize and display
    img = cv2.resize(img, (640, 360))
    cv2.imshow("Blink Detection", img)
    
    # Press 'q' to quit, 's' to adjust sensitivity
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):  # Adjust sensitivity
        blink_threshold += 0.05
        if blink_threshold > 0.5:
            blink_threshold = 0.2
        print(f"New threshold: {blink_threshold}")

cap.release()
cv2.destroyAllWindows()
print(f"Total blinks detected: {blink_counter}")
