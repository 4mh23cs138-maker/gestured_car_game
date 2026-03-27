import cv2
import pygame
import sys
from hand_tracking import HandDetector
from game_engine import Game, WIDTH, HEIGHT

def main():
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Gesture Racing")
    clock = pygame.time.Clock()
    
    game = Game(screen)
    
    # Initialize OpenCV Video Capture - Probing multiple indices
    cap = None
    for camera_id in range(4):
        temp_cap = cv2.VideoCapture(camera_id)
        if temp_cap.isOpened():
            # Try to read multiple frames to verify it's a stable camera feed
            read_success = False
            for _ in range(3):
                success, temp_img = temp_cap.read()
                if success:
                    read_success = True
                else:
                    read_success = False
                    break
            
            if read_success:
                cap = temp_cap
                print(f"Successfully connected to webcam at index {camera_id}")
                break
            else:
                temp_cap.release()
                
    if cap is None or not cap.isOpened():
        print("Error: Could not open any available webcam. Make sure no other program is exclusively grabbing the camera.")
        sys.exit()
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Initialize Hand Detector
    detector = HandDetector(maxHands=1, detectionCon=0.7)
    
    running = True
    while running:
        # Pygame Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
        # OpenCV Frame Capture
        success, img = cap.read()
        if not success:
            print("Failed to read from webcam. Make sure no other program (or another instance of this game) is using the camera!")
            break
            
        # Flip image horizontally for a mirror effect (selfie view)
        img = cv2.flip(img, 1)
        h, w, _ = img.shape
        
        # Detect hands and landmarks
        img = detector.findHands(img, draw=True)
        lmList = detector.findPosition(img, draw=False)
        
        gesture = "neutral"
        hand_x_normalized = None
        
        if len(lmList) > 0:
            gesture = detector.getGesture()
            
            # Using wrist point (id 0) as center of hand for steering
            wrist_x = lmList[0][1]
            hand_x_normalized = wrist_x / float(w)
            
            # Visual aids on the webcam feed
            cv2.putText(img, f"Gesture: {gesture.upper()}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(img, "Keep Hand Between Lines to Steer", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Draw boundary lines defining the usable playing area (25% and 75% screen width)
            cv2.line(img, (int(w * 0.25), 0), (int(w * 0.25), h), (200, 200, 200), 2)
            cv2.line(img, (int(w * 0.75), 0), (int(w * 0.75), h), (200, 200, 200), 2)
            
            # Draw tracking point
            cv2.circle(img, (lmList[0][1], lmList[0][2]), 10, (0, 0, 255), cv2.FILLED)
            
        # Display Webcam View
        cv2.imshow("Hand Tracking Config", img)
        
        # Check specific key press on OpenCV window
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Game Logic Update
        game.handle_input(gesture, hand_x_normalized)
        game.update()
        
        # Game Rendering
        game.draw()
        pygame.display.flip()
        
        # Cap Pygame framerate around 30 FPS to match standard webcam FPS
        clock.tick(30)
        
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
