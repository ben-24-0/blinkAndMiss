import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.PlotModule import LivePlot
import mediapipe as mp

cap = cv2.VideoCapture('blinking.mp4')
# cap = cv2.VideoCapture(0)s
detector = FaceMeshDetector(maxFaces=1)
plotY =LivePlot(640,360,[20,51],invert=True)
ratioList=[]
idList =[22,23,24,26,110,157,158,159,160,161,130,243]
blinkCounter =0
counter=0
color = (255,0,255)
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