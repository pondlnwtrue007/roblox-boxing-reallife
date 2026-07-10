"""
เก็บ/โหลดค่าจูน (threshold ที่ได้จาก record) ลงไฟล์ JSON
ที่ %LOCALAPPDATA%\\RobloxBoxingReallife\\boxing_settings.json

ทำให้จูนครั้งเดียวแล้วจำไว้ ไม่ต้องตั้งใหม่ทุกครั้งที่เปิดโปรแกรม
"""

import json
import os

from paths import appdata_dir

SETTINGS_FILE = os.path.join(appdata_dir(), "boxing_settings.json")


def load():
    """คืน dict ค่าจูนที่เคยเซฟไว้ (คืน {} ถ้ายังไม่มีไฟล์/อ่านไม่ได้)"""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save(d):
    """เซฟ dict ค่าจูนลงไฟล์ — คืน True ถ้าสำเร็จ"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return True
    except Exception as e:
        print("เซฟ settings ไม่สำเร็จ:", e)
        return False
