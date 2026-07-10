"""
Dropdown เลือกหน้าต่างเป้าหมาย (ใช้ Tkinter — built-in ไม่ต้องลงเพิ่ม)

choose_window(default) -> คืนค่า:
    "ชื่อ/คำที่ใช้ match"  = เลือกหน้าต่างนั้น
    ""                    = ปิดการกรอง (ส่งทุกหน้าต่าง)
    None                  = ยกเลิก/ปิดหน้าต่าง (คงค่าเดิมไว้)
"""

from winfocus import list_windows

ALL_WINDOWS_LABEL = "(ทุกหน้าต่าง — ปิดการกรอง)"


def _preselect_index(wins, default):
    """หา index ที่ควร preselect ใน combobox (0 = ตัวเลือก 'ทุกหน้าต่าง', i+1 = wins[i])"""
    if default:
        for i, t in enumerate(wins):
            if default.lower() in t.lower():
                return i + 1
    for i, t in enumerate(wins):
        if "roblox" in t.lower():
            return i + 1
    return 0


def _resolve(index, wins):
    """แปลง index ที่เลือก -> ค่าที่ใช้ match ('' = ทุกหน้าต่าง, Roblox ใช้คำเสถียร)"""
    if index <= 0 or index - 1 >= len(wins):
        return ""
    title = wins[index - 1]
    return "Roblox" if "roblox" in title.lower() else title


def choose_window(default=""):
    """เปิด dropdown ให้เลือก — ถ้า Tkinter ใช้ไม่ได้จะ raise ให้ผู้เรียกไป fallback"""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("เลือกหน้าต่างเป้าหมาย")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    state = {"wins": []}
    result = {"value": None}

    tk.Label(root, text="เลือกหน้าต่างเกม Roblox (เป้าหมายส่งปุ่ม):",
             font=("Segoe UI", 10)).pack(pady=(14, 6), padx=14)
    combo = ttk.Combobox(root, state="readonly", width=64)
    combo.pack(pady=4, padx=14)

    def refresh():
        wins = list_windows()
        state["wins"] = wins
        combo["values"] = [ALL_WINDOWS_LABEL] + wins
        combo.current(_preselect_index(wins, default))

    def on_select(*_):
        result["value"] = _resolve(combo.current(), state["wins"])
        root.destroy()

    def on_cancel(*_):
        result["value"] = None
        root.destroy()

    btns = tk.Frame(root)
    btns.pack(pady=12)
    tk.Button(btns, text="🔄 รีเฟรช", command=refresh, width=10).pack(side="left", padx=5)
    tk.Button(btns, text="เลือก", command=on_select, width=14,
              default="active").pack(side="left", padx=5)
    tk.Button(btns, text="ยกเลิก", command=on_cancel, width=10).pack(side="left", padx=5)

    refresh()
    root.bind("<Return>", on_select)
    root.bind("<Escape>", on_cancel)
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    # จัดให้อยู่กลางจอคร่าวๆ + โฟกัส
    root.update_idletasks()
    root.eval("tk::PlaceWindow . center")
    root.focus_force()
    root.mainloop()
    return result["value"]
