"""主对话框：贴着宠物弹出，左侧齿轮工具栏，聊天/设置双视图。"""

import html
import threading

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import Config
from llm.client import LLMError
from memory.store import MemoryStore
from pet.pet_window import PetWindow
from settings_view import SettingsView

PAGE_CHAT = 0
PAGE_SETTINGS = 1

STYLE = """
#card {
    background: #23262e;
    border: 1px solid #3a4150;
    border-radius: 12px;
}
QToolButton { background: transparent; border: none; border-radius: 8px;
              color: #a9b1c2; font-size: 16px; }
QToolButton:hover { background: #2f3542; }
QToolButton:checked { background: #2f3542; color: #eceff4; }
QToolButton#closeButton:hover { background: #b33; color: white; }
#header { color: #eceff4; font-size: 13px; font-weight: bold; }
#status { color: #8a93a5; font-size: 11px; }
QTextBrowser { background: transparent; border: none; color: #eceff4;
               font-size: 13px; }
QTextBrowser::viewport { background: transparent; }
#chatInput { background: #2f3542; border: 1px solid #3a4150; border-radius: 8px;
             color: #eceff4; padding: 6px 10px; }
#sendButton { background: #3b82f6; border: none; border-radius: 8px;
              color: white; padding: 6px 14px; }
#sendButton:disabled { background: #475569; }
"""


class ChatView(QWidget):
    reply_ready = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._busy = False
        self._build()

    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        self.status = QLabel("")
        v.addWidget(self.status)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        self.view.document().setDefaultStyleSheet(
            "p{margin:2px 0;} span.b{margin:2px 0;}"
        )
        self.view.setMinimumHeight(200)
        v.addWidget(self.view, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        v.addLayout(row)

        self.reply_ready.connect(self._on_reply)

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def _bubble(self, text: str, mine: bool) -> str:
        color = "#3b82f6" if mine else "#3a4150"
        align = "right" if mine else "left"
        t = html.escape(text).replace("\n", "<br>")
        return (
            f'<p style="text-align:{align}"><span style="background:{color};'
            f'border-radius:10px;padding:6px 10px;display:inline-block;'
            f'max-width:240px;word-wrap:break-word;">{t}</span></p>'
        )

    def append_user(self, text: str) -> None:
        self.view.append(self._bubble(text, mine=True))

    def append_assistant(self, text: str) -> None:
        self.view.append(self._bubble(text, mine=False))

    def send(self) -> None:
        text = self.input.text().strip()
        if not text or self._busy:
            return
        self.append_user(text)
        self.input.clear()
        self._set_busy(True)
        threading.Thread(target=self._work, args=(text,), daemon=True).start()

    def _work(self, text: str) -> None:
        try:
            reply = self.engine.ask(text)
        except LLMError as e:
            reply = str(e)
        except Exception as e:  # noqa: BLE001
            reply = f"（出错啦：{e}）"
        self.reply_ready.emit(reply)

    def _on_reply(self, reply: str) -> None:
        self.append_assistant(reply)
        self._set_busy(False)
        self.input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_btn.setDisabled(busy)
        self.input.setDisabled(busy)
        if not busy:
            self.input.setFocus()


class MainDialog(QWidget):
    eyes_toggled = Signal(bool)
    memory_cleared = Signal()
    settings_saved = Signal()

    def __init__(
        self,
        cfg: Config,
        engine,
        store: MemoryStore,
        pet: PetWindow,
        parent=None,
    ):
        super().__init__(parent)
        self.cfg = cfg
        self.engine = engine
        self.store = store
        self.pet = pet

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(STYLE)

        self._build_ui()
        self.pet.installEventFilter(self)

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)

        self.card = QWidget()
        self.card.setObjectName("card")
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(8)

        # 左侧工具栏：齿轮 + 关闭
        toolbar = QVBoxLayout()
        toolbar.setSpacing(4)

        self.gear_btn = QToolButton()
        self.gear_btn.setText("\u2699")
        self.gear_btn.setCheckable(True)
        self.gear_btn.setFixedSize(34, 34)
        self.gear_btn.setToolTip("设置")
        self.gear_btn.toggled.connect(self._on_gear)

        toolbar.addWidget(self.gear_btn)
        toolbar.addStretch(1)

        close_btn = QToolButton()
        close_btn.setObjectName("closeButton")
        close_btn.setText("\u2715")
        close_btn.setFixedSize(34, 34)
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close_dialog)

        toolbar.addWidget(close_btn)
        card_layout.addLayout(toolbar)

        # 内容：聊天 / 设置
        self.stacked = QStackedWidget()

        self.chat_view = ChatView(self.engine)
        self.chat_view.set_status(self._status_text())
        self.stacked.addWidget(self.chat_view)

        self.settings_view = SettingsView(self.cfg, self.store)
        self.settings_view.eyes_toggled.connect(self.eyes_toggled)
        self.settings_view.memory_cleared.connect(self.memory_cleared)
        self.settings_view.saved.connect(self._on_settings_saved)
        self.settings_view.saved.connect(self.settings_saved)
        self.stacked.addWidget(self.settings_view)

        card_layout.addWidget(self.stacked, 1)
        outer.addWidget(self.card)

        self.resize(380, 460)

    def _status_text(self) -> str:
        state = "识别中" if self.cfg.get("eyes_open", True) else "闭眼中"
        return f"{self.cfg.get('pet_name', 'Rant机')} · {state}"

    def update_status(self) -> None:
        self.chat_view.set_status(self._status_text())

    def _on_settings_saved(self) -> None:
        self.update_status()

    def _on_gear(self, checked: bool) -> None:
        self.stacked.setCurrentIndex(PAGE_SETTINGS if checked else PAGE_CHAT)
        if not checked:
            self.chat_view.set_status(self._status_text())
            self.chat_view.input.setFocus()

    # --- 显示与定位 ---

    def open_dialog(self, page: int = PAGE_CHAT) -> None:
        self.gear_btn.setChecked(page == PAGE_SETTINGS)
        self.stacked.setCurrentIndex(page)
        self._anchor()
        self.show()
        self.raise_()
        self.activateWindow()
        if page == PAGE_CHAT:
            self.chat_view.input.setFocus()

    def close_dialog(self) -> None:
        self.hide()
        if self.gear_btn.isChecked():
            self.gear_btn.setChecked(False)

    def _anchor(self) -> None:
        pet_geo = self.pet.geometry()
        screen = self.pet.screen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        w, h = self.width(), self.height()

        x = pet_geo.left()
        y = pet_geo.bottom() + 10
        if y + h > avail.bottom():
            y = pet_geo.top() - h - 10

        x = max(avail.left(), min(x, avail.right() - w))
        y = max(avail.top(), min(y, avail.bottom() - h))
        self.move(x, y)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.pet and event.type() == QEvent.Move and self.isVisible():
            self._anchor()
        return super().eventFilter(obj, event)

    def focusOutEvent(self, event):  # noqa: N802
        # 点击对话框或宠物之外的地方时自动收起
        fw = QApplication.focusWidget()
        if fw is not self and (fw is None or not self.isAncestorOf(fw)):
            self.close_dialog()
        super().focusOutEvent(event)
