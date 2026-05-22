"""
Module: app.py
Tác giả: Antigravity (Backend Developer)
Mô tả: Server WebSocket xử lý luồng ảnh thời gian thực cho game Shinobi Vision Battle.
"""

import base64
import cv2
import numpy as np
import time
import os
import threading
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from flask import Flask, request
from flask_socketio import SocketIO, emit
try:
    from backend.gesture_detector import process_frame  # Package mode
    from backend.game_logic import GameState, update_game_state
except ImportError:
    from gesture_detector import process_frame  # Script mode fallback
    from game_logic import GameState, update_game_state

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình SocketIO
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    max_http_buffer_size=20000000 
)

frame_count = 0 # Biến đếm để log
games = {} # Trạng thái game riêng theo từng Socket.IO client
client_runtime = {}  # Theo dõi tốc độ xử lý theo từng client
game_locks = {}
pending_futures = {}
pending_start_ts = {}
latency_stats = {}
runtime_lock = threading.Lock()
TARGET_AI_FPS = float(os.getenv("TARGET_AI_FPS", "15"))
if TARGET_AI_FPS <= 0:
    TARGET_AI_FPS = 15.0
MIN_PROCESS_INTERVAL_SEC = 1.0 / TARGET_AI_FPS
INFERENCE_WORKERS = max(1, int(os.getenv("INFERENCE_WORKERS", "1")))
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "thread").strip().lower()
if INFERENCE_MODE not in ("thread", "process"):
    INFERENCE_MODE = "thread"
LATENCY_LOG_INTERVAL_SEC = float(os.getenv("LATENCY_LOG_INTERVAL_SEC", "5"))
inference_pool = None
BACKEND_CAMERA_MODE = os.getenv("BACKEND_CAMERA_MODE", "0").strip() in ("1", "true", "True")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
BACKEND_CAMERA_FPS = float(os.getenv("BACKEND_CAMERA_FPS", "15"))
if BACKEND_CAMERA_FPS <= 0:
    BACKEND_CAMERA_FPS = 15.0
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "480"))
BACKEND_PREVIEW_FPS = float(os.getenv("BACKEND_PREVIEW_FPS", "15"))
if BACKEND_PREVIEW_FPS <= 0:
    BACKEND_PREVIEW_FPS = 15.0
BACKEND_PREVIEW_JPEG_QUALITY = int(os.getenv("BACKEND_PREVIEW_JPEG_QUALITY", "40"))
if BACKEND_PREVIEW_JPEG_QUALITY < 20:
    BACKEND_PREVIEW_JPEG_QUALITY = 20
if BACKEND_PREVIEW_JPEG_QUALITY > 95:
    BACKEND_PREVIEW_JPEG_QUALITY = 95
BACKEND_PREVIEW_MAX_WIDTH = int(os.getenv("BACKEND_PREVIEW_MAX_WIDTH", "320"))
if BACKEND_PREVIEW_MAX_WIDTH < 200:
    BACKEND_PREVIEW_MAX_WIDTH = 200
camera_thread = None
camera_stop_event = threading.Event()
camera_loop_lock = threading.Lock()
active_backend_camera_sid = None
preview_seq = 0

def get_client_game():
    """Lấy hoặc tạo trạng thái game riêng cho client hiện tại."""
    sid = request.sid
    if sid not in games:
        games[sid] = GameState()
    if sid not in game_locks:
        game_locks[sid] = threading.Lock()
    return games[sid]

def ensure_client_runtime(sid):
    client_runtime.setdefault(sid, {"last_process_ts": 0.0})
    latency_stats.setdefault(
        sid,
        {
            "samples_ms": deque(maxlen=120),
            "processed": 0,
            "dropped_busy": 0,
            "dropped_fps_limit": 0,
            "last_log_ts": time.perf_counter(),
        },
    )

def maybe_log_latency(sid):
    stats = latency_stats.get(sid)
    if not stats:
        return
    now = time.perf_counter()
    if now - stats["last_log_ts"] < LATENCY_LOG_INTERVAL_SEC:
        return
    stats["last_log_ts"] = now

    samples = list(stats["samples_ms"])
    if not samples:
        print(
            f"📊 [{sid[:6]}] no samples | processed={stats['processed']} "
            f"drop_busy={stats['dropped_busy']} drop_fps={stats['dropped_fps_limit']}"
        )
        return

    samples.sort()
    avg_ms = sum(samples) / len(samples)
    p95_ms = samples[min(len(samples) - 1, int(len(samples) * 0.95))]
    print(
        f"📊 [{sid[:6]}] latency avg={avg_ms:.1f}ms p95={p95_ms:.1f}ms "
        f"samples={len(samples)} processed={stats['processed']} "
        f"drop_busy={stats['dropped_busy']} drop_fps={stats['dropped_fps_limit']}"
    )

def emit_game_update(game, ai_result, sid=None):
    """Tính toán và gửi game_update về đúng client."""
    game_state = update_game_state(
        game,
        ai_result.get("skill"),
        ai_result.get("block", False),
        ai_result.get("dodge"),
    )
    game_state["landmarks"] = ai_result.get("landmarks", {})
    if sid:
        socketio.emit('game_update', game_state, to=sid)
    else:
        emit('game_update', game_state)

def run_inference(img_bytes):
    """Hàm inference chạy trong worker process."""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"skill": None, "block": False, "dodge": None, "landmarks": {}}
    return process_frame(img)

def get_inference_pool():
    global inference_pool
    if inference_pool is None:
        if INFERENCE_MODE == "process":
            inference_pool = ProcessPoolExecutor(max_workers=INFERENCE_WORKERS)
        else:
            inference_pool = ThreadPoolExecutor(max_workers=INFERENCE_WORKERS)
    return inference_pool

def handle_inference_done(sid, start_ts, future):
    """Nhận kết quả ngay khi worker xong, tránh chờ frame kế tiếp mới emit."""
    try:
        ai_result = future.result()
        if ai_result.get("skill"):
            print(f"🔥 [{sid[:6]}] Phát hiện tư thế: {ai_result['skill'].upper()}")

        game = games.get(sid)
        lock = game_locks.get(sid)
        if game is not None and lock is not None:
            with lock:
                emit_game_update(game, ai_result, sid=sid)

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        with runtime_lock:
            stats = latency_stats.get(sid)
            if stats:
                stats["samples_ms"].append(elapsed_ms)
                stats["processed"] += 1
    except Exception as e:
        print(f"⚠️ Lỗi worker inference ({sid}): {str(e)}")
    finally:
        with runtime_lock:
            current = pending_futures.get(sid)
            if current is future:
                pending_futures.pop(sid, None)
                pending_start_ts.pop(sid, None)
        maybe_log_latency(sid)

def run_backend_camera_loop():
    """Đọc camera trực tiếp ở backend và xử lý AI theo active sid."""
    global frame_count, preview_seq
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"❌ Không mở được backend camera index={CAMERA_INDEX}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, BACKEND_CAMERA_FPS)
    frame_interval = 1.0 / BACKEND_CAMERA_FPS
    preview_every_n = max(1, int(round(BACKEND_CAMERA_FPS / BACKEND_PREVIEW_FPS)))
    print(
        f"🎥 Backend camera mode ON | index={CAMERA_INDEX} | "
        f"{CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {BACKEND_CAMERA_FPS:.1f}fps"
    )

    try:
        while not camera_stop_event.is_set():
            sid = active_backend_camera_sid
            if not sid or sid not in games:
                time.sleep(0.05)
                continue

            frame_start = time.perf_counter()
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.02)
                continue

            frame_count += 1
            if frame_count == 1 or frame_count % 30 == 0:
                print(f"📡 Backend camera frame {frame_count}...")

            ai_result = process_frame(frame)
            if ai_result.get("skill"):
                print(f"🔥 [{sid[:6]}] Phát hiện tư thế: {ai_result['skill'].upper()}")

            game = games.get(sid)
            lock = game_locks.get(sid)
            if game is not None and lock is not None:
                with lock:
                    emit_game_update(game, ai_result, sid=sid)

            if frame_count % preview_every_n == 0:
                preview_frame = frame
                ph, pw = frame.shape[:2]
                if pw > BACKEND_PREVIEW_MAX_WIDTH:
                    scale = BACKEND_PREVIEW_MAX_WIDTH / float(pw)
                    preview_frame = cv2.resize(
                        frame,
                        (BACKEND_PREVIEW_MAX_WIDTH, int(ph * scale)),
                        interpolation=cv2.INTER_AREA,
                    )
                ok_preview, encoded = cv2.imencode(
                    ".jpg",
                    preview_frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), BACKEND_PREVIEW_JPEG_QUALITY],
                )
                if ok_preview:
                    preview_seq += 1
                    socketio.emit(
                        "camera_preview_bin",
                        {"seq": preview_seq, "image_bytes": encoded.tobytes()},
                        to=sid,
                    )

            elapsed_ms = (time.perf_counter() - frame_start) * 1000.0
            with runtime_lock:
                stats = latency_stats.get(sid)
                if stats:
                    stats["samples_ms"].append(elapsed_ms)
                    stats["processed"] += 1
            maybe_log_latency(sid)

            remaining = frame_interval - (time.perf_counter() - frame_start)
            if remaining > 0:
                time.sleep(remaining)
    finally:
        cap.release()
        print("🛑 Backend camera loop stopped.")

def ensure_backend_camera_loop():
    global camera_thread
    if not BACKEND_CAMERA_MODE:
        return
    with camera_loop_lock:
        if camera_thread and camera_thread.is_alive():
            return
        camera_stop_event.clear()
        camera_thread = threading.Thread(target=run_backend_camera_loop, daemon=True)
        camera_thread.start()

def stop_backend_camera_loop():
    if not BACKEND_CAMERA_MODE:
        return
    camera_stop_event.set()


@socketio.on('connect')
def handle_connect():
    """Sự kiện xảy ra khi một Shinobi (Client) kết nối thành công."""
    sid = request.sid
    print(f"✅ Client đã kết nối: {sid}")
    
    games[sid] = GameState()
    game_locks[sid] = threading.Lock()
    ensure_client_runtime(sid)
    emit('server_config', {"backend_camera_mode": BACKEND_CAMERA_MODE})
    if BACKEND_CAMERA_MODE:
        global active_backend_camera_sid
        active_backend_camera_sid = sid
        ensure_backend_camera_loop()
    
    print(f"🎮 Game đã được reset. Sẵn sàng chiến đấu!")

@socketio.on('disconnect')
def handle_disconnect():
    """Sự kiện xảy ra khi Client ngắt kết nối."""
    sid = request.sid
    games.pop(sid, None)
    game_locks.pop(sid, None)
    client_runtime.pop(sid, None)
    pending_futures.pop(sid, None)
    pending_start_ts.pop(sid, None)
    latency_stats.pop(sid, None)
    global active_backend_camera_sid
    if BACKEND_CAMERA_MODE and active_backend_camera_sid == sid:
        active_backend_camera_sid = next(iter(games.keys()), None)
        if active_backend_camera_sid is None:
            stop_backend_camera_loop()
    print(f"❌ Client ngắt kết nối: {sid}")

@socketio.on('reset_game')
def handle_reset_game():
    """Sự kiện xảy ra khi người chơi bấm nút Chơi Lại trên web."""
    sid = request.sid
    game = get_client_game()
    print(f"🔄 Đang Reset trận đấu cho client {sid}...")
    game.reset_game()
    # Không cần emit lại trạng thái máu, vì lần gửi ảnh tiếp theo sẽ tự cập nhật máu 100/100

@socketio.on('video_frame')
def handle_video_frame(data):
    """
    Sự kiện nhận frame ảnh từ Webcam của client gửi lên liên tục.
    """
    global frame_count
    if BACKEND_CAMERA_MODE:
        return
    frame_count += 1
    if frame_count == 1 or frame_count % 30 == 0:
        print(f"📡 Server đang nhận ảnh từ Webcam (Khung hình thứ {frame_count})...")

    try:
        sid = request.sid
        ensure_client_runtime(sid)
        if sid not in games:
            games[sid] = GameState()
        if sid not in game_locks:
            game_locks[sid] = threading.Lock()

        pending = pending_futures.get(sid)
        if pending and not pending.done():
            latency_stats[sid]["dropped_busy"] += 1
            maybe_log_latency(sid)
            return

        now = time.perf_counter()
        runtime = client_runtime.setdefault(sid, {"last_process_ts": 0.0})
        if now - runtime["last_process_ts"] < MIN_PROCESS_INTERVAL_SEC:
            latency_stats[sid]["dropped_fps_limit"] += 1
            maybe_log_latency(sid)
            return
        runtime["last_process_ts"] = now

        if not isinstance(data, dict):
            return

        image_data = data.get('image')
        if not image_data: return

        if "," in image_data:
            image_data = image_data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        pool = get_inference_pool()
        start_ts = time.perf_counter()
        future = pool.submit(run_inference, img_bytes)
        with runtime_lock:
            pending_futures[sid] = future
            pending_start_ts[sid] = start_ts
        future.add_done_callback(
            lambda done_future, client_sid=sid, submitted_at=start_ts: handle_inference_done(
                client_sid,
                submitted_at,
                done_future,
            )
        )
        maybe_log_latency(sid)

    except Exception as e:
        print(f"⚠️ Lỗi xử lý frame: {str(e)}")

@socketio.on('manual_input')
def handle_manual_input(data):
    """
    Fallback khi không có webcam:
    nhận input từ bàn phím frontend và update game state.
    """
    try:
        game = get_client_game()
        if not isinstance(data, dict):
            return

        ai_result = {
            "skill": data.get("skill"),
            "block": bool(data.get("block", False)),
            "dodge": data.get("dodge"),
            "landmarks": {}
        }
        with game_locks[request.sid]:
            emit_game_update(game, ai_result)
    except Exception as e:
        print(f"⚠️ Lỗi manual_input: {str(e)}")

if __name__ == '__main__':
    # Khởi chạy server:
    # - host='0.0.0.0': Cho phép truy cập từ mạng nội bộ (máy tính khác trong cùng Wi-Fi)
    # - port=5000: Cổng mặc định của Flask
    # - debug=True: Tự động tải lại code khi có thay đổi (chỉ dùng khi phát triển)
    print("🔥 Shinobi Server đang khởi động tại cổng 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
