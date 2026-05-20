/**
 * Shinobi Vision Battle - Game Client Logic
 * Xử lý: Webcam, SocketIO, Audio, Vẽ Khung Xương (Skeleton), và Giao Diện (UI).
 */

// Không tự khởi tạo Socket ở đây nữa, sẽ dùng chung socket từ gameEngine.js

// ===== KHAI BÁO BIẾN GIAO DIỆN =====
const canvas = document.getElementById('skeleton-overlay');
const ctx = canvas ? canvas.getContext('2d') : null;
const logContainer = document.getElementById('log');
const btnStory = document.getElementById('btn-toggle-story');
const storyContent = document.getElementById('story-content');
const btnReset = document.getElementById('btn-reset');
const btnMainMenu = document.getElementById('btn-main-menu');
const mainMenu = document.getElementById('main-menu');
const btnStartGame = document.getElementById('btn-start-game');
const btnOpenHowto = document.getElementById('btn-open-howto');
const howtoModal = document.getElementById('howto-modal');
const btnCloseHowto = document.getElementById('btn-close-howto');
const playerSelect = document.getElementById('player-select');
const botSelect = document.getElementById('bot-select');
const mapSelect = document.getElementById('map-select');
const pauseOverlay = document.getElementById('pause-overlay');
const btnResumeGame = document.getElementById('btn-resume-game');
const btnPauseMenu = document.getElementById('btn-pause-menu');
const keyHelpPanel = document.querySelector('.keyboard-help-panel');
const btnToggleKeyHelp = document.getElementById('btn-toggle-keyhelp');

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
let isGameRunning = false; // Trạng thái game
let lastEventKey = null; // Lưu id sự kiện cuối để tránh xử lý trùng packet
let isPaused = false;
let showSkeleton = true;
let socketRef = null;
let keyHelpAutoCollapseTimer = null;
window.gameConfig = window.gameConfig || { player: "naruto", bot: "mizuki", map: "arena" };

function setKeyHelpCollapsed(collapsed) {
    if (!keyHelpPanel || !btnToggleKeyHelp) return;
    keyHelpPanel.classList.toggle('collapsed', !!collapsed);
    btnToggleKeyHelp.setAttribute('aria-expanded', String(!collapsed));
    btnToggleKeyHelp.textContent = collapsed ? "Mở rộng" : "Thu gọn";
}

function scheduleKeyHelpAutoCollapse() {
    if (!keyHelpPanel || !btnToggleKeyHelp) return;
    if (keyHelpAutoCollapseTimer) clearTimeout(keyHelpAutoCollapseTimer);
    keyHelpAutoCollapseTimer = setTimeout(() => {
        setKeyHelpCollapsed(true);
    }, 7000);
}

function readConfigFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const player = params.get("player");
    const bot = params.get("bot");
    const map = params.get("map");
    if (player === "naruto" || player === "mizuki") {
        window.gameConfig.player = player;
    }
    if (bot === "naruto" || bot === "mizuki") {
        window.gameConfig.bot = bot;
    }
    if (map) {
        window.gameConfig.map = map;
    }
}

function setMenuVisible(isVisible) {
    if (!mainMenu) return;
    mainMenu.classList.toggle('hidden', !isVisible);
}

function setPauseVisible(isVisible) {
    if (!pauseOverlay) return;
    pauseOverlay.classList.toggle('hidden', !isVisible);
}

function setPaused(paused) {
    isPaused = !!paused;
    if (window.game2dControl) window.game2dControl.setPaused(isPaused);
    setPauseVisible(isPaused);
}

function syncSelectDefaults() {
    if (playerSelect) playerSelect.value = window.gameConfig.player || "naruto";
    if (botSelect) botSelect.value = window.gameConfig.bot || "mizuki";
    if (mapSelect) mapSelect.value = window.gameConfig.map || "arena";
}

function getMenuConfig() {
    const playerSource = playerSelect?.value || window.gameConfig.player || "naruto";
    const botSource = botSelect?.value || window.gameConfig.bot || "mizuki";
    const mapSource = mapSelect?.value || window.gameConfig.map || "arena";
    const player = playerSource === "mizuki" ? "mizuki" : "naruto";
    let bot = botSource === "naruto" ? "naruto" : "mizuki";
    if (bot === player) {
        bot = player === "naruto" ? "mizuki" : "naruto";
    }
    const map = mapSource;
    return { player, bot, map };
}

async function startMatch() {
    const config = getMenuConfig();
    window.gameConfig = config;
    if (window.game2dControl) {
        window.game2dControl.setMap(config.map);
        window.game2dControl.setPaused(false);
    }
    isGameRunning = true;
    isPaused = false;
    setMenuVisible(false);
    if (window.gameEngine) {
        await window.gameEngine.applyConfig(config);
    }
    bgm.currentTime = 0;
    bgm.play().catch(() => {});
}

function backToMenu() {
    isGameRunning = false;
    setPaused(false);
    if (!mainMenu) {
        window.location.href = "index.html";
        return;
    }
    setMenuVisible(true);
    if (window.gameEngine && window.gameEngine.instance) {
        window.gameEngine.instance.isGameOver = true;
    }
    bgm.pause();
}

// Tự động phát nhạc nền khi người dùng tương tác với màn hình lần đầu
document.body.addEventListener('click', () => {
    if (bgm.paused && isGameRunning) {
        bgm.play().catch(e => console.log("Không thể tự động phát nhạc:", e));
    }
}, { once: true });


// Đã loại bỏ các hàm setupWebcam, startSendingFrames, stopSendingFrames cũ vì đã chuyển sang webcamFeed.js

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

// Hàm addLog đã được chuyển sang gameEngine.js

/**
 * Vẽ khung xương (Pose & Hands) lên màn hình cực mượt kèm ÁNH SÁNG NEON
 */
function drawSkeleton(landmarks) {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!showSkeleton) return;
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

// updateCooldownUI đã chuyển sang gameEngine.js

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


// ===== LẮNG NGHE SỰ KIỆN TỪ WEBSOCKET (Đồng bộ với gameEngine) =====

document.addEventListener("DOMContentLoaded", () => {
    readConfigFromUrl();
    // Socket được khởi tạo đồng bộ trong initGameEngine() (dòng đầu tiên),
    // game2d.js load trước script.js nên socket đã sẵn sàng tại đây.
    const socket = window.gameEngine.instance.socket;
    socketRef = socket;

    if (!socket) {
        console.error("Lỗi: Không tìm thấy Socket từ GameEngine!");
        return;
    }

    socket.on('connect', () => {
        if (!window.gameEngine.instance.isGameOver && !isPaused) {
            isGameRunning = true;
        }
        window.gameEngine.instance.addLog("✅ Backend connected.", "system");
    });

    socket.on('disconnect', () => {
        isGameRunning = false;
        window.gameEngine.instance.addLog("❌ Backend disconnected. Đang chờ reconnect...", "system");
    });

    socket.io.on('reconnect', () => {
        if (!window.gameEngine.instance.isGameOver && !isPaused) {
            isGameRunning = true;
        }
        window.gameEngine.instance.addLog("🔁 Backend reconnected.", "system");
    });

    socket.io.on('reconnect_attempt', () => {
        window.gameEngine.instance.addLog("⏳ Đang reconnect backend...", "system");
    });

    socket.io.on('connect_error', () => {
        window.gameEngine.instance.addLog("⚠️ Không thể kết nối backend tại localhost:5000.", "system");
    });

    let isGameOverProcessed = false;

    socket.on('game_update', (data) => {
        // 1. Vẽ Skeleton (Chỉ vẽ nếu game đang diễn ra)
        if (data.landmarks && !data.game_over) {
            drawSkeleton(data.landmarks);
        } else if (data.game_over) {
            if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
            isGameRunning = false;
        }

        // 2. Phát Âm Thanh dựa trên log
        const eventKey = data.event_id ?? data.last_message;
        if (data.last_message && eventKey !== lastEventKey) {
            playSoundEffects(data.last_message);
            lastEventKey = eventKey;
        }

        // 3. Xử lý âm thanh Kết thúc Game
        if (data.game_over && !isGameOverProcessed) {
            isGameOverProcessed = true;
            bgm.pause();
            if (data.winner === 'player') {
                sfxWin.play().catch(()=>{});
            } else {
                sfxLose.play().catch(()=>{});
            }
        }
    });

    // XỬ LÝ SỰ KIỆN NÚT BẤM (Cần Socket)
    btnReset.addEventListener('click', async () => {
        await startMatch();

        lastEventKey = null;
        isGameOverProcessed = false;
    });

    if (btnMainMenu) {
        btnMainMenu.addEventListener('click', () => {
            backToMenu();
            isGameOverProcessed = false;
            lastEventKey = null;
        });
    }

    // Khởi chạy Webcam thông qua Module webcamFeed.js
    const hasMenuPage = !!mainMenu;
    isGameRunning = false;
    syncSelectDefaults();
    setMenuVisible(hasMenuPage);
    setPauseVisible(false);
    if (window.webcamFeed) {
        window.webcamFeed.initWebcam(socket, () => {
            return !isGameRunning || isPaused; // true = dừng gửi frame khi menu/pause
        });
    }

    if (keyHelpPanel && btnToggleKeyHelp) {
        btnToggleKeyHelp.addEventListener("click", () => {
            const isCollapsed = keyHelpPanel.classList.contains("collapsed");
            setKeyHelpCollapsed(!isCollapsed);
            if (!isCollapsed) {
                if (keyHelpAutoCollapseTimer) clearTimeout(keyHelpAutoCollapseTimer);
            } else {
                scheduleKeyHelpAutoCollapse();
            }
        });
        keyHelpPanel.addEventListener("mouseenter", () => {
            setKeyHelpCollapsed(false);
            if (keyHelpAutoCollapseTimer) clearTimeout(keyHelpAutoCollapseTimer);
        });
        keyHelpPanel.addEventListener("mouseleave", () => {
            scheduleKeyHelpAutoCollapse();
        });
        scheduleKeyHelpAutoCollapse();
    }

    if (!hasMenuPage) {
        startMatch();
    }
});

// Ẩn/Hiện cốt truyện (Không cần socket)
btnStory.addEventListener('click', () => {
    storyContent.classList.toggle('hidden');
    btnStory.innerText = storyContent.classList.contains('hidden') ? "📜 Xem Cốt Truyện" : "📖 Đóng Cốt Truyện";
});

if (btnStartGame) {
    btnStartGame.addEventListener('click', async () => {
        await startMatch();
    });
}
if (playerSelect && botSelect) {
    playerSelect.addEventListener("change", () => {
        if (playerSelect.value === botSelect.value) {
            botSelect.value = playerSelect.value === "naruto" ? "mizuki" : "naruto";
        }
    });
    botSelect.addEventListener("change", () => {
        if (botSelect.value === playerSelect.value) {
            playerSelect.value = botSelect.value === "naruto" ? "mizuki" : "naruto";
        }
    });
}
if (btnOpenHowto && howtoModal) {
    btnOpenHowto.addEventListener('click', () => howtoModal.classList.remove('hidden'));
}
if (btnCloseHowto && howtoModal) {
    btnCloseHowto.addEventListener('click', () => howtoModal.classList.add('hidden'));
}

if (btnResumeGame) {
    btnResumeGame.addEventListener('click', () => setPaused(false));
}
if (btnPauseMenu) {
    btnPauseMenu.addEventListener('click', () => backToMenu());
}

document.addEventListener("keydown", (e) => {
    const key = e.key.toLowerCase();

    if (key === "escape") {
        if (!isGameRunning || mainMenu?.classList.contains("hidden") === false) return;
        setPaused(!isPaused);
        return;
    }

    if (key === "h") {
        showSkeleton = !showSkeleton;
        if (!showSkeleton && ctx && canvas) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        if (window.gameEngine?.instance) {
            window.gameEngine.instance.addLog(
                `🦴 Skeleton: ${showSkeleton ? "ON" : "OFF"}`,
                "system"
            );
        }
        return;
    }

    const inBattle = mainMenu ? mainMenu.classList.contains("hidden") : true;
    if (!inBattle || !socketRef || !socketRef.connected) return;

    if (key === "1") socketRef.emit("manual_input", { skill: "kage_bunshin" });
    else if (key === "2") socketRef.emit("manual_input", { skill: "rasengan" });
    else if (key === "3") socketRef.emit("manual_input", { skill: "rasenshuriken" });
    else if (key === "b") socketRef.emit("manual_input", { block: true });
    else if (key === "a") socketRef.emit("manual_input", { dodge: "left" });
    else if (key === "d") socketRef.emit("manual_input", { dodge: "right" });
    else if (key === "r") window.gameEngine.resetGame();
});
