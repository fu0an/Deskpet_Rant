"""表情判定与统一控制。

- split_emotion(text)：解析模型返回的 {"emotion":..., "text":...}；解析失败用关键词兜底
- classify(text)：本地关键词判定情绪
- ExpressionController：统一管理表情切换与回默认的定时器
"""

import re

from PySide6.QtCore import QObject, QTimer

from .sprite import Expression

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


def split_emotion(text: str) -> tuple[str, Expression]:
    """返回 (干净的文本, 表情)。解析不出 JSON 时整段文本按关键词兜底。"""
    if not text:
        return text, Expression.NORMAL
    m = _EMOTION_RE.search(text)
    if m:
        emotion = EXPR_BY_NAME.get(m.group(1), Expression.NORMAL)
        if m.group(2) is not None:
            clean = m.group(2).replace('\\"', '"').replace("\\\\", "\\")
            return clean, emotion
        clean = (text[: m.start()] + text[m.end() :]).strip()
        return clean, emotion
    return text, classify(text)


class ExpressionController(QObject):
    """按展示内容切换表情，并在若干秒后回到默认表情。闭眼时不切换。"""

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.revert)

    def show(self, expression: Expression, revert_ms: int = 2500) -> None:
        if not self.pet.eyes_open:
            return
        self.pet.set_expression(expression)
        self._timer.start(revert_ms)

    def revert(self) -> None:
        if self.pet.eyes_open:
            self.pet.set_expression(Expression.NORMAL)
