"""
หุ้ม pydirectinput: ส่งปุ่มจริงเข้าหน้าต่างเกม (Roblox — Untitled Boxing Game)

ใช้ scancode ผ่าน SendInput ซึ่งเกม/DirectX รับได้ดีกว่า pynput/keyboard
รองรับ DRY_RUN: ถ้าเปิดไว้จะแค่ print ไม่ส่งปุ่มจริง (ไว้ทดสอบ/จูน)

ท่า/ปุ่ม:
  light()  -> แตะ LIGHT_KEY (แย็บ)       | tap
  heavy()  -> แตะ HEAVY_KEY (ฮุค)        | tap
  dodge()  -> แตะ DODGE_KEY (หลบ/dash)   | tap
  ultimate() -> แตะ ULT_KEY (ไม้ตาย)     | tap
  block_start()/block_end() -> BLOCK_KEY | กดค้าง (hold) ตราบที่ยังตั้งการ์ด
"""

import time

import pydirectinput

# ปิด delay ในตัวของ pydirectinput เพื่อลด latency (สำคัญกับเกมเร็ว)
pydirectinput.PAUSE = 0.0
pydirectinput.FAILSAFE = False

# กด "แตะ" ต้องกดค้างสั้นๆ ก่อนปล่อย ไม่งั้นเกม (อ่าน input ~60Hz) จะพลาด
# ถ้ากดปล่อยเร็วเกิน ~16ms เกมอาจมองไม่เห็นการกดเลย (ห้ามใช้ press() ตรงๆ ด้วยเหตุนี้)
TAP_HOLD_SEC = 0.05


class InputSender:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dry_run = cfg.DRY_RUN
        self._block_held = False
        # ตัวนับ ให้ UI โชว์ว่าส่งปุ่มแต่ละท่าไปกี่ครั้ง (นับทั้งโหมดทดสอบและจริง)
        self.light_count = 0
        self.heavy_count = 0
        self.dodge_count = 0
        self.ult_count = 0
        self.block_count = 0
        self.ability_count = 0

    # ---------- สลับโหมดทดสอบ/จริง ----------
    def toggle_dry_run(self):
        # ถ้ากำลังกดการ์ดค้างอยู่ ให้ปล่อยก่อนสลับโหมด กันปุ่มค้าง
        if self._block_held:
            self.block_end()
        self.dry_run = not self.dry_run
        return self.dry_run

    # ---------- helper แตะปุ่ม (กดค้างสั้นๆ แล้วปล่อย) ----------
    def _tap(self, key):
        pydirectinput.keyDown(key)
        time.sleep(TAP_HOLD_SEC)
        pydirectinput.keyUp(key)

    def _tap_combo(self, k1, k2):
        """กด 2 ปุ่มพร้อมกันสั้นๆ (เช่น Space+A เพื่อ dash มีทิศ)"""
        pydirectinput.keyDown(k1)
        pydirectinput.keyDown(k2)
        time.sleep(TAP_HOLD_SEC)
        pydirectinput.keyUp(k2)
        pydirectinput.keyUp(k1)

    # ---------- หมัด/หลบ/ไม้ตาย (แตะครั้งเดียว) ----------
    def light(self):
        self.light_count += 1
        if self.dry_run:
            print("[DRY] LIGHT (jab)  -> tap", self.cfg.LIGHT_KEY)
            return
        self._tap(self.cfg.LIGHT_KEY)

    def heavy(self):
        self.heavy_count += 1
        if self.dry_run:
            print("[DRY] HEAVY (hook) -> tap", self.cfg.HEAVY_KEY)
            return
        self._tap(self.cfg.HEAVY_KEY)

    def dodge(self):
        self.dodge_count += 1
        if self.dry_run:
            print("[DRY] DODGE        -> tap", self.cfg.DODGE_KEY)
            return
        self._tap(self.cfg.DODGE_KEY)

    def dodge_left(self):
        self.dodge_count += 1
        if self.dry_run:
            print("[DRY] DODGE LEFT   -> tap", self.cfg.DODGE_KEY, "+", self.cfg.DASH_LEFT_KEY)
            return
        self._tap_combo(self.cfg.DODGE_KEY, self.cfg.DASH_LEFT_KEY)

    def dodge_right(self):
        self.dodge_count += 1
        if self.dry_run:
            print("[DRY] DODGE RIGHT  -> tap", self.cfg.DODGE_KEY, "+", self.cfg.DASH_RIGHT_KEY)
            return
        self._tap_combo(self.cfg.DODGE_KEY, self.cfg.DASH_RIGHT_KEY)

    def ultimate(self):
        self.ult_count += 1
        if self.dry_run:
            print("[DRY] ULTIMATE     -> tap", self.cfg.ULT_KEY)
            return
        self._tap(self.cfg.ULT_KEY)

    def ability(self):
        self.ability_count += 1
        if self.dry_run:
            print("[DRY] ABILITY (T)  -> tap", self.cfg.ABILITY_KEY)
            return
        self._tap(self.cfg.ABILITY_KEY)

    # ---------- การ์ด (กดค้าง) ----------
    def block_start(self):
        if self._block_held:
            return
        self._block_held = True
        self.block_count += 1
        if self.dry_run:
            print("[DRY] BLOCK start  -> hold", self.cfg.BLOCK_KEY)
            return
        pydirectinput.keyDown(self.cfg.BLOCK_KEY)

    def block_end(self):
        if not self._block_held:
            return
        self._block_held = False
        if self.dry_run:
            print("[DRY] BLOCK end    -> release", self.cfg.BLOCK_KEY)
            return
        pydirectinput.keyUp(self.cfg.BLOCK_KEY)

    def cleanup(self):
        """ปล่อยปุ่มค้างทั้งหมดตอนปิดโปรแกรม กันปุ่มค้างในเกม"""
        if self._block_held and not self.dry_run:
            pydirectinput.keyUp(self.cfg.BLOCK_KEY)
        self._block_held = False
