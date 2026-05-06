const socket = io('http://localhost:5000');
const video = document.getElementById('webcam');
const canvas = document.getElementById('skeleton-overlay');
const ctx = canvas.getContext('2d');
const logContainer = document.getElementById('log');
const playerHpFill = document.getElementById('player-hp-fill');
const enemyHpFill = document.getElementById('enemy-hp-fill');

// 1. Khởi tạo Webcam
async function setupWebcam() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            startStreaming();
        };
    } catch (err) {
        console.error("Lỗi truy cập Webcam: ", err);
        addLog("Không thể truy cập camera. Vui lòng kiểm tra quyền.");
    }
}

// 2. Gửi frame tới Backend
function startStreaming() {
    setInterval(() => {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg', 0.5);
        socket.emit('image', data);
    }, 100); // 10 FPS
}

// 3. Lắng nghe sự kiện từ Backend
socket.on('connect', () => {
    addLog("Đã kết nối với máy chủ AI.");
});

socket.on('battle_status', (data) => {
    addLog(data.msg);
});

socket.on('skill_cast', (data) => {
    if (data.result.status === 'success') {
        addLog(data.result.msg, 'success');
        updateHP(data.result.player_hp, data.result.enemy_hp);
        triggerSkillEffect(data.skill);
    } else {
        // Cooldown...
    }
});

socket.on('processed_image', (data) => {
    // Nếu muốn hiển thị ảnh đã xử lý từ backend đè lên video
    const img = new Image();
    img.src = "data:image/jpeg;base64," + data;
    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
});

// Helper Functions
function addLog(message, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.prepend(entry);
}

function updateHP(playerHp, enemyHp) {
    playerHpFill.style.width = `${playerHp}%`;
    playerHpFill.innerText = `${playerHp}%`;
    enemyHpFill.style.width = `${enemyHp}%`;
    enemyHpFill.innerText = `${enemyHp}%`;

    if (enemyHp <= 0) {
        addLog("MIZUKI ĐÃ BỊ ĐÁNH BẠI! CHIẾN THẮNG!", "victory");
    }
}

function triggerSkillEffect(skillName) {
    const slotId = {
        "Kage Bunshin": "skill-kage",
        "Rasengan": "skill-rasengan",
        "Shuriken": "skill-shuriken"
    }[skillName];

    if (slotId) {
        const slot = document.getElementById(slotId);
        slot.classList.add('active');
        setTimeout(() => slot.classList.remove('active'), 500);
    }
}

// Cốt truyện
const btnStory = document.getElementById('btn-toggle-story');
const storyContent = document.getElementById('story-content');
btnStory.onclick = () => {
    storyContent.classList.toggle('hidden');
    if (storyContent.innerHTML === "") {
        fetch('assets/story.txt')
            .then(res => res.text())
            .then(text => storyContent.innerText = text);
    }
};

// Bắt đầu
setupWebcam();
