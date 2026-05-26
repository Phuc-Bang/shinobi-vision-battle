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
        self.stability_preset = os.getenv("GESTURE_STABILITY_PRESET", "balanced").strip().lower()
        if self.stability_preset not in ("fast", "balanced", "stable"):
            self.stability_preset = "balanced"
        stability = self._stability_defaults(self.stability_preset)
        self.pose_model_variant = os.getenv("POSE_MODEL_VARIANT", "lite").strip().lower()
        if self.pose_model_variant not in ("lite", "full", "heavy"):
            self.pose_model_variant = "lite"
        self.pose_model_path = os.path.join(
            self.base_path, f'pose_landmarker_{self.pose_model_variant}.task'
        )
        self._inference_lock = threading.Lock()
        self.frame_index = 0
        self.hand_detect_interval = self._env_int("HAND_DETECT_INTERVAL", stability["hand_detect_interval"])
        self.last_hand_state = {"right_open": False, "left_open": False}
        self.last_hand_landmarks = []
        self.hand_missing_frames = 0
        self.clear_hand_after_misses = self._env_int(
            "CLEAR_HAND_AFTER_MISSES", stability["clear_hand_after_misses"]
        )
        self.max_infer_width = self._env_int("MAX_INFER_WIDTH", stability["max_infer_width"])
        self.skill_smooth_window = self._env_int("SKILL_SMOOTH_WINDOW", stability["skill_smooth_window"])
        self.skill_history = deque(maxlen=max(2, self.skill_smooth_window))
        self.pose_ema_alpha = self._env_float("POSE_EMA_ALPHA", stability["pose_ema_alpha"])
        self.pose_keypoint_cache = {}
        self.dodge_threshold = self._env_float("DODGE_SHOULDER_DIFF", stability["dodge_threshold"])
        self.block_wrist_dist = self._env_float("BLOCK_WRIST_DIST", stability["block_wrist_dist"])
        self.kage_wrist_dist = self._env_float("KAGE_WRIST_DIST", stability["kage_wrist_dist"])
        self.charge_wrist_dist = self._env_float("CHARGE_WRIST_DIST", stability["charge_wrist_dist"])
        self.action_confirm_frames = self._env_int("ACTION_CONFIRM_FRAMES", stability["action_confirm_frames"])
        self.skill_repeat_cooldown_frames = self._env_int(
            "SKILL_REPEAT_COOLDOWN_FRAMES", stability["skill_repeat_cooldown_frames"]
        )
        self.skill_release_frames = self._env_int("SKILL_RELEASE_FRAMES", stability["skill_release_frames"])
        self.skill_switch_guard_frames = self._env_int(
            "SKILL_SWITCH_GUARD_FRAMES", stability["skill_switch_guard_frames"]
        )
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
            "charge_chakra": 0,
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

    def _env_int(self, name, default):
        return int(os.getenv(name, str(default)))

    def _env_float(self, name, default):
        return float(os.getenv(name, str(default)))

    def _stability_defaults(self, preset):
        presets = {
            "fast": {
                "hand_detect_interval": 1,
                "clear_hand_after_misses": 2,
                "max_infer_width": 640,
                "skill_smooth_window": 3,
                "pose_ema_alpha": 0.45,
                "dodge_threshold": 0.065,
                "block_wrist_dist": 0.145,
                "kage_wrist_dist": 0.135,
                "charge_wrist_dist": 0.095,
                "action_confirm_frames": 1,
                "skill_repeat_cooldown_frames": 6,
                "skill_release_frames": 5,
                "skill_switch_guard_frames": 1,
            },
            "balanced": {
                "hand_detect_interval": 2,
                "clear_hand_after_misses": 3,
                "max_infer_width": 640,
                "skill_smooth_window": 4,
                "pose_ema_alpha": 0.35,
                "dodge_threshold": 0.07,
                "block_wrist_dist": 0.14,
                "kage_wrist_dist": 0.13,
                "charge_wrist_dist": 0.09,
                "action_confirm_frames": 2,
                "skill_repeat_cooldown_frames": 8,
                "skill_release_frames": 8,
                "skill_switch_guard_frames": 2,
            },
            "stable": {
                "hand_detect_interval": 2,
                "clear_hand_after_misses": 4,
                "max_infer_width": 640,
                "skill_smooth_window": 5,
                "pose_ema_alpha": 0.28,
                "dodge_threshold": 0.08,
                "block_wrist_dist": 0.13,
                "kage_wrist_dist": 0.12,
                "charge_wrist_dist": 0.085,
                "action_confirm_frames": 3,
                "skill_repeat_cooldown_frames": 12,
                "skill_release_frames": 10,
                "skill_switch_guard_frames": 3,
            },
        }
        return presets[preset]

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
        # Sử dụng giải thuật khoảng cách Euclid tương đối so với cổ tay (Landmark 0)
        # Giúp nhận diện chính xác kể cả khi tay nghiêng, xoay ngang hoặc chéo (rotation & scale invariant)
        wrist = hand_lms[0]
        tips = [8, 12, 16, 20]  # Đầu các ngón: Trỏ, Giữa, Áp út, Út
        opened = 0
        
        for tip in tips:
            # Khớp gốc ngón tương ứng (MCP): index=5, middle=9, ring=13, pinky=17
            mcp = hand_lms[tip - 3]
            
            dist_to_tip = self.get_distance(wrist, hand_lms[tip])
            dist_to_mcp = self.get_distance(wrist, mcp)
            
            # Nếu đầu ngón tay duỗi xa hơn khớp gốc ít nhất 10% (để tránh nhiễu/jitter)
            if dist_to_tip > dist_to_mcp * 1.1:
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
        if self.last_emitted_skill is None:
            self.last_emitted_skill = skill
            self.last_skill_frame = self.frame_index
            return skill

        # Cùng một skill: chỉ cho phát lại sau một khoảng cooldown frame.
        if skill == self.last_emitted_skill:
            if frames_since_emit >= max(1, self.skill_repeat_cooldown_frames):
                self.last_skill_frame = self.frame_index
                return skill
            return None

        # Đổi skill quá nhanh thường là nhiễu do tracking dao động.
        if frames_since_emit < max(1, self.skill_switch_guard_frames):
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
        l_sh_x, l_sh_y = self.smooth_pose_keypoint(pose, 11)
        r_sh_x, r_sh_y = self.smooth_pose_keypoint(pose, 12)
        l_wr_x, l_wr_y = self.smooth_pose_keypoint(pose, 15)
        r_wr_x, r_wr_y = self.smooth_pose_keypoint(pose, 16)
        _, l_hip_y = self.smooth_pose_keypoint(pose, 23)
        
        # Cân chỉnh động dựa trên độ rộng vai để hoạt động ổn định ở mọi khoảng cách (scale-invariant)
        shoulder_dist = math.sqrt((l_sh_x - r_sh_x) ** 2 + (l_sh_y - r_sh_y) ** 2)
        if shoulder_dist < 0.05:
            shoulder_dist = 0.20
        scale_factor = shoulder_dist / 0.20
        
        dynamic_dodge_threshold = self.dodge_threshold * scale_factor
        dynamic_block_wrist_dist = self.block_wrist_dist * scale_factor
        dynamic_kage_wrist_dist = self.kage_wrist_dist * scale_factor
        dynamic_charge_wrist_dist = self.charge_wrist_dist * scale_factor
        
        # --- DODGE: chỉ phát hiện khi thân người nghiêng rõ ---
        if self.confirm_action("dodge_left", l_sh_y > r_sh_y + dynamic_dodge_threshold):
            self.action_counters["dodge_right"] = 0
            result["dodge"], result["message"] = "left", "Né sang TRÁI"
        elif self.confirm_action("dodge_right", r_sh_y > l_sh_y + dynamic_dodge_threshold):
            self.action_counters["dodge_left"] = 0
            result["dodge"], result["message"] = "right", "Né sang PHẢI"

        dist_wrists = math.sqrt((l_wr_x - r_wr_x) ** 2 + (l_wr_y - r_wr_y) ** 2)

        # --- BLOCK, CHARGE & SKILL: bỏ qua khi đang dodge để tránh xung đột ---
        if not result["dodge"]:
            block_condition = (
                dist_wrists < dynamic_block_wrist_dist and l_wr_y < nose_y and r_wr_y < nose_y
            )
            charge_condition = (
                dist_wrists < dynamic_charge_wrist_dist and nose_y < l_wr_y < l_sh_y + 0.06 * scale_factor
            )

            if self.confirm_action("block", block_condition):
                result["block"], result["message"] = True, "🛡️ ĐANG ĐỠ ĐÒN!"
            elif self.confirm_action("charge_chakra", charge_condition):
                result["skill"], result["message"] = "charge_chakra", "⚡ ĐANG SẠC CHAKRA! ⚡"

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

            # Block và Charge được ưu tiên hơn các skill tấn công khác
            if not result["block"] and result["skill"] != "charge_chakra":
                self.action_counters["charge_chakra"] = 0
                left_hand_up = l_wr_y < l_sh_y
                right_hand_up = r_wr_y < r_sh_y
                kage_cond = dist_wrists < dynamic_kage_wrist_dist and l_sh_y < l_wr_y < l_hip_y
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
            elif result["block"]:
                self.action_counters["charge_chakra"] = 0
                self.action_counters["kage_bunshin"] = 0
                self.action_counters["rasenshuriken"] = 0
                self.action_counters["rasengan"] = 0
            else: # charge_chakra
                self.action_counters["block"] = 0
                self.action_counters["kage_bunshin"] = 0
                self.action_counters["rasenshuriken"] = 0
                self.action_counters["rasengan"] = 0
        else:
            self.action_counters["block"] = 0
            self.action_counters["charge_chakra"] = 0
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

_detector = None
_detector_lock = threading.Lock()
_detector_init_error = None


def _get_detector():
    global _detector, _detector_init_error
    if _detector is not None:
        return _detector
    with _detector_lock:
        if _detector is not None:
            return _detector
        if _detector_init_error is not None:
            raise RuntimeError(_detector_init_error)
        try:
            _detector = GestureDetector()
        except Exception as exc:
            _detector_init_error = f"Không thể khởi tạo gesture detector: {exc}"
            raise RuntimeError(_detector_init_error) from exc
    return _detector


def process_frame(image):
    detector = _get_detector()
    return detector.process_frame(image)
