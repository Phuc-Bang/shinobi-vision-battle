# Shinobi Vision Battle (Naruto vs Mizuki)

Chào mừng bạn đến với dự án game đối kháng sử dụng công nghệ nhận diện cử chỉ (Computer Vision).

## 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- Webcam (để nhận diện thủ ấn).
- Trình duyệt web hiện đại (Chrome, Edge, Firefox).

## 2. Hướng dẫn cài đặt Backend
1. Mở terminal tại thư mục `backend/`.
2. Tạo môi trường ảo:
   ```bash
   python -m venv venv
   ```
3. Kích hoạt môi trường ảo:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Cài đặt các thư viện:
   ```bash
   pip install -r requirements.txt
   ```

## 3. Cách chạy dự án
- **Backend**: Chạy lệnh `python app.py`. Server sẽ lắng nghe tại `http://localhost:5000`.
- **Frontend**: 
  - Cách 1: Sử dụng Extension "Live Server" trên VS Code.
  - Cách 2: Chạy lệnh `python -m http.server 8000` tại thư mục `frontend/` và truy cập `http://localhost:8000`.

## 4. Lưu ý quan trọng
- **WebSocket**: Game sử dụng SocketIO để truyền tọa độ tay từ Python lên JS với độ trễ thấp.
- **CORS**: Backend đã được cấu hình `cors_allowed_origins="*"` để tránh lỗi chặn kết nối từ trình duyệt.

## 5. Cốt truyện
Làng Lá yên bình, Naruto đang luyện Rasengan cùng thầy Kakashi bên suối. Bỗng Mizuki hiện ra từ bóng tối, cười khẩy: 'Kẻ đần độn như mày xứng đáng làm Hokage ư?' Naruto siết chặt tay, luồng Chakra dâng trào. Hắn biết đây là lúc phải dùng những gì đã học: Kage Bunshin, Rasengan, và cả Rasenshuriken - chiêu thức cấm chưa hoàn thiện. Trận chiến sinh tử bắt đầu. Liệu Naruto có bảo vệ được danh dự của ninja làng Lá?
