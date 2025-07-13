import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.PlotModule import LivePlot
import mediapipe as mp
import time

# cap = cv2.VideoCapture('blinking.mp4')
cap = cv2.VideoCapture('retrd_blinking.mp4')
# cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)
plotY =LivePlot(640,360,[20,51],invert=True)
ratioList=[]
idList =[33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
blinkCounter =0
counter=0
color = (255,0,255)

# --- Parameters for robust blink detection & SOS ---
# DURATION
MIN_SHORT_BLINK_DURATION = 0.08  # Min duration for a short blink
MAX_SHORT_BLINK_DURATION = 0.4   # Max duration for a short blink (and min for a long one)
MAX_LONG_BLINK_DURATION = 1.5    # Max duration for a long blink
RESET_DURATION = 4.0             # Seconds of continuous eye closure to reset the sequence

# STABILITY
STABLE_FRAMES = 2  # Number of consecutive frames the eye must be closed/open to register a state change

# SOS PATTERN
SOS_PATTERN = ["SHORT", "SHORT", "SHORT", "LONG", "LONG", "LONG", "SHORT", "SHORT", "SHORT"]
blink_sequence = []
sos_detected_time = 0
SOS_COOLDOWN = 5 # seconds to display SOS message and ignore new blinks

# --- State variables ---
in_blink = False
blink_start_time = 0
stable_counter = 0
last_blink_type = ""
reset_feedback_time = 0

while True:

    if cap.get(cv2.CAP_PROP_POS_FRAMES)==cap.get(cv2.CAP_PROP_FRAME_COUNT):
        cap.set(cv2.CAP_PROP_POS_FRAMES,0)

    success, img =cap.read()
    img, faces = detector.findFaceMesh(img,draw=False)

    if faces:
        face= faces[0]
        for id in idList:
            cv2.circle(img,face[id],5,color)
        
        leftUp =face[159]
        leftDown= face[23]
        leftLeft =face[130]
        leftRight=face[243]
        lengthVert,_=detector.findDistance(leftUp,leftDown)
        lengthHoriz,_=detector.findDistance(leftLeft,leftRight)

        cv2.line(img,leftUp,leftDown,(0,200,0),3)
        cv2.line(img,leftLeft,leftRight,(0,200,0),3)
        

        ratio = int((lengthVert / lengthHoriz) * 100)
        ratioList.append(ratio)
        if(len(ratioList))>4:
            ratioList.pop(0)
        ratioAvg =sum(ratioList)/len(ratioList)

        # --- Reset sequence if eyes are closed for too long ---
        if in_blink and (time.time() - blink_start_time) > RESET_DURATION:
            blink_sequence = []
            in_blink = False
            stable_counter = 0
            reset_feedback_time = time.time()
            print("Sequence reset due to long eye closure.")

        # --- Display reset feedback for 1 second ---
        if time.time() - reset_feedback_time < 1.0:
            cvzone.putTextRect(img, "SEQUENCE RESET", (50, 150), scale=2, thickness=2, colorR=(0, 255, 0), colorT=(0, 0, 0))

        # --- Robust Blink Detection Logic ---
        eye_closed = ratioAvg < 35

        # If SOS was recently detected, just display the message and skip detection
        if time.time() - sos_detected_time < SOS_COOLDOWN:
            cvzone.putTextRect(img, "SOS DETECTED!", (50, 200), scale=3, thickness=5, colorR=(0, 0, 255), colorT=(255, 255, 255))
            in_blink = False # Reset state
            stable_counter = 0
        
        # --- State Change with Stability Check ---
        elif eye_closed and not in_blink:
            stable_counter += 1
            if stable_counter >= STABLE_FRAMES:
                in_blink = True
                blink_start_time = time.time()
                stable_counter = 0
        elif not eye_closed and in_blink:
            stable_counter += 1
            if stable_counter >= STABLE_FRAMES:
                in_blink = False
                blink_duration = time.time() - blink_start_time
                
                # --- Blink Classification ---
                if MIN_SHORT_BLINK_DURATION <= blink_duration < MAX_SHORT_BLINK_DURATION:
                    last_blink_type = "SHORT"
                    blink_sequence.append("SHORT")
                    print("SHORT")
                elif MAX_SHORT_BLINK_DURATION <= blink_duration < MAX_LONG_BLINK_DURATION:
                    last_blink_type = "LONG"
                    blink_sequence.append("LONG")
                    print("LONG")
                
                # --- SOS Pattern Matching ---
                if len(blink_sequence) >= len(SOS_PATTERN):
                    # Check if the last N blinks match the SOS pattern
                    if blink_sequence[-len(SOS_PATTERN):] == SOS_PATTERN:
                        print("SOS DETECTED!")
                        sos_detected_time = time.time()
                        blink_sequence = [] # Clear sequence after detection
                
                # Keep the sequence list from growing indefinitely
                if len(blink_sequence) > len(SOS_PATTERN):
                    blink_sequence.pop(0)

                blinkCounter += 1
                color = (0, 200, 2)
                stable_counter = 0
        else:
            # Reset counter if state is not stable
            stable_counter = 0

        # --- Reset color after a short period ---
        if color == (0, 200, 2) and time.time() - (blink_start_time if in_blink else time.time()) > 0.5:
             color = (255,0,255)

        cvzone.putTextRect(img,f'BlinkCount:{blinkCounter}',(100,100),colorR=color)
        # Display the current sequence for debugging, now at the bottom
        cvzone.putTextRect(img, f'Sequence: {" ".join(blink_sequence)}', (20, 340), scale=0.9, thickness=1, colorR=(200, 200, 200), colorT=(0,0,0))
        imgPlot=plotY.update(ratioAvg,color)
        img = cv2.resize(img,(640,360))
        imgStack=cvzone.stackImages ([img,imgPlot],2,1)
    else:
        img = cv2.resize(img,(640,360))
        imgStack=cvzone.stackImages ([img,img],1,1)
    cv2.imshow("image",imgStack)
    cv2.waitKey(25)