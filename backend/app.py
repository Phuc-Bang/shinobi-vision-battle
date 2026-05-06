import base64
import cv2
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from gesture_detector import GestureDetector
from game_logic import GameLogic

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Khởi tạo AI và Logic game
detector = GestureDetector()
game = GameLogic()

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('battle_status', {'msg': 'Chào mừng Shinobi! Hãy chuẩn bị chiến đấu.'})

@socketio.on('image')
def handle_image(data):
    # Giải mã ảnh từ base64
    try:
        header, encoded = data.split(",", 1)
        data = base64.b64decode(encoded)
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Nhận diện tay và thủ ấn
        img, hands_data = detector.find_hands(img)
        seal = detector.detect_seal(hands_data)

        if seal:
            # Xử lý logic game khi có kỹ năng được tung ra
            result = game.process_action(seal)
            emit('skill_cast', {'skill': seal, 'result': result})

        # Gửi lại ảnh đã vẽ xương khớp (tùy chọn, để debug hoặc hiển thị)
        _, buffer = cv2.imencode('.jpg', img)
        processed_img = base64.b64encode(buffer).decode('utf-8')
        emit('processed_image', processed_img)
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
