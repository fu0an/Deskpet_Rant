"""宠物主窗口：透明无边框置顶小方块，可拖动，右键菜单。

- 点击（无拖动）发出 clicked 信号，供外部弹出对话框；
- 长按（无拖动）约 POKE_HOLD_MS 发出 poke（摸头/戳它）；
- 拖动时快速来回（时间窗内方向反转够多）发出 shaken（被晃）；
- 眼睛状态（_eyes_open）与当前表情解耦：烦躁等表情可短暂“睁眼”不改变闭眼语义。
"""

import time

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCursor, QMouseEvent
from PySide6.QtWidgets import QMenu, QWidget

from .sprite import Expression, SpriteRenderer

MOVE_THRESHOLD = 4      # 超过此距离视为拖动而非点击
POKE_HOLD_MS = 550      # 按住这么久且没拖动 = 戳它
SHAKE_WINDOW_S = 0.6    # 晃动判定时间窗（秒）
SHAKE_REFS_MS = 80      # 采样“参考点”的最小时间差（毫秒）
SHAKE_FLIPS = 6         # 时间窗内方向反转几次算“晃来晃去”
SHAKE_MIN_STEP = 3      # 参考位移小于此像素忽略


class PetWindow(QWidget):
    clicked = Signal()
    chat_requested = Signal()
    settings_requested = Signal()
    toggle_eyes_requested = Signal()
    exit_requested = Signal()
    talk_requested = Signal()  # “再说一句”
    poke = Signal()            # 长按戳它
    shaken = Signal()          # 快速来回拖动

    def __init__(self, renderer: SpriteRenderer, eyes_open: bool = True):
        super().__init__()
        self.renderer = renderer
        self._eyes_open = bool(eyes_open)
        self.expression = (
            Expression.NORMAL if self._eyes_open else Expression.CLOSED
        )
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._dragged = False
        self._held = False

        self._shake_samples: list[tuple[float, int, int]] = []
        self._shake_dir: int | None = None
        self._shake_flips = 0
        self._shake_fired = False

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold)

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
        return self._eyes_open

    def set_eyes_open(self, open_: bool) -> None:
        self._eyes_open = bool(open_)
        self.set_expression(
            Expression.NORMAL if self._eyes_open else Expression.CLOSED
        )

    # --- 拖动 / 点击 / 长按 / 晃动 ---

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self._press_pos = event.globalPosition().toPoint()
            self._dragged = False
            self._held = False
            self._reset_shake()
            self._hold_timer.start(POKE_HOLD_MS)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            if not self._dragged:
                delta = event.globalPosition().toPoint() - self._press_pos
                if delta.manhattanLength() > MOVE_THRESHOLD:
                    self._dragged = True
                    self._hold_timer.stop()
            if self._dragged:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                self._track_shake(event.globalPosition().toPoint())
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            was_drag = self._dragged
            was_held = self._held
            self._drag_offset = None
            self._press_pos = None
            self._hold_timer.stop()
            if not (was_drag or was_held):
                self.clicked.emit()
            self._reset_shake()
            event.accept()

    def _on_hold(self) -> None:
        if not self._dragged:
            self._held = True
            self.poke.emit()

    def _reset_shake(self) -> None:
        self._shake_samples.clear()
        self._shake_dir = None
        self._shake_flips = 0
        self._shake_fired = False

    def _track_shake(self, point: QPoint) -> None:
        now = time.monotonic()
        self._shake_samples.append((now, point.x(), point.y()))
        cutoff = now - SHAKE_WINDOW_S
        while self._shake_samples and self._shake_samples[0][0] < cutoff:
            self._shake_samples.pop(0)

        ref = None
        for i in range(len(self._shake_samples) - 2, -1, -1):
            t = self._shake_samples[i][0]
            if now - t >= SHAKE_REFS_MS / 1000.0:
                ref = self._shake_samples[i]
                break
        if ref is None:
            self._shake_dir = None
            return

        dx = point.x() - ref[1]
        dy = point.y() - ref[2]
        if abs(dx) + abs(dy) < SHAKE_MIN_STEP:
            self._shake_dir = None
            return
        if abs(dx) >= abs(dy):
            s = 1 if dx > 0 else -1
        else:
            s = 1 if dy > 0 else -1
        if self._shake_dir is not None and s != self._shake_dir:
            self._shake_flips += 1
            if self._shake_flips >= SHAKE_FLIPS and not self._shake_fired:
                self._shake_fired = True
                self.shaken.emit()
        self._shake_dir = s

    # --- 右键菜单 ---

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = QMenu(self)
        chat_act = QAction("对话", menu)
        talk_act = QAction("再说一句", menu)
        settings_act = QAction("设置", menu)
        eyes_act = QAction("闭眼" if self.eyes_open else "睁眼", menu)
        exit_act = QAction("退出", menu)

        menu.addAction(chat_act)
        menu.addAction(talk_act)
        menu.addAction(settings_act)
        menu.addAction(eyes_act)
        menu.addSeparator()
        menu.addAction(exit_act)

        chosen = menu.exec(QCursor.pos())
        if chosen is chat_act:
            self.chat_requested.emit()
        elif chosen is talk_act:
            self.talk_requested.emit()
        elif chosen is settings_act:
            self.settings_requested.emit()
        elif chosen is eyes_act:
            self.toggle_eyes_requested.emit()
        elif chosen is exit_act:
            self.exit_requested.emit()
        event.accept()
