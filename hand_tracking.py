import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandDetector:
    def __init__(self, mode=False, maxHands=1, detectionCon=0.7, trackCon=0.5):
        self.maxHands = maxHands
        self.detectionCon = float(detectionCon)
        self.trackCon = float(trackCon)

        # Initialize MediaPipe HandLandmarker Tasks API
        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=self.maxHands,
            min_hand_detection_confidence=self.detectionCon,
            min_hand_presence_confidence=self.trackCon,
            min_tracking_confidence=self.trackCon,
            running_mode=vision.RunningMode.IMAGE
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.tipIds = [4, 8, 12, 16, 20]
        self.results = None
        self.lmList = []

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
        
        self.results = self.detector.detect(mp_image)

        if draw and self.results.hand_landmarks:
            for hand_landmarks in self.results.hand_landmarks:
                # Draw lines between landmarks
                connections = [
                    (0, 1), (1, 2), (2, 3), (3, 4), # Thumb
                    (0, 5), (5, 6), (6, 7), (7, 8), # Index
                    (5, 9), (9, 10), (10, 11), (11, 12), # Middle
                    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
                    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky and Palm
                ]
                h, w, c = img.shape
                for pt1, pt2 in connections:
                    x1, y1 = int(hand_landmarks[pt1].x * w), int(hand_landmarks[pt1].y * h)
                    x2, y2 = int(hand_landmarks[pt2].x * w), int(hand_landmarks[pt2].y * h)
                    cv2.line(img, (x1, y1), (x2, y2), (255, 255, 255), 2)
                    
                # Draw points
                for lm in hand_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(img, (cx, cy), 3, (255, 0, 255), cv2.FILLED)
        return img

    def findPosition(self, img, handNo=0, draw=True):
        self.lmList = []
        if self.results and self.results.hand_landmarks:
            myHand = self.results.hand_landmarks[handNo]
            for id, lm in enumerate(myHand):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lmList.append([id, cx, cy])
                if draw:
                    cv2.circle(img, (cx, cy), 5, (0, 255, 0), cv2.FILLED)
        return self.lmList

    def fingersUp(self):
        fingers = []
        if len(self.lmList) == 0:
            return []
            
        # 4 Fingers (Index, Middle, Ring, Pinky)
        # Assuming upright hand, tip y < pip y means finger is up
        for id in range(1, 5):
            if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers

    def getGesture(self):
        if len(self.lmList) == 0:
            return "none"
            
        fingers = self.fingersUp()
        
        # Open palm -> All 4 fingers are up
        if fingers.count(1) == 4:
            return "accelerate"
        # Closed fist -> All 4 fingers are down
        elif fingers.count(0) == 4:
            return "brake"
            
        return "neutral"
