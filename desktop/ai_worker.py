import threading
import time

from backend.gesture_detector import process_frame


class AIWorker:
    def __init__(self, camera_stream, input_state, ai_fps=15):
        self.camera_stream = camera_stream
        self.input_state = input_state
        self.ai_fps = ai_fps
        self._thread = None
        self._stop = threading.Event()
        self._last_frame_ts = 0.0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self):
        interval = 1.0 / max(self.ai_fps, 1)
        while not self._stop.is_set():
            t0 = time.perf_counter()
            frame, frame_ts = self.camera_stream.read_latest()
            if frame is not None and frame_ts != self._last_frame_ts:
                self._last_frame_ts = frame_ts
                infer_t0 = time.perf_counter()
                result = process_frame(frame)
                latency_ms = (time.perf_counter() - infer_t0) * 1000.0
                self.input_state.update(
                    result.get("skill"),
                    result.get("block", False),
                    result.get("dodge"),
                    result.get("landmarks", {"pose": [], "hands": []}),
                    latency_ms,
                )
            elapsed = time.perf_counter() - t0
            remain = interval - elapsed
            if remain > 0:
                time.sleep(remain)

