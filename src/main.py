"""DeskpetRant 入口：Rant机 桌宠。"""

import random
import sys
import threading
import time

import applog
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
from single_instance import SingleInstance
from vision.screen_observer import ScreenObserver
from sound import play as play_sound, set_enabled as set_sound_enabled

# --- 互动相关常量 ---
EYE_TOGGLE_WINDOW_S = 4.0   # 睁/闭眼拨弄判定时间窗（秒）
EYE_TOGGLE_THRESHOLD = 3    # 时间窗内睁闭眼次数达到即烦躁
ANNOY_COOLDOWN_S = 8.0      # 烦躁反应冷却（秒）
ANNOY_LINE = "到底要怎样啦！"
POKE_COOLDOWN_S = 4.0       # 戳一戳冷却（秒）
POKE_LINES = [
    "别戳啦，痒～",
    "嘿嘿，干嘛啦",
    "再戳我要咬人了哦。",
    "呜……我只是个小方块。",
]
SLEEPY_POKE_LINES = [
    "呼……（睡得正香）",
    "ZZZ……别闹。",
    "唔……还没睡醒……",
]
TALK_NOW_LINES = [
    "（此刻没什么好吐槽的）",
    "我在呢，你说～",
    "屏幕太无聊了，我先躺会儿。",
]


def main() -> int:
    applog.setup_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DeskpetRant")
    app.setQuitOnLastWindowClosed(False)

    guard = SingleInstance()
    if not guard.try_acquire():
        return 0  # 已有实例在运行，直接退出

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

    # --- 互动状态 ---
    _annoy_until = 0.0
    _poke_until = 0.0
    _eye_toggles: list[float] = []

    def apply_eyes(open_: bool) -> None:
        pet.set_eyes_open(open_)
        cfg.set("eyes_open", open_)
        dialog.update_status()
        if open_:
            observer.start()
        else:
            observer.stop()
        now = time.monotonic()
        _eye_toggles.append(now)
        _eye_toggles[:] = [
            t for t in _eye_toggles if now - t <= EYE_TOGGLE_WINDOW_S
        ]
        if len(_eye_toggles) >= EYE_TOGGLE_THRESHOLD:
            _eye_toggles.clear()
            trigger_annoyed()

    def toggle_eyes() -> None:
        apply_eyes(not pet.eyes_open)

    def trigger_annoyed() -> None:
        """被反复拨弄：烦躁脸 + 「到底要怎样啦！」（有冷却防刷）。"""
        nonlocal _annoy_until
        now = time.monotonic()
        if now < _annoy_until:
            return
        _annoy_until = now + ANNOY_COOLDOWN_S
        bubble.show_comment(ANNOY_LINE, 4000)
        bubble.anchor_above(pet.geometry().center(), pet.screen())
        expressions.show_annoyed(2800)
        play_sound("annoyed")

    def on_poke() -> None:
        """长按戳它：清醒就撒娇，闭眼就嘟囔睡话（有冷却）。"""
        nonlocal _poke_until
        now = time.monotonic()
        if now < _poke_until:
            return
        _poke_until = now + POKE_COOLDOWN_S
        bubble.show_comment(
            random.choice(POKE_LINES if pet.eyes_open else SLEEPY_POKE_LINES),
            3000,
        )
        bubble.anchor_above(pet.geometry().center(), pet.screen())
        if pet.eyes_open:
            expressions.show(Expression.HAPPY, 1800)
            play_sound("happy")

    def action_talk_now() -> None:
        """再说一句：能截屏就立刻截屏吐槽，否则本地来一句。"""
        if not observer.observe_now():
            bubble.show_comment(random.choice(TALK_NOW_LINES), 3000)
            bubble.anchor_above(pet.geometry().center(), pet.screen())
            if pet.eyes_open:
                expressions.show(Expression.PUZZLED, 1500)

    def show_comment(text: str, emotion: str, archive: bool) -> None:
        bubble.show_comment(text)
        bubble.anchor_above(pet.geometry().center(), pet.screen())
        expr = EXPR_BY_NAME.get(emotion, Expression.NORMAL)
        expressions.show(expr, 2500)
        play_sound(emotion)
        if archive:
            dialog.chat_view.append_taunt(text)

    def on_bubble_reply(text: str) -> None:
        dialog.open_dialog(PAGE_CHAT)
        dialog.begin_quoted_reply(text)

    # --- 宠物窗口 ---
    pet.clicked.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    pet.chat_requested.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    pet.settings_requested.connect(lambda: dialog.open_dialog(PAGE_SETTINGS))
    pet.exit_requested.connect(app.quit)
    pet.toggle_eyes_requested.connect(toggle_eyes)
    pet.talk_requested.connect(action_talk_now)
    pet.poke.connect(on_poke)
    pet.shaken.connect(trigger_annoyed)

    # --- 对话框 ---
    dialog.eyes_toggled.connect(apply_eyes)
    dialog.memory_cleared.connect(store.clear_all)
    dialog.settings_saved.connect(observer.restart)

    def on_settings_saved() -> None:
        llm.reset()  # 切换服务商/API key 后丢弃旧客户端
        observer.restart()
        set_sound_enabled(bool(cfg.get("sound_enabled", True)))

    dialog.settings_saved.connect(on_settings_saved)

    def show_bubble(text: str, emotion: str) -> None:
        show_comment(text, emotion, archive=True)

    observer.comment_ready.connect(show_bubble)
    observer.fallback_ready.connect(
        lambda text, emotion: show_comment(text, emotion, archive=False)
    )

    def on_assistant_reply(text: str, emotion: str) -> None:
        expr = EXPR_BY_NAME.get(emotion, Expression.NORMAL)
        expressions.show(expr, 4000)
        play_sound(emotion)

    dialog.assistant_replied.connect(on_assistant_reply)

    bubble.reply_requested.connect(on_bubble_reply)

    expressions.start_blinking()

    if cfg.get("eyes_open", True):
        observer.start()

    # --- 托盘 ---
    tray_icon = QIcon(renderer.render(Expression.NORMAL, 1.0))
    tray = QSystemTrayIcon(tray_icon, app)
    tray.setToolTip("Rant机")
    tray_menu = QMenu()
    act_chat = QAction("对话", tray_menu)
    act_talk = QAction("再说一句", tray_menu)
    act_settings = QAction("设置", tray_menu)
    act_eyes = QAction("", tray_menu)
    act_exit = QAction("退出", tray_menu)

    def refresh_eyes_label() -> None:
        act_eyes.setText("闭眼" if pet.eyes_open else "睁眼")

    refresh_eyes_label()
    act_chat.triggered.connect(lambda: dialog.open_dialog(PAGE_CHAT))
    act_talk.triggered.connect(action_talk_now)
    act_settings.triggered.connect(lambda: dialog.open_dialog(PAGE_SETTINGS))
    act_eyes.triggered.connect(toggle_eyes)
    act_exit.triggered.connect(app.quit)
    tray_menu.addAction(act_chat)
    tray_menu.addAction(act_talk)
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

    # 再次启动程序时，把已有实例唤起到前台而不是再开一个
    def show_primary() -> None:
        pet.show()
        pet.raise_()
        pet.activateWindow()

    guard.activated.connect(show_primary)

    pet.show()

    # --- 退出清理 ---
    def on_quit() -> None:
        observer.stop()
        # 退出时补一次记忆整理：后台线程做，最多等 2 秒，不阻塞退出
        t = threading.Thread(target=engine.summarizer.run, daemon=True)
        t.start()
        t.join(timeout=2.0)
        cfg.set("window_x", pet.x())
        cfg.set("window_y", pet.y())
        store.close()

    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec())
    return 0


if __name__ == "__main__":
    main()
