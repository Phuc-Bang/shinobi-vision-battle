/**
 * Module: webcamFeed.js
 * Chuyên trách quản lý Webcam: Lấy luồng hình ảnh, vẽ lên HTML,
 * nén khung hình sang dạng Base64 và gửi lên Server qua Socket.IO.
 */

class WebcamFeed {
    constructor() {
        this.socket = null;
        this.isGameOverChecker = null;
        this.mediaStream = null;
        this.sendInterval = null;
        this.fallbackInterval = null;
        this.fps = 12; // Định kỳ 10-15 fps (ở đây chọn 12)
        
        // Các phần tử DOM sẽ được gán trong quá trình khởi tạo
        this.video = null;
        this.overlayCanvas = null;
        this.errorText = null;
    }

    /**
     * Khởi tạo Webcam và bắt đầu quá trình gửi Frame
     * @param {Object} socket - Đối tượng Socket kết nối tới Server
     * @param {Function} gameOverChecker - Hàm callback trả về True nếu game đã kết thúc
     */
    async initWebcam(socket, gameOverChecker) {
        this.socket = socket;
        this.isGameOverChecker = gameOverChecker;

        // Lấy tham chiếu DOM (đã được tạo sẵn trong index.html)
        this.video = document.getElementById('webcam-video');
        this.overlayCanvas = document.getElementById('skeleton-overlay');
        this.errorText = document.getElementById('webcam-error');

        if (!this.video) {
            console.error("Không tìm thấy thẻ <video> của Webcam.");
            return;
        }

        try {
            // Yêu cầu quyền truy cập Camera
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: 640, height: 480 },
                audio: false 
            });
            this.video.srcObject = this.mediaStream;
            
            // Đợi video thực sự phát
            await this.video.play();
            
            // Cập nhật kích thước canvas thật khớp với độ phân giải video
            // Việc này giúp thẻ canvas vẽ Khung Xương (Skeleton) hoàn toàn khớp với người thật
            if (this.overlayCanvas) {
                this.overlayCanvas.width = this.video.videoWidth;
                this.overlayCanvas.height = this.video.videoHeight;
            }

            // Ghi Log lên màn hình Game
            if (window.gameEngine) {
                window.gameEngine.instance.addLog("🎥 Camera đã sẵn sàng. Trận chiến bắt đầu!", "system");
            }

            // Bắt đầu vòng lặp gửi frame
            this.startSendingFrames();

        } catch (err) {
            console.error("❌ Lỗi Camera:", err);
            // Hiển thị thông báo lỗi vào chính giữa khung hình
            if (this.errorText) {
                this.errorText.innerText = "Không thể truy cập webcam";
                this.errorText.style.display = 'block';
            }
            if (window.gameEngine) {
                window.gameEngine.instance.addLog("❌ Lỗi Camera: " + err.name + ". Vui lòng cấp quyền!", "system");
                window.gameEngine.instance.addLog("⌨️ Fallback keyboard mode: 1/2/3, B, A/D, R, H", "system");
            }
            this.startFallbackTick();
        }
    }

    /**
     * Định kỳ (setInterval) cắt khung hình từ Video, nén ảnh và gửi đi
     */
    startSendingFrames() {
        if (this.sendInterval) clearInterval(this.sendInterval);
        if (this.fallbackInterval) {
            clearInterval(this.fallbackInterval);
            this.fallbackInterval = null;
        }

        // Tạo một canvas ẩn trong bộ nhớ để làm công cụ resize và nén ảnh
        const captureCanvas = document.createElement('canvas');
        captureCanvas.width = 640;
        captureCanvas.height = 480;
        const captureCtx = captureCanvas.getContext('2d');

        const intervalMs = 1000 / this.fps; // Thời gian chờ giữa 2 frame (ms)

        this.sendInterval = setInterval(() => {
            // XỬ LÝ ĐIỀU KIỆN DỪNG GỬI (TIẾT KIỆM BĂNG THÔNG)
            // 1. Không có socket hoặc socket mất kết nối
            if (!this.socket || !this.socket.connected) return;
            // 2. Trò chơi đã kết thúc (Game Over)
            if (this.isGameOverChecker && this.isGameOverChecker() === true) return;

            // Chụp Frame hiện tại của Video vẽ lên thẻ Canvas ẩn
            captureCtx.drawImage(this.video, 0, 0, captureCanvas.width, captureCanvas.height);
            
            // Xuất ra chuỗi Base64 (Định dạng JPEG, Chất lượng nén 0.6 để tăng tốc độ truyền tải)
            const base64String = captureCanvas.toDataURL('image/jpeg', 0.6);
            
            // Bắn sự kiện lên Backend Python
            this.socket.emit('video_frame', { image: base64String });
            
        }, intervalMs);
    }

    startFallbackTick() {
        if (this.fallbackInterval) clearInterval(this.fallbackInterval);
        this.fallbackInterval = setInterval(() => {
            if (!this.socket || !this.socket.connected) return;
            if (this.isGameOverChecker && this.isGameOverChecker() === true) return;
            this.socket.emit('manual_input', {});
        }, 250);
    }

    /**
     * Dừng lấy hình từ Camera và dọn dẹp sạch tài nguyên (Thường dùng khi thoát game)
     */
    stopWebcam() {
        if (this.sendInterval) {
            clearInterval(this.sendInterval);
            this.sendInterval = null;
        }
        if (this.fallbackInterval) {
            clearInterval(this.fallbackInterval);
            this.fallbackInterval = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }
    }
}

// Bộc lộ (Export) đối tượng ra toàn cục để các file script.js hoặc gameEngine.js gọi
window.webcamFeed = new WebcamFeed();
