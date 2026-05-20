/**
 * Module: sprite.js
 * Mô tả: Lớp Sprite quản lý việc load ảnh sprite sheet, chia frame, và xử lý logic hoạt ảnh (animation).
 * Tối ưu cho việc vẽ trên HTML5 Canvas.
 */

class Sprite {
    /**
     * @param {string|HTMLImageElement|HTMLCanvasElement} image - URL ảnh hoặc đối tượng Image/Canvas đã load.
     * @param {number} frameWidth - Chiều rộng của 1 frame (pixel).
     * @param {number} frameHeight - Chiều cao của 1 frame (pixel).
     * @param {Object} animations - Object định nghĩa các animation.
     * @param {string} defaultAnimation - Tên animation mặc định (VD: 'idle').
     */
    constructor(image, frameWidth, frameHeight, animations, defaultAnimation = 'idle') {
        this.frameWidth = frameWidth;
        this.frameHeight = frameHeight;
        this.animations = animations;
        
        // Trạng thái load ảnh
        this.isLoaded = false;
        this.image = null;
        
        // Quản lý animation hiện tại
        this.currentAnimation = defaultAnimation;
        this.currentFrameIndex = 0; // Chỉ số trong mảng frames của animation hiện tại
        this.frameTimer = 0;        // Bộ đếm thời gian (ms)
        
        // Biến lưu trạng thái đã hoàn thành (dành cho các animation không loop)
        this.isAnimationFinished = false;

        // Xử lý load ảnh
        if (typeof image === 'string') {
            this.loadImage(image);
        } else if (image instanceof HTMLImageElement || image instanceof HTMLCanvasElement) {
            this.image = image;
            this.isLoaded = true;
        }
    }

    /**
     * Tải ảnh từ URL. Trả về Promise để có thể xử lý bất đồng bộ nếu cần.
     * @param {string} url - Đường dẫn tới ảnh sprite sheet.
     */
    loadImage(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.image = img;
                this.isLoaded = true;
                resolve(img);
            };
            img.onerror = (err) => {
                console.error(`❌ Lỗi tải ảnh Sprite từ: ${url}`, err);
                reject(err);
            };
            img.src = url;
        });
    }

    /**
     * Chuyển đổi sang một animation mới.
     * @param {string} animName - Tên animation cần chạy.
     */
    setAnimation(animName) {
        // Nếu animation không tồn tại hoặc đang chạy animation này rồi thì bỏ qua
        if (!this.animations[animName] || this.currentAnimation === animName) {
            return;
        }
        
        this.currentAnimation = animName;
        this.currentFrameIndex = 0;
        this.frameTimer = 0;
        this.isAnimationFinished = false;
    }

    /**
     * Cập nhật logic chuyển frame animation theo thời gian (deltaTime).
     * @param {number} deltaTime - Thời gian trôi qua từ frame trước (tính bằng giây).
     */
    update(deltaTime) {
        if (!this.isLoaded) return;
        
        const anim = this.animations[this.currentAnimation];
        if (!anim) return;

        // Đổi deltaTime (giây) sang mili-giây (ms) để cộng vào timer
        this.frameTimer += deltaTime * 1000;

        // Nếu thời gian vượt qua mức delay của 1 frame thì mới chuyển sang frame tiếp theo
        if (this.frameTimer >= anim.frameDelay) {
            // Trừ đi frameDelay để giữ lại phần thời gian thừa (giúp animation không bị trôi/chậm dần)
            this.frameTimer -= anim.frameDelay;
            
            // Nếu chưa kết thúc animation
            if (!this.isAnimationFinished) {
                this.currentFrameIndex++;
                
                // Kiểm tra xem đã chạy đến frame cuối cùng trong mảng chưa
                if (this.currentFrameIndex >= anim.frames.length) {
                    if (anim.loop) {
                        // Nếu cho phép lặp lại (loop = true), quay về frame đầu tiên
                        this.currentFrameIndex = 0;
                    } else {
                        // Nếu không lặp, neo chặt ở frame cuối cùng
                        this.currentFrameIndex = anim.frames.length - 1;
                        this.isAnimationFinished = true;
                        
                        // Nếu có chỉ định animation nối tiếp (thuộc tính 'next'), thì tự động chuyển sang
                        if (anim.next) {
                            this.setAnimation(anim.next);
                        }
                    }
                }
            }
        }
    }

    /**
     * Lấy chỉ số thực tế của frame trên sprite sheet.
     * @returns {number} Chỉ số frame.
     */
    getCurrentFrameIndex() {
        const anim = this.animations[this.currentAnimation];
        if (!anim) return 0;
        return anim.frames[this.currentFrameIndex];
    }

    /**
     * Vẽ frame hiện tại lên Canvas.
     * @param {CanvasRenderingContext2D} ctx - Context của Canvas để vẽ.
     * @param {number} x - Tọa độ X để vẽ.
     * @param {number} y - Tọa độ Y để vẽ.
     * @param {boolean} flipHorizontal - Cờ lật ngang nhân vật (dùng khi nhân vật quay sang trái).
     * @param {number} scale - Hệ số phóng to/thu nhỏ sprite.
     */
    draw(ctx, x, y, flipHorizontal = false, scale = 1) {
        if (!this.isLoaded || !this.image) return;

        const anim = this.animations[this.currentAnimation];
        if (!anim) return;

        // 1. Lấy vị trí (index) của frame thực tế trên sprite sheet
        const frameIndex = anim.frames[this.currentFrameIndex];

        // 2. Tính số lượng cột của tấm ảnh sprite sheet
        const cols = Math.floor(this.image.width / this.frameWidth);
        if (cols === 0) return; // Tránh lỗi chia cho 0 nếu ảnh chưa kịp load kích thước
        
        // 3. Tính tọa độ cắt ảnh (source X, source Y)
        const sx = (frameIndex % cols) * this.frameWidth;
        const sy = Math.floor(frameIndex / cols) * this.frameHeight;

        // Lưu trữ ngữ cảnh vẽ hiện tại
        ctx.save();

        // Dời hệ tọa độ (gốc 0,0) đến đúng vị trí muốn vẽ nhân vật
        ctx.translate(x, y);

        // Lật ngang tọa độ nếu cờ flipHorizontal được bật
        if (flipHorizontal) {
            ctx.scale(-1, 1);
        }

        // Áp dụng độ phóng to/thu nhỏ
        ctx.scale(scale, scale);

        // 4. Vẽ ảnh cắt từ sprite sheet lên Canvas
        // Tham số 2-5: Tọa độ sx, sy, width, height (Cắt từ ảnh gốc)
        // Tham số 6-9: Tọa độ dx, dy, width, height (Vị trí vẽ trên Canvas)
        // Lưu ý: Ta dịch lùi (dx = -width/2, dy = -height) để tọa độ (x,y) trở thành tọa độ ngay chân dưới cùng giữa của nhân vật.
        ctx.drawImage(
            this.image,
            sx, sy, this.frameWidth, this.frameHeight,
            -this.frameWidth / 2, -this.frameHeight, this.frameWidth, this.frameHeight 
        );

        // Phục hồi ngữ cảnh vẽ ban đầu
        ctx.restore();
    }
}

/**
 * Hàm tiện ích: Tạo ra một đối tượng Sprite giả (Placeholder) bằng Canvas DOM element.
 * Dùng cực kỳ tiện lợi để test game logic khi chưa có họa sĩ vẽ Sprite Sheet thật.
 * 
 * @param {string} color - Mã màu Hex cho khối hình (VD: "#ff8800")
 * @param {number} width - Chiều rộng 1 frame
 * @param {number} height - Chiều cao 1 frame
 * @param {Object} [animations] - Cấu hình animation (nếu không truyền sẽ dùng mặc định)
 * @returns {Sprite} Đối tượng Sprite mới
 */
function createPlaceholderSprite(color, width, height, animations) {
    // Tạo ra 1 tấm ảnh (canvas) có chiều ngang bằng 2 frame
    const framesCount = 2;
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = width * framesCount;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext("2d");

    // Frame 0: Màu sắc chuẩn, trạng thái bình thường
    tempCtx.fillStyle = color;
    tempCtx.fillRect(0, 0, width, height);

    // Vẽ thêm 1 vạch sọc ngang để phân biệt hướng mặt (mặt hướng sang phải)
    tempCtx.fillStyle = "#fff";
    tempCtx.fillRect(width - 15, 20, 10, 20);

    // Frame 1: Trạng thái chớp sáng (dùng để làm hiệu ứng di chuyển/idle)
    tempCtx.globalAlpha = 0.5;
    tempCtx.fillStyle = color;
    tempCtx.fillRect(width, 0, width, height);
    
    // Vạch hướng mặt cho frame 1
    tempCtx.globalAlpha = 1.0;
    tempCtx.fillStyle = "#fff";
    tempCtx.fillRect(width + width - 15, 20, 10, 20);

    // Placeholder chỉ có 2 frame (index 0 và 1) — dùng bộ animation riêng, bất kể config thật truyền vào
    // Không thể dùng frame index cao hơn 1 vì canvas tạm chỉ cao 1 frame
    const defaultAnimations = {
        idle:         { frames: [0, 1], frameDelay: 500, loop: true },
        attack1:      { frames: [1, 0], frameDelay: 100, loop: false, next: 'idle' },
        attack2:      { frames: [0, 1], frameDelay: 100, loop: false, next: 'idle' },
        buff:         { frames: [0, 1], frameDelay: 200, loop: true },
        block:        { frames: [1],    frameDelay: 500, loop: false },
        dodge_left:   { frames: [0],    frameDelay: 150, loop: false, next: 'idle' },
        dodge_right:  { frames: [0],    frameDelay: 150, loop: false, next: 'idle' },
        hurt:         { frames: [1],    frameDelay: 300, loop: false, next: 'idle' },
        dead:         { frames: [1],    frameDelay: 1000, loop: false }
    };

    // Khởi tạo đối tượng Sprite bằng thẻ canvas tạm (coi canvas như 1 thẻ img)
    return new Sprite(tempCanvas, width, height, defaultAnimations, 'idle');
}

// Bộc lộ (Export) các hàm này ra môi trường toàn cục để game2d.js có thể gọi
window.Sprite = Sprite;
window.createPlaceholderSprite = createPlaceholderSprite;
