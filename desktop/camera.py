import os
import threading
import time
from collections import deque

import cv2


class CameraStream:
    def __init__(self, index=0, width=640, height=480, fps=30, mirror=False):
        self.index = index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.mirror = mirror
        self._cap = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_ts = 0.0
        self._frame_times = deque(maxlen=90)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        try:
            if os.name == "nt":
                self._cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            else:
                self._cap = cv2.VideoCapture(self.index)
            if not self._cap.isOpened():
                self._cap = None
        except Exception:
            self._cap = None

        if self._cap is None:
            return

        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self._cap:
            self._cap.release()
        self._cap = None

    def read_latest(self):
        with self._lock:
            return self._latest_frame, self._latest_ts

    def actual_fps(self):
        with self._lock:
            if len(self._frame_times) < 2:
                return 0.0
            span = self._frame_times[-1] - self._frame_times[0]
            if span <= 0:
                return 0.0
            return (len(self._frame_times) - 1) / span

    def _run(self):
        interval = 1.0 / max(self.target_fps, 1)
        while not self._stop.is_set():
            t0 = time.perf_counter()
            ok, frame = self._cap.read()
            if ok and frame is not None:
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                with self._lock:
                    self._latest_frame = frame
                    self._latest_ts = time.perf_counter()
                    self._frame_times.append(self._latest_ts)
            elapsed = time.perf_counter() - t0
            remain = interval - elapsed
            if remain > 0:
                time.sleep(remain)
