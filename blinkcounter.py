import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.PlotModule import LivePlot
import mediapipe as mp
import time

# cap = cv2.VideoCapture('blinking.mp4')
cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)
plotY =LivePlot(640,360,[20,51],invert=True)
ratioList=[]
idList =[33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
blinkCounter =0
counter=0
color = (255,0,255)

# Peak detection variables
last_peak_time = None
peak_detected = False
blink_start_time = None
in_blink = False
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

        current_time = time.time()
        
        # Detect when blink starts (ratio drops below threshold)
        if ratioAvg < 35 and not in_blink:
            in_blink = True
            blink_start_time = current_time
        
        # Detect when blink ends (ratio goes back above threshold)
        elif ratioAvg >= 35 and in_blink:
            in_blink = False
            if blink_start_time:
                blink_duration = current_time - blink_start_time
                
                # Classify and print blink duration
                if blink_duration < 0.3:
                    print("SHORT")
                else:
                    print("LONG")
                
                last_peak_time = current_time

        if ratioAvg<35 and counter ==0:
            blinkCounter+=1
            color=(0,200,2)
            counter=1
        if counter !=0:
            counter+=1
            if counter >14:
                counter=0   
                color = (255,0,255)
        cvzone.putTextRect(img,f'BlinkCount:{blinkCounter}',(100,100),colorR=color)
        imgPlot=plotY.update(ratioAvg,color)
        img = cv2.resize(img,(640,360))
        imgStack=cvzone.stackImages ([img,imgPlot],2,1)
    else:
        img = cv2.resize(img,(640,360))
        imgStack=cvzone.stackImages ([img,img],1,1)
    cv2.imshow("image",imgStack)
    cv2.waitKey(25)