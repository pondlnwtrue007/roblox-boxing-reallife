"""
Roblox Boxing Real-Life — เล่น Untitled Boxing Game ด้วยการชกมวยจริงหน้ากล้อง

loop หลัก: กล้อง -> MediaPipe Pose -> ตัดสินท่า -> ส่งปุ่มเข้าเกม
พร้อมหน้าต่าง debug: skeleton + มิเตอร์สด + สถานะ + เส้นอ้างอิง

5 ท่า: แย็บซ้าย->K | ฮุคขวา->L | การ์ด->F(ค้าง) | หลบ(ย่อ)->Space | ไม้ตาย->Q

*** จูนแบบ record (ไม่ต้องพิมพ์เลข) ***
  1 = record หมัด | 2 = record หลบ | 3 = record ไม้ตาย | 4 = record การ์ด
  กดแล้วทำท่าตามที่จอบอก ~3 วิ ระบบตั้งค่าให้เอง + เซฟลงไฟล์อัตโนมัติ
  0 = คืนค่า default | S = เซฟ

ปุ่มลัดอื่น:
  C = calibrate ท่ายืน | T = สลับ DRY-RUN/LIVE | [ ] ; ' = ปรับสดๆ | X/ESC = ออก
"""

import sys
import time
import cv2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config as cfg
import settings_store
from camera import CameraStream
from winfocus import target_focused, list_windows
from pose_detector import PoseDetector
from motion_logic import (MotionLogic, STATE_STAND, STATE_PUNCH,
                          STATE_BLOCK, STATE_DODGE, STATE_ULT, STATE_TPOSE)
from input_sender import InputSender

FONT = cv2.FONT_HERSHEY_SIMPLEX

# สีสถานะ (BGR)
COLOR_STAND = (180, 180, 180)
COLOR_PUNCH = (0, 220, 0)
COLOR_BLOCK = (0, 160, 255)
COLOR_DODGE = (255, 160, 0)
COLOR_ULT = (255, 0, 255)
COLOR_TPOSE = (0, 255, 255)
COLOR_INFO = (255, 255, 255)
COLOR_WARN = (0, 0, 255)

STATE_COLORS = {
    STATE_STAND: COLOR_STAND, STATE_PUNCH: COLOR_PUNCH, STATE_BLOCK: COLOR_BLOCK,
    STATE_DODGE: COLOR_DODGE, STATE_ULT: COLOR_ULT, STATE_TPOSE: COLOR_TPOSE,
}

# คำแนะนำตอน record แต่ละท่า
REC_HINT = {
    "punch": "ชกซ้าย/ขวา สลับกันเรื่อยๆ (สุดแรง)",
    "dodge": "ย่อตัวลง-ขึ้น ซ้ำๆ (ให้ต่ำสุดเท่าที่จะหลบจริง)",
    "ultimate": "ยกแขนสองข้างขึ้นสูงสุด ค้างไว้",
    "tpose": "กางแขนสองข้างออกด้านข้าง (ท่า T) ค้างไว้",
    "guard": "ตั้งการ์ดค้างไว้ (ท่าที่จะใช้จริง)",
}


def choose_target(default):
    """
    เลือกหน้าต่างเป้าหมาย: ใช้ dropdown (Tkinter) ก่อน ถ้าเปิดไม่ได้ค่อย fallback เป็นพิมพ์ในเทอร์มินัล
    คืนค่าที่ควรใช้เป็น target (ถ้าผู้ใช้ยกเลิก = คงค่าเดิม)
    """
    try:
        import window_picker
        sel = window_picker.choose_window(default)
        return default if sel is None else sel   # None = ยกเลิก -> คงค่าเดิม
    except Exception as e:
        print("เปิด dropdown ไม่ได้ (ใช้แบบพิมพ์แทน):", e)
        return pick_target_window(default)


def pick_target_window(default):
    """
    (สำรอง) แสดงรายชื่อหน้าต่างในเทอร์มินัลให้เลือกด้วยการพิมพ์เลข
    คืน "ชื่อ/คำบางส่วน" ที่จะใช้จับคู่ (ถ้า Enter เฉยๆ = ใช้ค่าเดิม)
    """
    wins = list_windows()
    print("\n=== เลือกหน้าต่างเกม (เป้าหมายส่งปุ่ม) ===")
    for i, t in enumerate(wins):
        mark = "   <-- น่าจะใช่" if "roblox" in t.lower() else ""
        print(f"  [{i}] {t}{mark}")
    print(f"  [Enter] ใช้ค่าเดิม: '{default}'  |  [-] ปิดการกรอง (ส่งทุกหน้าต่าง)")
    try:
        s = input("พิมพ์เลข หรือชื่อบางส่วน แล้ว Enter: ").strip()
    except EOFError:
        s = ""
    if not s:
        return default
    if s == "-":
        return ""
    if s.isdigit() and 0 <= int(s) < len(wins):
        title = wins[int(s)]
        # ถ้าเป็น Roblox ใช้คำว่า "Roblox" (title เสถียรกว่าเวลาเข้าเกม ชื่ออาจเปลี่ยน)
        return "Roblox" if "roblox" in title.lower() else title
    return s  # ใช้เป็นคำบางส่วน (substring)


def open_camera():
    cam = CameraStream(
        cfg.CAMERA_INDEX, cfg.CAMERA_WIDTH, cfg.CAMERA_HEIGHT,
        prefer_backend=cfg.CAMERA_BACKEND, use_mjpg=cfg.USE_MJPG, fps=cfg.CAMERA_FPS,
    )
    if not cam.is_opened():
        print(f"เปิดกล้อง index {cfg.CAMERA_INDEX} ไม่ได้")
        print("  - ปิดโปรแกรมอื่นที่ใช้กล้องอยู่ (Zoom/Teams/OBS/เบราว์เซอร์) แล้วลองใหม่")
        print("  - ถ้ามีหลายกล้อง ลองเปลี่ยน CAMERA_INDEX ใน config.py เป็น 1 หรือ 2")
        sys.exit(1)
    cam.start()
    deadline = time.time() + 3.0
    while time.time() < deadline:
        ok, _ = cam.read()
        if ok:
            break
        time.sleep(0.02)
    print(f"เปิดกล้องด้วย backend {cam.backend_name} ที่ {cam.size[0]}x{cam.size[1]}")
    return cam


def draw_meter(frame, x, y, w, h, label, value, thr, active=False):
    """
    วาดมิเตอร์ (bar) 1 อัน: แถบเต็ม = thr*1.6 (เส้น threshold อยู่ ~62% ของความกว้าง)
    เขียว = ค่าปัจจุบันเกิน threshold (ท่าจะติด), ส้ม = ยังไม่ถึง
    """
    cv2.rectangle(frame, (x, y), (x + w, y + h), (55, 55, 55), -1)
    scale = thr * 1.6 if thr > 0 else 1.0
    v = max(0.0, value)
    fill = int(min(1.0, v / scale) * w)
    over = value >= thr
    col = (0, 220, 0) if over else (0, 170, 255)
    if fill > 0:
        cv2.rectangle(frame, (x, y), (x + fill, y + h), col, -1)
    # เส้น threshold (ขาว)
    tx = x + int(min(1.0, thr / scale) * w)
    cv2.line(frame, (tx, y - 2), (tx, y + h + 2), (255, 255, 255), 2)
    border = (0, 255, 255) if active else (120, 120, 120)
    cv2.rectangle(frame, (x, y), (x + w, y + h), border, 1)
    cv2.putText(frame, f"{label}: {value:5.2f} / {thr:.2f}", (x + 4, y + h - 4),
                FONT, 0.45, (255, 255, 255), 1)


def draw_overlay(frame, logic: MotionLogic, sender: InputSender, pose, fps,
                 target_window="", win_focused=True):
    h, w = frame.shape[:2]

    # ----- เส้นอ้างอิง baseline + ระดับหลบ -----
    if logic.is_ready:
        base_y_px = int(logic.baseline_y * h)
        span = logic.baseline_len * h
        dodge_y = int(base_y_px + logic.dodge_threshold * span)
        cv2.line(frame, (0, base_y_px), (w, base_y_px), (200, 200, 200), 1)
        cv2.line(frame, (0, dodge_y), (w, dodge_y), COLOR_DODGE, 2)
        cv2.putText(frame, "DODGE line", (w - 150, min(h - 6, dodge_y + 16)),
                    FONT, 0.45, COLOR_DODGE, 1)

    # ----- เส้นอ้างอิงระดับข้อมือ (การ์ด/ไม้ตาย) อิงจมูกปัจจุบัน -----
    if pose is not None and pose.found:
        nose_px = int(pose.nose_y * h)
        tspan = pose.torso_len * h
        ult_y = int(nose_px - logic.ult_wrist_above_nose * tspan)
        g_up = int(nose_px - logic.guard_above * tspan)
        g_dn = int(nose_px + logic.guard_below * tspan)
        cv2.line(frame, (w - 200, ult_y), (w, ult_y), COLOR_ULT, 2)
        cv2.putText(frame, "ULT", (w - 40, max(12, ult_y - 4)), FONT, 0.45, COLOR_ULT, 1)
        cv2.line(frame, (w - 200, g_up), (w, g_up), COLOR_BLOCK, 1)
        cv2.line(frame, (w - 200, g_dn), (w, g_dn), COLOR_BLOCK, 1)
        cv2.putText(frame, "GUARD", (w - 60, g_dn + 14), FONT, 0.4, COLOR_BLOCK, 1)

    # ----- ป้ายสถานะใหญ่ (ท่าล่าสุด) -----
    color = STATE_COLORS.get(logic.state, COLOR_STAND)
    label = logic.state
    if logic.last_action and time.time() - logic.last_action_time < 0.5:
        label = logic.last_action
    cv2.putText(frame, label, (w - 300, 40), FONT, 1.1, color, 3)

    # ----- แถบข้อมูล (ซ้ายบน) -----
    mode = "LIVE (sending keys)" if not sender.dry_run else "DRY-RUN (no keys)"
    mode_color = COLOR_WARN if not sender.dry_run else COLOR_INFO
    if not target_window:
        tgt_txt, tgt_col = "TARGET: (all windows) [W=pick]", (0, 200, 255)
    elif win_focused:
        tgt_txt, tgt_col = f"TARGET: {target_window} [FOCUSED]", COLOR_PUNCH
    else:
        tgt_txt, tgt_col = f"TARGET: {target_window} [not focused - W=pick]", COLOR_WARN
    lines = [
        (f"MODE: {mode}", mode_color),
        (tgt_txt, tgt_col),
        (f"FPS: {fps:4.1f}", COLOR_INFO),
        (f"K:{sender.light_count} L:{sender.heavy_count} F:{sender.block_count} "
         f"SPC:{sender.dodge_count} Q:{sender.ult_count} R:{sender.ability_count}",
         (0, 255, 255)),
    ]
    y = 24
    for text, c in lines:
        cv2.putText(frame, text, (10, y), FONT, 0.55, c, 2)
        y += 24

    # ----- มิเตอร์สด (bar) — เห็นค่าจริงเทียบ threshold -----
    mx, mw, mh, sp = 10, 240, 16, 22
    my = h - 178
    guard_gap = logic.last_gap
    draw_meter(frame, mx, my, mw, mh, "PUNCH ext", logic.last_ext, logic.punch_extend_min,
               active=(logic.state == STATE_PUNCH))
    draw_meter(frame, mx, my + sp, mw, mh, "DODGE", max(0.0, -logic.last_offset),
               logic.dodge_threshold, active=(logic.state == STATE_DODGE))
    draw_meter(frame, mx, my + sp * 2, mw, mh, "ULT lift", logic.last_lift,
               logic.ult_wrist_above_nose, active=(logic.state == STATE_ULT))
    draw_meter(frame, mx, my + sp * 3, mw, mh, "ULT ext", logic.last_min_ext,
               logic.ult_extend_min, active=(logic.state == STATE_ULT))
    draw_meter(frame, mx, my + sp * 4, mw, mh, "T-POSE gap", guard_gap,
               logic.tpose_gap_min, active=(logic.state == STATE_TPOSE))
    gcol = COLOR_BLOCK if logic.blocking else (150, 150, 150)
    cv2.putText(frame, f"GUARD gap: {guard_gap:.2f}/{logic.guard_gap_max:.2f}  "
                f"[{'ON' if logic.blocking else 'off'}]", (mx, my + sp * 5 + 14),
                FONT, 0.5, gcol, 2)

    # ----- ตัวชี้ "หัวเอียง" -> ทิศหลบ (โชว์ข้างมิเตอร์ DODGE) -----
    lean, lthr = logic.last_lean, cfg.DODGE_LEAN_THRESHOLD
    d = "left" if lean <= -lthr else "right" if lean >= lthr else None
    if cfg.DODGE_SWAP_LR and d:
        d = "right" if d == "left" else "left"
    tag = "A(left)" if d == "left" else "D(right)" if d == "right" else "center"
    lcol = COLOR_DODGE if d else (150, 150, 150)
    cv2.putText(frame, f"LEAN {lean:+.2f} -> {tag}", (mx + mw + 12, my + sp + mh - 2),
                FONT, 0.5, lcol, 2)

    # ----- แบนเนอร์ตอน record -----
    if logic.is_recording:
        g = logic.rec_gesture
        cv2.rectangle(frame, (0, h // 2 - 60), (w, h // 2 + 40), (0, 0, 0), -1)
        if logic.rec_phase == "ready":
            cv2.putText(frame, f"GET READY: {g.upper()}  {logic.rec_remaining():.1f}s",
                        (w // 2 - 260, h // 2 - 20), FONT, 1.0, (0, 255, 255), 2)
        else:
            cv2.putText(frame, f"RECORDING {g.upper()}  {logic.rec_remaining():.1f}s",
                        (w // 2 - 240, h // 2 - 20), FONT, 1.0, (0, 220, 0), 2)
        cv2.putText(frame, REC_HINT.get(g, ""), (w // 2 - 260, h // 2 + 16),
                    FONT, 0.6, (255, 255, 255), 2)

    # ----- ผลลัพธ์ record (flash 3.5 วิ) -----
    if logic.rec_result and time.time() - logic.rec_result_time < 3.5:
        cv2.putText(frame, logic.rec_result, (10, h - 62), FONT, 0.6, (0, 255, 0), 2)

    # ----- สถานะ calibrate -----
    if logic.is_calibrating:
        cv2.putText(frame, f"CALIBRATING... stand still {logic.calib_remaining():.1f}s",
                    (w // 2 - 200, 60), FONT, 0.8, COLOR_WARN, 2)
    elif not logic.is_ready:
        cv2.putText(frame, "Press C to calibrate (stand normally)",
                    (w // 2 - 220, 60), FONT, 0.7, COLOR_WARN, 2)

    # ----- คีย์ช่วยจำ -----
    cv2.putText(frame, "REC: 1=punch 2=dodge 3=ult 4=guard 5=Tpose  0=reset S=save",
                (10, h - 34), FONT, 0.46, (0, 255, 255), 1)
    cv2.putText(frame, "C=calib  T=send  W=window  [ ] ; '=tune  X/ESC=quit",
                (10, h - 14), FONT, 0.46, (0, 255, 255), 1)
    return frame


def main():
    # เลือกหน้าต่างเป้าหมายก่อน (ให้ input เข้า Roblox ตัวจริง)
    target_window = cfg.TARGET_WINDOW
    if cfg.PICK_WINDOW_AT_START:
        target_window = choose_target(cfg.TARGET_WINDOW)
    print(f"เป้าหมายส่งปุ่ม: '{target_window or '(ทุกหน้าต่าง)'}'")

    cap = open_camera()
    detector = PoseDetector()
    logic = MotionLogic(cfg)
    sender = InputSender(cfg)

    # โหลดค่าจูนที่เคยเซฟไว้ + ตั้ง callback ให้เซฟอัตโนมัติหลัง record
    saved = settings_store.load()
    logic.apply_tunables(saved)
    if saved:
        print("โหลดค่าจูนจากไฟล์แล้ว")
    logic.on_tuned = lambda: settings_store.save(logic.tunables())

    logic.start_calibration()
    print("เริ่ม calibrate — ยืนนิ่งๆ ในท่าปกติหน้ากล้องสักครู่")

    prev_t = cv2.getTickCount()
    fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("อ่านภาพจากกล้องไม่ได้")
                break

            if cfg.FLIP_HORIZONTAL:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            pose = detector.process(rgb)

            events = logic.update(pose)

            win_focused = target_focused(target_window)
            focused = sender.dry_run or win_focused
            if focused:
                for ev in events:
                    if ev == "punch_left":
                        sender.light()
                    elif ev == "punch_right":
                        sender.heavy()
                    elif ev == "dodge":
                        sender.dodge()
                    elif ev == "dodge_left":
                        sender.dodge_left()
                    elif ev == "dodge_right":
                        sender.dodge_right()
                    elif ev == "ultimate":
                        sender.ultimate()
                    elif ev == "tpose":
                        sender.ability()
            if logic.blocking and focused:
                sender.block_start()
            else:
                sender.block_end()

            now = cv2.getTickCount()
            dt = (now - prev_t) / cv2.getTickFrequency()
            prev_t = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0 else 1.0 / dt

            if cfg.SHOW_DEBUG_WINDOW:
                detector.draw(frame, pose)
                draw_overlay(frame, logic, sender, pose, fps, target_window, win_focused)
                cv2.imshow("Roblox Boxing Real-Life", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == 255:
                    continue
                if key in (ord(cfg.KEY_QUIT), 27):
                    break
                elif key == ord(cfg.KEY_CALIBRATE):
                    logic.start_calibration()
                    print("calibrate ใหม่ — ยืนนิ่งๆ")
                elif key == ord(cfg.KEY_TOGGLE_SEND):
                    dry = sender.toggle_dry_run()
                    print("โหมด:", "DRY-RUN" if dry else "LIVE ส่งปุ่มจริง")
                elif key == ord(cfg.KEY_PICK_WINDOW):
                    target_window = choose_target(target_window)
                    print(f"เป้าหมายส่งปุ่ม: '{target_window or '(ทุกหน้าต่าง)'}'")
                # ---- record ----
                elif key == ord(cfg.KEY_REC_PUNCH):
                    logic.start_record("punch")
                elif key == ord(cfg.KEY_REC_DODGE):
                    logic.start_record("dodge")
                elif key == ord(cfg.KEY_REC_ULT):
                    logic.start_record("ultimate")
                elif key == ord(cfg.KEY_REC_GUARD):
                    logic.start_record("guard")
                elif key == ord(cfg.KEY_REC_TPOSE):
                    logic.start_record("tpose")
                elif key == ord(cfg.KEY_RESET_TUNE):
                    logic.reset_defaults()
                    settings_store.save(logic.tunables())
                elif key == ord(cfg.KEY_SAVE):
                    if settings_store.save(logic.tunables()):
                        print("เซฟค่าจูนแล้ว")
                # ---- ปรับสดๆ (สำรอง) ----
                elif key == ord(cfg.KEY_PUNCH_EASIER):
                    logic.adjust_punch(-cfg.TUNE_STEP)
                elif key == ord(cfg.KEY_PUNCH_HARDER):
                    logic.adjust_punch(cfg.TUNE_STEP)
                elif key == ord(cfg.KEY_DODGE_EASIER):
                    logic.adjust_dodge(-cfg.TUNE_STEP)
                elif key == ord(cfg.KEY_DODGE_HARDER):
                    logic.adjust_dodge(cfg.TUNE_STEP)
    finally:
        settings_store.save(logic.tunables())
        sender.cleanup()
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print("ปิดโปรแกรมเรียบร้อย (เซฟค่าจูนแล้ว)")


if __name__ == "__main__":
    main()
