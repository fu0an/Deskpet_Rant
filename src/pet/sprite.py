"""Rant机 像素形象：从项目根目录 pictures/ 加载像素画，按表情切换图片。

表情（对应 pictures/ 下的 PNG，均为 24x24）：
- NORMAL      常规：rantRobert_normal.png
- HAPPY       开心/害羞：rantRobert_happyORshy.png
- SPEECHLESS  无语：rantRobert_haveNOwords.png
- PUZZLED     疑惑/好奇：rantRobert_puzzledORcurious.png
- CLOSED      闭眼：rantRobert_eyesClosed.png
- EXCITED_RESTLESS  兴奋/烦躁：rantRobert_excitedORrestless.png
- BLINK       眨眼（复用闭眼帧做短暂闪眨）
"""

import enum
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap

GRID = 16  # 逻辑像素网格（16x16）


class Expression(enum.Enum):
    NORMAL = "normal"
    HAPPY = "happy"
    SPEECHLESS = "speechless"
    PUZZLED = "puzzled"
    CLOSED = "closed"
    EXCITED_RESTLESS = "excitedORrestless"
    BLINK = "blink"


EXPRESSION_FILES = {
    Expression.NORMAL: "rantRobert_normal.png",
    Expression.HAPPY: "rantRobert_happyORshy.png",
    Expression.SPEECHLESS: "rantRobert_haveNOwords.png",
    Expression.PUZZLED: "rantRobert_puzzledORcurious.png",
    Expression.CLOSED: "rantRobert_eyesClosed.png",
    Expression.EXCITED_RESTLESS: "rantRobert_excitedORrestless.png",
    Expression.BLINK: "rantRobert_eyesClosed.png",
}


def _pictures_dir() -> Path:
    """素材目录：打包后从 PyInstaller 数据目录读取，开发时取项目根目录。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "pictures"


class SpriteRenderer:
    def __init__(self, cell: int = 6):
        self.cell = cell
        self._cache: dict[Expression, QPixmap] = {}

    def logical_size(self) -> int:
        return GRID * self.cell

    def render(self, expression: Expression, dpr: float = 1.0) -> QPixmap:
        # 在设置了 DPR 的 pixmap 上，QPainter 使用逻辑坐标；
        # 物理分辨率由 pixmap 尺寸与 DPR 负责，绘制坐标一律用逻辑值。
        size = self.logical_size()
        phys = int(round(size * dpr))
        pm = QPixmap(phys, phys)
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        # 像素画要求最近邻缩放，保证锐利无混叠
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        p.drawPixmap(0, 0, size, size, self._source(expression))
        p.end()
        return pm

    def _source(self, expression: Expression) -> QPixmap:
        if expression not in self._cache:
            pm = QPixmap(str(_pictures_dir() / EXPRESSION_FILES[expression]))
            if pm.isNull():
                pm = QPixmap(GRID, GRID)
                pm.fill(Qt.transparent)
            self._cache[expression] = pm
        return self._cache[expression]
