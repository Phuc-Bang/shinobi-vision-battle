"""
Module: app.py
Mục đích: Khởi tạo server Flask-SocketIO để điều phối dữ liệu giữa AI và Frontend.
"""
# To be implemented (Sẽ được triển khai ở phần sau)

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
# Cấu hình CORS để cho phép frontend kết nối
socketio = SocketIO(app, cors_allowed_origins="*")

if __name__ == "__main__":
    # Khởi chạy server trên cổng 5000
    socketio.run(app, debug=True)
