"""
สมองของโปรแกรม: แปลงเมตริกท่าทาง -> เหตุการณ์ (ท่าชกมวย)

เมตริก (หาร torso_len ทุกตัว ให้คงที่ไม่ขึ้นกับระยะกล้อง):
  offset = (baseline_y - torso_y) / baseline_len   (+ = สูงกว่ายืน, - = ต่ำกว่ายืน=หลบ)
  lift   = (nose_y - wrist_y) / torso_len           (+ = ข้อมือสูงกว่าจมูก)
  ext    = ระยะข้อมือ-ไหล่ / torso_len              (การเหยียดแขน)

ลำดับความสำคัญ (กันท่าชนกัน): ULTIMATE > BLOCK > DODGE > PUNCH

*** การจูนแบบใหม่ (record-by-example) ***
  ไม่ต้องเดาตัวเลขเอง — เรียก start_record("punch"/"dodge"/"ultimate"/"guard")
  แล้วผู้เล่นทำท่านั้นซ้ำๆ ~3 วิ ระบบจับ "ช่วงค่าจริง" ของร่างกายผู้เล่น
  แล้วตั้ง threshold ให้อัตโนมัติ (เก็บลงไฟล์ผ่าน main -> settings_store)

หมัด: ตัดเงื่อนไข "ความเร็ว" ออกแล้ว — แค่แขนเหยียดเกิน punch_extend_min = นับเป็นหมัด
      (มี re-arm ตอนหดแขน + cooldown กันยิงรัว)
"""

import time

STATE_STAND = "STAND"
STATE_PUNCH = "PUNCH"
STATE_BLOCK = "BLOCK"
STATE_DODGE = "DODGE"
STATE_ULT = "ULTIMATE"
STATE_TPOSE = "T-POSE"

# ชื่อ threshold ที่ปรับได้/บันทึกได้ (ใช้ทั้ง record และ persistence)
TUNABLE_KEYS = [
    "punch_extend_min", "punch_reset_extend",
    "dodge_threshold",
    "ult_wrist_above_nose", "ult_extend_min",
    "tpose_extend_min", "tpose_gap_min",
    "guard_above", "guard_below", "guard_gap_max",
]


def _pct(arr, p):
    """คืนค่าเปอร์เซ็นไทล์ที่ p (0..1) ของ list (กัน outlier ดีกว่า min/max ตรงๆ)"""
    if not arr:
        return 0.0
    s = sorted(arr)
    k = int(round(p * (len(s) - 1)))
    return s[k]


class MotionLogic:
    def __init__(self, cfg):
        self.cfg = cfg
        # ---- threshold ที่ปรับ/บันทึกได้ (เริ่มจากค่า default ใน config) ----
        self.punch_extend_min = cfg.PUNCH_EXTEND_MIN
        self.punch_reset_extend = cfg.PUNCH_RESET_EXTEND
        self.dodge_threshold = cfg.DODGE_THRESHOLD
        self.ult_wrist_above_nose = cfg.ULT_WRIST_ABOVE_NOSE
        self.ult_extend_min = cfg.ULT_EXTEND_MIN
        self.tpose_extend_min = cfg.TPOSE_EXTEND_MIN
        self.tpose_gap_min = cfg.TPOSE_GAP_MIN
        self.guard_above = cfg.GUARD_WRIST_ABOVE_NOSE
        self.guard_below = cfg.GUARD_WRIST_BELOW_NOSE
        self.guard_gap_max = cfg.GUARD_WRIST_GAP_MAX

        self.baseline_y = None
        self.baseline_len = None

        self.state = STATE_STAND
        self.blocking = False
        self._block_off = 0

        self._dodge_armed = True
        self._last_dodge_time = 0.0
        self._ult_armed = True
        self._last_ult_time = 0.0
        self._tpose_armed = True
        self._last_tpose_time = 0.0
        self._armed_l = True
        self._armed_r = True
        self._last_punch_l = 0.0
        self._last_punch_r = 0.0

        # calibrate baseline (ท่ายืน)
        self._calibrating = False
        self._calib_end = 0.0
        self._calib_y = []
        self._calib_len = []

        # ---- record-by-example ----
        self.rec_gesture = None        # None / "punch" / "dodge" / "ultimate" / "guard"
        self.rec_phase = ""            # "ready" (เตรียมตัว) / "rec" (กำลังบันทึก)
        self._rec_end = 0.0
        self._rec_samples = []
        self.rec_result = ""           # ข้อความผลลัพธ์ (โชว์ในหน้าต่าง)
        self.rec_result_time = 0.0
        self.on_tuned = None           # callback ให้ main เซฟไฟล์หลัง record เสร็จ

        # ค่าล่าสุดไว้โชว์มิเตอร์
        self.last_offset = 0.0
        self.last_lift = 0.0           # min(lift_l, lift_r)
        self.last_ext = 0.0            # max(ext_l, ext_r)  ใช้กับมิเตอร์หมัด
        self.last_min_ext = 0.0        # min(ext_l, ext_r)  ใช้กับมิเตอร์ไม้ตาย
        self.last_gap = 0.0
        self.last_lean = 0.0           # หัวเอียงล่าสุด (ไว้โชว์ทิศหลบ)
        self.last_action = ""
        self.last_action_time = 0.0

    # ---------- persistence ----------
    def tunables(self):
        return {k: getattr(self, k) for k in TUNABLE_KEYS}

    def apply_tunables(self, d):
        if not d:
            return
        for k, v in d.items():
            if k in TUNABLE_KEYS and isinstance(v, (int, float)):
                setattr(self, k, float(v))

    def reset_defaults(self):
        c = self.cfg
        self.punch_extend_min = c.PUNCH_EXTEND_MIN
        self.punch_reset_extend = c.PUNCH_RESET_EXTEND
        self.dodge_threshold = c.DODGE_THRESHOLD
        self.ult_wrist_above_nose = c.ULT_WRIST_ABOVE_NOSE
        self.ult_extend_min = c.ULT_EXTEND_MIN
        self.tpose_extend_min = c.TPOSE_EXTEND_MIN
        self.tpose_gap_min = c.TPOSE_GAP_MIN
        self.guard_above = c.GUARD_WRIST_ABOVE_NOSE
        self.guard_below = c.GUARD_WRIST_BELOW_NOSE
        self.guard_gap_max = c.GUARD_WRIST_GAP_MAX
        self._flash_result("RESET to defaults")

    # ---------- calibration (ท่ายืน) ----------
    def start_calibration(self):
        self._calibrating = True
        self._calib_end = time.time() + self.cfg.CALIBRATION_SEC
        self._calib_y = []
        self._calib_len = []

    @property
    def is_calibrating(self):
        return self._calibrating

    @property
    def is_ready(self):
        return self.baseline_y is not None

    def calib_remaining(self):
        return max(0.0, self._calib_end - time.time())

    # ---------- ปรับสดๆ ด้วยปุ่ม (สำรอง นอกจาก record) ----------
    def adjust_punch(self, delta):
        self.punch_extend_min = max(0.10, self.punch_extend_min + delta)
        self.punch_reset_extend = min(self.punch_reset_extend, self.punch_extend_min - 0.05)

    def adjust_dodge(self, delta):
        self.dodge_threshold = max(0.02, self.dodge_threshold + delta)

    # ---------- record-by-example ----------
    def start_record(self, gesture):
        if gesture == "dodge" and not self.is_ready:
            self._flash_result("calibrate (C) ก่อนถึงจะ record หลบได้")
            return
        self.rec_gesture = gesture
        self.rec_phase = "ready"
        self._rec_end = time.time() + self.cfg.RECORD_READY_SEC
        self._rec_samples = []
        self.blocking = False

    @property
    def is_recording(self):
        return self.rec_gesture is not None

    def rec_remaining(self):
        return max(0.0, self._rec_end - time.time())

    def _flash_result(self, msg):
        self.rec_result = msg
        self.rec_result_time = time.time()

    def _record_step(self, metrics, now):
        """เก็บตัวอย่างระหว่าง record แล้วสรุปตั้ง threshold เมื่อครบเวลา"""
        offset, min_lift, max_ext, min_ext, avg_lift, gap = metrics

        if self.rec_phase == "ready":
            if now >= self._rec_end:
                self.rec_phase = "rec"
                self._rec_end = now + self.cfg.RECORD_SEC
                self._rec_samples = []
            return

        # phase == "rec": เก็บค่าที่เกี่ยวกับท่านั้น
        g = self.rec_gesture
        if g == "punch":
            self._rec_samples.append(max_ext)
        elif g == "dodge":
            self._rec_samples.append(offset)
        elif g == "ultimate":
            self._rec_samples.append((min_lift, min_ext))
        elif g == "tpose":
            self._rec_samples.append((gap, min_ext))
        elif g == "guard":
            self._rec_samples.append((avg_lift, gap))

        if now >= self._rec_end:
            self._finalize_record()

    def _finalize_record(self):
        g = self.rec_gesture
        s = self._rec_samples
        c = self.cfg
        self.rec_gesture = None
        self.rec_phase = ""

        if len(s) < 3:
            self._flash_result("record ไม่พอ — ลองใหม่ (อยู่ในกล้องด้วย)")
            return

        if g == "punch":
            hi = _pct(s, 0.90)     # ตอนเหยียดสุด
            lo = _pct(s, 0.10)     # ตอนหดแขน
            rng = max(0.05, hi - lo)
            self.punch_extend_min = lo + rng * c.REC_PUNCH_TRIGGER_FRAC
            self.punch_reset_extend = lo + rng * c.REC_PUNCH_RESET_FRAC
            self._flash_result(
                f"PUNCH set: trig>={self.punch_extend_min:.2f} reset>={self.punch_reset_extend:.2f}")

        elif g == "dodge":
            deepest = _pct(s, 0.10)   # offset ต่ำสุด (ลบมากสุด = ย่อลึกสุด)
            self.dodge_threshold = max(0.05, -deepest * c.REC_DODGE_FRAC)
            self._flash_result(f"DODGE set: offset<-{self.dodge_threshold:.2f}")

        elif g == "ultimate":
            lifts = [a for a, _ in s]
            exts = [b for _, b in s]
            peak_lift = _pct(lifts, 0.90)
            peak_ext = _pct(exts, 0.90)
            self.ult_wrist_above_nose = max(0.1, peak_lift * c.REC_ULT_FRAC)
            self.ult_extend_min = max(0.5, peak_ext * c.REC_ULT_FRAC)
            self._flash_result(
                f"ULT set: lift>{self.ult_wrist_above_nose:.2f} ext>{self.ult_extend_min:.2f}")

        elif g == "tpose":
            gaps = [a for a, _ in s]
            exts = [b for _, b in s]
            self.tpose_gap_min = max(1.0, _pct(gaps, 0.50) * c.REC_TPOSE_FRAC)
            self.tpose_extend_min = max(0.5, _pct(exts, 0.50) * c.REC_TPOSE_FRAC)
            self._flash_result(
                f"T-POSE set: gap>{self.tpose_gap_min:.2f} ext>{self.tpose_extend_min:.2f}")

        elif g == "guard":
            lifts = [a for a, _ in s]
            gaps = [b for _, b in s]
            mid = _pct(lifts, 0.50)
            self.guard_above = mid + c.REC_GUARD_MARGIN
            self.guard_below = c.REC_GUARD_MARGIN - mid
            self.guard_gap_max = max(0.4, _pct(gaps, 0.90) * c.REC_GAP_FACTOR)
            self._flash_result(
                f"GUARD set: band[{-self.guard_below:.2f}..{self.guard_above:.2f}] gap<{self.guard_gap_max:.2f}")

        if self.on_tuned:
            self.on_tuned()   # ให้ main เซฟลงไฟล์

    # ---------- helper ----------
    def _check_punch(self, ext, now, side):
        """คืน True ถ้าแขนข้างนี้ 'ออกหมัด' (เหยียดเกินเส้น + armed + พ้น cooldown)"""
        if side == "L":
            armed, last_t = self._armed_l, self._last_punch_l
        else:
            armed, last_t = self._armed_r, self._last_punch_r

        if ext < self.punch_reset_extend:      # หดแขนกลับ -> พร้อมยิงใหม่
            armed = True

        fired = False
        if armed and ext > self.punch_extend_min and now - last_t >= self.cfg.PUNCH_COOLDOWN_SEC:
            fired = True
            armed = False
            last_t = now

        if side == "L":
            self._armed_l, self._last_punch_l = armed, last_t
        else:
            self._armed_r, self._last_punch_r = armed, last_t
        return fired

    def _flash(self, label, now):
        self.last_action = label
        self.last_action_time = now

    # ---------- loop หลัก ----------
    def update(self, pr):
        events = []

        if not pr.found:
            self._armed_l = self._armed_r = True
            self.blocking = False
            self.state = STATE_STAND
            return events

        # ระหว่าง calibrate baseline
        if self._calibrating:
            self._calib_y.append(pr.torso_y)
            self._calib_len.append(pr.torso_len)
            if time.time() >= self._calib_end and len(self._calib_y) > 0:
                self.baseline_y = sum(self._calib_y) / len(self._calib_y)
                self.baseline_len = sum(self._calib_len) / len(self._calib_len)
                self._calibrating = False
            return events

        now = time.time()

        # เมตริกพื้นฐาน (คำนวณทุกเฟรม ไว้ทั้งตัดสินท่า, record, และมิเตอร์)
        lift_l = (pr.nose_y - pr.lw_y) / pr.torso_len
        lift_r = (pr.nose_y - pr.rw_y) / pr.torso_len
        min_lift = min(lift_l, lift_r)
        avg_lift = (lift_l + lift_r) / 2.0
        max_ext = max(pr.ext_l, pr.ext_r)
        min_ext = min(pr.ext_l, pr.ext_r)
        offset = (self.baseline_y - pr.torso_y) / self.baseline_len if self.is_ready else 0.0

        self.last_offset = offset
        self.last_lift = min_lift
        self.last_ext = max_ext
        self.last_min_ext = min_ext
        self.last_gap = pr.wrist_gap
        self.last_lean = pr.head_lean

        # ระหว่าง record: เก็บตัวอย่าง ไม่ยิง event
        if self.rec_gesture is not None:
            self._record_step((offset, min_lift, max_ext, min_ext, avg_lift, pr.wrist_gap), now)
            self.state = STATE_STAND
            return events

        if not self.is_ready:
            return events

        cfg = self.cfg

        # ---- 1) ULTIMATE ----
        ult_now = (lift_l > self.ult_wrist_above_nose and lift_r > self.ult_wrist_above_nose
                   and pr.ext_l > self.ult_extend_min and pr.ext_r > self.ult_extend_min)
        if ult_now:
            self.blocking = False
            self._armed_l = self._armed_r = True
            if self._ult_armed and now - self._last_ult_time >= cfg.ULT_COOLDOWN_SEC:
                self._ult_armed = False
                self._last_ult_time = now
                events.append("ultimate")
                self._flash("ULTIMATE", now)
            self.state = STATE_ULT
            return events
        self._ult_armed = True

        # ---- 1.5) T-POSE (กางแขนสองข้าง) -> สกิล R ----
        # แยกจากไม้ตายด้วย "ข้อมือไม่สูงเหนือหัว" + "กางกว้าง (gap มาก)"
        tpose_now = (pr.ext_l > self.tpose_extend_min and pr.ext_r > self.tpose_extend_min
                     and pr.wrist_gap > self.tpose_gap_min
                     and lift_l < cfg.TPOSE_ABOVE_NOSE_MAX
                     and lift_r < cfg.TPOSE_ABOVE_NOSE_MAX)
        if tpose_now:
            self.blocking = False
            self._armed_l = self._armed_r = True
            if self._tpose_armed and now - self._last_tpose_time >= cfg.TPOSE_COOLDOWN_SEC:
                self._tpose_armed = False
                self._last_tpose_time = now
                events.append("tpose")
                self._flash("T-POSE R", now)
            self.state = STATE_TPOSE
            return events
        self._tpose_armed = True

        # ---- 2) BLOCK / การ์ด ----
        guard_now = (
            -self.guard_below <= lift_l <= self.guard_above and
            -self.guard_below <= lift_r <= self.guard_above and
            pr.wrist_gap < self.guard_gap_max
        )
        if guard_now:
            self.blocking = True
            self._block_off = 0
            self._armed_l = self._armed_r = True
            self.state = STATE_BLOCK
            self._flash("BLOCK", now)
            return events
        elif self.blocking:
            self._block_off += 1
            if self._block_off >= cfg.GUARD_RELEASE_FRAMES:
                self.blocking = False
                self.state = STATE_STAND
            else:
                self.state = STATE_BLOCK
                return events

        # ---- 3) DODGE (หลบ; ย่อ + เอียงหัว = เลือกทิศ) ----
        if offset < -self.dodge_threshold:
            if self._dodge_armed and now - self._last_dodge_time >= cfg.DODGE_COOLDOWN_SEC:
                self._dodge_armed = False
                self._last_dodge_time = now
                lean = pr.head_lean
                if lean <= -cfg.DODGE_LEAN_THRESHOLD:
                    direction = "left"      # จมูกเยื้องซ้ายของภาพ = เอียงหัวกายภาพซ้าย
                elif lean >= cfg.DODGE_LEAN_THRESHOLD:
                    direction = "right"
                else:
                    direction = None        # หัวตรง = พุ่งหน้า (Space เฉยๆ)
                if cfg.DODGE_SWAP_LR and direction:
                    direction = "right" if direction == "left" else "left"
                if direction == "left":
                    events.append("dodge_left"); self._flash("DODGE L", now)
                elif direction == "right":
                    events.append("dodge_right"); self._flash("DODGE R", now)
                else:
                    events.append("dodge"); self._flash("DODGE", now)
            self._armed_l = self._armed_r = True
            self.state = STATE_DODGE
            return events
        elif offset > -(self.dodge_threshold - cfg.DODGE_RELEASE_MARGIN):
            self._dodge_armed = True

        # ---- 4) PUNCH ซ้าย/ขวา ----
        left_key = "punch_right" if cfg.SWAP_LEFT_RIGHT else "punch_left"
        right_key = "punch_left" if cfg.SWAP_LEFT_RIGHT else "punch_right"
        if self._check_punch(pr.ext_l, now, "L"):
            events.append(left_key)
        if self._check_punch(pr.ext_r, now, "R"):
            events.append(right_key)

        if events:
            self.state = STATE_PUNCH
            self._flash("+".join(e.replace("punch_", "").upper() for e in events), now)
        else:
            self.state = STATE_STAND
        return events
