"""
Module: gesture_detector.py
Tác giả: Antigravity (Computer Vision Expert)
Mô tả: Nhận diện thủ ấn Naruto (Bản sửa lỗi nhận diện và thêm Log Debug).
"""

import os

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2
import mediapipe as mp
from absl import logging as absl_logging
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import urllib.request
import math
import threading
from collections import deque

absl_logging.set_verbosity(absl_logging.ERROR)

class GestureDetector:
    def __init__(self):
        self.base_path = os.path.dirname(__file__)
        self.hand_model_path = os.path.join(self.base_path, 'hand_landmarker.task')
        self.pose_model_variant = os.getenv("POSE_MODEL_VARIANT", "lite").strip().lower()
        if self.pose_model_variant not in ("lite", "full", "heavy"):
            self.pose_model_variant = "lite"
        self.pose_model_path = os.path.join(
            self.base_path, f'pose_landmarker_{self.pose_model_variant}.task'
        )
        self._inference_lock = threading.Lock()
        self.frame_index = 0
        self.hand_detect_interval = int(os.getenv("HAND_DETECT_INTERVAL", "2"))
        self.last_hand_state = {"right_open": False, "left_open": False}
        self.last_hand_landmarks = []
        self.hand_missing_frames = 0
        self.clear_hand_after_misses = int(os.getenv("CLEAR_HAND_AFTER_MISSES", "3"))
        self.max_infer_width = int(os.getenv("MAX_INFER_WIDTH", "640"))
        self.skill_smooth_window = int(os.getenv("SKILL_SMOOTH_WINDOW", "4"))
        self.skill_history = deque(maxlen=max(2, self.skill_smooth_window))
        self.pose_ema_alpha = float(os.getenv("POSE_EMA_ALPHA", "0.35"))
        self.pose_keypoint_cache = {}
        self.dodge_threshold = float(os.getenv("DODGE_SHOULDER_DIFF", "0.07"))
        self.block_wrist_dist = float(os.getenv("BLOCK_WRIST_DIST", "0.14"))
        self.kage_wrist_dist = float(os.getenv("KAGE_WRIST_DIST", "0.13"))
        self.action_confirm_frames = int(os.getenv("ACTION_CONFIRM_FRAMES", "2"))
        self.skill_repeat_cooldown_frames = int(os.getenv("SKILL_REPEAT_COOLDOWN_FRAMES", "8"))
        self.skill_release_frames = int(os.getenv("SKILL_RELEASE_FRAMES", "8"))
        self.last_emitted_skill = None
        self.last_skill_frame = -999
        self.no_skill_frames = self.skill_release_frames
        self.action_counters = {
            "dodge_left": 0,
            "dodge_right": 0,
            "block": 0,
            "kage_bunshin": 0,
            "rasenshuriken": 0,
            "rasengan": 0,
        }
        
        self._check_models()
        
        # Khởi tạo Detectors
        hand_options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.hand_model_path),
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        pose_options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.pose_model_path),
            num_poses=1,
            min_pose_detection_confidence=0.45,
            min_pose_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        self.pose_detector = vision.PoseLandmarker.create_from_options(pose_options)

    def _check_models(self):
        pose_url_map = {
            "lite": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            "full": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
            "heavy": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        }
        models = {
            self.hand_model_path: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            self.pose_model_path: pose_url_map[self.pose_model_variant]
        }
        for path, url in models.items():
            if not os.path.exists(path):
                print(f"📦 Đang tải AI Model: {os.path.basename(path)}...")
                urllib.request.urlretrieve(url, path)

    def smooth_skill(self, skill):
        self.skill_history.append(skill)
        votes = {}
        for item in self.skill_history:
            votes[item] = votes.get(item, 0) + 1
        top_skill, top_count = max(votes.items(), key=lambda kv: kv[1])
        # Ưu tiên output ổn định: cần đa số trong cửa sổ để xác nhận skill.
        if top_skill and top_count >= max(2, len(self.skill_history) // 2 + 1):
            return top_skill
        return None

    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def smooth_pose_keypoint(self, pose, index):
        kp = pose[index]
        prev = self.pose_keypoint_cache.get(index)
        if prev is None:
            smoothed = (kp.x, kp.y)
        else:
            a = self.pose_ema_alpha
            smoothed = (
                prev[0] + a * (kp.x - prev[0]),
                prev[1] + a * (kp.y - prev[1]),
            )
        self.pose_keypoint_cache[index] = smoothed
        return smoothed

    def is_hand_open(self, hand_lms):
        # Đếm ngón tay mở (so sánh đầu ngón với khớp phía dưới)
        tips = [8, 12, 16, 20]
        opened = 0
        for tip in tips:
            if hand_lms[tip].y < hand_lms[tip - 2].y:
                opened += 1
        return opened >= 3

    def confirm_action(self, action_key, condition):
        if condition:
            self.action_counters[action_key] = self.action_counters.get(action_key, 0) + 1
        else:
            self.action_counters[action_key] = 0
        return self.action_counters[action_key] >= max(1, self.action_confirm_frames)

    def gate_skill_repeat(self, skill, raw_skill=None):
        if not skill:
            if raw_skill:
                self.no_skill_frames = 0
            else:
                self.no_skill_frames += 1
            if self.no_skill_frames >= self.skill_release_frames:
                self.last_emitted_skill = None
            return None

        self.no_skill_frames = 0
        frames_since_emit = self.frame_index - self.last_skill_frame
        if self.last_emitted_skill is not None:
            return None

        self.last_emitted_skill = skill
        self.last_skill_frame = self.frame_index
        return skill

    def process_frame(self, image):
        self.frame_index += 1

        h, w = image.shape[:2]
        if w > self.max_infer_width:
            scale = self.max_infer_width / float(w)
            image = cv2.resize(
                image,
                (self.max_infer_width, int(h * scale)),
                interpolation=cv2.INTER_AREA,
            )

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        
        with self._inference_lock:
            pose_res = self.pose_detector.detect(mp_image)
            run_hand = (self.frame_index % self.hand_detect_interval) == 0
            hand_res = self.hand_detector.detect(mp_image) if run_hand else None
        
        result = {"skill": None, "block": False, "dodge": None, "message": "Chưa phát hiện cử chỉ"}

        if not pose_res.pose_landmarks:
            return result

        pose = pose_res.pose_landmarks[0]
        _, nose_y = self.smooth_pose_keypoint(pose, 0)
        _, l_sh_y = self.smooth_pose_keypoint(pose, 11)
        _, r_sh_y = self.smooth_pose_keypoint(pose, 12)
        l_wr_x, l_wr_y = self.smooth_pose_keypoint(pose, 15)
        r_wr_x, r_wr_y = self.smooth_pose_keypoint(pose, 16)
        _, l_hip_y = self.smooth_pose_keypoint(pose, 23)
        
        # --- DODGE: chỉ phát hiện khi thân người nghiêng rõ ---
        if self.confirm_action("dodge_left", l_sh_y > r_sh_y + self.dodge_threshold):
            self.action_counters["dodge_right"] = 0
            result["dodge"], result["message"] = "left", "Né sang TRÁI"
        elif self.confirm_action("dodge_right", r_sh_y > l_sh_y + self.dodge_threshold):
            self.action_counters["dodge_left"] = 0
            result["dodge"], result["message"] = "right", "Né sang PHẢI"

        dist_wrists = math.sqrt((l_wr_x - r_wr_x) ** 2 + (l_wr_y - r_wr_y) ** 2)

        # --- BLOCK & SKILL: bỏ qua khi đang dodge để tránh xung đột ---
        if not result["dodge"]:
            block_condition = (
                dist_wrists < self.block_wrist_dist and l_wr_y < nose_y and r_wr_y < nose_y
            )
            if self.confirm_action("block", block_condition):
                result["block"], result["message"] = True, "🛡️ ĐANG ĐỠ ĐÒN!"

            # Dùng handedness của MediaPipe thay vì x-position (chính xác hơn khi tay bắt chéo)
            is_r_open = self.last_hand_state["right_open"]
            is_l_open = self.last_hand_state["left_open"]
            if hand_res and hand_res.hand_landmarks:
                is_r_open = False
                is_l_open = False
                self.last_hand_landmarks = []
                self.hand_missing_frames = 0
                for i, hand in enumerate(hand_res.hand_landmarks):
                    label = hand_res.handedness[i][0].category_name
                    if label == "Right":   # Tay phải của người chơi
                        is_r_open = self.is_hand_open(hand)
                    else:                  # Tay trái của người chơi
                        is_l_open = self.is_hand_open(hand)
                    self.last_hand_landmarks.append([[lm.x, lm.y] for lm in hand])
                self.last_hand_state["right_open"] = is_r_open
                self.last_hand_state["left_open"] = is_l_open
            elif run_hand:
                self.hand_missing_frames += 1
                if self.hand_missing_frames >= self.clear_hand_after_misses:
                    self.last_hand_state["right_open"] = False
                    self.last_hand_state["left_open"] = False
                    self.last_hand_landmarks = []

            # Block được ưu tiên hơn skill để một frame không vừa đỡ vừa tung chiêu.
            if not result["block"]:
                left_hand_up = l_wr_y < l_sh_y
                right_hand_up = r_wr_y < r_sh_y
                kage_cond = dist_wrists < self.kage_wrist_dist and l_sh_y < l_wr_y < l_hip_y
                rasenshuriken_cond = (
                    left_hand_up and right_hand_up and is_r_open and is_l_open
                )
                # Rasengan là thế một tay. Nếu tay còn lại cũng đang ở vùng tung chiêu,
                # không fallback xuống Rasengan khi hand tracking của tay trái chớp tắt.
                rasengan_cond = right_hand_up and is_r_open and not left_hand_up

                kage_ok = self.confirm_action("kage_bunshin", kage_cond)
                rasenshuriken_ok = self.confirm_action("rasenshuriken", rasenshuriken_cond)
                if rasenshuriken_cond:
                    self.action_counters["rasengan"] = 0
                    rasengan_ok = False
                else:
                    rasengan_ok = self.confirm_action("rasengan", rasengan_cond)

                if kage_ok:
                    result["skill"], result["message"] = "kage_bunshin", "👥 KAGE BUNSHIN!"
                elif rasenshuriken_ok:
                    result["skill"], result["message"] = "rasenshuriken", "🌪️ RASENSHURIKEN!"
                elif rasengan_ok:
                    result["skill"], result["message"] = "rasengan", "🌀 RASENGAN!"
            else:
                self.action_counters["kage_bunshin"] = 0
                self.action_counters["rasenshuriken"] = 0
                self.action_counters["rasengan"] = 0
        else:
            self.action_counters["block"] = 0
            self.action_counters["kage_bunshin"] = 0
            self.action_counters["rasenshuriken"] = 0
            self.action_counters["rasengan"] = 0

        raw_skill = result["skill"]
        smoothed_skill = self.smooth_skill(raw_skill)
        if smoothed_skill != result["skill"]:
            result["skill"] = smoothed_skill
            if smoothed_skill is None and not result["block"] and not result["dodge"]:
                result["message"] = "Đang ổn định cử chỉ..."

        gated_skill = self.gate_skill_repeat(result["skill"], raw_skill)
        if gated_skill != result["skill"]:
            result["skill"] = gated_skill
            if gated_skill is None and not result["block"] and not result["dodge"]:
                result["message"] = "Đã nhận skill, chờ đổi tư thế..."

        # Đóng gói tọa độ khung xương để vẽ ở frontend
        landmarks = {
            "pose": [[lm.x, lm.y] for lm in pose] if pose else [],
            "hands": self.last_hand_landmarks
        }
        
        result["landmarks"] = landmarks
        return result

# Instance toàn cục
_detector = GestureDetector()

def process_frame(image):
    return _detector.process_frame(image)
