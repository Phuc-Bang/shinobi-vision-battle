/**
 * Module: character.js
 * Mô tả: Định nghĩa lớp Character (Nhân vật) trong game đối kháng 2D.
 * Bao bọc (wrap) lớp Sprite để xử lý thêm các logic về máu (HP), sát thương,
 * trạng thái chiến đấu (Block, Dodge, Attack) và định tuyến Callback.
 */

class Character {
    /**
     * Khởi tạo nhân vật mới.
     * @param {string} name - Tên nhân vật (ví dụ: 'Naruto', 'Mizuki').
     * @param {Sprite} sprite - Đối tượng Sprite đã khởi tạo (chứa ảnh và animation).
     * @param {number} x - Tọa độ X trên bản đồ (thường là tâm của nhân vật).
     * @param {number} y - Tọa độ Y trên bản đồ (thường là dưới mặt đất).
     * @param {string} side - Hướng xuất phát: 'left' (nhìn sang phải) hoặc 'right' (nhìn sang trái).
     * @param {Object} options - Các thông số tùy chọn (maxHp, attackPower, scale, ...).
     */
    constructor(name, sprite, x, y, side, options = {}) {
        this.name = name;
        this.sprite = sprite;
        
        // Tọa độ và hiển thị
        this.baseX = x; // Lưu lại gốc để quay về sau khi Né (Dodge)
        this.x = x;
        this.y = y;
        this.side = side; // 'left' hoặc 'right'
        this.scale = options.scale || 1.0;
        this.flipSprite = options.flipSprite ?? (side === 'right');
        this.baseFacingRight = options.baseFacingRight ?? false;
        this.faceTargetX = null;
        this.faceDeadzone = options.faceDeadzone ?? 24;
        this.facingRight = this.side === 'left';
        this.facingLockUntil = 0;
        
        // Chỉ số sinh tồn
        this.maxHp = options.maxHp || 100;
        this.hp = this.maxHp;
        this.attackPower = options.attackPower || 15;
        
        // Cờ trạng thái logic
        this.state = 'idle'; // Trạng thái ban đầu
        this.isBlocking = false;
        this.isDodging = false;
        this.isDead = false;
        this.hitStunTimer = 0;
        this.hitReactionOffsetX = 0;
        this.hitReactionVelocityX = 0;
        
        // Quản lý luồng xử lý (Callback)
        this.onStateComplete = null;
    }

    /**
     * Đổi trạng thái (Animation) của nhân vật.
     * @param {string} newState - Trạng thái mới (ví dụ: 'attack1', 'hurt', 'block').
     * @param {function} onComplete - Hàm gọi lại khi hoạt ảnh kết thúc.
     */
    setState(newState, onComplete = null) {
        // Không làm gì nếu nhân vật đã chết hoặc đang ở đúng trạng thái đó
        if (this.isDead && newState !== 'dead' && newState !== 'idle') return;
        if (this.state === newState) return;

        // Lưu trạng thái mới
        this.state = newState;
        this.onStateComplete = onComplete;

        // Gửi lệnh thay đổi Animation cho lớp Sprite
        if (this.sprite) {
            this.sprite.setAnimation(newState);
        }

        // Tự động điều chỉnh tọa độ nếu Né (Dodge)
        if (newState === 'dodge_left') {
            this.x = this.baseX - 50; // Lướt sang trái
        } else if (newState === 'dodge_right') {
            this.x = this.baseX + 50; // Lướt sang phải
        } else {
            // Các trạng thái bình thường thì phải đứng ở vị trí gốc
            this.x = this.baseX;
        }
    }

    /**
     * Cập nhật logic nhân vật mỗi khung hình.
     * @param {number} deltaTime - Khoảng thời gian từ frame trước (giây).
     */
    update(deltaTime) {
        if (!this.sprite) return;

        if (this.hitStunTimer > 0) {
            this.hitStunTimer -= deltaTime;
            if (this.hitStunTimer < 0) this.hitStunTimer = 0;
        }

        if (Math.abs(this.hitReactionVelocityX) > 0.1 || Math.abs(this.hitReactionOffsetX) > 0.1) {
            this.hitReactionOffsetX += this.hitReactionVelocityX * deltaTime;
            this.hitReactionVelocityX *= 0.82;
            this.hitReactionOffsetX *= 0.9;
        } else {
            this.hitReactionOffsetX = 0;
            this.hitReactionVelocityX = 0;
        }

        // Cập nhật Sprite (để tính toán khung hình hiện tại)
        this.sprite.update(deltaTime);

        // --- ĐỒNG BỘ TRẠNG THÁI (SYNC STATE) ---
        // 1. Nếu Sprite tự động chuyển từ animation hiện tại sang 'idle' (thông qua thuộc tính 'next' trong sprite.js)
        if (this.sprite.currentAnimation !== this.state) {
            
            // Xử lý khi hoàn thành state cũ
            if (this.onStateComplete) {
                this.onStateComplete();
                this.onStateComplete = null;
            }

            // Đồng bộ state của Character theo state của Sprite
            this.state = this.sprite.currentAnimation;
            
            // Xóa các cờ đặc biệt nếu đã quay về 'idle'
            if (this.state === 'idle') {
                this.stopBlocking();
                this.stopDodging();
                this.x = this.baseX; // Đưa về vị trí gốc
            }
        } 
        // 2. Nếu Sprite đã dừng lại ở frame cuối cùng (không có 'next' và không loop)
        else if (this.sprite.isAnimationFinished && !this.isDead) {
            
            if (this.onStateComplete) {
                this.onStateComplete();
                this.onStateComplete = null;
            }

            // Ép đưa về 'idle'
            this.setState('idle');
        }
    }

    /**
     * Vẽ nhân vật lên Canvas.
     * @param {CanvasRenderingContext2D} ctx - Context của canvas.
     */
    draw(ctx) {
        if (!this.sprite) return;

        // Xác định lật ngang: 
        // Đội đứng bên phải ('right') phải quay mặt sang trái (lật hình).
        // Đội đứng bên trái ('left') không cần lật (nhìn thẳng sang phải).
        let flipHorizontal = this.flipSprite;
        if (typeof this.faceTargetX === 'number') {
            const dx = this.faceTargetX - this.x;
            const now = performance.now();
            if (now >= this.facingLockUntil && Math.abs(dx) > this.faceDeadzone) {
                this.facingRight = dx > 0;
            }
            const shouldFaceRight = this.facingRight;
            // baseFacingRight=true: ảnh gốc quay sang phải.
            // baseFacingRight=false: ảnh gốc quay sang trái.
            flipHorizontal = this.baseFacingRight ? !shouldFaceRight : shouldFaceRight;
        }

        // Mờ nhẹ khi đang né tránh
        if (this.isDodging) {
            ctx.globalAlpha = 0.5;
        }

        // Vẽ Sprite
        this.sprite.draw(ctx, this.x + this.hitReactionOffsetX, this.y, flipHorizontal, this.scale);
        
        ctx.globalAlpha = 1.0; // Phục hồi độ trong suốt
    }

    /**
     * Xử lý khi nhân vật bị nhận sát thương.
     * @param {number} amount - Lượng sát thương truyền vào.
     * @returns {number} Sát thương thực tế (sau khi đã tính né/đỡ).
     */
    takeDamage(amount) {
        if (this.isDead) return 0;

        let actualDamage = amount;

        // Cơ chế phòng thủ
        if (this.isDodging) {
            // Né tránh hoàn toàn 100% sát thương
            actualDamage = 0;
            console.log(`💨 ${this.name} đã né được chiêu thức!`);
            return 0;
        } else if (this.isBlocking) {
            // Đỡ đòn giảm 70% sát thương (chỉ nhận 30%)
            actualDamage = Math.floor(amount * 0.3);
            console.log(`🛡️ ${this.name} đỡ đòn! Sát thương giảm còn ${actualDamage}.`);
        }

        // Trừ máu
        this.hp -= actualDamage;
        if (this.hp < 0) this.hp = 0;

        // Kiểm tra sinh tử
        if (this.hp === 0) {
            this.isDead = true;
            this.setState('dead');
            console.log(`💀 ${this.name} đã gục ngã!`);
        } else {
            // Nếu không chết và không đỡ/né, chuyển sang trạng thái bị thương
            if (!this.isBlocking && !this.isDodging) {
                this.setState('hurt');
            }
        }

        return actualDamage;
    }

    /**
     * Hồi máu (Phòng hờ cho chiêu thức buff máu).
     */
    heal(amount) {
        if (this.isDead) return;
        this.hp += amount;
        if (this.hp > this.maxHp) this.hp = this.maxHp;
    }

    /**
     * Khởi động lại (Hồi sinh) nhân vật.
     */
    reset(maxHp = null) {
        if (maxHp) this.maxHp = maxHp;
        this.hp = this.maxHp;
        this.isDead = false;
        this.hitStunTimer = 0;
        this.hitReactionOffsetX = 0;
        this.hitReactionVelocityX = 0;
        this.facingRight = this.side === 'left';
        this.facingLockUntil = 0;
        this.x = this.baseX;
        this.setState('idle');
    }

    lockFacing(ms = 0) {
        const now = performance.now();
        this.facingLockUntil = Math.max(this.facingLockUntil, now + Math.max(0, ms));
    }

    forceFaceTarget(targetX) {
        if (typeof targetX !== 'number') return;
        this.faceTargetX = targetX;
        this.facingRight = targetX > this.x;
    }

    applyKnockback(direction, force = 180, hitStunSec = 0.06) {
        if (this.isDead) return;
        this.hitReactionVelocityX += direction * force;
        this.hitStunTimer = Math.max(this.hitStunTimer, hitStunSec);
    }

    // --- CÁC HÀM TIỆN ÍCH HỖ TRỢ CHIẾN ĐẤU ---

    startBlocking() {
        if (this.isDead) return;
        this.isBlocking = true;
        this.setState('block');
    }

    stopBlocking() {
        this.isBlocking = false;
        // Trở về idle nếu đang block
        if (this.state === 'block') this.setState('idle');
    }

    startDodging(direction) {
        if (this.isDead) return;
        this.isDodging = true;
        
        // Hướng né (dodge_left hoặc dodge_right)
        if (direction === 'left' || direction === 'right') {
            this.setState(`dodge_${direction}`);
        } else {
            // Mặc định lùi về sau (Tùy thuộc phe nào)
            this.setState(this.side === 'left' ? 'dodge_left' : 'dodge_right');
        }
    }

    stopDodging() {
        this.isDodging = false;
        if (this.state.includes('dodge')) this.setState('idle');
    }
}

// Bộc lộ ra toàn cục
window.Character = Character;
