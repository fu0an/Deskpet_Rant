"""截屏：mss 抓取 + 降采样 + JPEG 压缩，减少视觉 token 消耗。"""

import io

import mss
from PIL import Image

MAX_SIZE = 768
QUALITY = 70


def capture_screen(max_size: int = MAX_SIZE, quality: int = QUALITY) -> bytes | None:
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)
    except Exception:  # noqa: BLE001
        return None

    w, h = img.size
    scale = max_size / max(w, h)
    if scale < 1.0:
        img = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS
        )

    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()
