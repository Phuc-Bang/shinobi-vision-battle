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

## 3.1 Desktop Local Mode (không qua web)
- Mục tiêu: chạy camera + AI + game hoàn toàn trong app Python local.
- Cài thư viện:
  ```bash
  pip install -r desktop/requirements.txt
  ```
- Chạy:
  - Windows PowerShell:
    ```powershell
    .\desktop\run_desktop.ps1
    ```
    Script này dùng môi trường riêng `desktop/.venv`, tự tạo và cài `desktop/requirements.txt` nếu thiếu.
  - Hoặc:
    ```bash
    python desktop/main.py
    ```
- Tùy chỉnh hiệu năng camera (PowerShell ví dụ):
  ```powershell
  # Performance preset: low | balanced | high
  $env:DESKTOP_PERFORMANCE_PRESET="balanced"
  $env:DESKTOP_CAMERA_WIDTH="640"
  $env:DESKTOP_CAMERA_HEIGHT="480"
  $env:DESKTOP_CAMERA_FPS="30"
  $env:DESKTOP_AI_FPS="15"
  $env:DESKTOP_PREVIEW_FPS="15"
  $env:DESKTOP_AI_PRIORITY_MODE="1"
  $env:DESKTOP_PREVIEW_FPS_MIN="8"
  $env:DESKTOP_PREVIEW_FPS_MAX="15"
  $env:DESKTOP_AI_LATENCY_HIGH_MS="70"
  $env:DESKTOP_AI_LATENCY_LOW_MS="45"
  $env:DESKTOP_CAMERA_MIRROR="0"   # 0 = normal, 1 = mirror
  # Gesture stability preset: fast | balanced | stable
  $env:GESTURE_STABILITY_PRESET="balanced"
  # Tinh chỉnh sâu nếu cần (backend/desktop dùng chung detector)
  $env:SKILL_REPEAT_COOLDOWN_FRAMES="8"
  $env:SKILL_RELEASE_FRAMES="8"
  $env:SKILL_SWITCH_GUARD_FRAMES="2"
  .\desktop\run_desktop.ps1
  ```
- Gợi ý chọn `DESKTOP_PERFORMANCE_PRESET`:
  - `low`: máy yếu, ưu tiên ổn định FPS và ít nóng máy.
  - `balanced`: mặc định, phù hợp đa số laptop.
  - `high`: AI kiểm tra nhiều frame hơn, hợp máy khỏe.
- Gợi ý chọn `GESTURE_STABILITY_PRESET`:
  - `fast`: phản hồi nhanh nhất, hợp khi ánh sáng tốt và camera rõ.
  - `balanced`: mặc định, cân bằng giữa tốc độ và chống nhiễu.
  - `stable`: ít nhận nhầm hơn, hợp khi tay bị rung hoặc tracking chập chờn.

## 3.2 Build Desktop App (.exe)
- Khuyến nghị dùng Python 3.12 cho desktop build. Script sẽ tạo môi trường riêng tại `desktop/.venv`.
- Build bản desktop local:
  ```powershell
  cd E:\AI\Computer-Vision\shinobi-vision-battle
  .\desktop\build_desktop.ps1
  ```
- File chạy sau khi build:
  ```powershell
  .\dist\ShinobiVisionBattle\ShinobiVisionBattle.exe
  ```
- Bản build dùng dạng `onedir`: vẫn có `.exe`, nhưng đi kèm thư mục asset/model để mở nhanh và ổn định hơn với MediaPipe.
- Phím tắt test:
  - `1` = Kage Bunshin
  - `2` = Rasengan
  - `3` = Rasenshuriken
  - `B` = Block
  - `A / D` = Dodge
  - `R` = Reset
  - `H` = Toggle skeleton
  - `P` = Toggle camera preview
  - `Space` = Pause
  - `ESC` = Thoát

## 4. Lưu ý quan trọng
- **WebSocket**: Game sử dụng SocketIO để truyền tọa độ tay từ Python lên JS với độ trễ thấp.
- **CORS**: Backend đã được cấu hình `cors_allowed_origins="*"` để tránh lỗi chặn kết nối từ trình duyệt.

## 5. Cốt truyện
Làng Lá yên bình, Naruto đang luyện Rasengan cùng thầy Kakashi bên suối. Bỗng Mizuki hiện ra từ bóng tối, cười khẩy: 'Kẻ đần độn như mày xứng đáng làm Hokage ư?' Naruto siết chặt tay, luồng Chakra dâng trào. Hắn biết đây là lúc phải dùng những gì đã học: Kage Bunshin, Rasengan, và cả Rasenshuriken - chiêu thức cấm chưa hoàn thiện. Trận chiến sinh tử bắt đầu. Liệu Naruto có bảo vệ được danh dự của ninja làng Lá?
