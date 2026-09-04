"""吐槽气泡：宠物附近的浮动文本，过一段时间自动淡出消失。

点击气泡不会只是关闭：会把这条内容带出去（reply_requested），由外部决定
是否打开对话框引用它继续聊。
"""

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

BUBBLE_MAX_WIDTH = 260


class Bubble(QWidget):
    dismissed = Signal()
    reply_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._label = QLabel(self)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "color:#eceff4; font-size:13px;"
            "background:transparent; padding:0px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.addWidget(self._label)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self._label.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(400)
        self._fade.finished.connect(self._hide_now)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade)
        self._dismissed = False
        self._text = ""

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 10
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, Qt.darkGray)
        p.setPen(QPen(Qt.lightGray, 1))
        p.drawPath(path)
        p.end()

    def show_comment(self, text: str, duration_ms: int = 6000) -> None:
        self._dismissed = False
        self._text = text
        self._opacity.setOpacity(1.0)
        self._label.setText(text)
        self._label.adjustSize()
        width = min(BUBBLE_MAX_WIDTH, max(120, self._label.width() + 28))
        self.resize(width, self.sizeHint().height())
        self.adjustSize()
        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def anchor_above(self, global_pos: QPoint, screen) -> None:
        """把气泡放在目标点上方，自动限制在屏幕内。"""
        self.adjustSize()
        geo = screen.availableGeometry() if screen else None
        x, y = global_pos.x(), global_pos.y()
        w, h = self.width(), self.height()
        x -= w // 2
        y -= h + 8
        if geo is not None:
            x = max(geo.left(), min(x, geo.right() - w))
            y = max(geo.top(), min(y, geo.bottom() - h))
        self.move(x, y)

    def _start_fade(self) -> None:
        if self._dismissed:
            return
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _hide_now(self) -> None:
        self.hide()
        if not self._dismissed:
            self._dismissed = True
            self.dismissed.emit()

    def mousePressEvent(self, event):  # noqa: N802
        self.hide()
        if not self._dismissed:
            self._dismissed = True
            self.dismissed.emit()
        self.reply_requested.emit(self._text)
        event.accept()
