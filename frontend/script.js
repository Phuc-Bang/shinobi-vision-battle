/**
 * Shinobi Vision Battle - Game Client Logic
 * Xử lý: Webcam, SocketIO, Audio, Vẽ Khung Xương (Skeleton), và Giao Diện (UI).
 */

// Bỏ ép buộc transport để trình duyệt tự do chọn cách kết nối (Fix lỗi đứt kết nối ngầm)
const socket = io('http://localhost:5000');

// ===== KHAI BÁO BIẾN GIAO DIỆN =====
const video = document.getElementById('webcam');
const canvas = document.getElementById('skeleton-overlay');
const ctx = canvas.getContext('2d');
const logContainer = document.getElementById('log');
const btnStory = document.getElementById('btn-toggle-story');
const storyContent = document.getElementById('story-content');
const btnReset = document.getElementById('btn-reset');

// ===== KHAI BÁO BIẾN ÂM THANH =====
// (Hiện tại có thể src trống, khi nào bạn có file mp3 thì điền src vào HTML)
const bgm = document.getElementById('bgm');
const sfxRasengan = document.getElementById('sfx-rasengan');
const sfxShuriken = document.getElementById('sfx-shuriken');
const sfxKage = document.getElementById('sfx-kage');
const sfxKunai = document.getElementById('sfx-kunai');
const sfxWin = document.getElementById('sfx-win');
const sfxLose = document.getElementById('sfx-lose');

// ===== CẤU HÌNH GAME =====
const SEND_FPS = 12; // 12 khung hình/giây
const SEND_INTERVAL = 1000 / SEND_FPS;
let frameInterval = null; // Biến lưu trữ vòng lặp gửi ảnh
let isGameRunning = false; // Trạng thái game
let lastMessage = ""; // Lưu tin nhắn cuối để tránh spam
let isGameOverLogged = false; // Ngăn chặn spam log khi kết thúc

// Tự động phát nhạc nền khi người dùng tương tác với màn hình lần đầu
document.body.addEventListener('click', () => {
    if (bgm.paused && isGameRunning) {
        bgm.play().catch(e => console.log("Không thể tự động phát nhạc:", e));
    }
}, { once: true });


/**
 * Khởi tạo Webcam và yêu cầu quyền truy cập
 */
async function setupWebcam() {
    addLog("🔍 Đang khởi tạo camera...", "system");
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
            audio: false
        });
        video.srcObject = stream;
        
        // Đợi video thực sự phát
        await video.play();
        
        // Cập nhật kích thước canvas khớp với video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        addLog("🎥 Camera đã sẵn sàng. Trận chiến bắt đầu!", "system");
        
        isGameRunning = true;
        startSendingFrames(); // Bắt đầu gửi ảnh lên Server
    } catch (err) {
        addLog("❌ Lỗi Camera: " + err.name + ". Vui lòng cấp quyền!", "system");
    }
}

/**
 * Gửi frame ảnh lên Server liên tục
 */
function startSendingFrames() {
    if (frameInterval) clearInterval(frameInterval);

    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = 640;
    captureCanvas.height = 480;
    const captureCtx = captureCanvas.getContext('2d');

    frameInterval = setInterval(() => {
        // Chỉ gửi nếu Socket đang kết nối VÀ Game đang diễn ra
        if (socket.connected && isGameRunning) {
            captureCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
            // Giảm chất lượng ảnh xuống 0.5 để truyền tải siêu tốc
            const imageData = captureCanvas.toDataURL('image/jpeg', 0.5);
            socket.emit('video_frame', { image: imageData });
        }
    }, SEND_INTERVAL);
}

/**
 * Dừng gửi frame (Khi kết thúc game)
 */
function stopSendingFrames() {
    isGameRunning = false;
    if (frameInterval) {
        clearInterval(frameInterval);
        frameInterval = null;
    }
}

// Khai báo các đường nối cơ thể của MediaPipe Pose
const POSE_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8], [9, 10], 
    [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19], 
    [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20], [11, 23], 
    [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28], [27, 29], 
    [28, 30], [29, 31], [30, 32], [27, 31], [28, 32]
];

// Khai báo các đường nối bàn tay của MediaPipe Hand
const HAND_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], 
    [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15], 
    [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20]
];

let previousPlayerHp = 100;
let previousBotHp = 100;

/**
 * Kích hoạt hiệu ứng Rung lắc & Chớp sáng khi bị sát thương
 */
function triggerDamageEffect(target) {
    if (target === 'player') {
        const videoBox = document.querySelector('.video-container');
        if (videoBox) {
            videoBox.classList.add('shake-effect', 'damage-flash');
            setTimeout(() => {
                videoBox.classList.remove('shake-effect', 'damage-flash');
            }, 300); // Gỡ hiệu ứng sau 0.3 giây
        }
    }
}

/**
 * Ghi log ra giao diện kèm Đổ Màu (Color-coded)
 */
function addLog(message, type = "") {
    // Tô màu từ khóa tự động bằng Regex
    let formattedMsg = message
        .replace(/(Rasengan|Rasenshuriken|Kage Bunshin|Phân thân)/gi, '<span style="color: var(--primary-orange); font-weight: bold; text-shadow: 0 0 5px var(--primary-orange);">$1</span>')
        .replace(/(\d+ sát thương|mất \d+ máu|mất \d+ HP)/gi, '<span style="color: var(--hp-enemy); font-weight: bold; text-shadow: 0 0 5px var(--hp-enemy);">$1</span>')
        .replace(/(Thay Thế|né được|chặn thành công|hồi máu)/gi, '<span style="color: var(--hp-player); font-weight: bold; text-shadow: 0 0 5px var(--hp-player);">$1</span>');

    const p = document.createElement('p');
    p.className = "log-entry " + type;
    p.innerHTML = `[${new Date().toLocaleTimeString()}] ${formattedMsg}`;
    logContainer.appendChild(p);
    // Tự động cuộn xuống cuối
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Vẽ khung xương (Pose & Hands) lên màn hình cực mượt kèm ÁNH SÁNG NEON
 */
function drawSkeleton(landmarks) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!landmarks) return;

    // Bật hiệu ứng Phát Sáng (Neon Glow)
    ctx.shadowBlur = 12;

    // 1. VẼ CƠ THỂ (POSE)
    if (landmarks.pose && landmarks.pose.length > 0) {
        ctx.shadowColor = "#39FF14"; // Glow Xanh Lá
        ctx.strokeStyle = "rgba(57, 255, 20, 0.8)";
        ctx.lineWidth = 4;
        POSE_CONNECTIONS.forEach(conn => {
            const pt1 = landmarks.pose[conn[0]];
            const pt2 = landmarks.pose[conn[1]];
            if (pt1 && pt2) {
                ctx.beginPath();
                ctx.moveTo(pt1[0] * canvas.width, pt1[1] * canvas.height);
                ctx.lineTo(pt2[0] * canvas.width, pt2[1] * canvas.height);
                ctx.stroke();
            }
        });

        ctx.fillStyle = "#39FF14"; 
        landmarks.pose.forEach(pt => {
            ctx.beginPath();
            ctx.arc(pt[0] * canvas.width, pt[1] * canvas.height, 5, 0, 2 * Math.PI);
            ctx.fill();
        });
    }

    // 2. VẼ BÀN TAY (HANDS)
    if (landmarks.hands && landmarks.hands.length > 0) {
        ctx.shadowColor = "#FF9900"; // Glow Cam
        landmarks.hands.forEach(hand => {
            ctx.strokeStyle = "rgba(255, 153, 0, 0.9)";
            ctx.lineWidth = 3;
            HAND_CONNECTIONS.forEach(conn => {
                const pt1 = hand[conn[0]];
                const pt2 = hand[conn[1]];
                if (pt1 && pt2) {
                    ctx.beginPath();
                    ctx.moveTo(pt1[0] * canvas.width, pt1[1] * canvas.height);
                    ctx.lineTo(pt2[0] * canvas.width, pt2[1] * canvas.height);
                    ctx.stroke();
                }
            });

            ctx.fillStyle = "#FF9900"; 
            hand.forEach(pt => {
                ctx.beginPath();
                ctx.arc(pt[0] * canvas.width, pt[1] * canvas.height, 4, 0, 2 * Math.PI);
                ctx.fill();
            });
        });
    }
    // Tắt Glow để không ảnh hưởng các hàm vẽ khác (nếu có)
    ctx.shadowBlur = 0;
}

/**
 * Cập nhật giao diện Cooldown của Kỹ năng
 */
function updateCooldownUI(elementId, timeRemaining) {
    const el = document.getElementById(elementId);
    if (timeRemaining > 0) {
        el.innerText = timeRemaining.toFixed(1);
        el.classList.remove('hidden');
    } else {
        el.classList.add('hidden');
    }
}

/**
 * Xử lý phát âm thanh tự động dựa vào Text
 */
function playSoundEffects(message) {
    if (!message) return;
    const msg = message.toLowerCase();
    
    if (msg.includes('rasenshuriken')) {
        sfxShuriken.currentTime = 0; sfxShuriken.play().catch(()=>{});
    } else if (msg.includes('rasengan')) {
        sfxRasengan.currentTime = 0; sfxRasengan.play().catch(()=>{});
    } else if (msg.includes('kage bunshin') || msg.includes('phân thân')) {
        sfxKage.currentTime = 0; sfxKage.play().catch(()=>{});
    } else if (msg.includes('kunai')) {
        sfxKunai.currentTime = 0; sfxKunai.play().catch(()=>{});
    }
}


// ===== LẮNG NGHE SỰ KIỆN TỪ WEBSOCKET =====

socket.on('connect', () => {
    addLog("✅ Đã kết nối với máy chủ AI. Sẵn sàng chiến đấu!", "system");
    socket.emit('client_ready', { status: 'ready' });
});

socket.on('disconnect', () => {
    addLog("❌ Mất kết nối tới Server. Đang thử kết nối lại...", "system");
    stopSendingFrames();
});

socket.on('game_update', (data) => {
    // 1. Vẽ Skeleton (Chỉ vẽ nếu game đang diễn ra)
    if (data.landmarks && !data.game_over) {
        drawSkeleton(data.landmarks);
    } else if (data.game_over) {
        // Nếu game kết thúc, xóa sạch khung xương còn sót lại trên màn hình
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // 2. Cập nhật Máu & Kiểm tra Sát Thương
    if (data.player_hp !== undefined && data.bot_hp !== undefined) {
        const pFill = document.getElementById('player-hp-fill');
        const bFill = document.getElementById('enemy-hp-fill');
        
        // KIỂM TRA MẤT MÁU ĐỂ RUNG MÀN HÌNH
        if (data.player_hp < previousPlayerHp) {
            triggerDamageEffect('player');
        }
        previousPlayerHp = data.player_hp;
        previousBotHp = data.bot_hp;
        
        pFill.style.width = `${data.player_hp}%`;
        document.getElementById('player-hp-text').innerText = `${data.player_hp}/100`;
        
        bFill.style.width = `${data.bot_hp}%`;
        document.getElementById('enemy-hp-text').innerText = `${data.bot_hp}/100`;

        pFill.style.backgroundColor = data.player_hp <= 30 ? "darkred" : "var(--hp-player)";
    }

    // 3. Cập nhật Cooldown & Số lượng skill
    if (data.cooldown) {
        updateCooldownUI('cooldown-rasengan', data.cooldown.rasengan);
        updateCooldownUI('cooldown-shuriken', data.cooldown.rasenshuriken);
        updateCooldownUI('cooldown-kage', data.cooldown.kage_bunshin);
    }
    if (data.rasenshuriken_remaining !== undefined) {
        document.getElementById('shuriken-count').innerText = `${data.rasenshuriken_remaining}/3`;
    }

    // 4. Ghi Log và Phát Âm Thanh
    if (data.last_message && data.last_message !== lastMessage) {
        addLog(data.last_message, "skill-cast");
        playSoundEffects(data.last_message);
        lastMessage = data.last_message;
    }

    // 5. Cốt Truyện
    if (data.story_message) {
        storyContent.innerText = data.story_message;
        if (storyContent.classList.contains('hidden')) {
            storyContent.classList.remove('hidden');
            btnStory.innerText = "📖 Đóng Cốt Truyện";
        }
    }

    // 6. Xử lý Kết thúc Game
    if (data.game_over) {
        if (!isGameOverLogged) {
            stopSendingFrames(); // Ngừng gửi ảnh
            bgm.pause(); // Tắt nhạc nền
            
            if (data.winner === 'player') {
                addLog("🏆 CHIẾN THẮNG! Bạn đã đánh bại Mizuki!", "system");
                sfxWin.play().catch(()=>{});
            } else {
                addLog("💀 THẤT BẠI! Naruto đã gục ngã...", "system");
                sfxLose.play().catch(()=>{});
            }
            isGameOverLogged = true;
        }
    } else {
        isGameOverLogged = false;
    }
});


// ===== XỬ LÝ SỰ KIỆN NÚT BẤM =====

// Ẩn/Hiện cốt truyện
btnStory.addEventListener('click', () => {
    storyContent.classList.toggle('hidden');
    btnStory.innerText = storyContent.classList.contains('hidden') ? "📜 Xem Cốt Truyện" : "📖 Đóng Cốt Truyện";
});

// Chơi lại (Reset Game)
btnReset.addEventListener('click', () => {
    addLog("🔄 Đang thiết lập lại trận đấu...", "system");
    socket.emit('reset_game');
    
    // Khởi động lại trạng thái trên giao diện
    lastMessage = "";
    isGameOverLogged = false;
    logContainer.innerHTML = ""; // Xóa log cũ
    addLog("Trận chiến bắt đầu! Hãy kết ấn...", "system");
    
    // Bật lại camera
    isGameRunning = true;
    startSendingFrames();
    
    // Bật nhạc
    bgm.currentTime = 0;
    bgm.play().catch(()=>{});
});

// Khởi chạy
setupWebcam();
