import threading
import time
from collections import deque


class InputState:
    def __init__(self):
        self._lock = threading.Lock()
        self._ai_times = deque(maxlen=120)
        self._latencies = deque(maxlen=120)
        self._snapshot = {
            "skill": None,
            "block": False,
            "dodge": None,
            "landmarks": {"pose": [], "hands": []},
            "latency_ms": 0.0,
            "latency_avg_ms": 0.0,
            "latency_p95_ms": 0.0,
            "ai_fps_actual": 0.0,
            "ts": 0.0,
        }
        self._last_consumed_skill = None

    def update(self, skill, block, dodge, landmarks, latency_ms):
        with self._lock:
            now = time.perf_counter()
            self._ai_times.append(now)
            self._latencies.append(float(latency_ms))
            ai_fps = self._rate_from_times(self._ai_times)
            latency_avg = sum(self._latencies) / len(self._latencies)
            latency_p95 = self._percentile(self._latencies, 95)
            self._snapshot = {
                "skill": skill,
                "block": bool(block),
                "dodge": dodge,
                "landmarks": landmarks or {"pose": [], "hands": []},
                "latency_ms": float(latency_ms),
                "latency_avg_ms": latency_avg,
                "latency_p95_ms": latency_p95,
                "ai_fps_actual": ai_fps,
                "ts": now,
            }

    def snapshot(self):
        with self._lock:
            return dict(self._snapshot)

    def consume_skill_once(self, skill):
        with self._lock:
            if not skill:
                self._last_consumed_skill = None
                return None
            if self._last_consumed_skill == skill:
                return None
            self._last_consumed_skill = skill
            return skill

    def _rate_from_times(self, times):
        if len(times) < 2:
            return 0.0
        span = times[-1] - times[0]
        if span <= 0:
            return 0.0
        return (len(times) - 1) / span

    def _percentile(self, values, percentile):
        if not values:
            return 0.0
        ordered = sorted(values)
        index = int(round((len(ordered) - 1) * percentile / 100.0))
        return ordered[max(0, min(index, len(ordered) - 1))]
