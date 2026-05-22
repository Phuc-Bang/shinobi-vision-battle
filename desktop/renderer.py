import os
import sys
import time

import cv2
import pygame


POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24),
    (23, 24), (23, 25), (24, 26), (25, 27), (26, 28), (27, 31), (28, 32),
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (17, 18), (18, 19), (19, 20),
]


class DesktopRenderer:
    def __init__(self, root_dir, width=1280, height=720, preview_fps=15):
        pygame.init()
        self.base_width = 1280
        self.base_height = 720
        self.root_dir = root_dir
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Shinobi Vision Battle - Desktop")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.title_font = pygame.font.SysFont("consolas", 54, bold=True)
        self.pause_title_font = pygame.font.SysFont("consolas", 42, bold=True)
        self.logs = []
        self.scene_rect = pygame.Rect(20, 20, 840, 500)
        self.hud_rect = pygame.Rect(880, 20, 380, 680)
        self.controls_rect = pygame.Rect(20, 540, 410, 160)
        self.preview_rect = pygame.Rect(450, 540, 410, 160)
        self.show_skeleton = True
        self.show_preview = True
        self.preview_fps = max(1, int(preview_fps))
        self._preview_interval = 1.0 / self.preview_fps
        self._preview_last_ts = 0.0
        self._preview_surface = None
        self.projectiles = []
        self.damage_texts = []
        self.hit_flashes = []
        self.player_state = "idle"
        self.bot_state = "idle"
        self.player_state_until = 0.0
        self.bot_state_until = 0.0
        self._load_assets()
        self._status_bottom_y = self.hud_rect.y + 560
        self._menu_start_rect = None
        self._menu_quit_rect = None
        self._menu_controls = None
        self.resize(width, height)

    def resize(self, width, height):
        self.width = max(1024, int(width))
        self.height = max(640, int(height))
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        sx = self.width / self.base_width
        sy = self.height / self.base_height
        self.ui_scale = min(sx, sy)
        margin = int(20 * self.ui_scale)
        gap = int(20 * self.ui_scale)
        top_h = self.height - margin * 2
        hud_w = int(380 * sx)
        left_w = self.width - (margin * 2) - gap - hud_w
        bottom_h = int(160 * sy)
        scene_h = max(360, top_h - bottom_h - gap)

        self.scene_rect = pygame.Rect(margin, margin, left_w, scene_h)
        self.hud_rect = pygame.Rect(self.scene_rect.right + gap, margin, hud_w, top_h)

        controls_w = int((left_w - gap) * 0.5)
        preview_w = left_w - gap - controls_w
        bottom_y = self.scene_rect.bottom + gap
        self.controls_rect = pygame.Rect(margin, bottom_y, controls_w, bottom_h)
        self.preview_rect = pygame.Rect(self.controls_rect.right + gap, bottom_y, preview_w, bottom_h)

        self.font = pygame.font.SysFont("consolas", max(16, int(20 * self.ui_scale)))
        self.small_font = pygame.font.SysFont("consolas", max(13, int(16 * self.ui_scale)))
        self.title_font = pygame.font.SysFont("consolas", max(40, int(54 * self.ui_scale)), bold=True)
        self.pause_title_font = pygame.font.SysFont("consolas", max(30, int(42 * self.ui_scale)), bold=True)

    def set_preview_fps(self, fps):
        fps = max(1, int(fps))
        if fps == self.preview_fps:
            return
        self.preview_fps = fps
        self._preview_interval = 1.0 / self.preview_fps

    def render_fps(self):
        return float(self.clock.get_fps())

    def menu_buttons(self):
        if self._menu_start_rect is not None and self._menu_quit_rect is not None:
            return self._menu_start_rect, self._menu_quit_rect
        layout = self._compute_menu_layout()
        return layout["start_rect"], layout["quit_rect"]

    def menu_controls(self):
        if self._menu_controls is not None:
            return self._menu_controls
        return self._compute_menu_layout()["controls"]

    def _compute_menu_layout(self):
        panel_w = min(int(760 * self.ui_scale), self.width - 80)
        panel_h = min(int(740 * self.ui_scale), self.height - 40)
        panel = pygame.Rect(self.width // 2 - panel_w // 2, self.height // 2 - panel_h // 2, panel_w, panel_h)

        bw = min(int(370 * self.ui_scale), panel.width - 80)
        start_h = int(58 * self.ui_scale)
        quit_h = int(50 * self.ui_scale)
        x = self.width // 2 - bw // 2
        start_y = panel.y + int(350 * self.ui_scale)
        start_rect = pygame.Rect(x, start_y, bw, start_h)
        quit_rect = pygame.Rect(x, start_rect.bottom + max(10, int(14 * self.ui_scale)), bw, quit_h)

        w = min(int(560 * self.ui_scale), panel.width - 60)
        row_h = max(34, int(40 * self.ui_scale))
        btn_w = max(30, int(36 * self.ui_scale))
        gap = max(6, int(8 * self.ui_scale))
        y0 = quit_rect.bottom + max(14, int(16 * self.ui_scale))
        cx = self.width // 2 - w // 2
        available_h = (panel.bottom - 14) - y0
        needed_h = (row_h * 4) + (gap * 3)
        if needed_h > available_h and available_h > 0:
            scale = available_h / float(needed_h)
            row_h = max(28, int(row_h * scale))
            gap = max(3, int(gap * scale))
        perf_row = pygame.Rect(cx, y0, w, row_h)
        cam_row = pygame.Rect(cx, perf_row.bottom + gap, w, row_h)
        controls = {
            "perf_row": perf_row,
            "cam_row": cam_row,
            "perf_prev": pygame.Rect(perf_row.x + 6, perf_row.y + 4, btn_w, row_h - 8),
            "perf_next": pygame.Rect(perf_row.right - btn_w - 6, perf_row.y + 4, btn_w, row_h - 8),
            "cam_prev": pygame.Rect(cam_row.x + 6, cam_row.y + 4, btn_w, row_h - 8),
            "cam_next": pygame.Rect(cam_row.right - btn_w - 6, cam_row.y + 4, btn_w, row_h - 8),
            "mirror_toggle": pygame.Rect(cx, cam_row.bottom + gap, w, row_h),
            "reset_settings": pygame.Rect(cx, cam_row.bottom + gap + row_h + gap, w, row_h),
        }
        return {"panel": panel, "start_rect": start_rect, "quit_rect": quit_rect, "controls": controls}

    def draw_menu(self, performance_preset, camera_label, camera_index, mirror_on):
        self.screen.fill((18, 20, 26))
        if self.bg is not None:
            bg = pygame.transform.smoothscale(self.bg, (self.width, self.height))
            self.screen.blit(bg, (0, 0))
            shade = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 135))
            self.screen.blit(shade, (0, 0))

        layout = self._compute_menu_layout()
        panel = layout["panel"]
        start_rect = layout["start_rect"]
        quit_rect = layout["quit_rect"]
        controls = layout["controls"]
        self._menu_start_rect = start_rect
        self._menu_quit_rect = quit_rect
        self._menu_controls = controls
        panel_bg = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        panel_bg.fill((8, 12, 20, 150))
        self.screen.blit(panel_bg, panel.topleft)
        pygame.draw.rect(self.screen, (255, 166, 42), panel, width=2, border_radius=12)

        title = self.title_font.render(
            "SHINOBI BATTLE", True, (255, 184, 45)
        )
        self.screen.blit(title, title.get_rect(center=(self.width // 2, panel.y + int(72 * self.ui_scale))))

        subtitle = self.font.render("Desktop Local Mode", True, (235, 235, 235))
        self.screen.blit(subtitle, subtitle.get_rect(center=(self.width // 2, panel.y + int(124 * self.ui_scale))))

        if self.avatar_naruto is not None:
            av = int(110 * self.ui_scale)
            avatar = pygame.transform.smoothscale(self.avatar_naruto, (av, av))
            self.screen.blit(avatar, (panel.centerx - int(168 * self.ui_scale), panel.y + int(180 * self.ui_scale)))
        if self.avatar_mizuki is not None:
            av = int(110 * self.ui_scale)
            avatar = pygame.transform.smoothscale(self.avatar_mizuki, (av, av))
            self.screen.blit(avatar, (panel.centerx + int(58 * self.ui_scale), panel.y + int(180 * self.ui_scale)))

        versus = self.pause_title_font.render("VS", True, (255, 72, 72))
        self.screen.blit(versus, versus.get_rect(center=(self.width // 2, panel.y + int(246 * self.ui_scale))))

        p1 = self.font.render("NARUTO", True, (245, 245, 245))
        p2 = self.font.render("MIZUKI", True, (245, 245, 245))
        self.screen.blit(p1, p1.get_rect(center=(panel.centerx - int(120 * self.ui_scale), panel.y + int(340 * self.ui_scale))))
        self.screen.blit(p2, p2.get_rect(center=(panel.centerx + int(120 * self.ui_scale), panel.y + int(340 * self.ui_scale))))

        mouse = pygame.mouse.get_pos()
        start_bg = (255, 186, 68) if start_rect.collidepoint(mouse) else (255, 166, 42)
        quit_bg = (44, 50, 66) if quit_rect.collidepoint(mouse) else (30, 34, 45)
        pygame.draw.rect(self.screen, start_bg, start_rect, border_radius=8)
        pygame.draw.rect(self.screen, quit_bg, quit_rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 72, 72), quit_rect, width=2, border_radius=8)

        start = self.font.render("ENTER / SPACE  START", True, (10, 10, 12))
        quit_text = self.font.render("ESC  QUIT", True, (245, 245, 245))
        self.screen.blit(start, start.get_rect(center=start_rect.center))
        self.screen.blit(quit_text, quit_text.get_rect(center=quit_rect.center))

        for key in ("perf_row", "cam_row", "mirror_toggle", "reset_settings"):
            rect = controls[key]
            pygame.draw.rect(self.screen, (30, 34, 45), rect, border_radius=6)
            pygame.draw.rect(self.screen, (255, 166, 42), rect, width=1, border_radius=6)
            if rect.collidepoint(mouse):
                pygame.draw.rect(self.screen, (52, 60, 80), rect, border_radius=6)
                pygame.draw.rect(self.screen, (255, 184, 45), rect, width=2, border_radius=6)

        for key in ("perf_prev", "perf_next", "cam_prev", "cam_next"):
            rect = controls[key]
            pygame.draw.rect(self.screen, (22, 28, 40), rect, border_radius=6)
            pygame.draw.rect(self.screen, (255, 166, 42), rect, width=1, border_radius=6)
            if rect.collidepoint(mouse):
                pygame.draw.rect(self.screen, (58, 72, 96), rect, border_radius=6)
                pygame.draw.rect(self.screen, (255, 200, 90), rect, width=2, border_radius=6)

        labels = {
            "perf_prev": "<",
            "perf_next": ">",
            "cam_prev": "-",
            "cam_next": "+",
            "mirror_toggle": f"Mirror: {'ON' if mirror_on else 'OFF'} (click to toggle)",
            "reset_settings": "Reset Settings (default)",
        }
        for key, text_value in labels.items():
            rect = controls[key]
            text = self.small_font.render(text_value, True, (240, 240, 240))
            self.screen.blit(text, text.get_rect(center=rect.center))

        perf_value = self.small_font.render(f"Performance: {performance_preset}", True, (230, 236, 246))
        cam_value = self.small_font.render(f"Camera Index: {camera_index}  |  {camera_label}", True, (230, 236, 246))
        self.screen.blit(perf_value, perf_value.get_rect(center=controls["perf_row"].center))
        self.screen.blit(cam_value, cam_value.get_rect(center=controls["cam_row"].center))

        pygame.display.flip()
        self.clock.tick(60)

    def pause_buttons(self):
        center_x = self.width // 2
        bw = int(360 * self.ui_scale)
        bh = max(40, int(48 * self.ui_scale))
        gap = max(10, int(12 * self.ui_scale))
        base_y = self.height // 2 - int(30 * self.ui_scale)
        return {
            "resume": pygame.Rect(center_x - bw // 2, base_y, bw, bh),
            "restart": pygame.Rect(center_x - bw // 2, base_y + bh + gap, bw, bh),
            "menu": pygame.Rect(center_x - bw // 2, base_y + (bh + gap) * 2, bw, bh),
        }

    def draw_pause_overlay(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        self.screen.blit(overlay, (0, 0))

        title = self.pause_title_font.render("PAUSED", True, (255, 184, 45))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 96)))

        buttons = self.pause_buttons()
        mouse = pygame.mouse.get_pos()
        items = [("resume", "Resume"), ("restart", "Restart"), ("menu", "Back To Menu")]
        for key, label in items:
            rect = buttons[key]
            bg = (44, 50, 66) if rect.collidepoint(mouse) else (30, 34, 45)
            border = (255, 184, 45) if rect.collidepoint(mouse) else (255, 166, 42)
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=8)
            text = self.font.render(label, True, (240, 240, 240))
            self.screen.blit(text, text.get_rect(center=rect.center))

        pygame.display.flip()
        self.clock.tick(60)

    def _resolve_asset_path(self, rel_path):
        candidates = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(meipass)
        if self.root_dir:
            candidates.append(self.root_dir)
            candidates.append(os.path.dirname(self.root_dir))
        candidates.append(os.getcwd())
        for base in candidates:
            full_path = os.path.join(base, rel_path)
            if os.path.exists(full_path):
                return full_path
        return None

    def _load_image(self, rel_path):
        full_path = self._resolve_asset_path(rel_path)
        if not full_path:
            return None
        try:
            loaded = pygame.image.load(full_path)
            if loaded.get_alpha() is None:
                return loaded.convert()
            return loaded.convert_alpha()
        except Exception:
            return None

    def _fit_height(self, surface, target_h):
        if surface is None:
            return None
        w, h = surface.get_size()
        if h <= 0:
            return surface
        scale = target_h / h
        return pygame.transform.smoothscale(surface, (int(w * scale), int(target_h)))

    def _fit_size(self, surface, size):
        if surface is None:
            return None
        return pygame.transform.smoothscale(surface, size)

    def _load_assets(self):
        self.bg = self._load_image("frontend/assets/images/background/arena.png")
        if self.bg is None:
            self.bg = self._load_image("frontend/assets/images/background/arena_konoha.jpg")
        self.avatar_naruto = self._fit_size(
            self._load_image("frontend/assets/images/sprites/naruto/avatar_naruto.png"), (54, 54)
        )
        self.avatar_mizuki = self._fit_size(
            self._load_image("frontend/assets/images/sprites/mizuki/avatar_mizuki.png"), (54, 54)
        )
        if self.avatar_naruto is None:
            self.avatar_naruto = self._fit_size(
                self._load_image("frontend/assets/images/sprites/naruto/idle.png"), (54, 54)
            )
        if self.avatar_mizuki is None:
            self.avatar_mizuki = self._fit_size(
                self._load_image("frontend/assets/images/sprites/mizuki/idle.png"), (54, 54)
            )
        self.skill_icons = {
            "kage_bunshin": self._fit_size(
                self._load_image("frontend/assets/images/ui/skill_kagebunshin.png"), (58, 58)
            ),
            "rasengan": self._fit_size(
                self._load_image("frontend/assets/images/ui/skill_rasengan.png"), (58, 58)
            ),
            "rasenshuriken": self._fit_size(
                self._load_image("frontend/assets/images/ui/skill_rasenshuriken.png"), (58, 58)
            ),
        }
        self.naruto_idle = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/idle.png"), 250
        )
        self.mizuki_idle = self._fit_height(
            self._load_image("frontend/assets/images/sprites/mizuki/idle.png"), 255
        )
        self.proj_images = {
            "rasengan": self._fit_height(
                self._load_image("frontend/assets/images/projectiles/rasengan.png"), 74
            ),
            "rasenshuriken": self._fit_height(
                self._load_image("frontend/assets/images/projectiles/rasenshuriken.png"), 88
            ),
            "kunai": self._fit_height(
                self._load_image("frontend/assets/images/projectiles/kunai.png"), 54
            ),
        }
        self.naruto_attack = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/rasengan.png"), 260
        )
        self.naruto_rasenshuriken = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/rasenshuriken.png"), 265
        )
        self.naruto_kage = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/kagebunshin.png"), 258
        )
        self.naruto_block = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/block.png"), 250
        )
        self.naruto_dodge_left = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/dodge_left.png"), 245
        )
        self.naruto_dodge_right = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/dodge_right.png"), 245
        )
        self.naruto_hurt = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/hurt.png"), 250
        )
        self.naruto_dead = self._fit_height(
            self._load_image("frontend/assets/images/sprites/naruto/dead.png"), 235
        )
        self.mizuki_attack = self._fit_height(
            self._load_image("frontend/assets/images/sprites/mizuki/throw_kunai.png"), 265
        )
        self.mizuki_hurt = self._fit_height(
            self._load_image("frontend/assets/images/sprites/mizuki/hurt.png"), 255
        )
        self.mizuki_dead = self._fit_height(
            self._load_image("frontend/assets/images/sprites/mizuki/dead.png"), 240
        )

    def trigger_projectile(self, kind):
        kind = (kind or "").lower()
        if kind not in ("rasengan", "rasenshuriken", "kunai"):
            return
        if kind == "kunai":
            start_x, end_x = self.scene_rect.right - 170, self.scene_rect.left + 210
            y = self.scene_rect.bottom - 250
            speed = -720
        elif kind == "rasenshuriken":
            start_x, end_x = self.scene_rect.left + 200, self.scene_rect.right - 230
            y = self.scene_rect.bottom - 250
            speed = 540
        else:
            start_x, end_x = self.scene_rect.left + 200, self.scene_rect.right - 230
            y = self.scene_rect.bottom - 245
            speed = 670
        self.projectiles.append(
            {
                "kind": kind,
                "x": float(start_x),
                "y": float(y),
                "vx": float(speed),
                "target_x": float(end_x),
            }
        )

    def trigger_state(self, fighter, state, duration_sec=0.35):
        until = time.perf_counter() + max(0.05, duration_sec)
        if fighter == "player":
            self.player_state = state
            self.player_state_until = until
        else:
            self.bot_state = state
            self.bot_state_until = until

    def trigger_damage(self, fighter, amount):
        if amount <= 0:
            return
        if fighter == "player":
            x = self.scene_rect.left + 210
            y = self.scene_rect.bottom - 290
        else:
            x = self.scene_rect.right - 220
            y = self.scene_rect.bottom - 290
        self.damage_texts.append(
            {"text": f"-{amount}", "x": float(x), "y": float(y), "life": 0.9}
        )
        self.hit_flashes.append({"fighter": fighter, "life": 0.18})

    def push_log(self, text):
        ts = time.strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {text}")
        self.logs = self.logs[-14:]

    def draw(self, game_state, input_snapshot, latest_frame, dt_sec):
        self.screen.fill((18, 20, 26))
        self._draw_scene_background()
        pygame.draw.rect(self.screen, (20, 22, 30), self.hud_rect, border_radius=8)
        pygame.draw.rect(self.screen, (20, 22, 30), self.controls_rect, border_radius=8)
        pygame.draw.rect(self.screen, (20, 22, 30), self.preview_rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 166, 42), self.controls_rect, width=1, border_radius=8)
        pygame.draw.rect(self.screen, (255, 166, 42), self.preview_rect, width=1, border_radius=8)

        self._update_states()
        self._update_projectiles(dt_sec)
        self._update_effects(dt_sec)
        self._draw_fighters()
        self._draw_projectiles()
        self._draw_hit_flashes()
        self._draw_damage_texts()
        self._draw_title()
        self._draw_hp(game_state)
        self._draw_status(input_snapshot)
        self._draw_logs()
        self._draw_controls_panel()
        if self.show_preview:
            self._draw_preview(latest_frame, input_snapshot.get("landmarks", {}))
        else:
            self._draw_preview_off_panel()

        pygame.display.flip()
        self.clock.tick(60)

    def _update_states(self):
        now = time.perf_counter()
        if now >= self.player_state_until:
            self.player_state = "idle"
        if now >= self.bot_state_until:
            self.bot_state = "idle"

    def _draw_scene_background(self):
        if self.bg is None:
            pygame.draw.rect(self.screen, (35, 38, 48), self.scene_rect, border_radius=8)
            return
        bg = pygame.transform.smoothscale(self.bg, self.scene_rect.size)
        self.screen.blit(bg, self.scene_rect.topleft)
        pygame.draw.rect(self.screen, (255, 166, 42), self.scene_rect, width=2, border_radius=8)

    def _draw_fighters(self):
        floor_y = self.scene_rect.bottom - 55
        n = self.naruto_idle
        if self.player_state == "dead" and self.naruto_dead is not None:
            n = self.naruto_dead
        elif self.player_state == "rasenshuriken" and self.naruto_rasenshuriken is not None:
            n = self.naruto_rasenshuriken
        elif self.player_state == "kage_bunshin" and self.naruto_kage is not None:
            n = self.naruto_kage
        elif self.player_state == "block" and self.naruto_block is not None:
            n = self.naruto_block
        elif self.player_state == "dodge_left" and self.naruto_dodge_left is not None:
            n = self.naruto_dodge_left
        elif self.player_state == "dodge_right" and self.naruto_dodge_right is not None:
            n = self.naruto_dodge_right
        elif self.player_state == "attack" and self.naruto_attack is not None:
            n = self.naruto_attack
        elif self.player_state == "hurt" and self.naruto_hurt is not None:
            n = self.naruto_hurt
        if n is not None:
            self.screen.blit(n, (self.scene_rect.left + 110, floor_y - n.get_height()))
        m = self.mizuki_idle
        if self.bot_state == "dead" and self.mizuki_dead is not None:
            m = self.mizuki_dead
        elif self.bot_state == "attack" and self.mizuki_attack is not None:
            m = self.mizuki_attack
        elif self.bot_state == "hurt" and self.mizuki_hurt is not None:
            m = self.mizuki_hurt
        if m is not None:
            m = pygame.transform.flip(m, True, False)
            self.screen.blit(m, (self.scene_rect.right - 290, floor_y - m.get_height()))

    def _update_projectiles(self, dt_sec):
        for p in self.projectiles:
            p["x"] += p["vx"] * dt_sec
        self.projectiles = [
            p for p in self.projectiles
            if (p["vx"] > 0 and p["x"] < p["target_x"]) or (p["vx"] < 0 and p["x"] > p["target_x"])
        ]

    def _draw_projectiles(self):
        for p in self.projectiles:
            img = self.proj_images.get(p["kind"])
            if img is not None:
                draw_img = img
                if p["vx"] < 0:
                    draw_img = pygame.transform.flip(draw_img, True, False)
                x = int(p["x"] - draw_img.get_width() / 2)
                y = int(p["y"] - draw_img.get_height() / 2)
                self.screen.blit(draw_img, (x, y))
            else:
                color = (38, 179, 255) if p["kind"] != "kunai" else (255, 190, 70)
                pygame.draw.circle(self.screen, color, (int(p["x"]), int(p["y"])), 16)

    def _update_effects(self, dt_sec):
        for item in self.damage_texts:
            item["life"] -= dt_sec
            item["y"] -= 72 * dt_sec
        self.damage_texts = [d for d in self.damage_texts if d["life"] > 0]

        for f in self.hit_flashes:
            f["life"] -= dt_sec
        self.hit_flashes = [f for f in self.hit_flashes if f["life"] > 0]

    def _draw_damage_texts(self):
        for d in self.damage_texts:
            alpha = max(0, min(255, int(255 * d["life"])))
            txt = self.font.render(d["text"], True, (255, 72, 72))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (int(d["x"]), int(d["y"])))

    def _draw_hit_flashes(self):
        for flash in self.hit_flashes:
            alpha = max(0, min(180, int(180 * flash["life"] / 0.18)))
            surf = pygame.Surface((220, 280), pygame.SRCALPHA)
            surf.fill((255, 100, 100, alpha))
            if flash["fighter"] == "player":
                x = self.scene_rect.left + 110
            else:
                x = self.scene_rect.right - 330
            y = self.scene_rect.bottom - 340
            self.screen.blit(surf, (x, y))

    def _draw_title(self):
        text = self.font.render("SHINOBI BATTLE (Desktop Local)", True, (255, 184, 45))
        self.screen.blit(text, (self.hud_rect.x + 20, self.hud_rect.y + 12))

    def _draw_hp_bar(self, x, y, hp, color):
        hp = max(0, min(100, int(hp)))
        pygame.draw.rect(self.screen, (58, 58, 58), (x, y, 300, 24), border_radius=12)
        pygame.draw.rect(self.screen, color, (x, y, int(300 * hp / 100), 24), border_radius=12)
        txt = self.small_font.render(f"{hp}/100", True, (240, 240, 240))
        self.screen.blit(txt, (x + 130, y + 3))

    def _draw_hp(self, state):
        player_hp = state.get("player_hp", 100)
        bot_hp = state.get("bot_hp", 100)
        p = self.font.render("NARUTO", True, (230, 230, 230))
        b = self.font.render("MIZUKI", True, (230, 230, 230))
        x = self.hud_rect.x + 20
        y = self.hud_rect.y + 58
        if self.avatar_naruto is not None:
            self.screen.blit(self.avatar_naruto, (x, y))
        if self.avatar_mizuki is not None:
            self.screen.blit(self.avatar_mizuki, (x, y + int(80 * self.ui_scale)))
        self.screen.blit(p, (x + int(66 * self.ui_scale), y + int(12 * self.ui_scale)))
        self._draw_hp_bar(x, y + int(44 * self.ui_scale), player_hp, (52, 245, 36))
        self.screen.blit(b, (x + int(66 * self.ui_scale), y + int(92 * self.ui_scale)))
        self._draw_hp_bar(x, y + int(124 * self.ui_scale), bot_hp, (255, 48, 88))
        self._draw_skill_icons(state)

    def _draw_skill_icons(self, state):
        cooldowns = state.get("cooldown", {})
        remaining = state.get("rasenshuriken_remaining", 3)
        skills = [
            ("kage_bunshin", "Kage", 0),
            ("rasengan", "Rasengan", 1),
            ("rasenshuriken", "Shuriken", 2),
        ]
        base_x = self.hud_rect.x + 20
        y = self.hud_rect.y + int(226 * self.ui_scale)
        step = int(115 * self.ui_scale)
        for key, label, idx in skills:
            x = base_x + idx * step
            icon = self.skill_icons.get(key)
            pygame.draw.circle(self.screen, (255, 166, 42), (x + 29, y + 29), 34, width=2)
            if icon is not None:
                self.screen.blit(icon, (x, y))
            cd = float(cooldowns.get(key, 0) or 0)
            if cd > 0:
                overlay = pygame.Surface((58, 58), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                self.screen.blit(overlay, (x, y))
                t = self.font.render(f"{cd:.1f}", True, (245, 245, 245))
                self.screen.blit(t, (x + 10, y + 17))
            name = self.small_font.render(label, True, (230, 230, 230))
            self.screen.blit(name, (x, y + 68))
            if key == "rasenshuriken":
                stock = self.small_font.render(f"{remaining}/3", True, (255, 166, 42))
                self.screen.blit(stock, (x + 12, y + 88))

    def _draw_status(self, snapshot):
        y = self.hud_rect.y + int(328 * self.ui_scale)
        x = self.hud_rect.x + 20
        latency_ema = float(snapshot.get("latency_ema_ms", snapshot.get("latency_ms", 0.0)))
        latency_avg = float(snapshot.get("latency_avg_ms", 0.0))
        latency_p95 = float(snapshot.get("latency_p95_ms", 0.0))
        ai_fps = float(snapshot.get("ai_fps_actual", 0.0))
        camera_fps = float(snapshot.get("camera_fps_actual", 0.0))
        render_fps = float(snapshot.get("render_fps_actual", 0.0))
        priority_state = str(snapshot.get("ai_priority_state", "off")).upper()
        preview_runtime_fps = int(snapshot.get("preview_fps", self.preview_fps))
        items = [
            f"Skill: {snapshot.get('skill') or '-'}",
            f"Block: {'ON' if snapshot.get('block') else 'OFF'}",
            f"Dodge: {snapshot.get('dodge') or '-'}",
            f"AI Latency: {snapshot.get('latency_ms', 0.0):.1f} ms",
            f"AI Latency EMA: {latency_ema:.1f} ms",
            f"AI Avg/P95: {latency_avg:.1f}/{latency_p95:.1f} ms",
            f"FPS R/C/AI: {render_fps:.0f}/{camera_fps:.0f}/{ai_fps:.0f}",
            f"AI Priority: {priority_state}",
            f"Preview: {'ON' if self.show_preview else 'OFF'} (P) - {preview_runtime_fps} FPS",
            f"Skeleton: {'ON' if self.show_skeleton else 'OFF'} (H)",
        ]
        for line in items:
            t = self.small_font.render(line, True, (188, 198, 216))
            self.screen.blit(t, (x, y))
            y += max(18, int(26 * self.ui_scale))
        self._status_bottom_y = y

    def _draw_logs(self):
        y = max(self.hud_rect.y + int(566 * self.ui_scale), self._status_bottom_y + max(8, int(10 * self.ui_scale)))
        x = self.hud_rect.x + 20
        title = self.font.render("BATTLE LOG", True, (255, 184, 45))
        self.screen.blit(title, (x, y))
        y += 30
        area_h = max(80, self.hud_rect.bottom - y - 14)
        area_w = max(120, self.hud_rect.width - 20)
        log_area = pygame.Rect(x, y, area_w, area_h)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(log_area)
        wrapped_lines = []
        max_line_w = log_area.width - 6
        for line in self.logs[-8:]:
            wrapped_lines.extend(self._wrap_text(line, max_line_w))
        line_h = max(16, self.small_font.get_height() + 2)
        max_lines = max(1, log_area.height // line_h)
        visible = wrapped_lines[-max_lines:]
        draw_y = y
        for line in visible:
            t = self.small_font.render(line, True, (210, 218, 232))
            self.screen.blit(t, (x, draw_y))
            draw_y += line_h
        self.screen.set_clip(old_clip)

    def _wrap_text(self, text, max_width):
        words = (text or "").split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self.small_font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_controls_panel(self):
        x, y, _, _ = self.controls_rect
        title = self.font.render("KEYBOARD CONTROLS", True, (255, 184, 45))
        self.screen.blit(title, (x + 14, y + 10))
        lines = [
            "1: Kage Bunshin",
            "2: Rasengan",
            "3: Rasenshuriken",
            "B: Block    A/D: Dodge",
            "R: Reset    H: Skeleton",
            "P: Preview  SPACE: Pause",
            "ESC: Quit",
        ]
        line_y = y + 44
        for line in lines:
            t = self.small_font.render(line, True, (205, 214, 228))
            self.screen.blit(t, (x + 16, line_y))
            line_y += 16

    def _draw_preview_off_panel(self):
        title = self.font.render("CAM PREVIEW", True, (255, 184, 45))
        self.screen.blit(title, (self.preview_rect.x + 12, self.preview_rect.y + 10))
        t = self.small_font.render("Preview OFF (press P to show)", True, (220, 120, 120))
        self.screen.blit(t, (self.preview_rect.x + 12, self.preview_rect.y + 70))

    def _draw_preview(self, frame, landmarks):
        title = self.font.render("CAM PREVIEW", True, (255, 184, 45))
        self.screen.blit(title, (self.preview_rect.x + 12, self.preview_rect.y + 10))
        content_rect = pygame.Rect(
            self.preview_rect.x + 8,
            self.preview_rect.y + 36,
            self.preview_rect.width - 16,
            self.preview_rect.height - 44,
        )
        if frame is None and self._preview_surface is None:
            t = self.small_font.render("No camera frame", True, (220, 120, 120))
            self.screen.blit(t, (content_rect.x + 8, content_rect.y + 8))
            return

        now = time.perf_counter()
        if frame is not None and (
            self._preview_surface is None or (now - self._preview_last_ts) >= self._preview_interval
        ):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb.shape
            surf = pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB")
            self._preview_surface = pygame.transform.smoothscale(surf, content_rect.size)
            self._preview_last_ts = now

        if self._preview_surface is not None:
            self.screen.blit(self._preview_surface, content_rect.topleft)

        if self.show_skeleton:
            self._draw_skeleton_overlay(landmarks, content_rect)

    def _draw_skeleton_overlay(self, landmarks, draw_rect):
        px, py, pw, ph = draw_rect
        pose = landmarks.get("pose") or []
        hands = landmarks.get("hands") or []

        for a, b in POSE_CONNECTIONS:
            if a < len(pose) and b < len(pose):
                x1, y1 = pose[a]
                x2, y2 = pose[b]
                pygame.draw.line(
                    self.screen,
                    (70, 255, 90),
                    (int(px + x1 * pw), int(py + y1 * ph)),
                    (int(px + x2 * pw), int(py + y2 * ph)),
                    2,
                )
        for pt in pose:
            pygame.draw.circle(
                self.screen,
                (70, 255, 90),
                (int(px + pt[0] * pw), int(py + pt[1] * ph)),
                3,
            )

        for hand in hands:
            for a, b in HAND_CONNECTIONS:
                if a < len(hand) and b < len(hand):
                    x1, y1 = hand[a]
                    x2, y2 = hand[b]
                    pygame.draw.line(
                        self.screen,
                        (255, 166, 42),
                        (int(px + x1 * pw), int(py + y1 * ph)),
                        (int(px + x2 * pw), int(py + y2 * ph)),
                        2,
                    )
            for pt in hand:
                pygame.draw.circle(
                    self.screen,
                    (255, 166, 42),
                    (int(px + pt[0] * pw), int(py + pt[1] * ph)),
                    3,
                )
