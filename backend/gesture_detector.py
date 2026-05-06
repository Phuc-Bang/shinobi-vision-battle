import cv2
import mediapipe as mp
import numpy as np

class GestureDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)
        
        all_hands_data = []
        if self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                
                # Extract landmarks as a list of (x, y, z)
                landmarks = []
                for id, lm in enumerate(hand_lms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks.append((cx, cy, lm.z))
                all_hands_data.append(landmarks)
        
        return img, all_hands_data

    def detect_seal(self, all_hands_data):
        """
        Nhận diện các thủ ấn Naruto cơ bản.
        """
        if not all_hands_data:
            return None

        # Logic đơn giản: Đếm số ngón tay mở
        # Đây là ví dụ, trong thực tế sẽ cần logic phức tạp hơn cho từng thủ ấn
        
        if len(all_hands_data) == 2:
            # Hai tay -> Có thể là Kage Bunshin
            return "Kage Bunshin"
        
        if len(all_hands_data) == 1:
            landmarks = all_hands_data[0]
            # Đếm ngón tay (Thumb: 4, Index: 8, Middle: 12, Ring: 16, Pinky: 20)
            fingers = []
            
            # Thumb (so sánh x với điểm 3)
            if landmarks[4][0] > landmarks[3][0]:
                fingers.append(1)
            else:
                fingers.append(0)
                
            # 4 ngón còn lại (so sánh y với điểm khớp dưới)
            for tip_id in [8, 12, 16, 20]:
                if landmarks[tip_id][1] < landmarks[tip_id - 2][1]:
                    fingers.append(1)
                else:
                    fingers.append(0)
            
            total_fingers = sum(fingers)
            
            if total_fingers == 5:
                return "Rasengan"
            elif total_fingers == 0:
                return "Chidori"
            elif total_fingers == 2: # Victory sign / Peace
                return "Shuriken"
                
        return None
