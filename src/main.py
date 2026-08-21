"""DeskpetRant 入口：Rant机 桌宠。"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from chat.chat_engine import ChatEngine
from chat.main_dialog import PAGE_CHAT, PAGE_SETTINGS, MainDialog
from config import Config
from llm.client import LLMClient
from memory.store import MemoryStore
from pet.bubble import Bubble
from pet.expressions import EXPR_BY_NAME, ExpressionController
from pet.pet_window import PetWindow
from pet.sprite import Expression, SpriteRenderer
from vision.screen_observer import ScreenObserver
from sound import play as play_sound, set_enabled as set_sound_enabled


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DeskpetRant")
    app.setQuitOnLastWindowClosed(False)

    cfg = Config()
    store = MemoryStore()
    llm = LLMClient(cfg)
    engine = ChatEngine(cfg, llm, store)

    renderer = SpriteRenderer(cell=6)
    pet = PetWindow(renderer, eyes_open=bool(cfg.get("eyes_open", True)))
    if cfg.get("window_x") is not None and cfg.get("window_y") is not None:
        pet.move(int(cfg.get("window_x")), int(cfg.get("window_y")))

    dialog = MainDialog(cfg, engine, store, pet)
    observer = ScreenObserver(cfg, llm)
    bubble = Bubble()
    expressions = ExpressionController(pet)
    set_sound_enabled(bool(cfg.get("sound_enabled", True)))

    def apply_eyes(open_: bool) -> None:
        pet.set_eyes_open(open_)
        cfg.set("eyes_open", open_)
        dialog.update_status()
        if open_:
            observer.start()
        else:
            observer.stop()

    def toggle_eyes() -> None:
        apply_eyes(not pet.eyes_open)

    # --- 宠物窗口 ---
    pet.clicked.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    pet.chat_requested.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    pet.settings_requested.connect(lambda: dialog.open_dialog(PAGE_SETTINGS))
    pet.exit_requested.connect(app.quit)
    pet.toggle_eyes_requested.connect(toggle_eyes)

    # --- 对话框 ---
    dialog.eyes_toggled.connect(apply_eyes)
    dialog.memory_cleared.connect(store.clear_all)
    dialog.settings_saved.connect(observer.restart)

    def on_settings_saved() -> None:
        observer.restart()
        set_sound_enabled(bool(cfg.get("sound_enabled", True)))

    dialog.settings_saved.connect(on_settings_saved)

    def show_bubble(text: str, emotion: str) -> None:
        bubble.show_comment(text)
        bubble.anchor_above(pet.geometry().center(), pet.screen())
        expr = EXPR_BY_NAME.get(emotion, Expression.NORMAL)
        expressions.show(expr, 2500)
        play_sound(emotion)

    observer.comment_ready.connect(show_bubble)
    observer.fallback_ready.connect(show_bubble)

    def on_assistant_reply(text: str, emotion: str) -> None:
        expr = EXPR_BY_NAME.get(emotion, Expression.NORMAL)
        expressions.show(expr, 4000)
        play_sound(emotion)

    dialog.assistant_replied.connect(on_assistant_reply)

    if cfg.get("eyes_open", True):
        observer.start()

    # --- 托盘 ---
    tray_icon = QIcon(renderer.render(Expression.NORMAL, 1.0))
    tray = QSystemTrayIcon(tray_icon, app)
    tray.setToolTip("Rant机")
    tray_menu = QMenu()
    act_chat = QAction("对话", tray_menu)
    act_settings = QAction("设置", tray_menu)
    act_eyes = QAction("", tray_menu)
    act_exit = QAction("退出", tray_menu)

    def refresh_eyes_label() -> None:
        act_eyes.setText("闭眼" if pet.eyes_open else "睁眼")

    refresh_eyes_label()
    act_chat.triggered.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    act_settings.triggered.connect(lambda: dialog.open_dialog(PAGE_SETTINGS))
    act_eyes.triggered.connect(toggle_eyes)
    act_exit.triggered.connect(app.quit)
    tray_menu.addAction(act_chat)
    tray_menu.addAction(act_settings)
    tray_menu.addAction(act_eyes)
    tray_menu.addSeparator()
    tray_menu.addAction(act_exit)
    tray.setContextMenu(tray_menu)
    tray.activated.connect(
        lambda reason: (
            dialog.open_dialog(PAGE_CHAT) if reason == QSystemTrayIcon.Trigger else None
        )
    )
    tray.show()

    pet.show()

    # --- 退出清理 ---
    def on_quit() -> None:
        observer.stop()
        engine.summarizer.run()  # 退出时补一次记忆整理（尽力而为）
        cfg.set("window_x", pet.x())
        cfg.set("window_y", pet.y())
        store.close()

    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec())
    return 0


if __name__ == "__main__":
    main()
