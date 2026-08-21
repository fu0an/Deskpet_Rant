"""Rant机 像素形象：程序化绘制，虚线边框小方块 + 像素表情。

表情：
- NORMAL      常规：方形眼
- HAPPY       开心/害羞：八字眯眼 + 腮红
- SPEECHLESS  无语：一字型眯眼 + 流汗
- CLOSED      闭眼：一字型眯眼
嘴巴始终一字型。
"""

import enum

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

GRID = 16  # 逻辑像素网格（16x16）

COLOR_BODY = "#3b4252"
COLOR_BORDER = "#d8dee9"
COLOR_EYE = "#eceff4"
COLOR_BLUSH = "#f2a0b0"
COLOR_SWEAT = "#7fd4f7"


class Expression(enum.Enum):
    NORMAL = "normal"
    HAPPY = "happy"
    SPEECHLESS = "speechless"
    CLOSED = "closed"


def _fill(p: QPainter, cell: int, x: int, y: int, w: int, h: int, color: str) -> None:
    p.fillRect(QRect(x * cell, y * cell, w * cell, h * cell), QColor(color))


class SpriteRenderer:
    def __init__(self, cell: int = 6):
        self.cell = cell

    def logical_size(self) -> int:
        return GRID * self.cell

    def render(self, expression: Expression, dpr: float = 1.0) -> QPixmap:
        # 在设置了 DPR 的 pixmap 上，QPainter 使用逻辑坐标；
        # 物理分辨率由 pixmap 尺寸与 DPR 负责，绘制坐标一律用逻辑值。
        cell = self.cell
        size = self.logical_size()
        phys = int(round(size * dpr))
        pm = QPixmap(phys, phys)
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, False)

        # 身体
        p.fillRect(0, 0, size, size, QColor(COLOR_BODY))

        # 虚线边框
        pen = QPen(QColor(COLOR_BORDER))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(max(2, round(cell / 2)))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        inset = pen.width() // 2
        p.drawRect(QRect(inset, inset, size - 2 * inset, size - 2 * inset))

        # 眼睛
        if expression is Expression.NORMAL:
            _fill(p, cell, 4, 6, 3, 2, COLOR_EYE)
            _fill(p, cell, 10, 6, 3, 2, COLOR_EYE)
        elif expression is Expression.HAPPY:
            # 八字眯眼（^ ^）：斜向两格组成
            _fill(p, cell, 4, 7, 1, 1, COLOR_EYE)
            _fill(p, cell, 5, 6, 1, 1, COLOR_EYE)
            _fill(p, cell, 6, 7, 1, 1, COLOR_EYE)
            _fill(p, cell, 9, 7, 1, 1, COLOR_EYE)
            _fill(p, cell, 10, 6, 1, 1, COLOR_EYE)
            _fill(p, cell, 11, 7, 1, 1, COLOR_EYE)
            # 腮红
            _fill(p, cell, 2, 9, 2, 1, COLOR_BLUSH)
            _fill(p, cell, 12, 9, 2, 1, COLOR_BLUSH)
        elif expression is Expression.SPEECHLESS:
            # 一字型眯眼
            _fill(p, cell, 4, 6, 3, 1, COLOR_EYE)
            _fill(p, cell, 10, 6, 3, 1, COLOR_EYE)
            # 流汗（右侧小水滴）
            _fill(p, cell, 13, 3, 1, 1, COLOR_SWEAT)
            _fill(p, cell, 13, 4, 1, 1, COLOR_SWEAT)
            _fill(p, cell, 12, 4, 1, 1, COLOR_SWEAT)
        else:  # CLOSED
            _fill(p, cell, 4, 6, 3, 1, COLOR_EYE)
            _fill(p, cell, 10, 6, 3, 1, COLOR_EYE)

        # 嘴巴：一字型，始终不变
        _fill(p, cell, 7, 11, 3, 1, COLOR_EYE)

        p.end()
        return pm
