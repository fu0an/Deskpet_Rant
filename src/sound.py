"""程序合成复古提示音，运行时生成，零素材依赖。

三种：happy（上扬）、speechless（低平）、normal（轻快啵）。
Windows 用 winsound 异步播放；其它平台静默跳过。
"""

import math
import struct

try:
    import winsound
except ImportError:  # 非 Windows
    winsound = None

_enabled = True
SAMPLE_RATE = 8000


def _synth(freqs: list[int], duration_ms: int) -> bytes:
    total = int(SAMPLE_RATE * duration_ms / 1000)
    seg = max(1, total // len(freqs))
    out = []
    for f in freqs:
        period = SAMPLE_RATE / f
        phase = 0.0
        for _ in range(seg):
            phase += 1.0 / period
            if phase >= 1.0:
                phase -= 1.0
            env = math.exp(-3.0 * (_ % seg) / seg)
            v = (
                math.sin(2 * math.pi * phase) * 0.6
                + math.sin(4 * math.pi * phase) * 0.2
            ) * env
            out.append(int(max(-1.0, min(1.0, v)) * 32767))
    return struct.pack("<%dh" % len(out), *out)


_SOUNDS = {
    "happy": _synth([660, 990], 130),
    "speechless": _synth([220], 150),
    "normal": _synth([523, 392], 110),
}


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def play(kind: str = "normal") -> None:
    if not _enabled or winsound is None:
        return
    try:
        winsound.PlaySound(
            _SOUNDS.get(kind, _SOUNDS["normal"]),
            winsound.SND_MEMORY | winsound.SND_ASYNC,
        )
    except Exception:  # noqa: BLE001
        pass
