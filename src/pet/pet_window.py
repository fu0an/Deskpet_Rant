"""宠物主窗口：透明无边框置顶小方块，可拖动，右键菜单。

点击（无拖动）发出 clicked 信号，供外部弹出对话框。
"""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QCursor, QMouseEvent
from PySide6.QtWidgets import QMenu, QWidget

from .sprite import Expression, SpriteRenderer

MOVE_THRESHOLD = 4  # 超过此距离视为拖动而非点击


class PetWindow(QWidget):
    clicked = Signal()
    chat_requested = Signal()
    settings_requested = Signal()
    toggle_eyes_requested = Signal()
    exit_requested = Signal()

    def __init__(self, renderer: SpriteRenderer, eyes_open: bool = True):
        super().__init__()
        self.renderer = renderer
        self.expression = Expression.NORMAL if eyes_open else Expression.CLOSED
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._dragged = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(renderer.logical_size(), renderer.logical_size())
        self._render()

    def _render(self) -> None:
        self._pixmap = self.renderer.render(self.expression, self.devicePixelRatioF())
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtGui import QPainter

        p = QPainter(self)
        p.drawPixmap(0, 0, self.width(), self.height(), self._pixmap)
        p.end()

    def set_expression(self, expression: Expression) -> None:
        if self.expression is not expression:
            self.expression = expression
            self._render()

    @property
    def eyes_open(self) -> bool:
        return self.expression is not Expression.CLOSED

    def set_eyes_open(self, open_: bool) -> None:
        self.set_expression(Expression.NORMAL if open_ else Expression.CLOSED)

    # --- 拖动 & 点击 ---

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self._press_pos = event.globalPosition().toPoint()
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            if not self._dragged:
                delta = event.globalPosition().toPoint() - self._press_pos
                if delta.manhattanLength() > MOVE_THRESHOLD:
                    self._dragged = True
            if self._dragged:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            was_drag = self._dragged
            self._drag_offset = None
            self._press_pos = None
            if not was_drag:
                self.clicked.emit()
            event.accept()

    # --- 右键菜单 ---

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = QMenu(self)
        chat_act = QAction("对话", menu)
        settings_act = QAction("设置", menu)
        eyes_act = QAction("闭眼" if self.eyes_open else "睁眼", menu)
        exit_act = QAction("退出", menu)

        menu.addAction(chat_act)
        menu.addAction(settings_act)
        menu.addAction(eyes_act)
        menu.addSeparator()
        menu.addAction(exit_act)

        chosen = menu.exec(QCursor.pos())
        if chosen is chat_act:
            self.chat_requested.emit()
        elif chosen is settings_act:
            self.settings_requested.emit()
        elif chosen is eyes_act:
            self.toggle_eyes_requested.emit()
        elif chosen is exit_act:
            self.exit_requested.emit()
        event.accept()
