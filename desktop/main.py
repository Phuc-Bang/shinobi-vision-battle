import os
import sys
import time
import traceback
import json

import pygame

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

from backend.game_logic import GameState, update_game_state
from desktop.ai_worker import AIWorker
from desktop.camera import CameraStream
from desktop.input_state import InputState
from desktop.renderer import DesktopRenderer

SETTINGS_PATH = os.path.join(ROOT_DIR, "desktop", "settings.json")


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def performance_defaults(preset):
    presets = {
        "low": {
            "camera_width": 480,
            "camera_height": 360,
            "camera_fps": 24,
            "ai_fps": 12,
            "preview_fps": 8,
        },
        "balanced": {
            "camera_width": 640,
            "camera_height": 480,
            "camera_fps": 30,
            "ai_fps": 18,
            "preview_fps": 12,
        },
        "high": {
            "camera_width": 640,
            "camera_height": 480,
            "camera_fps": 30,
            "ai_fps": 24,
            "preview_fps": 15,
        },
    }
    return presets.get(preset, presets["balanced"])


def map_manual_key_to_action(event):
    if event.type != pygame.KEYDOWN:
        return None
    key = event.key
    if key == pygame.K_1:
        return {"skill": "kage_bunshin"}
    if key == pygame.K_2:
        return {"skill": "rasengan"}
    if key == pygame.K_3:
        return {"skill": "rasenshuriken"}
    if key == pygame.K_4:
        return {"skill": "charge_chakra"}
    if key == pygame.K_b:
        return {"block": True}
    if key == pygame.K_a:
        return {"dodge": "left"}
    if key == pygame.K_d:
        return {"dodge": "right"}
    return None


def run():
    settings = load_settings()
    perf_order = ["low", "balanced", "high"]
    performance_preset = str(
        settings.get(
            "performance_preset",
            os.getenv("DESKTOP_PERFORMANCE_PRESET", "balanced"),
        )
    ).strip().lower()
    if performance_preset not in perf_order:
        performance_preset = "balanced"
    perf_index = perf_order.index(performance_preset)
    defaults = performance_defaults(performance_preset)
    cam_width = int(os.getenv("DESKTOP_CAMERA_WIDTH", str(defaults["camera_width"])))
    cam_height = int(os.getenv("DESKTOP_CAMERA_HEIGHT", str(defaults["camera_height"])))
    cam_fps = int(os.getenv("DESKTOP_CAMERA_FPS", str(defaults["camera_fps"])))
    ai_fps = int(os.getenv("DESKTOP_AI_FPS", str(defaults["ai_fps"])))
    preview_fps = int(os.getenv("DESKTOP_PREVIEW_FPS", str(defaults["preview_fps"])))
    ai_priority_mode = os.getenv("DESKTOP_AI_PRIORITY_MODE", "1") == "1"
    preview_fps_min = int(os.getenv("DESKTOP_PREVIEW_FPS_MIN", "8"))
    preview_fps_max = int(os.getenv("DESKTOP_PREVIEW_FPS_MAX", str(preview_fps)))
    latency_high_ms = float(os.getenv("DESKTOP_AI_LATENCY_HIGH_MS", "70"))
    latency_low_ms = float(os.getenv("DESKTOP_AI_LATENCY_LOW_MS", "45"))
    default_mirror = "1" if bool(settings.get("camera_mirror", False)) else "0"
    default_cam_index = str(settings.get("camera_index", 0))
    cam_mirror = os.getenv("DESKTOP_CAMERA_MIRROR", default_mirror) == "1"
    cam_index = int(os.getenv("DESKTOP_CAMERA_INDEX", default_cam_index))

    camera = None
    input_state = InputState()
    ai_worker = None
    renderer = DesktopRenderer(ROOT_DIR, 1280, 720, preview_fps=preview_fps)
    game = GameState()

    def camera_label():
        return f"{cam_width}x{cam_height}@{cam_fps}"

    def persist_current_settings():
        save_settings(
            {
                "performance_preset": perf_order[perf_index],
                "camera_index": cam_index,
                "camera_mirror": cam_mirror,
            }
        )

    def apply_performance_preset():
        nonlocal cam_width, cam_height, cam_fps, ai_fps, preview_fps
        preset_name = perf_order[perf_index]
        d = performance_defaults(preset_name)
        cam_width = d["camera_width"]
        cam_height = d["camera_height"]
        cam_fps = d["camera_fps"]
        ai_fps = d["ai_fps"]
        preview_fps = d["preview_fps"]
        renderer.set_preview_fps(preview_fps)
        persist_current_settings()

    def start_runtime():
        nonlocal camera, ai_worker, input_state, ai_started, last_tick, current_preview_fps, latency_ema, priority_state
        camera = CameraStream(
            index=cam_index,
            width=cam_width,
            height=cam_height,
            fps=cam_fps,
            mirror=cam_mirror,
        )
        input_state = InputState()
        ai_worker = AIWorker(camera, input_state, ai_fps=ai_fps)
        camera.start()
        ai_worker.start()
        ai_started = True
        last_tick = time.perf_counter()
        current_preview_fps = preview_fps
        latency_ema = 0.0
        priority_state = "normal"

    def stop_runtime():
        nonlocal ai_started, camera, ai_worker
        if ai_started and ai_worker is not None:
            ai_worker.stop()
        if camera is not None:
            camera.stop()
        ai_worker = None
        camera = None
        ai_started = False

    running = True
    in_menu = True
    paused = False
    is_fullscreen = False
    last_event_id = None
    last_tick = time.perf_counter()
    prev_player_hp = game.player_hp
    prev_bot_hp = game.bot_hp
    latency_ema = 0.0
    current_preview_fps = preview_fps
    priority_state = "normal"
    ai_started = False
    game_over_triggered = False
    game_over_show_overlay_at = 0.0

    try:
        while running:
            manual_action = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        if not is_fullscreen:
                            display = pygame.display.Info()
                            renderer.resize(display.current_w, display.current_h)
                            renderer.screen = pygame.display.set_mode(
                                (renderer.width, renderer.height), pygame.FULLSCREEN
                            )
                            is_fullscreen = True
                        else:
                            renderer.resize(1280, 720)
                            is_fullscreen = False
                        continue
                    if in_menu:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            break
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            start_runtime()
                            in_menu = False
                            renderer.push_log("Desktop mode started.")
                            renderer.push_log(f"Performance preset: {perf_order[perf_index]}")
                            renderer.push_log(f"Camera: {camera_label()}")
                            renderer.push_log(f"Preview FPS: {preview_fps}")
                            renderer.push_log(f"AI priority mode: {'ON' if ai_priority_mode else 'OFF'}")
                            renderer.push_log("Keyboard test: 1/2/3 B A/D R H P ESC")
                        continue
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        break
                    if event.key == pygame.K_RETURN:
                        if game.game_over and game.winner == "player":
                            if game.campaign_stage < 3:
                                game.campaign_stage += 1
                                game.reset_game()
                                game_over_triggered = False
                                prev_player_hp = game.player_hp
                                prev_bot_hp = game.bot_hp
                                renderer.push_log(f"Advanced to Stage {game.campaign_stage}!")
                            else:
                                stop_runtime()
                                game.campaign_stage = 1
                                game.reset_game()
                                game_over_triggered = False
                                prev_player_hp = game.player_hp
                                prev_bot_hp = game.bot_hp
                                in_menu = True
                                renderer.push_log("Campaign completed! Returned to menu.")
                        continue
                    if event.key == pygame.K_r:
                        game.reset_game()
                        game_over_triggered = False
                        prev_player_hp = game.player_hp
                        prev_bot_hp = game.bot_hp
                        renderer.push_log("Game reset.")
                    if event.key == pygame.K_h:
                        renderer.show_skeleton = not renderer.show_skeleton
                    if event.key == pygame.K_p:
                        renderer.show_preview = not renderer.show_preview
                    if event.key == pygame.K_SPACE:
                        paused = not paused
                        renderer.push_log(f"Paused: {paused}")
                if event.type == pygame.VIDEORESIZE and not is_fullscreen:
                    renderer.resize(event.w, event.h)
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and in_menu and event.button == 1:
                    start_rect, quit_rect = renderer.menu_buttons()
                    controls = renderer.menu_controls()
                    if start_rect.collidepoint(event.pos):
                        start_runtime()
                        in_menu = False
                        renderer.push_log("Desktop mode started.")
                        renderer.push_log(f"Performance preset: {perf_order[perf_index]}")
                        renderer.push_log(f"Camera: {camera_label()}")
                        renderer.push_log(f"Preview FPS: {preview_fps}")
                        renderer.push_log(f"AI priority mode: {'ON' if ai_priority_mode else 'OFF'}")
                        renderer.push_log("Keyboard test: 1/2/3 B A/D R H P ESC")
                    elif quit_rect.collidepoint(event.pos):
                        running = False
                        break
                    elif controls["perf_prev"].collidepoint(event.pos):
                        perf_index = (perf_index - 1) % len(perf_order)
                        apply_performance_preset()
                    elif controls["perf_next"].collidepoint(event.pos):
                        perf_index = (perf_index + 1) % len(perf_order)
                        apply_performance_preset()
                    elif controls["cam_prev"].collidepoint(event.pos):
                        cam_index = max(0, cam_index - 1)
                        persist_current_settings()
                    elif controls["cam_next"].collidepoint(event.pos):
                        cam_index += 1
                        persist_current_settings()
                    elif controls["mirror_toggle"].collidepoint(event.pos):
                        cam_mirror = not cam_mirror
                        persist_current_settings()
                    elif controls["reset_settings"].collidepoint(event.pos):
                        perf_index = perf_order.index("balanced")
                        cam_index = 0
                        cam_mirror = False
                        apply_performance_preset()
                        persist_current_settings()
                if event.type == pygame.MOUSEBUTTONDOWN and (not in_menu) and paused and event.button == 1:
                    btn = renderer.pause_buttons()
                    if btn["resume"].collidepoint(event.pos):
                        paused = False
                        renderer.push_log("Paused: False")
                    elif btn["restart"].collidepoint(event.pos):
                        game.reset_game()
                        game_over_triggered = False
                        prev_player_hp = game.player_hp
                        prev_bot_hp = game.bot_hp
                        paused = False
                        renderer.push_log("Game reset.")
                    elif btn["menu"].collidepoint(event.pos):
                        stop_runtime()
                        game.campaign_stage = 1
                        game.reset_game()
                        game_over_triggered = False
                        prev_player_hp = game.player_hp
                        prev_bot_hp = game.bot_hp
                        paused = False
                        in_menu = True
                        renderer.push_log("Back to menu.")
                mapped = map_manual_key_to_action(event)
                if mapped:
                    manual_action = mapped

            if not running:
                break

            if in_menu:
                renderer.draw_menu(perf_order[perf_index], camera_label(), cam_index, cam_mirror)
                continue

            if paused:
                snap = input_state.snapshot()
                frame, _ = camera.read_latest() if camera is not None else (None, 0.0)
                render_snapshot = dict(snap)
                render_snapshot["latency_ema_ms"] = latency_ema
                render_snapshot["ai_priority_state"] = priority_state if ai_priority_mode else "off"
                render_snapshot["preview_fps"] = current_preview_fps
                render_snapshot["camera_fps_actual"] = camera.actual_fps() if camera is not None else 0.0
                render_snapshot["render_fps_actual"] = renderer.render_fps()
                renderer.draw(
                    {
                        "player_hp": game.player_hp,
                        "bot_hp": game.bot_hp,
                    },
                    render_snapshot,
                    frame,
                    0.0,
                )
                renderer.draw_pause_overlay()
                continue

            snapshot = input_state.snapshot()
            latency_ms = float(snapshot.get("latency_ms", 0.0))
            if latency_ema <= 0.0:
                latency_ema = latency_ms
            else:
                latency_ema = (latency_ema * 0.85) + (latency_ms * 0.15)

            if ai_priority_mode:
                target_preview_fps = current_preview_fps
                if latency_ema >= latency_high_ms:
                    target_preview_fps = max(preview_fps_min, current_preview_fps - 1)
                    priority_state = "degraded"
                elif latency_ema <= latency_low_ms:
                    target_preview_fps = min(preview_fps_max, current_preview_fps + 1)
                    priority_state = "normal"
                if target_preview_fps != current_preview_fps:
                    current_preview_fps = target_preview_fps
                    renderer.set_preview_fps(current_preview_fps)

            skill = snapshot.get("skill")
            skill = input_state.consume_skill_once(skill)
            block = snapshot.get("block", False)
            dodge = snapshot.get("dodge")

            # Đọc phím giữ sạc Chakra (Phím 4) hoặc áp dụng đè phím thủ công khác
            keys = pygame.key.get_pressed()
            if keys[pygame.K_4]:
                skill = "charge_chakra"
            elif manual_action:
                if "skill" in manual_action:
                    skill = manual_action["skill"]
                if "block" in manual_action:
                    block = manual_action["block"]
                if "dodge" in manual_action:
                    dodge = manual_action["dodge"]

            if game.game_over:
                if not game_over_triggered:
                    game_over_triggered = True
                    game_over_show_overlay_at = time.perf_counter() + 1.2
                    if game.winner == "player":
                        renderer.push_log("WIN")
                        renderer.trigger_state("bot", "dead", 1.2)
                        renderer.trigger_shake(24.0, 0.6)
                    else:
                        renderer.push_log("LOSE")
                        renderer.trigger_state("player", "dead", 1.2)
                        renderer.trigger_shake(24.0, 0.6)

                frame, _ = camera.read_latest() if camera is not None else (None, 0.0)
                now = time.perf_counter()
                dt_sec = now - last_tick
                last_tick = now
                
                ko_cinematic_active = now < game_over_show_overlay_at
                if ko_cinematic_active:
                    dt_sec = dt_sec / 5.0
                
                renderer._update_states()
                renderer._update_projectiles(dt_sec)
                renderer._update_effects(dt_sec)
                
                render_snapshot = dict(snapshot)
                render_snapshot["latency_ema_ms"] = latency_ema
                render_snapshot["ai_priority_state"] = priority_state if ai_priority_mode else "off"
                render_snapshot["preview_fps"] = current_preview_fps
                render_snapshot["camera_fps_actual"] = camera.actual_fps() if camera is not None else 0.0
                render_snapshot["render_fps_actual"] = renderer.render_fps()
                
                current_state = {
                    "player_hp": game.player_hp,
                    "bot_hp": game.bot_hp,
                    "cooldown": {
                        "rasengan": 0.0,
                        "rasenshuriken": 0.0,
                        "kage_bunshin": 0.0
                    },
                    "rasenshuriken_remaining": 3 - game.rasenshuriken_used_count,
                    "game_over": game.game_over,
                    "winner": game.winner,
                    "ko_cinematic": ko_cinematic_active,
                    "campaign_stage": game.campaign_stage,
                }
                renderer.draw(current_state, render_snapshot, frame, dt_sec)
                
                if now >= game_over_show_overlay_at:
                    renderer.draw_game_over_overlay(game.winner, stage=game.campaign_stage, player_hp=game.player_hp)
                
                continue

            state = update_game_state(game, skill, block, dodge)
            event_id = state.get("event_id")
            msg = state.get("last_message")
            if msg and event_id != last_event_id:
                renderer.push_log(msg)
                player_action = state.get("player_action")
                bot_action = state.get("bot_action")
                if player_action == "rasenshuriken":
                    renderer.trigger_state("player", "rasenshuriken", 0.48)
                    renderer.trigger_projectile(player_action)
                    renderer.trigger_shake(16.0, 0.4)
                elif player_action == "rasengan":
                    renderer.trigger_state("player", "attack", 0.36)
                    renderer.trigger_projectile(player_action)
                    renderer.trigger_shake(10.0, 0.28)
                elif player_action == "kage_bunshin":
                    renderer.trigger_state("player", "kage_bunshin", 0.55)
                    renderer.trigger_shake(5.0, 0.15)
                elif player_action == "charge_chakra":
                    renderer.trigger_state("player", "charge", 0.15)
                elif player_action == "kawarimi":
                    renderer.trigger_state("player", "kawarimi", 0.6)
                    renderer.trigger_shake(12.0, 0.3)
                
                if bot_action in ("kunai", "double_kunai"):
                    renderer.trigger_state("bot", "attack", 0.34)
                    renderer.trigger_projectile(bot_action)
                last_event_id = event_id

            if block and state.get("player_action") != "kawarimi":
                renderer.trigger_state("player", "block", 0.18)
            elif dodge == "left":
                renderer.trigger_state("player", "dodge_left", 0.22)
            elif dodge == "right":
                renderer.trigger_state("player", "dodge_right", 0.22)

            player_dmg = max(0, prev_player_hp - state.get("player_hp", prev_player_hp))
            bot_dmg = max(0, prev_bot_hp - state.get("bot_hp", prev_bot_hp))
            if player_dmg > 0:
                renderer.trigger_state("player", "hurt", 0.32)
                renderer.trigger_damage("player", player_dmg)
                renderer.trigger_shake(8.0, 0.2)
            if bot_dmg > 0:
                renderer.trigger_state("bot", "hurt", 0.32)
                renderer.trigger_damage("bot", bot_dmg)
                renderer.trigger_shake(10.0, 0.22)
            prev_player_hp = state.get("player_hp", prev_player_hp)
            prev_bot_hp = state.get("bot_hp", prev_bot_hp)



            frame, _ = camera.read_latest() if camera is not None else (None, 0.0)
            now = time.perf_counter()
            dt_sec = now - last_tick
            last_tick = now
            render_snapshot = dict(snapshot)
            render_snapshot["latency_ema_ms"] = latency_ema
            render_snapshot["ai_priority_state"] = priority_state if ai_priority_mode else "off"
            render_snapshot["preview_fps"] = current_preview_fps
            render_snapshot["camera_fps_actual"] = camera.actual_fps() if camera is not None else 0.0
            render_snapshot["render_fps_actual"] = renderer.render_fps()
            renderer.draw(state, render_snapshot, frame, dt_sec)
    except Exception as exc:
        traceback.print_exc()
        renderer.push_log(f"ERROR: {exc}")
        error_state = {"player_hp": game.player_hp, "bot_hp": game.bot_hp}
        error_snapshot = input_state.snapshot()
        error_snapshot["ai_priority_state"] = "error"
        error_snapshot["preview_fps"] = current_preview_fps
        error_snapshot["camera_fps_actual"] = 0.0
        error_snapshot["render_fps_actual"] = renderer.render_fps()
        waiting_error = True
        while waiting_error:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    waiting_error = False
                    break
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    waiting_error = False
                    break
            renderer.draw(error_state, error_snapshot, None, 0.0)
    finally:
        stop_runtime()
        pygame.quit()


if __name__ == "__main__":
    run()
