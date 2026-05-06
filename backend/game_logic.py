import time

class GameLogic:
    def __init__(self):
        self.player_hp = 100
        self.enemy_hp = 100
        self.last_skill_time = {}
        self.skills = {
            "Kage Bunshin": {"damage": 10, "cooldown": 2},
            "Rasengan": {"damage": 25, "cooldown": 5},
            "Shuriken": {"damage": 5, "cooldown": 1},
            "Chidori": {"damage": 30, "cooldown": 7}
        }

    def process_action(self, skill_name):
        """Xử lý sát thương và hồi chiêu của kỹ năng."""
        current_time = time.time()
        
        # Kiểm tra hồi chiêu
        if skill_name in self.last_skill_time:
            elapsed = current_time - self.last_skill_time[skill_name]
            if elapsed < self.skills[skill_name]["cooldown"]:
                return {"status": "cooldown", "remaining": round(self.skills[skill_name]["cooldown"] - elapsed, 1)}

        # Tính sát thương
        damage = self.skills[skill_name]["damage"]
        self.enemy_hp -= damage
        if self.enemy_hp < 0: self.enemy_hp = 0
        
        self.last_skill_time[skill_name] = current_time
        
        return {
            "status": "success",
            "damage": damage,
            "player_hp": self.player_hp,
            "enemy_hp": self.enemy_hp,
            "msg": f"Bạn đã tung {skill_name} gây {damage} sát thương!"
        }

    def enemy_attack(self):
        """Mizuki tấn công lại (có thể gọi định kỳ)."""
        damage = 5
        self.player_hp -= damage
        if self.player_hp < 0: self.player_hp = 0
        return {"damage": damage, "player_hp": self.player_hp}
