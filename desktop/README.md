# Desktop App Guide - Shinobi Vision Battle

Tài liệu này hướng dẫn chạy phiên bản desktop (local mode) trong thư mục `desktop/`.

## 1. Yêu cầu

- Windows + PowerShell.
- Python 3.10+ (khuyến nghị 3.12 để build `.exe` ổn định hơn).
- Webcam hoạt động bình thường.

## 2. Chạy nhanh (khuyến nghị)

Chạy từ thư mục gốc dự án:

```powershell
cd E:\AI\Computer-Vision\shinobi-vision-battle
.\desktop\run_desktop.ps1
```

Script `run_desktop.ps1` sẽ:

1. Tự tạo môi trường ảo `desktop/.venv` nếu chưa có.
2. Tự cài thư viện từ `desktop/requirements.txt` nếu thiếu.
3. Kiểm tra asset bắt buộc.
4. Chạy app desktop (`desktop/main.py`).

## 3. Chạy thủ công (không dùng script)

```powershell
cd E:\AI\Computer-Vision\shinobi-vision-battle
python -m venv .\desktop\.venv
.\desktop\.venv\Scripts\python -m pip install -r .\desktop\requirements.txt
.\desktop\.venv\Scripts\python .\desktop\main.py
```

## 4. Build file EXE

```powershell
cd E:\AI\Computer-Vision\shinobi-vision-battle
.\desktop\build_desktop.ps1
```

Sau khi build xong, file chạy ở:

```text
dist\ShinobiVisionBattle\ShinobiVisionBattle.exe
```

## 5. Phím điều khiển

- `1`: Kage Bunshin
- `2`: Rasengan
- `3`: Rasenshuriken
- `B`: Block
- `A` / `D`: Dodge trái / phải
- `R`: Reset trận
- `H`: Bật/tắt skeleton
- `P`: Bật/tắt camera preview
- `Space`: Pause/Resume
- `F11`: Fullscreen
- `ESC`: Thoát

## 6. Tuỳ chỉnh hiệu năng bằng biến môi trường

Ví dụ cấu hình trước khi chạy:

```powershell
$env:DESKTOP_PERFORMANCE_PRESET="balanced"  # low | balanced | high
$env:DESKTOP_CAMERA_WIDTH="640"
$env:DESKTOP_CAMERA_HEIGHT="480"
$env:DESKTOP_CAMERA_FPS="30"
$env:DESKTOP_AI_FPS="18"
$env:DESKTOP_PREVIEW_FPS="12"
$env:DESKTOP_CAMERA_INDEX="0"               # đổi nếu có nhiều webcam
$env:DESKTOP_CAMERA_MIRROR="0"              # 0 = normal, 1 = mirror
.\desktop\run_desktop.ps1
```

Các biến nâng cao có hỗ trợ:

- `DESKTOP_AI_PRIORITY_MODE` (`1` hoặc `0`)
- `DESKTOP_PREVIEW_FPS_MIN`
- `DESKTOP_PREVIEW_FPS_MAX`
- `DESKTOP_AI_LATENCY_HIGH_MS`
- `DESKTOP_AI_LATENCY_LOW_MS`
- `GESTURE_STABILITY_PRESET` (`fast`, `balanced`, `stable`)
- `SKILL_REPEAT_COOLDOWN_FRAMES`
- `SKILL_RELEASE_FRAMES`
- `SKILL_SWITCH_GUARD_FRAMES`

## 7. Lỗi thường gặp

- Không mở được script `.ps1`:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- Camera đen hoặc không nhận:
  - Đổi `DESKTOP_CAMERA_INDEX` sang `1`, `2`, ...
  - Đóng app khác đang chiếm webcam (Zoom, Teams, OBS...).
- Thiếu thư viện khi chạy:
  ```powershell
  .\desktop\.venv\Scripts\python -m pip install -r .\desktop\requirements.txt
  ```
- Thiếu asset:
  - Kiểm tra còn đầy đủ thư mục `frontend/assets/images/...`.

## 8. File cấu hình runtime

App lưu một phần cấu hình menu vào:

```text
desktop\settings.json
```

Có thể xoá file này để reset lựa chọn camera/performance về mặc định.
