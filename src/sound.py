"""程序合成复古提示音，运行时生成，零素材依赖。

三种：happy（上扬）、speechless（低平）、normal（轻快啵）。
Windows 用 winsound 异步播放；其它平台静默跳过。
"""

import io
import math
import os
import struct
import tempfile
import wave

try:
    import winsound
except ImportError:  # 非 Windows
    winsound = None

_enabled = True
SAMPLE_RATE = 8000


def _synth(freqs: list[int], duration_ms: int) -> bytes:
    """合成一段带 WAV 头的单声道 16bit 波形（PlaySound SND_MEMORY 需要 WAV 格式）。"""
    total = int(SAMPLE_RATE * duration_ms / 1000)
    seg = max(1, total // len(freqs))
    frames = []
    for f in freqs:
        period = SAMPLE_RATE / f
        phase = 0.0
        for n in range(seg):
            phase += 1.0 / period
            if phase >= 1.0:
                phase -= 1.0
            env = math.exp(-3.0 * (n % seg) / seg)
            v = (
                math.sin(2 * math.pi * phase) * 0.6
                + math.sin(4 * math.pi * phase) * 0.2
            ) * env
            frames.append(int(max(-1.0, min(1.0, v)) * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack("<%dh" % len(frames), *frames))
    return buf.getvalue()


_SOUNDS = {
    "happy": _synth([660, 990], 130),
    "speechless": _synth([220], 150),
    "normal": _synth([523, 392], 110),
}

_SOUND_FILES: dict[str, str] = {}


def _ensure_files() -> None:
    """把 WAV 写到临时文件（winsound 的 SND_ASYNC 不支持内存数据）。"""
    if _SOUND_FILES:
        return
    for kind, data in _SOUNDS.items():
        try:
            path = os.path.join(tempfile.gettempdir(), f"deskpet_rant_{kind}.wav")
            with open(path, "wb") as f:
                f.write(data)
            _SOUND_FILES[kind] = path
        except OSError:
            pass


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def play(kind: str = "normal") -> None:
    if not _enabled or winsound is None:
        return
    _ensure_files()
    path = _SOUND_FILES.get(kind) or _SOUND_FILES.get("normal")
    if not path:
        return
    try:
        winsound.PlaySound(
            path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
        )
    except Exception:  # noqa: BLE001
        pass
