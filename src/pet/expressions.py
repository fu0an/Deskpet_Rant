"""表情判定与统一控制。

- split_emotion(text)：解析模型返回的 {"emotion":..., "text":...}；解析失败用关键词兜底
- classify(text)：本地关键词判定情绪
- ExpressionController：统一管理表情切换与回默认的定时器；清醒时偶尔自动眨眼；
  被反复拨弄时 show_annoyed() 无论睁闭眼都露烦躁脸，结束后回到对应状态。
"""

import json
import random
import re

from PySide6.QtCore import QObject, QTimer

from .sprite import Expression

BLINK_MIN_MS = 3000   # 眨眼最小间隔
BLINK_MAX_MS = 9000   # 眨眼最大间隔
BLINK_LEN_MS = 130    # 单次眨眼时长

HAPPY_WORDS = [
    "哈哈", "嘻嘻", "嘿嘿", "开心", "高兴", "不错", "好耶", "厉害", "棒",
    "赞", "漂亮", "可爱", "喜欢", "有意思", "笑死", "妙啊", "爽", "好活",
    "爱了", "满意", "有意思",
]
SPEECHLESS_WORDS = [
    "无语", "算了", "唉", "服了", "麻了", "佛了", "救命", "血压", "离谱",
    "摆烂", "摸鱼", "困", "累", "沉默", "受够", "看不下去", "无聊", "没眼看",
    "扶额", "挠头", "不想说",
]
PUZZLED_WORDS = [
    "好奇", "疑惑", "奇怪", "什么鬼", "怎么回事", "咋回事", "干嘛",
    "为什么", "搞不懂", "不明白",
]

EXPR_BY_NAME = {
    "happy": Expression.HAPPY,
    "normal": Expression.NORMAL,
    "speechless": Expression.SPEECHLESS,
    "puzzled": Expression.PUZZLED,
    "curious": Expression.PUZZLED,
}

_EMOTION_RE = re.compile(
    r'\{\s*"emotion"\s*:\s*"(happy|normal|speechless|puzzled)"'
    r'(?:\s*,\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)")?\s*\}'
)


def classify(text: str) -> Expression:
    if not text:
        return Expression.NORMAL
    for w in SPEECHLESS_WORDS:
        if w in text:
            return Expression.SPEECHLESS
    for w in HAPPY_WORDS:
        if w in text:
            return Expression.HAPPY
    for w in PUZZLED_WORDS:
        if w in text:
            return Expression.PUZZLED
    if text.count("？") >= 2 or text.count("?") >= 2:
        return Expression.SPEECHLESS
    if "……" in text or "..." in text:
        return Expression.SPEECHLESS
    if text.count("！") >= 1 or text.count("!") >= 1:
        return Expression.HAPPY
    return Expression.NORMAL


def _clean_json_scalar(s: str) -> str:
    return s.replace("\\\"", '"').replace("\\\\", "\\")


def _try_parse_object(text: str):
    """从文本中抽取最外层 {...} 尝试 json 解析；失败返回 None。

    兼容模型常见的不规范输出：前后有废话、键值用中文引号/全角逗号等。
    """
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    chunk = text[start : end + 1]
    for candidate in (
        chunk,
        chunk.replace("，", ",").replace("：", ":").replace("；", ";"),
    ):
        for pair in (
            (chr(8220), '"'),  # “
            (chr(8221), '"'),  # ”
            (chr(8216), "'"),  # ‘
            (chr(8217), "'"),  # ’
        ):
            candidate = candidate.replace(*pair)
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return None


def split_emotion(text: str) -> tuple[str, Expression]:
    """返回 (干净的文本, 表情)。解析不出 JSON 时整段文本按关键词兜底。"""
    if not text:
        return text, Expression.NORMAL
    m = _EMOTION_RE.search(text)
    if m:
        emotion = EXPR_BY_NAME.get(m.group(1), Expression.NORMAL)
        if m.group(2) is not None:
            clean = _clean_json_scalar(m.group(2))
            return clean, emotion
        clean = (text[: m.start()] + text[m.end() :]).strip()
        return clean, emotion
    obj = _try_parse_object(text)
    if obj is not None:
        emotion = EXPR_BY_NAME.get(str(obj.get("emotion", "")), Expression.NORMAL)
        body = obj.get("text")
        clean = str(body).strip() if body is not None else ""
        if clean:
            return clean, emotion
        # 有 emotion 没 text：把 JSON 去掉，剩文本按情绪返回
        head, tail = text.find("{"), text.rfind("}")
        remainder = (text[:head] + text[tail + 1 :]).strip()
        return remainder, emotion
    return text, classify(text)


class ExpressionController(QObject):
    """按展示内容切换表情，并在若干秒后回到当前状态对应的默认表情。

    - 闭眼睡觉时 show() 不切换（保持安静），但眨眼/烦躁不在此限；
    - revert() 会按眼睛状态回到 NORMAL（睁眼）或 CLOSED（闭眼）。
    """

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.revert)

        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._do_blink)

    def show(self, expression: Expression, revert_ms: int = 2500) -> None:
        if not self.pet.eyes_open:
            return
        self.pet.set_expression(expression)
        self._timer.start(revert_ms)

    def show_annoyed(self, revert_ms: int = 2800) -> None:
        """被反复拨弄：无论睁闭眼都露烦躁脸，结束后回到对应状态。"""
        self._timer.stop()
        self.pet.set_expression(Expression.EXCITED_RESTLESS)
        self._timer.start(revert_ms)

    def revert(self) -> None:
        self.pet.set_expression(
            Expression.NORMAL if self.pet.eyes_open else Expression.CLOSED
        )

    # --- 自动眨眼（清醒空闲时）---

    def start_blinking(self) -> None:
        self._blink_timer.stop()
        self._schedule_blink()

    def _schedule_blink(self) -> None:
        self._blink_timer.start(random.randint(BLINK_MIN_MS, BLINK_MAX_MS))

    def _do_blink(self) -> None:
        if self.pet.eyes_open and self.pet.expression is Expression.NORMAL:
            self.pet.set_expression(Expression.BLINK)
            QTimer.singleShot(BLINK_LEN_MS, self._unblink)
        self._schedule_blink()

    def _unblink(self) -> None:
        if self.pet.expression is Expression.BLINK:
            self.pet.set_expression(Expression.NORMAL)
