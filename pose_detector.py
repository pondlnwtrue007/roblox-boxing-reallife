"""
หุ้ม MediaPipe Pose (Tasks API — PoseLandmarker): รับเฟรม -> landmark + เมตริกท่าชกมวย

หมายเหตุ: mediapipe เวอร์ชันใหม่ (0.10.3x+) ตัด legacy `mp.solutions` ออกแล้ว
จึงใช้ Tasks API ซึ่งต้องมีไฟล์โมเดล .task (ดาวน์โหลดอัตโนมัติถ้ายังไม่มี)

เมตริกหลักที่ใช้ตัดสิน (normalize ด้วย torso_len ทุกตัว ให้ไม่ขึ้นกับระยะกล้อง):
  - torso_y   : ตำแหน่งแนวตั้งเฉลี่ยของ (ไหล่ + สะโพก)  ใช้ตรวจ "หลบ" (ย่อตัว)
  - torso_len : ความยาวลำตัว = ระยะไหล่ถึงสะโพก (ตัวหารมาตรฐาน)
  - nose_y    : ตำแหน่งแนวตั้งของจมูก ใช้เทียบระดับข้อมือ (การ์ด vs ไม้ตาย)
  - ext_l/ext_r : "การเหยียดแขน" = ระยะข้อมือ-ไหล่ ในระนาบภาพ / torso_len (ตรวจหมัด/ไม้ตาย)
  - wrist_gap : ระยะห่างข้อมือสองข้างในแนวนอน / torso_len (ตรวจการ์ด ข้อมือชิดกัน)

TODO (เผื่ออนาคต): เพิ่มการใช้ landmark.z (ความลึก) ช่วยจับหมัดที่พุ่ง "ตรงเข้ากล้อง"
ตอนนี้ยังไม่ใช้เพราะ z จากภาพเดี่ยวมี noise ค่อนข้างสูง
"""

import os
import time
import urllib.request

import cv2
import mediapipe as mp

from paths import resource_path, appdata_dir

_V = mp.tasks.vision

# ไฟล์โมเดล + ที่มา (ถ้าไม่มีจะโหลดให้อัตโนมัติ)
MODEL_FILE = "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

# index ของ landmark (ตาม MediaPipe Pose 33 จุด)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

# คู่จุดสำหรับวาดโครงลำตัว + แขน ในหน้าต่าง debug
_TORSO_CONNECTIONS = [
    (L_SHOULDER, R_SHOULDER),
    (L_HIP, R_HIP),
    (L_SHOULDER, L_HIP),
    (R_SHOULDER, R_HIP),
]
_ARM_CONNECTIONS = [
    (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),
]


def ensure_model():
    """
    หาไฟล์โมเดล ตามลำดับ:
      1) ไฟล์ที่แนบมากับโปรแกรม (bundled ใน exe หรืออยู่ข้างสคริปต์)
      2) ไฟล์ที่เคยโหลดไว้ในโฟลเดอร์ appdata
      3) โหลดใหม่ลง appdata
    """
    bundled = resource_path(MODEL_FILE)
    if os.path.exists(bundled):
        return bundled

    cached = os.path.join(appdata_dir(), MODEL_FILE)
    if os.path.exists(cached):
        return cached

    print(f"กำลังดาวน์โหลดโมเดล {MODEL_FILE} ...")
    urllib.request.urlretrieve(MODEL_URL, cached)
    print("ดาวน์โหลดโมเดลเสร็จ")
    return cached


def _dist(a, b):
    """ระยะ euclidean ในระนาบภาพ (x,y) ระหว่าง landmark สองจุด (normalized)"""
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


class PoseResult:
    """ผลลัพธ์ต่อ 1 เฟรม"""

    def __init__(self, found, torso_y=None, torso_len=None, landmarks=None,
                 nose_y=None, ext_l=0.0, ext_r=0.0,
                 lw_x=0.0, lw_y=0.0, rw_x=0.0, rw_y=0.0, wrist_gap=0.0,
                 head_lean=0.0):
        self.found = found          # เจอคนในเฟรมไหม
        self.torso_y = torso_y      # ตำแหน่งแนวตั้งของลำตัว (normalized 0..1)
        self.torso_len = torso_len  # ความยาวลำตัว (normalized) — ตัวหารมาตรฐาน
        self.landmarks = landmarks  # list ของ landmark คนแรก (ไว้วาด)
        self.nose_y = nose_y        # y ของจมูก (normalized 0..1)
        self.ext_l = ext_l          # การเหยียดแขนซ้าย (ระยะ wrist-shoulder / torso_len)
        self.ext_r = ext_r          # การเหยียดแขนขวา
        self.lw_x = lw_x            # ข้อมือซ้าย x (normalized)
        self.lw_y = lw_y            # ข้อมือซ้าย y (normalized)
        self.rw_x = rw_x            # ข้อมือขวา x
        self.rw_y = rw_y            # ข้อมือขวา y
        self.wrist_gap = wrist_gap  # ระยะห่างข้อมือสองข้างแนวนอน / torso_len
        # หัวเอียง: จมูกเยื้องจากกึ่งกลางไหล่แค่ไหน / torso_len
        #   + = เยื้องขวาของภาพ (= เอียงหัวไปทางกายภาพขวา เพราะภาพกระจก)
        #   - = เยื้องซ้ายของภาพ (= เอียงหัวไปทางกายภาพซ้าย)
        self.head_lean = head_lean


class PoseDetector:
    def __init__(self, model_path=None):
        model_path = model_path or ensure_model()
        options = _V.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=_V.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = _V.PoseLandmarker.create_from_options(options)
        self._t0 = time.perf_counter()
        self._last_ts = -1

    def _timestamp_ms(self):
        # ต้องเพิ่มขึ้นเรื่อยๆ อย่างเคร่งครัด ไม่งั้น detect_for_video จะ error
        ts = int((time.perf_counter() - self._t0) * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        return ts

    def process(self, rgb_frame) -> PoseResult:
        """รับภาพ RGB (uint8, HxWx3) -> PoseResult"""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms())

        if not result.pose_landmarks:
            return PoseResult(found=False)

        pts = result.pose_landmarks[0]
        ls, rs = pts[L_SHOULDER], pts[R_SHOULDER]
        lw, rw = pts[L_WRIST], pts[R_WRIST]

        shoulder_y = (ls.y + rs.y) / 2.0
        hip_y = (pts[L_HIP].y + pts[R_HIP].y) / 2.0

        torso_y = (shoulder_y + hip_y) / 2.0
        torso_len = abs(hip_y - shoulder_y)
        if torso_len < 1e-3:
            torso_len = 1e-3

        # การเหยียดแขนแต่ละข้าง = ระยะข้อมือ-ไหล่ (ข้างเดียวกัน) หาร torso_len
        ext_l = _dist(lw, ls) / torso_len
        ext_r = _dist(rw, rs) / torso_len

        # ระยะห่างข้อมือสองข้างในแนวนอน (ไว้ตรวจการ์ด: ข้อมือชิดกัน)
        wrist_gap = abs(lw.x - rw.x) / torso_len

        # หัวเอียง: จมูกเยื้องจากกึ่งกลางไหล่ในแนวนอน (ไว้เลือกทิศหลบ ซ้าย/ขวา)
        shoulder_cx = (ls.x + rs.x) / 2.0
        head_lean = (pts[NOSE].x - shoulder_cx) / torso_len

        return PoseResult(
            found=True, torso_y=torso_y, torso_len=torso_len, landmarks=pts,
            nose_y=pts[NOSE].y, ext_l=ext_l, ext_r=ext_r,
            lw_x=lw.x, lw_y=lw.y, rw_x=rw.x, rw_y=rw.y, wrist_gap=wrist_gap,
            head_lean=head_lean,
        )

    def draw(self, bgr_frame, pose_result: PoseResult):
        """วาด landmark + โครงลำตัว + แขน ลงบนภาพ BGR (หน้าต่าง debug)"""
        if not pose_result.found or pose_result.landmarks is None:
            return bgr_frame
        h, w = bgr_frame.shape[:2]
        pts = pose_result.landmarks

        # เส้นเชื่อมลำตัว (เขียว)
        for a, b in _TORSO_CONNECTIONS:
            ax, ay = int(pts[a].x * w), int(pts[a].y * h)
            bx, by = int(pts[b].x * w), int(pts[b].y * h)
            cv2.line(bgr_frame, (ax, ay), (bx, by), (0, 255, 0), 2)

        # เส้นแขน (ไหล่-ศอก-ข้อมือ) — สีฟ้า ให้เห็นการเหยียดตอนออกหมัด
        for a, b in _ARM_CONNECTIONS:
            ax, ay = int(pts[a].x * w), int(pts[a].y * h)
            bx, by = int(pts[b].x * w), int(pts[b].y * h)
            cv2.line(bgr_frame, (ax, ay), (bx, by), (255, 200, 0), 2)

        # จุด landmark ทั้งหมด (ส้ม) + เน้นจมูกเป็นวงใหญ่ (เหลือง) ไว้ดูระดับอ้างอิง
        for lm in pts:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(bgr_frame, (cx, cy), 3, (0, 200, 255), -1)
        nx, ny = int(pts[NOSE].x * w), int(pts[NOSE].y * h)
        cv2.circle(bgr_frame, (nx, ny), 6, (0, 255, 255), 2)
        return bgr_frame

    def close(self):
        self._landmarker.close()
