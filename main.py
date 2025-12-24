import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import time

# --- Configuration ---
wCam, hCam = 640, 480       # Camera Resolution
frameR = 100                # Frame Reduction (padding from edge)
smoothening = 7             # Higher = smoother but more lag (try 5-10)

# --- Variables ---
pTime = 0
plocX, plocY = 0, 0         # Previous Location
clocX, clocY = 0, 0         # Current Location
wScr, hScr = pyautogui.size() # Get your OS Screen Size

# --- Setup MediaPipe ---
mp_hands = mp.solutions.hands
# max_num_hands=1 because we don't want two hands fighting for the mouse
hands = mp_hands.Hands(max_num_hands=1, 
                       model_complexity=1, 
                       min_detection_confidence=0.7, 
                       min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

print("Virtual Mouse Started. Press 'q' to exit.")

while True:
    # 1. Find Hand Landmarks
    success, img = cap.read()
    img = cv2.flip(img, 1) # Important: Mirror the image for intuitive movement!
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)
    
    cv2.rectangle(img, (frameR, frameR), (wCam - frameR, hCam - frameR), (255, 0, 255), 2)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get landmarks list
            lmList = []
            for id, lm in enumerate(hand_landmarks.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            # 2. Get the tip of the Index and Middle fingers
            if len(lmList) != 0:
                x1, y1 = lmList[8][1:]  # Index Finger Tip (ID 8)
                x2, y2 = lmList[12][1:] # Middle Finger Tip (ID 12)

                # 3. Check which fingers are up
                # Simple logic: Is tip above the middle joint? (y coordinate is lower)
                fingers = []
                # Index Finger Check (Tip < Pip)
                if lmList[8][2] < lmList[6][2]: fingers.append(1)
                else: fingers.append(0)
                # Middle Finger Check
                if lmList[12][2] < lmList[10][2]: fingers.append(1)
                else: fingers.append(0)

                # 4. Moving Mode: Only Index Finger is Up
                if fingers[0] == 1 and fingers[1] == 0:
                    # 5. Convert Coordinates (Interpolation)
                    # Map x1 from (frameR, wCam-frameR) to (0, wScr)
                    x3 = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
                    y3 = np.interp(y1, (frameR, hCam - frameR), (0, hScr))

                    # 6. Smoothen Values
                    clocX = plocX + (x3 - plocX) / smoothening
                    clocY = plocY + (y3 - plocY) / smoothening

                    # Move Mouse
                    pyautogui.moveTo(clocX, clocY)
                    cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
                    plocX, plocY = clocX, clocY

                # 7. Clicking Mode: Both Index and Middle Fingers are Up
                if fingers[0] == 1 and fingers[1] == 1:
                    # 8. Find Distance between fingers
                    length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5 # Pythagoras
                    
                    # Draw visual for clicking mode
                    line_center_x, line_center_y = (x1 + x2) // 2, (y1 + y2) // 2
                    cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                    cv2.circle(img, (line_center_x, line_center_y), 15, (255, 0, 255), cv2.FILLED)

                    # 9. Click if distance is short
                    if length < 40:
                        cv2.circle(img, (line_center_x, line_center_y), 15, (0, 255, 0), cv2.FILLED)
                        pyautogui.click()
                        # Short delay to prevent double clicks
                        time.sleep(0.15) 

    # Frame Rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, str(int(fps)), (20, 50), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 0), 3)

    cv2.imshow("Virtual Mouse", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()