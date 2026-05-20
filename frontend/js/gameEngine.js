class StateImageSprite {
  constructor(
    images,
    animations,
    fallbackSprite,
    defaultAnimation = "idle",
    renderConfig = {},
  ) {
    this.images = images;
    this.animations = animations;
    this.fallbackSprite = fallbackSprite;
    this.currentAnimation = defaultAnimation;
    this.frameTimer = 0;
    this.isAnimationFinished = false;
    this.isLoaded = true;
    this.renderConfig = renderConfig;
    this.alphaThreshold = 16;
    this.trimCache = new WeakMap();
  }

  setAnimation(animName) {
    if (!this.animations[animName] || this.currentAnimation === animName) {
      return;
    }
    this.currentAnimation = animName;
    this.frameTimer = 0;
    this.isAnimationFinished = false;
    if (!this.images[animName] && this.fallbackSprite) {
      this.fallbackSprite.setAnimation(animName);
    }
  }

  update(deltaTime) {
    const anim = this.animations[this.currentAnimation];
    if (!anim) return;

    if (!this.images[this.currentAnimation] && this.fallbackSprite) {
      this.fallbackSprite.update(deltaTime);
      this.currentAnimation = this.fallbackSprite.currentAnimation;
      return;
    }

    this.frameTimer += deltaTime * 1000;
    const duration = Math.max(
      anim.frameDelay || 150,
      (anim.frames?.length || 1) * (anim.frameDelay || 150),
    );
    if (!anim.loop && this.frameTimer >= duration) {
      this.isAnimationFinished = true;
      if (anim.next) {
        this.setAnimation(anim.next);
      }
    }
  }

  getTrimmedBounds(img) {
    const cached = this.trimCache.get(img);
    if (cached) return cached;

    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const cctx = canvas.getContext("2d", { willReadFrequently: true });
    cctx.drawImage(img, 0, 0);

    const { data, width, height } = cctx.getImageData(
      0,
      0,
      canvas.width,
      canvas.height,
    );
    let minX = width;
    let minY = height;
    let maxX = -1;
    let maxY = -1;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const alpha = data[(y * width + x) * 4 + 3];
        if (alpha > this.alphaThreshold) {
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
        }
      }
    }

    const bounds =
      maxX >= 0
        ? { sx: minX, sy: minY, sw: maxX - minX + 1, sh: maxY - minY + 1 }
        : { sx: 0, sy: 0, sw: width, sh: height };

    this.trimCache.set(img, bounds);
    return bounds;
  }

  draw(ctx, x, y, flipHorizontal = false, scale = 1) {
    const img = this.images[this.currentAnimation] || this.images.idle;
    if (!img) {
      if (this.fallbackSprite) {
        this.fallbackSprite.draw(ctx, x, y, flipHorizontal, scale);
      }
      return;
    }

    const bounds = this.getTrimmedBounds(img);
    const cfg =
      this.renderConfig[this.currentAnimation] ||
      this.renderConfig.default ||
      {};
    const targetHeight = (cfg.height || 260) * scale;
    const yOffset = cfg.yOffset || 0;
    const xOffset = cfg.xOffset || 0;
    let resolvedFlip = flipHorizontal;
    if (cfg.flip === "invert") {
      resolvedFlip = !flipHorizontal;
    } else if (typeof cfg.flip === "boolean") {
      resolvedFlip = cfg.flip;
    }
    const drawHeight = targetHeight;
    const drawWidth = (bounds.sw / bounds.sh) * targetHeight;

    ctx.save();
    ctx.translate(x, y);
    if (resolvedFlip) {
      ctx.scale(-1, 1);
    }
    const drawX = -drawWidth / 2 + (resolvedFlip ? -xOffset : xOffset);
    ctx.drawImage(
      img,
      bounds.sx,
      bounds.sy,
      bounds.sw,
      bounds.sh,
      drawX,
      -drawHeight + yOffset,
      drawWidth,
      drawHeight,
    );
    ctx.restore();
  }
}

/**
 * Module: gameEngine.js
 * Mô tả: Đóng vai trò là Bộ Não Trung Tâm (Controller).
 * Kết nối WebSocket với Server, lắng nghe event, quản lý trạng thái UI (thanh máu, cooldown, log),
 * và điều khiển lớp Character (Naruto & Mizuki) thực hiện Animation dựa vào nội dung Log (last_message).
 */

class GameEngine {
  constructor() {
    this.socket = null;

    // Các nhân vật (Characters)
    this.playerChar = null;
    this.botChar = null;

    // Canvas và trạng thái
    this.gameCanvas = null;
    this.ctx = null;
    this.isGameOver = false;
    this.lastMessage = "";
    this.lastEventKey = null;

    // Tham chiếu (Cache) các phần tử DOM UI
    this.logContainer = document.getElementById("log");
    this.cooldownElements = {
      rasengan: document.getElementById("cooldown-rasengan"),
      rasenshuriken: document.getElementById("cooldown-shuriken"),
      kage_bunshin: document.getElementById("cooldown-kage"),
    };
    this.rasenshurikenCountElem = document.getElementById("shuriken-count");
    this.playerHpFill = document.getElementById("player-hp-fill");
    this.playerHpText = document.getElementById("player-hp-text");
    this.enemyHpFill = document.getElementById("enemy-hp-fill");
    this.enemyHpText = document.getElementById("enemy-hp-text");
    this.storyContent = document.getElementById("story-content");
    this.btnStory = document.getElementById("btn-toggle-story");

    // Mảng chứa đạn (Kỹ năng bay)
    this.projectiles = [];
    this.projectileImages = {};
    this.maxProjectilesOnScreen = 8;
    this.projectileProfile = {
      rasengan: { size: 170, xOffset: 70, yOffset: -100, speed: 720 },
      rasenshuriken: { size: 214, xOffset: 86, yOffset: -108, speed: 560 },
      kunai: { size: 124, xOffset: 64, yOffset: -112, speed: 760 },
    };
    this.actionProfile = {
      player: {
        attack1: { startupMs: 140, recoveryMs: 320, projectile: "rasengan" },
        attack2: {
          startupMs: 220,
          recoveryMs: 520,
          projectile: "rasenshuriken",
        },
        buff: { startupMs: 70, recoveryMs: 240 },
        block: { startupMs: 0, recoveryMs: 210 },
        dodge_left: { startupMs: 0, recoveryMs: 260 },
      },
      bot: {
        attack1: { startupMs: 160, recoveryMs: 360, projectile: "kunai" },
        dodge_right: { startupMs: 0, recoveryMs: 250 },
      },
    };
    this.actionLockUntil = { player: 0, bot: 0 };
    this.actionTimers = [];

    // Mảng chứa Text sát thương bay lên (Damage Texts)
    this.damageTexts = [];
    this.hitFlashes = [];
    this.impactEffects = [];
    this.hitFlashProfile = {
      light: { color: "#ffe08a", radius: 78, life: 0.1 },
      medium: { color: "#8ad8ff", radius: 90, life: 0.12 },
      heavy: { color: "#ff9a9a", radius: 108, life: 0.16 },
      guard: { color: "#c0d2ff", radius: 84, life: 0.12 },
    };
      this.impactProfile = {
        light: { color: "#ffd36e", ringMax: 34, life: 0.2, particleCount: 6 },
        medium: { color: "#7fd3ff", ringMax: 42, life: 0.24, particleCount: 8 },
        heavy: { color: "#ff7474", ringMax: 52, life: 0.3, particleCount: 11 },
        guard: { color: "#a8beff", ringMax: 38, life: 0.22, particleCount: 7 },
      };
      this.hitStopProfile = {
        light: 0.03,
        medium: 0.05,
        heavy: 0.075,
        guard: 0.03,
      };
      this.knockbackProfile = {
        light: 130,
        medium: 190,
        heavy: 255,
        guard: 90,
      };
      this.hitStopTimer = 0;
      this.comboTimeoutSec = 1.1;
      this.comboState = {
        player: { hits: 0, totalDamage: 0, timer: 0, lastHitType: "light" },
        bot: { hits: 0, totalDamage: 0, timer: 0, lastHitType: "light" },
      };
      this.combatNotices = [];

    // Thông số rung màn hình Canvas (Screen Shake)
    this.shakeTimer = 0;
    this.shakeDuration = 0;
    this.shakeIntensity = 0;
    this.shakeX = 0;
    this.shakeY = 0;
    this.debugEnabled = false;
    this.fpsSmoothing = 0.12;
    this.fpsEstimate = 60;

    window.addEventListener("keydown", (e) => {
      if (e.key === "F3") {
        e.preventDefault();
        this.debugEnabled = !this.debugEnabled;
        this.addLog(
          this.debugEnabled
            ? "🧪 Debug overlay: ON (F3)"
            : "🧪 Debug overlay: OFF (F3)",
          "system",
        );
      }
    });
  }

  /**
   * Tải Sprite Sheet thực tế từ URL, nếu lỗi (404) sẽ tự động dùng Khối màu thay thế.
   * @param {string} sheetUrl - Đường dẫn tới file ảnh Sprite (VD: 'assets/sprites/naruto_sheet.png')
   * @param {number} frameWidth - Chiều rộng của 1 khung hình (pixel)
   * @param {number} frameHeight - Chiều cao của 1 khung hình (pixel)
   * @param {Object} animationsConfig - Object định nghĩa các hoạt ảnh (frame index, delay)
   * @param {string} fallbackColor - Màu của khối dự phòng nếu load ảnh thất bại
   * @returns {Promise<Sprite>} Đối tượng Sprite sẵn sàng sử dụng
   */
  async loadSprite(
    sheetUrl,
    frameWidth,
    frameHeight,
    animationsConfig,
    fallbackColor,
  ) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        // Tải ảnh thành công, khởi tạo Sprite thật
        const sprite = new window.Sprite(
          img,
          frameWidth,
          frameHeight,
          animationsConfig,
        );
        resolve(sprite);
      };
      img.onerror = () => {
        // Tải ảnh thất bại (File không tồn tại), khởi tạo Sprite khối màu dự phòng
        console.warn(
          `⚠️ Không tìm thấy ảnh ${sheetUrl}, tự động chuyển sang Khối màu (Placeholder).`,
        );
        const fallbackSprite = window.createPlaceholderSprite(
          fallbackColor,
          frameWidth,
          frameHeight,
          animationsConfig,
        );
        resolve(fallbackSprite);
      };
      img.src = sheetUrl; // Kích hoạt quá trình tải ảnh
    });
  }

  async loadStateSprite(
    stateUrls,
    animationsConfig,
    fallbackColor,
    renderConfig = {},
  ) {
    const entries = await Promise.all(
      Object.entries(stateUrls).map(([state, url]) => {
        return new Promise((resolve) => {
          const img = new Image();
          img.onload = () => {
            if (img.naturalWidth <= 1 || img.naturalHeight <= 1) {
              resolve([state, null]);
              return;
            }
            resolve([state, img]);
          };
          img.onerror = () => {
            console.warn(
              `⚠️ Không tìm thấy ảnh ${url}, bỏ qua trạng thái ${state}.`,
            );
            resolve([state, null]);
          };
          img.src = url;
        });
      }),
    );

    const images = {};
    entries.forEach(([state, img]) => {
      if (img) images[state] = img;
    });

    const fallbackSprite = window.createPlaceholderSprite(
      fallbackColor,
      128,
      128,
      animationsConfig,
    );
    return new StateImageSprite(
      images,
      animationsConfig,
      fallbackSprite,
      "idle",
      renderConfig,
    );
  }

  /**
   * Khởi tạo Game Engine: Kết nối Server và Tạo Nhân vật (Bất đồng bộ để đợi load ảnh)
   */
  getFighterDefs(narutoAnimations, mizukiAnimations) {
    return {
      naruto: {
        name: "Naruto",
        animations: narutoAnimations,
        fallbackColor: "#ff8800",
        avatar: "assets/images/sprites/naruto/avatar_naruto.png",
        stateUrls: {
          idle: "assets/images/sprites/naruto/idle.png",
          attack1: "assets/images/sprites/naruto/rasengan.png",
          attack2: "assets/images/sprites/naruto/rasenshuriken.png",
          buff: "assets/images/sprites/naruto/kagebunshin.png",
          block: "assets/images/sprites/naruto/block.png",
          dodge_left: "assets/images/sprites/naruto/dodge_left.png",
          dodge_right: "assets/images/sprites/naruto/dodge_right.png",
          hurt: "assets/images/sprites/naruto/hurt.png",
          dead: "assets/images/sprites/naruto/dead.png",
        },
        renderConfig: {
          default: { height: 280 },
          attack1: { height: 286, flip: "invert", xOffset: 12 },
          attack2: { height: 300, flip: "invert", xOffset: 16 },
          buff: { height: 295 },
          dodge_left: { height: 260 },
          dodge_right: { height: 260 },
          dead: { height: 150, yOffset: 10 },
        },
      },
      mizuki: {
        name: "Mizuki",
        animations: mizukiAnimations,
        fallbackColor: "#6600ff",
        avatar: "assets/images/sprites/mizuki/avatar_mizuki.png",
        stateUrls: {
          idle: "assets/images/sprites/mizuki/idle.png",
          attack1: "assets/images/sprites/mizuki/throw_kunai.png",
          dodge_right: "assets/images/sprites/mizuki/dodge_right.png",
          hurt: "assets/images/sprites/mizuki/hurt.png",
          dead: "assets/images/sprites/mizuki/dead.png",
        },
        renderConfig: {
          default: { height: 285 },
          attack1: { height: 292, flip: "invert", xOffset: 10 },
          dodge_right: { height: 268 },
          dead: { height: 145, yOffset: 12 },
        },
      },
    };
  }

  async setupCharactersFromConfig() {
    const selectedPlayer =
      window.gameConfig?.player === "mizuki" ? "mizuki" : "naruto";
    let selectedBot = window.gameConfig?.bot === "naruto" ? "naruto" : "mizuki";
    if (selectedBot === selectedPlayer) {
      selectedBot = selectedPlayer === "naruto" ? "mizuki" : "naruto";
    }

    const narutoAnimations = {
      idle: { frames: [0, 1, 2, 3], frameDelay: 150, loop: true },
      attack1: { frames: [4, 5, 6, 7, 8, 9], frameDelay: 80, loop: false, next: "idle" },
      attack2: {
        frames: [10, 11, 12, 13, 14, 15, 16, 17],
        frameDelay: 80,
        loop: false,
        next: "idle",
      },
      buff: { frames: [18, 19, 20, 21], frameDelay: 120, loop: true },
      block: { frames: [22, 23], frameDelay: 100, loop: false },
      dodge_left: { frames: [24, 25, 26, 27], frameDelay: 80, loop: false, next: "idle" },
      dodge_right: { frames: [28, 29, 30, 31], frameDelay: 80, loop: false, next: "idle" },
      hurt: { frames: [32, 33], frameDelay: 200, loop: false, next: "idle" },
      dead: { frames: [34, 35, 36, 37], frameDelay: 150, loop: false },
    };
    const mizukiAnimations = {
      idle: { frames: [0, 1, 2, 3], frameDelay: 150, loop: true },
      attack1: { frames: [4, 5, 6, 7, 8, 9], frameDelay: 80, loop: false, next: "idle" },
      dodge_right: { frames: [28, 29, 30, 31], frameDelay: 80, loop: false, next: "idle" },
      hurt: { frames: [32, 33], frameDelay: 200, loop: false, next: "idle" },
      dead: { frames: [34, 35, 36, 37], frameDelay: 150, loop: false },
    };

    const fighterDefs = this.getFighterDefs(narutoAnimations, mizukiAnimations);
    const playerDef = fighterDefs[selectedPlayer];
    const botDef = fighterDefs[selectedBot];

    const playerSprite = await this.loadStateSprite(
      playerDef.stateUrls,
      playerDef.animations,
      playerDef.fallbackColor,
      playerDef.renderConfig,
    );
    const botSprite = await this.loadStateSprite(
      botDef.stateUrls,
      botDef.animations,
      botDef.fallbackColor,
      botDef.renderConfig,
    );

    this.playerChar = new window.Character(playerDef.name, playerSprite, 250, 620, "left", {
      maxHp: 100,
      scale: 1.0,
      flipSprite: true,
    });
    this.botChar = new window.Character(botDef.name, botSprite, 1280 - 250, 620, "right", {
      maxHp: 100,
      scale: 1.0,
      flipSprite: false,
    });

    this.updateHudIdentity(playerDef, botDef);
  }

  updateHudIdentity(playerDef, botDef) {
    const playerName = document.querySelector(".character-stats:first-child .name");
    const playerAvatar = document.querySelector(".character-stats:first-child .avatar-img");
    const botName = document.querySelector(".character-stats:nth-child(2) .name");
    const botAvatar = document.querySelector(".character-stats:nth-child(2) .avatar-img");
    if (playerName) playerName.textContent = `${playerDef.name.toUpperCase()} (Player)`;
    if (playerAvatar) playerAvatar.src = playerDef.avatar;
    if (botName) botName.textContent = `${botDef.name.toUpperCase()} (Boss)`;
    if (botAvatar) botAvatar.src = botDef.avatar;
  }

  async initGameEngine() {
    // 1. Kết nối Socket.IO tới backend (Server Python Flask đang chạy cổng 5000)
    // Nếu mất kết nối, Socket.IO sẽ tự động thử kết nối lại
    this.socket = io("http://localhost:5000", {
      reconnectionAttempts: Infinity,
      reconnectionDelay: 3000, // Thử lại sau mỗi 3s nếu đứt mạng
    });
    this.setupSocketEvents();

    this.projectileImages = await this.loadProjectileImages();
    await this.setupCharactersFromConfig();

    console.log("🚀 GameEngine đã khởi tạo và sẵn sàng!");
  }

  async applyConfig(config) {
    window.gameConfig = { ...(window.gameConfig || {}), ...(config || {}) };
    await this.setupCharactersFromConfig();
    this.resetGame();
  }

  async loadProjectileImages() {
    const defs = {
      rasengan: "assets/images/projectiles/rasengan.png",
      rasenshuriken: "assets/images/projectiles/rasenshuriken.png",
      kunai: "assets/images/projectiles/kunai.png",
    };
    const entries = await Promise.all(
      Object.entries(defs).map(([type, url]) => {
        return new Promise((resolve) => {
          const img = new Image();
          img.onload = () => resolve([type, img]);
          img.onerror = () => {
            console.warn(
              `⚠️ Không tải được projectile ${url}, sẽ dùng fallback.`,
            );
            resolve([type, null]);
          };
          img.src = url;
        });
      }),
    );
    return Object.fromEntries(entries);
  }

  /**
   * Lắng nghe các sự kiện gửi từ Server thông qua WebSocket
   */
  setupSocketEvents() {
    // Sự kiện kết nối thành công
    this.socket.on("connect", () => {
      this.addLog("✅ Đã kết nối tới Server. Sẵn sàng chiến đấu!", "system");
    });

    // Sự kiện mất kết nối
    this.socket.on("disconnect", () => {
      this.addLog(
        "❌ Mất kết nối Server. Sẽ thử kết nối lại sau 3s...",
        "system",
      );
    });

    // Sự kiện chính: Server gửi gói dữ liệu cập nhật trạng thái Game (12 lần/giây)
    this.socket.on("game_update", (data) => {
      if (this.isGameOver) return;

      // 1. Cập nhật Thanh Máu UI HTML
      if (data.player_hp !== undefined && data.bot_hp !== undefined) {
        this.updateHealthUI(data.player_hp, data.bot_hp, data.last_message || "");
      }

      // 2. Cập nhật Số lượng Shuriken
      if (
        data.rasenshuriken_remaining !== undefined &&
        this.rasenshurikenCountElem
      ) {
        this.rasenshurikenCountElem.innerText = `${data.rasenshuriken_remaining}/3`;
      }

      // 3. Cập nhật Cooldown cho các chiêu thức
      if (data.cooldown) {
        this.updateCooldownUI("rasengan", data.cooldown.rasengan);
        this.updateCooldownUI("rasenshuriken", data.cooldown.rasenshuriken);
        this.updateCooldownUI("kage_bunshin", data.cooldown.kage_bunshin);
      }

      // 4. Dừng buff animation khi hết thời gian buff
      if (
        data.player_buff_remain !== undefined &&
        data.player_buff_remain <= 0
      ) {
        if (this.playerChar && this.playerChar.state === "buff") {
          this.playerChar.setState("idle");
        }
      }

      // 5. Kích hoạt Animation dựa trên dòng Log nhận được từ Server
      const eventKey = data.event_id ?? data.last_message;
      if (data.last_message && eventKey !== this.lastEventKey) {
        this.addLog(data.last_message, "skill-cast");
        this.handleAnimationFromLog(data.last_message);
        this.lastMessage = data.last_message;
        this.lastEventKey = eventKey;
      }

      // 6. Cập nhật Cốt Truyện (Story)
      if (data.story_message && this.storyContent) {
        this.storyContent.innerText = data.story_message;
        if (this.storyContent.classList.contains("hidden")) {
          this.storyContent.classList.remove("hidden");
          if (this.btnStory) this.btnStory.innerText = "📖 Đóng Cốt Truyện";
        }
      }

      // 7. Xử lý logic Game Over
      if (data.game_over) {
        this.isGameOver = true;
        if (data.winner === "player") {
          this.addLog("🏆 CHIẾN THẮNG! Bạn đã đánh bại Mizuki!", "system");
        } else {
          this.addLog("💀 THẤT BẠI! Naruto đã gục ngã...", "system");
        }
      }
    });
  }

  /**
   * Cập nhật số hiển thị máu trên DOM HTML và sinh hiệu ứng Sát thương
   */
  updateHealthUI(playerHp, botHp, eventMessage = "") {
    const hasCharacters = this.playerChar && this.botChar;
    const hitType = this.getHitTypeFromText(String(eventMessage).toLowerCase());

    // Kiểm tra sát thương cho Player (Naruto)
    if (
      hasCharacters &&
      this.playerChar.hp !== undefined &&
      playerHp < this.playerChar.hp
    ) {
      const damage = this.playerChar.hp - playerHp;
      // Gọi hàm sinh chữ sát thương (bay lên)
      this.addDamageText(
        `-${damage}`,
        this.playerChar.x,
        this.playerChar.y - 120,
      );

      // Rung màn hình dựa trên độ lớn sát thương
      if (damage >= 20) {
        this.startShake(0.3, 10);
      } else {
        this.startShake(0.15, 5);
      }

      this.registerHit("bot", damage, hitType);

      // Giữ lại chớp đỏ viền CSS
      this.triggerDamageEffect("player");
    }

    // Kiểm tra sát thương cho Boss (Mizuki)
    if (
      hasCharacters &&
      this.botChar.hp !== undefined &&
      botHp < this.botChar.hp
    ) {
      const damage = this.botChar.hp - botHp;
      this.addDamageText(
        `-${damage}`,
        this.botChar.x,
        this.botChar.y - 120,
        "#ff9900",
      ); // Màu cam cho boss

      if (damage >= 20) {
        this.startShake(0.3, 10);
      }

      this.registerHit("player", damage, hitType);
    }

    // Đồng bộ dữ liệu máu vào lớp Character để xử lý tự chết (Dead Animation)
    if (this.playerChar) this.playerChar.hp = playerHp;
    if (this.botChar) this.botChar.hp = botHp;

    // Nếu máu về 0 mà nhân vật chưa chết (chưa gọi takeDamage) thì ép chết luôn
    if (this.playerChar && this.playerChar.hp <= 0 && !this.playerChar.isDead) {
      this.playerChar.isDead = true;
      this.playerChar.setState("dead");
    }
    if (this.botChar && this.botChar.hp <= 0 && !this.botChar.isDead) {
      this.botChar.isDead = true;
      this.botChar.setState("dead");
    }

    if (this.playerHpFill) {
      this.playerHpFill.style.width = `${playerHp}%`;
      this.playerHpText.innerText = `${playerHp}/100`;
      this.playerHpFill.style.backgroundColor =
        playerHp <= 30 ? "darkred" : "var(--hp-player)";
    }
    if (this.enemyHpFill) {
      this.enemyHpFill.style.width = `${botHp}%`;
      this.enemyHpText.innerText = `${botHp}/100`;
    }
  }

  /**
   * Kích hoạt hiệu ứng Rung lắc & Chớp sáng Camera khi bị sát thương
   */
  triggerDamageEffect(target) {
    if (target === "player") {
      const videoBox = document.querySelector("#webcam-container");
      if (videoBox) {
        videoBox.classList.add("shake-effect", "damage-flash");
        setTimeout(() => {
          videoBox.classList.remove("shake-effect", "damage-flash");
        }, 300); // Gỡ hiệu ứng sau 0.3 giây
      }
    }
  }

  // ===============================================
  // CÁC HÀM XỬ LÝ EFFECTS MỚI: RUNG MÀN HÌNH & DAMAGE TEXT
  // ===============================================

  /**
   * Khởi động hiệu ứng Rung Màn Hình bằng Canvas
   * @param {number} duration - Thời gian rung (giây)
   * @param {number} intensity - Cường độ rung tối đa (pixel)
   */
  startShake(duration, intensity = 5) {
    this.shakeTimer = duration;
    this.shakeDuration = duration;
    this.shakeIntensity = intensity;
  }

  /**
   * Thêm text sát thương bay lên (Ví dụ: "-15")
   * @param {string} text - Nội dung chữ
   * @param {number} x - Tọa độ X
   * @param {number} y - Tọa độ Y
   * @param {string} color - Màu sắc (mặc định đỏ)
   */
  addDamageText(text, x, y, color = "#ff3333") {
    this.damageTexts.push({
      text: text,
      x: x + (Math.random() * 40 - 20), // Trải đều vị trí X ra chút xíu để không đè lên nhau
      y: y,
      life: 1.0, // Thời gian tồn tại (giây)
      color: color,
    });
  }

  addCombatNotice(text, x, y, color = "#ffffff", life = 0.7, size = 22) {
    this.combatNotices.push({
      text,
      x,
      y,
      color,
      life,
      maxLife: life,
      size,
    });
  }

  registerHit(attackerKey, damage, hitType = "light") {
    const combo = this.comboState[attackerKey];
    if (!combo || damage <= 0) return;

    if (combo.timer > 0) {
      combo.hits += 1;
      combo.totalDamage += damage;
    } else {
      combo.hits = 1;
      combo.totalDamage = damage;
    }

    combo.lastHitType = hitType;
    combo.timer = this.comboTimeoutSec;

    if (combo.hits >= 2) {
      const attacker = attackerKey === "player" ? this.playerChar : this.botChar;
      const x = attacker ? attacker.x : 640;
      const y = attacker ? attacker.y - 235 : 360;
      const color = hitType === "heavy" ? "#ff9a9a" : "#ffe08a";
      this.addCombatNotice(`${combo.hits} HIT`, x, y, color, 0.62, 28);
    }
  }

  flushCombo(attackerKey) {
    const combo = this.comboState[attackerKey];
    if (!combo) return;

    if (combo.hits >= 2) {
      const attacker = attackerKey === "player" ? this.playerChar : this.botChar;
      const x = attacker ? attacker.x : 640;
      const y = attacker ? attacker.y - 260 : 340;
      this.addCombatNotice(
        `COMBO ${combo.hits} | DMG ${combo.totalDamage}`,
        x,
        y,
        "#7fd3ff",
        0.9,
        20,
      );
    }

    combo.hits = 0;
    combo.totalDamage = 0;
    combo.timer = 0;
  }

  getHitTypeFromText(text) {
    if (text.includes("rasenshuriken")) return "heavy";
    if (text.includes("rasengan")) return "medium";
    if (text.includes("kunai")) return "light";
    return "medium";
  }

  resolveImpactPoint(targetChar, attackerChar = null) {
    const baseX = targetChar?.x ?? 640;
    const baseY = (targetChar?.y ?? 620) - 116;
    if (!attackerChar) return { x: baseX, y: baseY };

    const pushDir = baseX >= attackerChar.x ? -1 : 1;
    return {
      x: baseX + pushDir * 16 + (Math.random() * 10 - 5),
      y: baseY + (Math.random() * 8 - 4),
    };
  }

  spawnHitFlash(targetChar, type = "medium") {
    const profile = this.hitFlashProfile[type] || this.hitFlashProfile.medium;
    this.hitFlashes.push({
      x: targetChar.x,
      y: targetChar.y - 124,
      radius: profile.radius,
      baseRadius: profile.radius,
      color: profile.color,
      life: profile.life,
      maxLife: profile.life,
    });
  }

  spawnImpactEffect(x, y, type = "medium") {
    const profile = this.impactProfile[type] || this.impactProfile.medium;
    const particles = [];
    for (let i = 0; i < profile.particleCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 110 + Math.random() * 170;
      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
      });
    }

    this.impactEffects.push({
      x,
      y,
      color: profile.color,
      ringMax: profile.ringMax,
      life: profile.life,
      maxLife: profile.life,
      particles,
    });
  }

    emitHitEffect(targetChar, attackerChar, type = "medium") {
      if (!targetChar) return;
      const point = this.resolveImpactPoint(targetChar, attackerChar);
      this.spawnHitFlash(targetChar, type);
      this.spawnImpactEffect(point.x, point.y, type);

      const hitStop = this.hitStopProfile[type] || this.hitStopProfile.medium;
      this.hitStopTimer = Math.max(this.hitStopTimer, hitStop);

      if (typeof targetChar.applyKnockback === "function") {
        const force = this.knockbackProfile[type] || this.knockbackProfile.medium;
        const attackerX = attackerChar?.x ?? targetChar.x - 1;
        const direction = targetChar.x >= attackerX ? 1 : -1;
        targetChar.applyKnockback(direction, force, hitStop * 0.9);
      }
    }

  /**
   * Cập nhật thời gian hồi chiêu lên icon của UI HTML
   */
  updateCooldownUI(skillName, timeRemaining) {
    const el = this.cooldownElements[skillName];
    if (!el) return;

    if (timeRemaining > 0) {
      el.innerText = timeRemaining.toFixed(1); // Làm tròn 1 chữ số thập phân
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden"); // Chiêu đã sẵn sàng
    }
  }

  /**
   * Bộ não Dịch Log -> Ra lệnh cho Character múa Animation
   * @param {string} msg - Chuỗi tin nhắn gửi từ backend
   */
  handleAnimationFromLog(msg) {
    if (!this.playerChar || !this.botChar) return;

    const text = msg.toLowerCase();
    const hitType = this.getHitTypeFromText(text);

    // ======= ANIMATION CỦA NARUTO (PLAYER) =======
    // Rasenshuriken phải check TRƯỚC rasengan vì cùng chứa "rasen"
    if (text.includes("rasenshuriken")) {
      this.runTimedAction("player", this.playerChar, "attack2");
      this.startShake(0.2, 8);
    } else if (text.includes("rasengan")) {
      this.runTimedAction("player", this.playerChar, "attack1");
    } else if (text.includes("phân thân") || text.includes("kage bunshin")) {
      this.runTimedAction("player", this.playerChar, "buff");
    }

    // ======= ANIMATION CỦA MIZUKI (BOSS) =======
    // Mizuki né đòn: backend gửi "Mizuki dùng Thuật Thay Thế né được ..."
    if (text.includes("thuật thay thế")) {
      this.runTimedAction("bot", this.botChar, "dodge_right");
    }

    // Kunai của Mizuki bay ra
    if (text.includes("kunai")) {
      this.runTimedAction("bot", this.botChar, "attack1");

      if (text.includes("dính kunai")) {
        // Player dính đòn toàn bộ
        this.playerChar.takeDamage(0);
        this.emitHitEffect(this.playerChar, this.botChar, "light");
        } else if (text.includes("đỡ được kunai")) {
          // Player block — vẫn cho chạy animation hurt nhẹ
          this.runTimedAction("player", this.playerChar, "block");
          this.emitHitEffect(this.playerChar, this.botChar, "guard");
          this.addCombatNotice(
            "GUARD",
            this.playerChar.x,
            this.playerChar.y - 220,
            "#b9c8ff",
            0.65,
            24,
          );
        } else if (text.includes("né thành công")) {
          // Player né thành công
          this.runTimedAction("player", this.playerChar, "dodge_left");
        }
      }

    // Mizuki bị trúng đòn — backend gửi "Trúng đòn! ... gây N sát thương!"
    if (text.includes("trúng đòn") && text.includes("sát thương")) {
      const wasAttacking = this.botChar.state === "attack1";
      this.botChar.takeDamage(0);
      this.emitHitEffect(this.botChar, this.playerChar, hitType);
      if (wasAttacking) {
        this.addCombatNotice(
          "COUNTER",
          this.botChar.x,
          this.botChar.y - 220,
          "#ffae6b",
          0.7,
          24,
        );
      }
    }
  }

  /**
   * Hàm sinh ra đạn (Projectile)
   */
  spawnProjectile(character, speed, type) {
    if (!character) return;
    if (this.projectiles.length >= this.maxProjectilesOnScreen) return;

    const profile = this.projectileProfile[type] || {
      size: 80,
      xOffset: 50,
      yOffset: -90,
      speed: 650,
    };
    const sameTypeCount = this.projectiles.filter((p) => p.type === type).length;
    if (sameTypeCount >= 4) return;
    const resolvedSpeed = speed ?? profile.speed;
    const direction = character.side === "left" ? 1 : -1;

    // Tọa độ bắn ra theo profile từng loại đạn để khớp pose nhân vật.
    const x = character.x + profile.xOffset * direction;
    const y = character.y + profile.yOffset;
    const vx = Math.abs(resolvedSpeed) * direction;

    this.projectiles.push(
      new Projectile(
        x,
        y,
        vx,
        type,
        this.projectileImages[type] || null,
        profile.size,
      ),
    );
  }

  clearActionTimers() {
    for (const timerId of this.actionTimers) {
      clearTimeout(timerId);
    }
    this.actionTimers = [];
  }

  runTimedAction(actorKey, character, stateName) {
    if (!character || character.isDead) return;

    const now = performance.now();
    const profile = this.actionProfile[actorKey]?.[stateName];
    if (!profile) {
      character.setState(stateName);
      return;
    }

    if (now < this.actionLockUntil[actorKey]) {
      return;
    }

    const startup = Math.max(0, profile.startupMs || 0);
    const recovery = Math.max(80, profile.recoveryMs || 0);
    this.actionLockUntil[actorKey] = now + startup + recovery;
    character.setState(stateName);

    const runActive = () => {
      if (this.isGameOver || character.isDead) return;
      if (profile.projectile) {
        this.spawnProjectile(character, null, profile.projectile);
      }
    };

    if (startup > 0) {
      const timerId = setTimeout(runActive, startup);
      this.actionTimers.push(timerId);
    } else {
      runActive();
    }
  }

  escapeHtml(value) {
    return String(value).replace(
      /[&<>"']/g,
      (ch) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[ch],
    );
  }

  /**
   * Viết Log ra màn hình HTML
   */
  addLog(message, type = "") {
    if (!this.logContainer) return;

    // Bôi màu từ khóa nổi bật (Optional)
    let formattedMsg = this.escapeHtml(message)
      .replace(
        /(Rasengan|Rasenshuriken)/gi,
        '<span style="color: #ffaa00; font-weight: bold;">$1</span>',
      )
      .replace(
        /(\d+ sát thương|mất \d+ máu)/gi,
        '<span style="color: #ff3333; font-weight: bold;">$1</span>',
      );

    const p = document.createElement("p");
    p.className = `log-entry ${type}`;
    p.innerHTML = `[${new Date().toLocaleTimeString()}] ${formattedMsg}`;

    this.logContainer.appendChild(p);
    this.logContainer.scrollTop = this.logContainer.scrollHeight; // Cuộn xuống cùng
  }

  /**
   * Reset Game (Gửi lệnh lên server và khôi phục giao diện)
   */
  resetGame() {
    this.clearActionTimers();
    if (this.socket) {
      this.socket.emit("reset_game");
    }
    this.isGameOver = false;
    this.lastMessage = "";
    this.lastEventKey = null;
    this.projectiles = [];
    this.damageTexts = [];
    this.hitFlashes = [];
    this.impactEffects = [];
    this.combatNotices = [];
    this.shakeTimer = 0;
    this.shakeDuration = 0;
    this.hitStopTimer = 0;
    this.comboState.player.hits = 0;
    this.comboState.player.totalDamage = 0;
    this.comboState.player.timer = 0;
    this.comboState.bot.hits = 0;
    this.comboState.bot.totalDamage = 0;
    this.comboState.bot.timer = 0;
    this.actionLockUntil.player = 0;
    this.actionLockUntil.bot = 0;

    if (this.logContainer) this.logContainer.innerHTML = ""; // Xóa sạch bảng Log
    if (this.playerChar) this.playerChar.reset();
    if (this.botChar) this.botChar.reset();
    this.updateHealthUI(100, 100);
    if (this.rasenshurikenCountElem)
      this.rasenshurikenCountElem.innerText = "3/3";
    Object.values(this.cooldownElements).forEach((el) => {
      if (el) el.classList.add("hidden");
    });

    this.addLog("🔄 Trận đấu đã được thiết lập lại. Sẵn sàng!", "system");
  }

  // ===============================================
  // CÁC HÀM CUNG CẤP CHO GAME LOOP CỦA game2d.js
  // ===============================================

  update(deltaTime) {
    if (deltaTime > 0) {
      const fpsNow = 1 / deltaTime;
      this.fpsEstimate =
        this.fpsEstimate + (fpsNow - this.fpsEstimate) * this.fpsSmoothing;
    }

    let simDelta = deltaTime;
    if (this.hitStopTimer > 0) {
      this.hitStopTimer -= deltaTime;
      if (this.hitStopTimer < 0) this.hitStopTimer = 0;
      simDelta = 0;
    }

    if (this.playerChar) this.playerChar.update(simDelta);
    if (this.botChar) this.botChar.update(simDelta);

    // Cập nhật đạn bay
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      let p = this.projectiles[i];
        p.update(simDelta);

      // Xóa nếu đạn bay ra khỏi màn hình
      if (!p.active) {
        this.projectiles.splice(i, 1);
      }
    }

    // ==========================================
    // CẬP NHẬT HIỆU ỨNG (Screen Shake & Damage Text)
    // ==========================================

    // 1. Cập nhật Rung màn hình
    if (this.shakeTimer > 0) {
      this.shakeTimer -= deltaTime;
      if (this.shakeTimer <= 0) {
        this.shakeTimer = 0;
        this.shakeX = 0;
        this.shakeY = 0;
      } else {
        const t = Math.max(0, this.shakeTimer / Math.max(this.shakeDuration, 0.0001));
        const eased = t * t;
        const currentIntensity = this.shakeIntensity * eased;
        this.shakeX = (Math.random() - 0.5) * 2 * currentIntensity;
        this.shakeY = (Math.random() - 0.5) * 2 * currentIntensity;
      }
    }

    // 2. Cập nhật chữ bay (Damage Text)
    for (let i = this.damageTexts.length - 1; i >= 0; i--) {
      let dt = this.damageTexts[i];
      dt.life -= deltaTime;
      dt.y -= 50 * deltaTime; // Bay lên tốc độ 50px/s
      if (dt.life <= 0) {
        this.damageTexts.splice(i, 1);
      }
    }

    for (const side of ["player", "bot"]) {
      const combo = this.comboState[side];
      if (combo.timer > 0) {
        combo.timer -= deltaTime;
        if (combo.timer <= 0) {
          this.flushCombo(side);
        }
      }
    }

    for (let i = this.combatNotices.length - 1; i >= 0; i--) {
      const notice = this.combatNotices[i];
      notice.life -= deltaTime;
      const t = Math.max(0, Math.min(1, notice.life / notice.maxLife));
      const rise = 14 + (1 - t) * 26;
      notice.y -= rise * deltaTime;
      if (notice.life <= 0) {
        this.combatNotices.splice(i, 1);
      }
    }

    for (let i = this.hitFlashes.length - 1; i >= 0; i--) {
      const flash = this.hitFlashes[i];
      flash.life -= deltaTime;
      if (flash.life <= 0) {
        this.hitFlashes.splice(i, 1);
      }
    }

    for (let i = this.impactEffects.length - 1; i >= 0; i--) {
      const impact = this.impactEffects[i];
      impact.life -= deltaTime;
      const drag = 0.9;

      for (const p of impact.particles) {
        p.x += p.vx * deltaTime;
        p.y += p.vy * deltaTime;
        p.vx *= drag;
        p.vy = p.vy * drag + 170 * deltaTime;
      }

      if (impact.life <= 0) {
        this.impactEffects.splice(i, 1);
      }
    }
  }

  draw(ctx) {
    ctx.save(); // Lưu trạng thái gốc của Canvas

    // Áp dụng rung màn hình (Dịch chuyển hệ tọa độ Canvas)
    if (this.shakeTimer > 0) {
      ctx.translate(this.shakeX, this.shakeY);
    }

    if (this.playerChar) {
      this.playerChar.draw(ctx);
      // Vẽ IDLE text như cũ
      ctx.fillStyle = this.playerChar.state === "hurt" ? "#FF0000" : "#FFFFFF";
      ctx.font = "bold 16px Poppins, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        this.playerChar.state.toUpperCase(),
        this.playerChar.x,
        this.playerChar.y - 200,
      );
    }
    if (this.botChar) {
      this.botChar.draw(ctx);
      ctx.fillStyle = this.botChar.state === "hurt" ? "#FF0000" : "#FFFFFF";
      ctx.font = "bold 16px Poppins, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        this.botChar.state.toUpperCase(),
        this.botChar.x,
        this.botChar.y - 200,
      );
    }

    // Vẽ đạn
    this.projectiles.forEach((p) => p.draw(ctx));

    for (const flash of this.hitFlashes) {
      const t = Math.max(0, Math.min(1, flash.life / flash.maxLife));
      ctx.globalAlpha = t * 0.8;
      const pulseRadius = flash.baseRadius * (1.08 + (1 - t) * 0.28);
      const glow = ctx.createRadialGradient(
        flash.x,
        flash.y,
        0,
        flash.x,
        flash.y,
        pulseRadius,
      );
      glow.addColorStop(0, flash.color);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(flash.x, flash.y, pulseRadius, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const impact of this.impactEffects) {
      const t = Math.max(0, Math.min(1, impact.life / impact.maxLife));
      const ringRadius = impact.ringMax * (1 - t);
      ctx.globalAlpha = t * 0.9;
      ctx.strokeStyle = impact.color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(impact.x, impact.y, ringRadius, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = impact.color;
      for (const p of impact.particles) {
        ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
      }
    }

    for (const notice of this.combatNotices) {
      const alpha = Math.max(0, Math.min(1, notice.life / notice.maxLife));
      ctx.globalAlpha = alpha;
      ctx.fillStyle = notice.color;
      ctx.font = `bold ${notice.size}px Poppins, sans-serif`;
      ctx.textAlign = "center";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 4;
      ctx.strokeText(notice.text, notice.x, notice.y);
      ctx.fillText(notice.text, notice.x, notice.y);
    }

    if (this.debugEnabled) {
      ctx.globalAlpha = 0.92;
      ctx.fillStyle = "rgba(8, 12, 20, 0.8)";
      ctx.fillRect(16, 16, 250, 132);
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#9be7ff";
      ctx.font = "bold 14px Consolas, monospace";
      ctx.textAlign = "left";
      ctx.fillText(`FPS: ${this.fpsEstimate.toFixed(1)}`, 28, 40);
      ctx.fillText(`Projectiles: ${this.projectiles.length}`, 28, 60);
      ctx.fillText(`HitStop: ${this.hitStopTimer.toFixed(3)}s`, 28, 80);
      ctx.fillText(`Combo P: ${this.comboState.player.hits}`, 28, 100);
      ctx.fillText(`Combo B: ${this.comboState.bot.hits}`, 28, 120);
      ctx.fillText(
        `Shake: ${this.shakeTimer.toFixed(2)} / ${this.shakeDuration.toFixed(2)}`,
        28,
        140,
      );
    }

    // Vẽ chữ bay sát thương (Damage Texts)
    for (let dt of this.damageTexts) {
      ctx.globalAlpha = Math.max(0, Math.min(1, dt.life)); // Mờ dần
      ctx.fillStyle = dt.color;
      ctx.font = "bold 24px Poppins, sans-serif";
      ctx.textAlign = "center";

      // Viền chữ (Outline) đen
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 4;
      ctx.strokeText(dt.text, dt.x, dt.y);

      // Màu chữ
      ctx.fillText(dt.text, dt.x, dt.y);
    }

    ctx.globalAlpha = 1.0; // Phục hồi Alpha
    ctx.restore(); // Phục hồi Canvas (kết thúc vùng bị Rung)
  }
}

// ==========================================
// ĐÓNG GÓI VÀ XUẤT MODULE
// ==========================================

// Khởi tạo 1 Instance (Singleton) duy nhất của GameEngine
const engine = new GameEngine();

// Gắn các hàm quan trọng vào window.gameEngine để file khác (game2d.js, script.js) có thể gọi
window.gameEngine = {
  initGameEngine: () => engine.initGameEngine(),
  applyConfig: (config) => engine.applyConfig(config),
  update: (dt) => engine.update(dt),
  draw: (ctx) => engine.draw(ctx),
  resetGame: () => engine.resetGame(),
  instance: engine,
};

// ==========================================
// CLASS ĐẠN BAY (PROJECTILE)
// ==========================================
class Projectile {
  constructor(x, y, speed, type, image = null, size = 84) {
    this.x = x;
    this.y = y;
    this.speed = speed;
    this.type = type; // "rasengan", "rasenshuriken", "kunai"
    this.image = image;
    this.active = true;
    this.size = size;
  }

  update(dt) {
    this.x += this.speed * dt;
    // Xóa đạn nếu bay ra quá xa
    if (this.x < -100 || this.x > 2000) {
      this.active = false;
    }
  }

  draw(ctx) {
    if (this.image && this.image.complete && this.image.naturalWidth > 0) {
      ctx.save();
      ctx.translate(this.x, this.y);
      if (this.speed < 0) {
        ctx.scale(-1, 1);
      }
      const aspect = this.image.naturalWidth / this.image.naturalHeight;
      const width = this.size;
      const height = width / aspect;
      ctx.drawImage(this.image, -width / 2, -height / 2, width, height);
      ctx.restore();
      return;
    }

    // Fallback nếu ảnh projectile thiếu hoặc lỗi.
    ctx.beginPath();
    ctx.fillStyle = this.type === "kunai" ? "#ffaa00" : "#00a2ff";
    ctx.arc(this.x, this.y, this.size * 0.22, 0, Math.PI * 2);
    ctx.fill();
  }
}
