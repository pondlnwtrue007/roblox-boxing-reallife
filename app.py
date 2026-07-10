"""
Roblox Boxing Real-Life — แอป GUI (CustomTkinter)

หน้าตาแบบ release: ธีมมืด, กล้อง+skeleton, มิเตอร์สด (progress bar), ปุ่มควบคุม,
dropdown เลือกหน้าต่างเป้าหมาย, ปุ่ม record จูนทุกท่า

รันด้วย:  python app.py
(ถ้าอยากได้เวอร์ชันเบา/ดีบักด้วยหน้าต่าง OpenCV ใช้ python main.py แทน)
"""

import sys
import time
import tkinter as tk

import cv2
from PIL import Image

try:
    import customtkinter as ctk
except Exception as e:  # pragma: no cover
    print("ต้องติดตั้ง customtkinter ก่อน:  pip install customtkinter")
    print("รายละเอียด:", e)
    sys.exit(1)

import config as cfg
import settings_store
from camera import CameraStream
from winfocus import target_focused, list_windows
from pose_detector import PoseDetector
from motion_logic import (MotionLogic, STATE_STAND, STATE_PUNCH,
                          STATE_BLOCK, STATE_DODGE, STATE_ULT, STATE_TPOSE)
from input_sender import InputSender

# ---------- สี (hex) ----------
C_BG = "#15171c"
C_CARD = "#1e2128"
C_GREEN = "#22c55e"
C_BLUE = "#3b82f6"
C_ORANGE = "#f59e0b"
C_MAGENTA = "#d946ef"
C_CYAN = "#06b6d4"
C_RED = "#ef4444"
C_GRAY = "#6b7280"
C_TEXT = "#e5e7eb"

STATE_COLOR = {
    STATE_STAND: C_GRAY, STATE_PUNCH: C_GREEN, STATE_BLOCK: C_ORANGE,
    STATE_DODGE: C_BLUE, STATE_ULT: C_MAGENTA, STATE_TPOSE: C_CYAN,
}
STATE_TH = {
    STATE_STAND: "พร้อม", STATE_PUNCH: "หมัด", STATE_BLOCK: "การ์ด",
    STATE_DODGE: "หลบ", STATE_ULT: "ไม้ตาย", STATE_TPOSE: "ท่า T / สกิล",
}

ALL_WINDOWS = "(ทุกหน้าต่าง — ปิดการกรอง)"

REC_HINT = {
    "punch": "ชกซ้าย/ขวา สลับกันเรื่อยๆ (สุดแรง)",
    "dodge": "ย่อตัวลง-ขึ้น ซ้ำๆ (ต่ำสุดเท่าที่จะหลบจริง)",
    "ultimate": "ยกแขนสองข้างขึ้นสูงสุด ค้างไว้",
    "tpose": "กางแขนสองข้างออกด้านข้าง (ท่า T) ค้างไว้",
    "guard": "ตั้งการ์ดค้างไว้ (ท่าที่จะใช้จริง)",
}

DISP_W, DISP_H = 640, 480


class BoxingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Roblox Boxing — Real Life")
        self.geometry("1060x700")
        self.minsize(980, 640)
        self.configure(fg_color=C_BG)

        # ---------- backend ----------
        self.detector = PoseDetector()
        self.logic = MotionLogic(cfg)
        self.logic.apply_tunables(settings_store.load())
        self.logic.on_tuned = lambda: settings_store.save(self.logic.tunables())
        self.sender = InputSender(cfg)
        self.target = cfg.TARGET_WINDOW
        self._fps = 0.0
        self._prev = time.perf_counter()
        self._win_focused = True

        self.cam = self._open_camera()
        self.logic.start_calibration()

        # ---------- UI ----------
        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_windows()
        self.after(30, self._tick)

    # =================== camera ===================
    def _open_camera(self):
        cam = CameraStream(cfg.CAMERA_INDEX, cfg.CAMERA_WIDTH, cfg.CAMERA_HEIGHT,
                           prefer_backend=cfg.CAMERA_BACKEND, use_mjpg=cfg.USE_MJPG,
                           fps=cfg.CAMERA_FPS)
        if not cam.is_opened():
            self._fatal("เปิดกล้องไม่ได้\n\nปิดโปรแกรมที่ใช้กล้องอยู่ (Zoom/OBS/เบราว์เซอร์)\n"
                        "หรือเปลี่ยน CAMERA_INDEX ใน config.py")
        cam.start()
        deadline = time.time() + 3.0
        while time.time() < deadline:
            ok, _ = cam.read()
            if ok:
                break
            time.sleep(0.02)
        return cam

    def _fatal(self, msg):
        import tkinter.messagebox as mb
        mb.showerror("Roblox Boxing", msg)
        self.destroy()
        sys.exit(1)

    # =================== build UI ===================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # ---------- ซ้าย: หัวข้อ + สถานะ + วิดีโอ ----------
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="🥊  Roblox Boxing", font=("Segoe UI", 24, "bold"),
                     text_color=C_TEXT).pack(side="left")
        ctk.CTkLabel(header, text="เล่นด้วยการชกมวยจริงหน้ากล้อง",
                     font=("Segoe UI", 13), text_color=C_GRAY).pack(side="left", padx=12)

        # แถบสถานะท่า + FPS
        statusbar = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12)
        statusbar.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        self.state_dot = ctk.CTkLabel(statusbar, text="●", font=("Segoe UI", 22),
                                      text_color=C_GRAY, width=24)
        self.state_dot.pack(side="left", padx=(14, 4), pady=8)
        self.state_lbl = ctk.CTkLabel(statusbar, text="พร้อม", font=("Segoe UI", 20, "bold"),
                                      text_color=C_TEXT)
        self.state_lbl.pack(side="left")
        self.fps_lbl = ctk.CTkLabel(statusbar, text="FPS --", font=("Segoe UI", 13),
                                    text_color=C_GRAY)
        self.fps_lbl.pack(side="right", padx=16)

        # วิดีโอ
        vidwrap = ctk.CTkFrame(left, fg_color="#000000", corner_radius=12)
        vidwrap.grid(row=2, column=0, sticky="nsew")
        self.video = ctk.CTkLabel(vidwrap, text="กำลังเปิดกล้อง...", text_color=C_GRAY)
        self.video.pack(expand=True, padx=6, pady=6)

        # แถบใต้ภาพ (record banner / lean)
        self.footer = ctk.CTkLabel(left, text="กด C เพื่อ calibrate ท่ายืน",
                                   font=("Segoe UI", 13), text_color=C_GRAY, anchor="w")
        self.footer.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # ---------- ขวา: sidebar ควบคุม (scroll) ----------
        side = ctk.CTkScrollableFrame(self, width=350, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=14)

        self._build_control_card(side)
        self._build_meters_card(side)
        self._build_record_card(side)
        self._build_counters_card(side)
        self._build_legend_card(side)

    def _card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 14, "bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=14, pady=(12, 6))
        return card

    def _build_control_card(self, parent):
        card = self._card(parent, "⚙️  ควบคุม")

        # โหมด DRY/LIVE
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text="ส่งปุ่มเข้าเกม", font=("Segoe UI", 13),
                     text_color=C_TEXT).pack(side="left")
        self.live_switch = ctk.CTkSwitch(row, text="", command=self._toggle_live,
                                         progress_color=C_GREEN)
        self.live_switch.pack(side="right")
        self.mode_pill = ctk.CTkLabel(card, text="DRY-RUN (ไม่ส่งปุ่ม)", font=("Segoe UI", 13, "bold"),
                                      fg_color="#2a2f3a", corner_radius=8, text_color=C_GRAY)
        self.mode_pill.pack(fill="x", padx=14, pady=(2, 8), ipady=5)

        # หน้าต่างเป้าหมาย
        ctk.CTkLabel(card, text="หน้าต่างเป้าหมาย", font=("Segoe UI", 13),
                     text_color=C_TEXT).pack(anchor="w", padx=14)
        wrow = ctk.CTkFrame(card, fg_color="transparent"); wrow.pack(fill="x", padx=14, pady=(2, 8))
        self.win_var = tk.StringVar(value=self.target or ALL_WINDOWS)
        self.win_menu = ctk.CTkOptionMenu(wrow, variable=self.win_var, values=[ALL_WINDOWS],
                                          command=self._pick_window, dynamic_resizing=False,
                                          width=250)
        self.win_menu.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(wrow, text="🔄", width=36, command=self._refresh_windows).pack(side="right", padx=(6, 0))
        self.focus_pill = ctk.CTkLabel(card, text="", font=("Segoe UI", 12, "bold"),
                                       fg_color="#2a2f3a", corner_radius=8)
        self.focus_pill.pack(fill="x", padx=14, pady=(0, 8), ipady=4)

        # calibrate
        ctk.CTkButton(card, text="🎯  Calibrate ท่ายืน (C)", command=self._calibrate,
                      height=38, font=("Segoe UI", 14, "bold")).pack(fill="x", padx=14, pady=(2, 12))

    def _build_meters_card(self, parent):
        card = self._card(parent, "📊  มิเตอร์สด")
        self.meters = {}
        specs = [("PUNCH", "หมัด"), ("DODGE", "หลบ"), ("ULT_LIFT", "ไม้ตาย (ยกสูง)"),
                 ("ULT_EXT", "ไม้ตาย (เหยียด)"), ("TPOSE", "ท่า T (กางแขน)")]
        for key, label in specs:
            row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=14, pady=2)
            top = ctk.CTkFrame(row, fg_color="transparent"); top.pack(fill="x")
            ctk.CTkLabel(top, text=label, font=("Segoe UI", 12), text_color=C_TEXT).pack(side="left")
            val = ctk.CTkLabel(top, text="--", font=("Segoe UI", 11), text_color=C_GRAY)
            val.pack(side="right")
            bar = ctk.CTkProgressBar(row, height=10, progress_color=C_BLUE)
            bar.set(0); bar.pack(fill="x", pady=(2, 4))
            self.meters[key] = (bar, val)

        # LEAN (หลบมีทิศ)
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=14, pady=(2, 12))
        self.lean_lbl = ctk.CTkLabel(row, text="เอียงหัว: center", font=("Segoe UI", 12),
                                     text_color=C_GRAY)
        self.lean_lbl.pack(anchor="w")
        self.lean_bar = ctk.CTkProgressBar(row, height=10, progress_color=C_BLUE)
        self.lean_bar.set(0.5); self.lean_bar.pack(fill="x", pady=(2, 0))

    def _build_record_card(self, parent):
        card = self._card(parent, "🎬  จูนท่า (Record)")
        ctk.CTkLabel(card, text="กดแล้วทำท่านั้นค้าง ~3 วิ ระบบตั้งค่าให้เอง",
                     font=("Segoe UI", 11), text_color=C_GRAY, wraplength=310,
                     justify="left").pack(anchor="w", padx=14)
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=14, pady=8)
        for i in range(2):
            grid.grid_columnconfigure(i, weight=1)
        btns = [("หมัด", "punch"), ("หลบ", "dodge"), ("ไม้ตาย", "ultimate"),
                ("การ์ด", "guard"), ("ท่า T", "tpose")]
        for i, (label, g) in enumerate(btns):
            ctk.CTkButton(grid, text=label, command=lambda x=g: self._record(x),
                          fg_color="#2a2f3a", hover_color="#3a4150", height=34).grid(
                row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
        act = ctk.CTkFrame(card, fg_color="transparent"); act.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(act, text="↺ Reset", command=self._reset, fg_color="#3a2a2a",
                      hover_color="#4a3030", width=120).pack(side="left", expand=True, padx=3)
        ctk.CTkButton(act, text="💾 Save", command=self._save, width=120).pack(
            side="right", expand=True, padx=3)

    def _build_counters_card(self, parent):
        card = self._card(parent, "🔢  จำนวนที่ส่ง")
        self.count_lbl = ctk.CTkLabel(card, text="", font=("Consolas", 13), text_color=C_TEXT,
                                      justify="left")
        self.count_lbl.pack(anchor="w", padx=14, pady=(0, 12))

    def _build_legend_card(self, parent):
        card = self._card(parent, "🥋  ท่า → ปุ่ม")
        rows = [("แย็บซ้าย", "K"), ("ฮุคขวา", "L"), ("การ์ด", "F (ค้าง)"),
                ("หลบ / ซ้าย / ขวา", "Space / +A / +D"), ("ไม้ตาย", "Q"), ("ท่า T (สกิล)", "R")]
        for name, key in rows:
            r = ctk.CTkFrame(card, fg_color="transparent"); r.pack(fill="x", padx=14, pady=1)
            ctk.CTkLabel(r, text=name, font=("Segoe UI", 12), text_color=C_TEXT).pack(side="left")
            ctk.CTkLabel(r, text=key, font=("Consolas", 12, "bold"), text_color=C_CYAN).pack(side="right")
        ctk.CTkLabel(card, text="", height=4).pack()

    # =================== actions ===================
    def _toggle_live(self):
        want_live = bool(self.live_switch.get())
        if want_live == self.sender.dry_run:      # dry_run True = DRY; want_live True = LIVE
            self.sender.toggle_dry_run()

    def _kbd_toggle_live(self):
        # สลับสวิตช์ด้วยคีย์บอร์ด (T)
        if self.live_switch.get():
            self.live_switch.deselect()
        else:
            self.live_switch.select()
        self._toggle_live()

    def _calibrate(self):
        self.logic.start_calibration()

    def _record(self, gesture):
        self.logic.start_record(gesture)

    def _reset(self):
        self.logic.reset_defaults()
        settings_store.save(self.logic.tunables())

    def _save(self):
        settings_store.save(self.logic.tunables())
        self.footer.configure(text="💾 เซฟค่าจูนแล้ว", text_color=C_GREEN)

    def _refresh_windows(self):
        wins = list_windows()
        self._wins = wins
        self.win_menu.configure(values=[ALL_WINDOWS] + wins)
        # preselect roblox ถ้าเจอ
        cur = self.win_var.get()
        if cur in ([ALL_WINDOWS] + wins):
            return
        for t in wins:
            if "roblox" in t.lower():
                self.win_var.set(t); self._pick_window(t); return

    def _pick_window(self, choice):
        if choice == ALL_WINDOWS:
            self.target = ""
        elif "roblox" in choice.lower():
            self.target = "Roblox"
        else:
            self.target = choice

    # =================== keys ===================
    def _bind_keys(self):
        keymap = {
            cfg.KEY_CALIBRATE: self._calibrate,
            cfg.KEY_TOGGLE_SEND: self._kbd_toggle_live,
            cfg.KEY_REC_PUNCH: lambda: self._record("punch"),
            cfg.KEY_REC_DODGE: lambda: self._record("dodge"),
            cfg.KEY_REC_ULT: lambda: self._record("ultimate"),
            cfg.KEY_REC_GUARD: lambda: self._record("guard"),
            cfg.KEY_REC_TPOSE: lambda: self._record("tpose"),
            cfg.KEY_RESET_TUNE: self._reset,
            cfg.KEY_SAVE: self._save,
            cfg.KEY_PICK_WINDOW: self._refresh_windows,
        }

        def on_key(e):
            fn = keymap.get(e.char.lower())
            if fn:
                fn()
            elif e.keysym == "Escape":
                self._on_close()
        self.bind("<Key>", on_key)

    # =================== main loop ===================
    def _tick(self):
        ok, frame = self.cam.read()
        if ok:
            if cfg.FLIP_HORIZONTAL:
                frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            pose = self.detector.process(rgb)

            events = self.logic.update(pose)
            self._win_focused = target_focused(self.target)
            focused = self.sender.dry_run or self._win_focused
            if focused:
                for ev in events:
                    self._dispatch(ev)
            if self.logic.blocking and focused:
                self.sender.block_start()
            else:
                self.sender.block_end()

            # วาด skeleton + เส้นอ้างอิงบนภาพ
            self.detector.draw(frame, pose)
            self._draw_lines(frame, pose)

            # อัปเดตภาพ
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            ctkimg = ctk.CTkImage(light_image=img, dark_image=img, size=(DISP_W, DISP_H))
            self.video.configure(image=ctkimg, text="")
            self.video._img = ctkimg

            # FPS
            now = time.perf_counter()
            dt = now - self._prev
            self._prev = now
            if dt > 0:
                self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt

            self._update_panel()

        self.after(8, self._tick)

    def _dispatch(self, ev):
        s = self.sender
        {"punch_left": s.light, "punch_right": s.heavy, "dodge": s.dodge,
         "dodge_left": s.dodge_left, "dodge_right": s.dodge_right,
         "ultimate": s.ultimate, "tpose": s.ability}.get(ev, lambda: None)()

    def _draw_lines(self, frame, pose):
        h, w = frame.shape[:2]
        L = self.logic
        if L.is_ready:
            base = int(L.baseline_y * h)
            span = L.baseline_len * h
            dodge_y = int(base + L.dodge_threshold * span)
            cv2.line(frame, (0, base), (w, base), (120, 120, 120), 1)
            cv2.line(frame, (0, dodge_y), (w, dodge_y), (255, 160, 0), 2)
        if pose is not None and pose.found:
            npx = int(pose.nose_y * h)
            ts = pose.torso_len * h
            uy = int(npx - L.ult_wrist_above_nose * ts)
            cv2.line(frame, (w - 200, uy), (w, uy), (239, 70, 239), 2)

    def _meter(self, key, value, thr):
        bar, val = self.meters[key]
        scale = thr * 1.6 if thr > 0 else 1.0
        bar.set(max(0.0, min(1.0, value / scale)))
        over = value >= thr
        bar.configure(progress_color=C_GREEN if over else C_BLUE)
        val.configure(text=f"{value:.2f} / {thr:.2f}",
                      text_color=C_GREEN if over else C_GRAY)

    def _update_panel(self):
        L, S = self.logic, self.sender

        # ป้ายท่า
        col = STATE_COLOR.get(L.state, C_GRAY)
        label = STATE_TH.get(L.state, L.state)
        if L.last_action and time.time() - L.last_action_time < 0.5:
            label = L.last_action
        self.state_dot.configure(text_color=col)
        self.state_lbl.configure(text=label, text_color=col)
        self.fps_lbl.configure(text=f"FPS {self._fps:4.1f}")

        # โหมด + โฟกัส
        if S.dry_run:
            self.mode_pill.configure(text="DRY-RUN (ไม่ส่งปุ่ม)", text_color=C_GRAY, fg_color="#2a2f3a")
            self.focus_pill.configure(text="โหมดทดสอบ — ปลอดภัย", text_color=C_GRAY, fg_color="#2a2f3a")
        else:
            self.mode_pill.configure(text="● LIVE — ส่งปุ่มจริง", text_color="#ffffff", fg_color=C_RED)
            if self._win_focused:
                self.focus_pill.configure(text="● ส่งเข้าเกมได้ (โฟกัสอยู่)", text_color="#ffffff",
                                          fg_color=C_GREEN)
            else:
                self.focus_pill.configure(text="○ ยังไม่โฟกัสหน้าต่างเกม", text_color="#ffffff",
                                          fg_color="#8a5a00")

        # มิเตอร์
        self._meter("PUNCH", L.last_ext, L.punch_extend_min)
        self._meter("DODGE", max(0.0, -L.last_offset), L.dodge_threshold)
        self._meter("ULT_LIFT", L.last_lift, L.ult_wrist_above_nose)
        self._meter("ULT_EXT", L.last_min_ext, L.ult_extend_min)
        self._meter("TPOSE", L.last_gap, L.tpose_gap_min)

        # lean
        lean, lthr = L.last_lean, cfg.DODGE_LEAN_THRESHOLD
        d = "left" if lean <= -lthr else "right" if lean >= lthr else None
        if cfg.DODGE_SWAP_LR and d:
            d = "right" if d == "left" else "left"
        tag = "◀ ซ้าย (Space+A)" if d == "left" else "ขวา (Space+D) ▶" if d == "right" else "ตรง (Space)"
        self.lean_lbl.configure(text=f"เอียงหัว: {lean:+.2f}  →  {tag}",
                                text_color=C_BLUE if d else C_GRAY)
        sc = lthr * 2.5 if lthr > 0 else 1.0
        self.lean_bar.set(max(0.0, min(1.0, 0.5 + lean / (2 * sc))))
        self.lean_bar.configure(progress_color=C_BLUE if d else C_GRAY)

        # counters
        self.count_lbl.configure(
            text=(f"K {S.light_count:<3} L {S.heavy_count:<3} F {S.block_count:<3}\n"
                  f"Space {S.dodge_count:<3} Q {S.ult_count:<3} R {S.ability_count}"))

        # footer: record banner / คำแนะนำ
        if L.is_recording:
            g = L.rec_gesture
            phase = "เตรียมตัว" if L.rec_phase == "ready" else "● กำลังบันทึก"
            self.footer.configure(
                text=f"{phase} [{g}] {L.rec_remaining():.1f}s — {REC_HINT.get(g, '')}",
                text_color=C_GREEN if L.rec_phase == "rec" else C_ORANGE)
        elif L.is_calibrating:
            self.footer.configure(text=f"CALIBRATING... ยืนนิ่ง {L.calib_remaining():.1f}s",
                                  text_color=C_ORANGE)
        elif L.rec_result and time.time() - L.rec_result_time < 3.5:
            self.footer.configure(text="✓ " + L.rec_result, text_color=C_GREEN)
        elif not L.is_ready:
            self.footer.configure(text="กด 🎯 Calibrate แล้วยืนนิ่งในท่าปกติ", text_color=C_GRAY)
        else:
            self.footer.configure(text="พร้อมเล่น — จูนท่าด้วยปุ่ม Record ได้ตามใจ", text_color=C_GRAY)

    # =================== close ===================
    def _on_close(self):
        try:
            settings_store.save(self.logic.tunables())
            self.sender.cleanup()
            self.detector.close()
            self.cam.release()
        except Exception:
            pass
        self.destroy()


class _NullIO:
    """ตัวรับ print กันพัง เมื่อ build เป็น .exe แบบ windowed (sys.stdout เป็น None)"""
    def write(self, *a):
        pass

    def flush(self):
        pass


def main():
    # ในโหมด windowed exe ไม่มี console -> sys.stdout/err = None ทำให้ print() พัง
    if sys.stdout is None:
        sys.stdout = _NullIO()
    if sys.stderr is None:
        sys.stderr = _NullIO()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    app = BoxingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
