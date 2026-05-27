"""
Module: sound.py
Tác giả: Antigravity (Sound Engineer)
Mô tả: Bộ tạo âm thanh cổ điển bằng thuật toán (procedural retro synthesis) cho Pygame.
"""

import numpy as np
import pygame

class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            # Khởi tạo mixer với tần số 22050Hz, 16-bit signed, 1 kênh mono
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.enabled = True
            self.sounds = {}
            self._generate_procedural_sounds()
        except Exception:
            # Bỏ qua nếu môi trường không có card âm thanh (headless, v.v.)
            pass

    def _generate_procedural_sounds(self):
        sr = 22050
        
        def make_sound(data):
            # Cân chỉnh biên độ âm thanh về dạng 16-bit int
            data_scaled = (data * 32767).astype(np.int16)
            return pygame.mixer.Sound(buffer=data_scaled)
            
        # 1. Click (Tiếng click menu ngắn gọn)
        t = np.linspace(0, 0.05, int(sr * 0.05), endpoint=False)
        click_data = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 80)
        self.sounds["click"] = make_sound(click_data)
        
        # 2. Select (Tiếng rít tần số tăng dần khi chọn tướng/màn chơi)
        t = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
        freqs = np.linspace(440, 880, len(t))
        select_data = np.sin(2 * np.pi * freqs * t) * np.exp(-t * 20)
        self.sounds["select"] = make_sound(select_data)
        
        # 3. Kawarimi (Tiếng gõ gỗ của thế thân gỗ)
        t = np.linspace(0, 0.08, int(sr * 0.08), endpoint=False)
        kawarimi_data = np.sin(2 * np.pi * 320 * t) * np.exp(-t * 50)
        kawarimi_data += np.sin(2 * np.pi * 480 * t) * np.exp(-t * 70) * 0.5
        self.sounds["kawarimi"] = make_sound(kawarimi_data)
        
        # 4. Hit (Tiếng va đập mạnh)
        t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
        hit_data = np.sin(2 * np.pi * np.linspace(250, 80, len(t)) * t) * np.exp(-t * 30)
        self.sounds["hit"] = make_sound(hit_data)
        
        # 5. Hurt (Tiếng dính đòn trầm)
        t = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
        hurt_data = np.sin(2 * np.pi * np.linspace(150, 50, len(t)) * t) * np.exp(-t * 20)
        self.sounds["hurt"] = make_sound(hurt_data)
        
        # 6. Rasengan (Tiếng quay xoáy của luồng Chakra)
        t = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
        mod = 1.0 + 0.3 * np.sin(2 * np.pi * 45 * t)
        freq = np.linspace(200, 550, len(t))
        rasengan_data = np.sin(2 * np.pi * freq * t) * mod * np.exp(-t * 5)
        self.sounds["rasengan"] = make_sound(rasengan_data)
        
        # 7. Chidori (Tiếng sấm sét giật điện)
        t = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
        noise = np.random.uniform(-1, 1, len(t))
        crackle = np.sin(2 * np.pi * 1500 * t) * (noise > 0.8)
        chidori_data = (np.sin(2 * np.pi * 1200 * t) * 0.5 + crackle * 0.5) * np.exp(-t * 4)
        self.sounds["chidori"] = make_sound(chidori_data)
        
        # 8. Rasenshuriken (Tiếng chém gió siêu tốc rít lên)
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        freq = np.linspace(300, 800, len(t))
        mod = np.sin(2 * np.pi * np.linspace(10, 80, len(t)) * t)
        shuriken_data = np.sin(2 * np.pi * freq * t) * (1.0 + 0.5 * mod) * np.exp(-t * 2)
        self.sounds["rasenshuriken"] = make_sound(shuriken_data)
        
        # 9. Katon (Tiếng nổ trầm của cầu lửa)
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        noise = np.random.uniform(-1, 1, len(t))
        rumble = np.sin(2 * np.pi * np.linspace(120, 40, len(t)) * t)
        katon_data = (rumble * 0.6 + noise * 0.4) * np.exp(-t * 5)
        self.sounds["katon"] = make_sound(katon_data)
        
        # 10. Kage Bunshin (Tiếng khói xì hơi 'poof')
        t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
        noise = np.random.uniform(-1, 1, len(t))
        poof = noise * np.exp(-t * 25)
        poof_delay = np.zeros(len(t))
        d_idx = int(sr * 0.08)
        poof_delay[d_idx:] = noise[:-d_idx] * np.exp(-t[:-d_idx] * 25)
        bunshin_data = poof * 0.5 + poof_delay * 0.5
        self.sounds["kage_bunshin"] = make_sound(bunshin_data)
        
        # 11. Sharingan (Tiếng kêu đặc biệt huyền bí)
        t = np.linspace(0, 0.45, int(sr * 0.45), endpoint=False)
        sharingan_data = (np.sin(2 * np.pi * 523.25 * t) * 0.5 + np.sin(2 * np.pi * 528.25 * t) * 0.5) * np.exp(-t * 8)
        self.sounds["sharingan"] = make_sound(sharingan_data)
        
        # 12. Charge (Tiếng tụ điện/Chakra)
        t = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
        charge_data = np.sin(2 * np.pi * np.linspace(180, 260, len(t)) * t) * np.exp(-t * 5)
        self.sounds["charge"] = make_sound(charge_data)
        
        # 13. Win (Nhạc hợp âm trưởng chiến thắng ngắn)
        t_note = 0.12
        notes_f = [261.63, 329.63, 392.00, 523.25]
        total_len = int(sr * (t_note * 4 + 0.3))
        win_data = np.zeros(total_len)
        for idx, f in enumerate(notes_f):
            start = int(sr * idx * t_note)
            dur = total_len - start
            t = np.linspace(0, dur / sr, dur, endpoint=False)
            win_data[start:] += np.sin(2 * np.pi * f * t) * np.exp(-t * 12) * 0.35
        self.sounds["win"] = make_sound(win_data)
        
        # 14. Lose (Nhạc hợp âm buồn khi thua)
        t_note = 0.15
        notes_f = [261.63, 220.00, 174.61, 164.81]
        total_len = int(sr * (t_note * 4 + 0.4))
        lose_data = np.zeros(total_len)
        for idx, f in enumerate(notes_f):
            start = int(sr * idx * t_note)
            dur = total_len - start
            t = np.linspace(0, dur / sr, dur, endpoint=False)
            lose_data[start:] += np.sin(2 * np.pi * f * t) * np.exp(-t * 6) * 0.35
        self.sounds["lose"] = make_sound(lose_data)

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass
