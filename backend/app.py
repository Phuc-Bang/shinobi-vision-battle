"""
Module: app.py
Tác giả: Antigravity (Backend Developer)
Mô tả: Server WebSocket xử lý luồng ảnh thời gian thực cho game Shinobi Vision Battle.
"""

import base64
import cv2
import numpy as np
from flask import Flask, request
from flask_socketio import SocketIO, emit
from gesture_detector import process_frame # Import trực tiếp hàm xử lý từ AI
from game_logic import GameState, update_game_state # Import Logic Game

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
game = GameState() # KHỞI TẠO TRẠNG THÁI GAME GLOBAL

@socketio.on('connect')
def handle_connect():
    """Sự kiện xảy ra khi một Shinobi (Client) kết nối thành công."""
    sid = request.sid
    print(f"✅ Client đã kết nối: {sid}")
    
    # Reset game mỗi khi có người chơi mới kết nối vào
    game.reset_game()
    
    emit('game_status', {'msg': 'Kết nối máy chủ thành công. Sẵn sàng chiến đấu!'})

@socketio.on('disconnect')
def handle_disconnect():
    """Sự kiện xảy ra khi Client ngắt kết nối."""
    sid = request.sid
    print(f"❌ Client ngắt kết nối: {sid}")

@socketio.on('reset_game')
def handle_reset_game():
    """Sự kiện xảy ra khi người chơi bấm nút Chơi Lại trên web."""
    print("🔄 Đang Reset toàn bộ trận đấu...")
    game.reset_game()
    # Không cần emit lại trạng thái máu, vì lần gửi ảnh tiếp theo sẽ tự cập nhật máu 100/100

@socketio.on('video_frame')
def handle_video_frame(data):
    """
    Sự kiện nhận frame ảnh từ Webcam của client gửi lên liên tục.
    """
    global frame_count
    frame_count += 1
    if frame_count == 1 or frame_count % 30 == 0:
        print(f"📡 Server đang nhận ảnh từ Webcam (Khung hình thứ {frame_count})...")

    try:
        image_data = data.get('image')
        if not image_data: return

        if "," in image_data:
            image_data = image_data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None: return

        # 1. Gọi AI Nhận diện Cử chỉ
        ai_result = process_frame(img)
        
        # In thông báo ra Terminal nếu phát hiện kỹ năng
        if ai_result["skill"]:
            print(f"🔥 Phát hiện tư thế: {ai_result['skill'].upper()}")

        # 2. Đưa kết quả AI vào Engine Game Logic để tính toán
        game_state = update_game_state(
            game, 
            ai_result["skill"], 
            ai_result["block"], 
            ai_result["dodge"]
        )

        # 3. Gộp tọa độ khung xương (để vẽ ở web) vào dữ liệu gửi về
        game_state["landmarks"] = ai_result.get("landmarks", {})
        
        # 4. Gửi kết quả cuối cùng về Client
        emit('game_update', game_state)

    except Exception as e:
        print(f"⚠️ Lỗi xử lý frame: {str(e)}")

if __name__ == '__main__':
    # Khởi chạy server:
    # - host='0.0.0.0': Cho phép truy cập từ mạng nội bộ (máy tính khác trong cùng Wi-Fi)
    # - port=5000: Cổng mặc định của Flask
    # - debug=True: Tự động tải lại code khi có thay đổi (chỉ dùng khi phát triển)
    print("🔥 Shinobi Server đang khởi động tại cổng 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
