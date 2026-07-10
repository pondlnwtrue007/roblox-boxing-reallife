<div align="center">

<img src="assets/logo.png" width="120" alt="Roblox Boxing Real-Life">

# Roblox Boxing — Real Life 🥊

**เล่น Untitled Boxing Game ด้วยการชกมวยจริงผ่านเว็บแคม**
แย็บ · ฮุค · การ์ด · หลบ (ซ้าย/ขวา) · ไม้ตาย · สกิล — จับจากร่างกายจริง ไม่ต้องแตะคีย์บอร์ด

[![Release](https://img.shields.io/github/v/release/pondlnwtrue007/roblox-boxing-reallife?label=release&color=e63946)](../../releases/latest)
[![Windows](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](../../releases/latest)
[![Downloads](https://img.shields.io/github/downloads/pondlnwtrue007/roblox-boxing-reallife/total?color=2ea44f&label=downloads)](../../releases)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![MediaPipe](https://img.shields.io/badge/AI-MediaPipe%20Pose-00897b)](https://developers.google.com/mediapipe)

<a href="https://github.com/pondlnwtrue007/roblox-boxing-reallife/releases/latest/download/RobloxBoxing-win64.zip">
  <img src="https://img.shields.io/badge/%E2%AC%87_DOWNLOAD-Windows_.zip-2ea44f?style=for-the-badge&logo=windows&logoColor=white" alt="ดาวน์โหลดสำหรับ Windows" height="46">
</a>

<sub>คลิกปุ่มด้านบนโหลด `RobloxBoxing-win64.zip` (~140MB) → แตกไฟล์ → ดับเบิลคลิก `RobloxBoxing.exe`</sub>

<sub>🎨 FAN-MADE · แจกฟรี · ไม่เกี่ยวข้องกับ Roblox Corporation — ดู [LICENSE](LICENSE)</sub>

</div>

---

## 🎬 หน้าตาแอป

<div align="center">
<img src="assets/app-screenshot.png" width="760" alt="Roblox Boxing Real-Life — app screenshot">
</div>

> มี **skeleton** ลากตามตัว + **มิเตอร์สด** ทางขวาบอกทุกท่าว่าจับได้จริง (แถบ **เขียว = ท่าจะติด**)

---

## 🕹️ วิธีใช้งาน (เริ่มเล่นใน 4 ขั้น)

### 1️⃣ ยืนตัวตรง แล้วกด Calibrate
เข้ามา **ยืนตัวตรงในท่าปกติ** ให้เห็นตัวตั้งแต่หัวถึงเอวในกล้อง แล้วกดปุ่ม
**🎯 Calibrate ท่ายืน (C)** → **ยืนนิ่งๆ ~2 วินาที** จนเสร็จ

> ระบบจะจำ "ความสูงลำตัวตอนยืนปกติ" ไว้เป็นฐาน เพื่อใช้ตัดสินว่า *หลบ* คือย่อต่ำกว่านี้
> — **ต้องทำขั้นนี้ก่อนเสมอ** (ถ้าขยับกล้อง/เปลี่ยนที่ยืน ให้กด `C` calibrate ใหม่)

### 2️⃣ สอนท่าให้โปรแกรม (Record ทีละท่า)
กดปุ่ม Record ของแต่ละท่าในการ์ด **"จูนท่า"** แล้ว **ทำท่านั้นจริงๆ ตามที่จอบอก**
(จะมีนับถอยหลัง *"เตรียมตัว"* ก่อน แล้วค่อย *"บันทึก"* — ทำท่าตอนคำว่าบันทึกขึ้น)
ระบบจับช่วงค่าจริงของร่างกายคุณแล้วตั้งค่าให้เอง **ทำครั้งเดียวจำไว้เลย**

| กด | ท่าที่ต้องทำตอน "บันทึก" |
|:---:|---|
| 🥊 **หมัด** `1` | หันหน้าเข้ากล้อง **ชกออกไปข้างหน้า สลับซ้าย-ขวา เหยียดแขนสุด** ซ้ำๆ |
| 💨 **หลบ** `2` | **ย่อตัวลงต่ำ แล้วลุกขึ้น** ซ้ำๆ (ให้ต่ำสุดเท่าที่จะหลบจริงในเกม) |
| 💥 **ไม้ตาย** `3` | **ยกแขนสองข้างขึ้นสูงสุดเหนือหัว** ค้างไว้จนครบเวลา |
| 🛡️ **การ์ด** `4` | **ยกการ์ดบังหน้า** (ข้อมือสองข้างชิดกันระดับหน้า) ค้างไว้ |
| ✨ **ท่า T** `5` | **กางแขนสองข้างออกเป็นตัว T** ค้างไว้ |

> 👀 ดู **มิเตอร์สด** ทางขวาไปด้วย — ตอนทำท่าถูก แถบของท่านั้นจะ **เขียว** (= จับได้แล้ว)
> ถ้าท่าไหนยังไม่ค่อยติด กด Record ท่านั้นซ้ำได้เรื่อยๆ · กด `0` = คืนค่าเริ่มต้น · ค่าจูนถูกเซฟให้อัตโนมัติ

### 3️⃣ ทดสอบก่อน (ปลอดภัย — ยังไม่ส่งปุ่ม)
ตอนนี้สวิตช์ **"ส่งปุ่มเข้าเกม" ยังปิดอยู่** (โหมด **DRY-RUN**) — ลองทำ 5 ท่าดูว่า
ป้ายท่าด้านบน + มิเตอร์เปลี่ยนถูกต้องไหม โดย **ยังไม่ส่งปุ่มเข้าเกมจริง**

### 4️⃣ เล่นจริง (LIVE)
1. ในช่อง **"หน้าต่างเป้าหมาย"** เลือก **Roblox** (กด 🔄 ถ้าเพิ่งเปิดเกมยังไม่เห็นในลิสต์)
2. เปิด Roblox เข้าเกม → **เปิดสวิตช์ "ส่งปุ่มเข้าเกม"** → เปลี่ยนเป็น **🔴 LIVE**
3. **คลิกที่หน้าต่าง Roblox ให้โฟกัส** → ป้ายขึ้น **🟢 ส่งเข้าเกมได้** → ชกได้เลย!
   - ถ้าขึ้น **🟠 ยังไม่โฟกัส** = ปุ่มยังไม่ส่ง (คลิกที่เกมก่อน)
   - วางหน้าต่างแอปไว้มุมจอ/จอที่ 2 จะได้เห็น skeleton + มิเตอร์ระหว่างเล่น

> **🥋 หลบมีทิศ:** ตอนย่อหลบ **เอียงหัว** ไปทางที่จะหลบ — หัวตรง → `Space` ·
> เอียงซ้าย → `Space`+`A` · เอียงขวา → `Space`+`D`
>
> **💡 อยากเช็คว่าปุ่มออกจริงไหม?** เลือก "(ทุกหน้าต่าง)" ในช่องหน้าต่างเป้าหมาย → เปิด
> Notepad โฟกัสไว้ → เปิด LIVE → ทำท่า จะเห็นตัวอักษร `k` `l` `f` พิมพ์ลง Notepad

---

## 🥊 ท่า → ปุ่ม

| ท่าทางจริง | ตรวจจับจาก | ปุ่มที่ส่ง |
|-----------|-----------|-----------|
| 🥊 แย็บซ้าย | แขนซ้ายเหยียดออก | `K` |
| 🥊 ฮุคขวา | แขนขวาเหยียดออก | `L` |
| 🛡️ ตั้งการ์ด | ข้อมือสองข้างระดับหน้า ชิดกัน | `F` (ค้าง) |
| 💨 หลบ (พุ่งหน้า) | ย่อตัว หัวตรง | `Space` |
| ↔️ หลบซ้าย / ขวา | ย่อ + เอียงหัวซ้าย/ขวา | `Space`+`A` / `Space`+`D` |
| 💥 ไม้ตาย | ยกแขนสองข้างขึ้นเหนือหัว | `Q` |
| ✨ สกิล (ท่า T) | กางแขนสองข้างระดับไหล่ | `R` |

---

## ⬇️ โหลดแล้วเล่นเลย (สำหรับคนทั่วไป)

1. คลิก **[⬇️ ดาวน์โหลด RobloxBoxing-win64.zip](https://github.com/pondlnwtrue007/roblox-boxing-reallife/releases/latest/download/RobloxBoxing-win64.zip)** (~140MB) — หรือดูทุกเวอร์ชันที่ [Releases](../../releases)
2. **แตกไฟล์ (Extract All)** แล้วเข้าโฟลเดอร์ → ดับเบิลคลิก **`RobloxBoxing.exe`**
   - ถ้า SmartScreen เตือน "Windows protected your PC" → กด **More info → Run anyway**
     (เพราะ .exe ยังไม่ได้เซ็นดิจิทัล เป็นเรื่องปกติของโปรแกรมทำเอง)
   - ครั้งแรกเปิดช้า ~10-20 วิ (โหลดโมเดล AI) ครั้งต่อไปเร็วขึ้น
3. แอปเปิดแล้ว → ทำตามหัวข้อ **[🕹️ วิธีใช้งาน](#-วิธีใช้งาน-เริ่มเล่นใน-4-ขั้น)** ด้านบนได้เลย

> 💻 ต้องใช้ **Windows 10/11** + **เว็บแคม** และเปิด **Roblox (Untitled Boxing Game)** ไว้
> ⌨️ ตั้ง keybind ในเกมให้ตรง: Light `K` · Heavy `L` · Block `F` · Dash `Space` · Ultimate `Q` · Ability `R`

---

## ⌨️ ปุ่มลัด

| ปุ่ม | ทำอะไร | | ปุ่ม | ทำอะไร |
|:---:|---|---|:---:|---|
| `C` | calibrate ท่ายืน | | `1`–`5` | record ท่า |
| `T` | สลับ DRY ↔ LIVE | | `0` | คืนค่า default |
| `W` | รีเฟรชรายชื่อหน้าต่าง | | `S` | เซฟค่าจูน |
| `[` `]` | ปรับหมัดง่าย/ยาก | | `;` `'` | ปรับหลบง่าย/ยาก |
| `Esc` | ออก | | | (ไม่ใช้ `Q` — เป็นไม้ตายในเกม) |

---

## 🖥️ รันจาก source (สำหรับคนมี Python)

ต้องมี **Python 3.10+** บน Windows

```bash
pip install -r requirements.txt
python app.py          # แอป GUI (แนะนำ)
# python main.py       # รุ่นเบา หน้าต่าง OpenCV ล้วน
```

ค่าจูนเก็บที่ `%LOCALAPPDATA%\RobloxBoxingReallife\boxing_settings.json` (ลบ = คืนค่า default)

---

## 🛠️ จูนละเอียด (`config.py`)

ค่าทั้งหมดอยู่ด้านบนไฟล์ มีคอมเมนต์ครบ หน่วยเป็น "สัดส่วนของความยาวลำตัว"
(ใช้ได้เหมือนกันไม่ว่าตัวใหญ่/เล็ก กล้องใกล้/ไกล) จุดที่มักปรับ:

- **หมัดยิงรัวไป** → เพิ่ม `PUNCH_COOLDOWN_SEC`
- **แย็บ/ฮุคสลับข้าง** (ภาพกระจก) → `SWAP_LEFT_RIGHT = True`
- **หลบซ้าย/ขวาสลับข้าง** → `DODGE_SWAP_LR = True`

> **มุมกล้อง:** หมัดพุ่งตรงเข้ากล้องตรวจยากใน 2D — ยืน **เฉียงกล้องนิดหน่อย** หรือชกออกด้านข้าง
> เล็กน้อยจะจับได้ชัดกว่า

---

## 🗂️ โครงสร้างไฟล์

| ไฟล์ | หน้าที่ |
|------|---------|
| **`app.py`** | แอป GUI (CustomTkinter) — ตัวหลัก |
| `main.py` | รุ่นเบา หน้าต่าง OpenCV + ปุ่มลัด |
| `config.py` | ค่าตั้งค่า/threshold ทั้งหมด |
| `pose_detector.py` | หุ้ม MediaPipe Pose → landmark + เมตริกท่าชกมวย |
| `motion_logic.py` | สมอง — ตัดสินท่า (priority + cooldown + hysteresis + record) |
| `input_sender.py` | ส่งปุ่มผ่าน pydirectinput (tap / hold / combo) |
| `settings_store.py` | เซฟ/โหลดค่าจูนลง JSON |
| `window_picker.py` | dropdown เลือกหน้าต่าง (สำหรับ `main.py`) |
| `camera.py` | กล้องแบบ threaded (ลด latency) |
| `winfocus.py` | เช็ก/ลิสต์หน้าต่าง active (กันปุ่มรั่ว) |
| `paths.py` | จัดการ path (รองรับ build `.exe`) |

---

## 🧠 ทำงานยังไง (ย่อ)

```
เว็บแคม → MediaPipe Pose → เมตริก (normalize ด้วยความยาวลำตัว)
        → ตัดสินท่า (priority: ไม้ตาย > ท่า T > การ์ด > หลบ > หมัด)
        → pydirectinput ส่ง scancode เข้า Roblox (เฉพาะตอนเกมโฟกัส)
```

---

## 🗺️ Roadmap

- [ ] ถอยหลัง: ย่อ + เอนตัวไปหลัง → `Space`+`S`
- [ ] คอมโบ/ท่าต่อเนื่อง

---

## 📄 License

[MIT](LICENSE) © 2026 · แก้ชื่อเจ้าของลิขสิทธิ์ในไฟล์ `LICENSE` ได้ตามต้องการ

<div align="center"><sub>🥊 ต่อยอดโครงสร้างจากโปรเจกต์ <a href="https://github.com/pondlnwtrue007/cookie-run-reallife">Cookie Run Real-Life</a></sub></div>
