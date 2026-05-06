"""
Module: gesture_detector.py
Tác giả: Antigravity (Computer Vision Expert)
Mô tả: Nhận diện thủ ấn Naruto (Bản sửa lỗi nhận diện và thêm Log Debug).
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import urllib.request
import math

class GestureDetector:
    def __init__(self):
        self.base_path = os.path.dirname(__file__)
        self.hand_model_path = os.path.join(self.base_path, 'hand_landmarker.task')
        self.pose_model_path = os.path.join(self.base_path, 'pose_landmarker.task')
        
        self._check_models()
        
        # Khởi tạo Detectors
        hand_options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.hand_model_path),
            num_hands=2, min_hand_detection_confidence=0.5
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)
        
        pose_options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.pose_model_path),
            min_pose_detection_confidence=0.5
        )
        self.pose_detector = vision.PoseLandmarker.create_from_options(pose_options)

    def _check_models(self):
        models = {
            self.hand_model_path: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            self.pose_model_path: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
        }
        for path, url in models.items():
            if not os.path.exists(path):
                print(f"📦 Đang tải AI Model: {os.path.basename(path)}...")
                urllib.request.urlretrieve(url, path)

    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def is_hand_open(self, hand_lms):
        # Đếm ngón tay mở (so sánh đầu ngón với khớp phía dưới)
        tips = [8, 12, 16, 20]
        opened = 0
        for tip in tips:
            if hand_lms[tip].y < hand_lms[tip - 2].y:
                opened += 1
        return opened >= 3

    def process_frame(self, image):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        pose_res = self.pose_detector.detect(mp_image)
        hand_res = self.hand_detector.detect(mp_image)
        
        result = {"skill": None, "block": False, "dodge": None, "message": "Chưa phát hiện cử chỉ"}

        if not pose_res.pose_landmarks:
            return result

        pose = pose_res.pose_landmarks[0]
        nose = pose[0]
        l_sh, r_sh = pose[11], pose[12] 
        l_wr, r_wr = pose[15], pose[16] 
        l_hip, r_hip = pose[23], pose[24]
        
        if l_sh.y > r_sh.y + 0.05: result["dodge"], result["message"] = "left", "Né sang TRÁI"
        elif r_sh.y > l_sh.y + 0.05: result["dodge"], result["message"] = "right", "Né sang PHẢI"

        dist_wrists = self.get_distance(l_wr, r_wr)
        if dist_wrists < 0.15 and l_wr.y < nose.y and r_wr.y < nose.y:
            result["block"], result["message"] = True, "🛡️ ĐANG ĐỠ ĐÒN!"
        
        is_r_open = False
        is_l_open = False
        if hand_res.hand_landmarks:
            for hand in hand_res.hand_landmarks:
                if hand[0].x < 0.5: is_r_open = self.is_hand_open(hand)
                else: is_l_open = self.is_hand_open(hand)

        if dist_wrists < 0.15 and l_sh.y < l_wr.y < l_hip.y:
            result["skill"], result["message"] = "kage_bunshin", "👥 KAGE BUNSHIN!"
        elif l_wr.y < l_sh.y and r_wr.y < r_sh.y and is_r_open and is_l_open:
            result["skill"], result["message"] = "rasenshuriken", "🌪️ RASENSHURIKEN!"
        elif r_wr.y < r_sh.y and is_r_open:
            result["skill"], result["message"] = "rasengan", "🌀 RASENGAN!"

        # Đóng gói tọa độ khung xương để vẽ ở frontend
        landmarks = {
            "pose": [[lm.x, lm.y] for lm in pose] if pose else [],
            "hands": []
        }
        if hand_res.hand_landmarks:
            for hand in hand_res.hand_landmarks:
                landmarks["hands"].append([[lm.x, lm.y] for lm in hand])
        
        result["landmarks"] = landmarks
        return result

# Instance toàn cục
_detector = GestureDetector()

def process_frame(image):
    return _detector.process_frame(image)
