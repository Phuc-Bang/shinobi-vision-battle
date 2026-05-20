"""
Module: game_logic.py
Tác giả: Antigravity (Game Logic Programmer)
Mô tả: Quản lý trạng thái trận đấu, sát thương, hồi chiêu và cốt truyện.
"""

import time
import random

class GameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        """Khởi tạo lại toàn bộ thông số trận đấu."""
        self.player_hp = 100
        self.bot_hp = 100
        self.player_buff_end_time = None
        self.player_damage_multiplier = 1.0

        # Thời điểm dùng skill lần cuối (0 nghĩa là chưa dùng)
        self.last_skill_time = {
            "rasengan": 0.0,
            "rasenshuriken": 0.0,
            "kage_bunshin": 0.0
        }
        self.rasenshuriken_used_count = 0
        self.event_seq = 0

        # Cấu hình AI của Boss (Mizuki)
        self.next_bot_attack_time = time.time() + 4.0 # Tấn công sau 4 giây
        self.bot_last_action = ""

        self.game_over = False
        self.winner = None

        # Reset cốt truyện mỗi ván để triggered flags được xóa
        self.story_messages = [
            {"threshold": 100, "msg": "Mizuki: Ngươi nghĩ vài trò vặt đó có thể đánh bại ta sao, Naruto?", "triggered": False},
            {"threshold": 50, "msg": "Mizuki: Tên nhóc này... sức mạnh của hắn từ đâu ra vậy?!", "triggered": False},
            {"threshold": 30, "msg": "Naruto: Ta sẽ không bỏ cuộc! Đó là nhẫn đạo của ta!", "triggered": False},
            {"threshold": 10, "msg": "Mizuki: Không thể nào! Cuộn giấy phong ấn... sức mạnh của Cửu Vĩ...", "triggered": False},
            {"threshold": 0, "msg": "Naruto: Kết thúc rồi, Mizuki!", "triggered": False}
        ]

    def apply_player_skill(self, skill_name, is_blocking, dodge_dir):
        """Xử lý sát thương và hiệu ứng khi người chơi tung chiêu."""
        result = {"damage_dealt": 0, "message": ""}
        
        if self.game_over or not skill_name:
            return result

        now = time.time()
        
        # 1. Kiểm tra Cooldown & Giới hạn
        if skill_name == "rasengan":
            if now - self.last_skill_time["rasengan"] < 2.0:
                return result # Chưa hồi xong
            base_damage = 15
            self.last_skill_time["rasengan"] = now
            
        elif skill_name == "rasenshuriken":
            if self.rasenshuriken_used_count >= 3:
                result["message"] = "⚠️ Đã hết Chakra cho Rasenshuriken!"
                return result
            if now - self.last_skill_time["rasenshuriken"] < 10.0:
                return result # Chưa hồi xong
            base_damage = 30
            self.last_skill_time["rasenshuriken"] = now
            self.rasenshuriken_used_count += 1
            
        elif skill_name == "kage_bunshin":
            if now - self.last_skill_time["kage_bunshin"] < 5.0:
                return result
            # Kage Bunshin không gây sát thương, chỉ buff sát thương x1.5 trong 5s
            self.player_buff_end_time = now + 5.0
            self.player_damage_multiplier = 1.5
            self.last_skill_time["kage_bunshin"] = now
            result["message"] = "🔥 Đa Trọng Ảnh Phân Thân! Sát thương x1.5"
            return result
        else:
            return result

        # 2. Xử lý Boss né đòn (30% tỷ lệ né nếu Boss không tấn công/nhận sát thương khác)
        if random.random() < 0.3:
            result["message"] = f"💨 Mizuki dùng Thuật Thay Thế né được {skill_name.upper()}!"
            return result

        # 3. Tính toán sát thương tổng
        total_damage = int(base_damage * self.player_damage_multiplier)
        self.bot_hp = max(0, self.bot_hp - total_damage)
        
        result["damage_dealt"] = total_damage
        result["message"] = f"💥 Trúng đòn! {skill_name.upper()} gây {total_damage} sát thương!"
        
        return result

    def apply_bot_attack(self, is_blocking, dodge_dir):
        """Xử lý Boss Mizuki ném phi tiêu tấn công tự động."""
        result = {"damage_dealt": 0, "message": ""}
        now = time.time()
        
        if self.game_over or now < self.next_bot_attack_time:
            return result

        # Tính toán lần tấn công tiếp theo (Random từ 4s đến 5.5s)
        self.next_bot_attack_time = now + random.uniform(4.0, 5.5)
        
        # Boss ném Kunai (Sát thương 10)
        bot_damage = 10
        
        # Kiểm tra người chơi có đang phòng thủ hoặc né không
        if is_blocking:
            # Block giảm 70% sát thương, vẫn nhận 30%
            reduced = max(1, int(bot_damage * 0.3))
            self.player_hp = max(0, self.player_hp - reduced)
            result["damage_dealt"] = reduced
            result["message"] = f"🛡️ Đỡ được Kunai! Nhận {reduced} sát thương (giảm 70%)."
        elif dodge_dir:
            result["message"] = f"🏃 Né thành công Kunai của Mizuki!"
        else:
            # Dính đòn toàn bộ
            self.player_hp = max(0, self.player_hp - bot_damage)
            result["damage_dealt"] = bot_damage
            result["message"] = f"🔪 Dính Kunai! Bạn mất {bot_damage} máu!"
            self.bot_last_action = "throw_kunai"

        return result

    def update_buff(self):
        """Cập nhật trạng thái các buff theo thời gian thực."""
        now = time.time()
        if self.player_buff_end_time and now >= self.player_buff_end_time:
            self.player_buff_end_time = None
            self.player_damage_multiplier = 1.0 # Hết buff Kage Bunshin

    def check_game_over(self):
        """Kiểm tra điều kiện kết thúc trận đấu."""
        if self.player_hp <= 0:
            self.game_over = True
            self.winner = "bot"
        elif self.bot_hp <= 0:
            self.game_over = True
            self.winner = "player"

    def get_story_message(self):
        """Lấy lời thoại cốt truyện dựa trên % máu của Boss."""
        for story in self.story_messages:
            if not story["triggered"] and self.bot_hp <= story["threshold"]:
                story["triggered"] = True
                return story["msg"]
        return ""

def update_game_state(game, player_skill, is_blocking, dodge_dir):
    """
    Hàm cầu nối: Nhận input từ app.py, đẩy vào GameState và trả về JSON tổng hợp.
    """
    now = time.time()
    
    # 1. Cập nhật Buff
    game.update_buff()
    
    # 2. Xử lý người chơi tung chiêu
    skill_res = game.apply_player_skill(player_skill, is_blocking, dodge_dir)
    
    # 3. Xử lý Boss tấn công
    bot_res = game.apply_bot_attack(is_blocking, dodge_dir)
    
    # 4. Kiểm tra sinh tử
    game.check_game_over()
    
    # 5. Cập nhật cốt truyện
    story_msg = game.get_story_message()
    
    # Gộp cả hai thông điệp nếu cùng xảy ra trong một frame
    msgs = [m for m in [skill_res.get("message"), bot_res.get("message")] if m]
    last_message = " | ".join(msgs)
    event_id = None
    if last_message:
        game.event_seq += 1
        event_id = game.event_seq

    # Trả về bộ trạng thái hoàn chỉnh cho Frontend
    return {
        "player_hp": game.player_hp,
        "bot_hp": game.bot_hp,
        "player_buff_remain": max(0, round(game.player_buff_end_time - now, 1)) if game.player_buff_end_time else 0,
        "cooldown": {
            "rasengan": max(0, round(game.last_skill_time["rasengan"] + 2.0 - now, 1)),
            "rasenshuriken": max(0, round(game.last_skill_time["rasenshuriken"] + 10.0 - now, 1)),
            "kage_bunshin": max(0, round(game.last_skill_time["kage_bunshin"] + 5.0 - now, 1))
        },
        "rasenshuriken_remaining": 3 - game.rasenshuriken_used_count,
        "game_over": game.game_over,
        "winner": game.winner,
        "event_id": event_id,
        "last_message": last_message,
        "story_message": story_msg
    }
