"""屏幕观察器：定时截屏交给视觉模型，出吐槽。

- 闭眼时完全不截屏；
- 每次按概率决定是否真正调用模型（省钱）；
- 模型返回【无】或调用失败时不打扰用户（失败时用本地兜底语录）；
- 被内容审核拦截时给出专属文案并冷却一段时间，避免对同一画面反复上传。
"""

import logging
import random
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

from config import Config
from llm import prompts
from llm.client import ContentBlocked, LLMClient, LLMError
from pet.expressions import classify, split_emotion
from .capture import capture_screen

log = logging.getLogger(__name__)

FALLBACK_LINES = [
    "屏幕太安静了，是不是在摸鱼呀。",
    "刚想看一眼，信号不太好，我先背会儿老段子。",
    "等我连上网络，再来好好吐槽你。",
    "看不清楚屏幕，我先眯会儿。",
    "脑子（模型）还没接上线，先打个盹。",
]

BLOCKED_LINE = "这个画面太敏感了，我装作没看见，先休息会儿。"
BLOCK_COOLDOWN_S = 600  # 被审核拦截后这段时间不再发起识别


class ScreenObserver(QObject):
    comment_ready = Signal(str, str)   # (文本, 情绪名)
    fallback_ready = Signal(str, str)  # (文本, 情绪名)

    def __init__(self, cfg: Config, llm: LLMClient, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.llm = llm
        self._busy = False
        self._blocked_until = 0.0
        self.timer = QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._tick)

    def start(self) -> None:
        self.timer.start(self._interval_ms())

    def restart(self) -> None:
        self.timer.start(self._interval_ms())

    def stop(self) -> None:
        self.timer.stop()

    def _interval_ms(self) -> int:
        return max(1, int(self.cfg.get("observe_interval_minutes", 3))) * 60 * 1000

    def _tick(self) -> None:
        if self._busy or not self.cfg.get("eyes_open", True):
            return
        if not self.cfg.get("api_key", "").strip():
            return
        if not self.cfg.vision_model():  # 当前服务商不支持视觉，不必截屏
            return
        if time.time() < self._blocked_until:
            return
        prob = float(self.cfg.get("comment_probability", 0.4))
        if random.random() > prob:
            return
        self._busy = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            jpeg = capture_screen()
            if jpeg is None:
                line = random.choice(FALLBACK_LINES)
                self.fallback_ready.emit(line, classify(line).value)
                return
            reply = self.llm.vision_chat(prompts.screen_comment_prompt(self.cfg), jpeg)
            if reply and reply != prompts.REPLY_NONE:
                text, expr = split_emotion(reply)
                if text:
                    self.comment_ready.emit(text, expr.value)
        except ContentBlocked:
            self._blocked_until = time.time() + BLOCK_COOLDOWN_S
            self.fallback_ready.emit(BLOCKED_LINE, "speechless")
        except LLMError as e:
            log.warning("屏幕识别失败：%s", e)
            line = random.choice(FALLBACK_LINES)
            self.fallback_ready.emit(line, classify(line).value)
        except Exception:  # noqa: BLE001
            log.exception("屏幕识别发生未预期异常")
            line = random.choice(FALLBACK_LINES)
            self.fallback_ready.emit(line, classify(line).value)
        finally:
            self._busy = False
