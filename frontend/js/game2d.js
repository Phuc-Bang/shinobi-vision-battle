/**
 * Module: game2d.js
 * Mô tả: Chuyên biệt quản lý Vòng lặp Game (Game Loop) và vẽ Background.
 * Nhường toàn bộ quyền điều khiển Logic cho gameEngine.js.
 */

(() => {
    let canvas;
    let ctx;
    let lastTimestamp = 0;
    let deltaTime = 0;
    let isGameRunning = false;
    let isPaused = false;
    let arenaBackground = null;
    let currentMap = "arena";

    // ==========================================
    // VẼ BACKGROUND
    // ==========================================
    function drawBackground() {
        if (arenaBackground && arenaBackground.complete && arenaBackground.naturalWidth > 0) {
            ctx.drawImage(arenaBackground, 0, 0, canvas.width, canvas.height);
            return;
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, "#0a192f");
        gradient.addColorStop(1, "#000000");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    // ==========================================
    // GAME LOOP
    // ==========================================
    function gameLoop(timestamp) {
        if (!isGameRunning) return;

        if (!lastTimestamp) lastTimestamp = timestamp;
        deltaTime = (timestamp - lastTimestamp) / 1000;
        lastTimestamp = timestamp;

        // Giới hạn deltaTime tối đa để tránh lỗi xuyên thấu khi tụt FPS
        if (deltaTime > 0.033) deltaTime = 0.033;

        // Xóa màn hình và vẽ nền
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawBackground();

        // Ủy quyền Cập nhật và Vẽ cho GameEngine
        if (window.gameEngine) {
            if (!isPaused) {
                window.gameEngine.update(deltaTime);
            }
            window.gameEngine.draw(ctx);
        }

        requestAnimationFrame(gameLoop);
    }

    // ==========================================
    // HÀM KHỞI TẠO (INIT)
    // ==========================================
    function initCanvas() {
        canvas = document.getElementById("gameCanvas");

        if (!canvas) {
            canvas = document.createElement("canvas");
            canvas.id = "gameCanvas";
            canvas.width = 1280;
            canvas.height = 720;
            canvas.className = "game-canvas-2d";
            
            const container = document.getElementById('canvas-container');
            if (container) {
                container.prepend(canvas);
            } else {
                document.body.prepend(canvas);
            }
        }

        ctx = canvas.getContext("2d");
        arenaBackground = new Image();
        setMap(window.gameConfig?.map || "arena");

        // KHỞI TẠO GAME ENGINE TẠI ĐÂY (Thay thế cho code khởi tạo nhân vật cũ)
        if (window.gameEngine) {
            window.gameEngine.initGameEngine();
        }

        isGameRunning = true;
        requestAnimationFrame((timestamp) => {
            lastTimestamp = timestamp;
            gameLoop(timestamp);
        });
        
        console.log("🎮 Vòng lặp Game 2D Canvas đã khởi động thành công!");
    }

    // Lắng nghe DOM Ready
    document.addEventListener("DOMContentLoaded", () => {
        initCanvas();
    });

    function setMap(mapKey = "arena") {
        currentMap = mapKey;
        if (!arenaBackground) arenaBackground = new Image();
        const mapDefs = {
            arena: "assets/images/background/arena.png"
        };
        arenaBackground.src = mapDefs[mapKey] || mapDefs.arena;
    }

    function setPaused(paused) {
        isPaused = !!paused;
    }

    window.game2dControl = {
        setMap,
        setPaused,
        isPaused: () => isPaused,
        getMap: () => currentMap
    };

})();
