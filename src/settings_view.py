"""设置面板：服务商/API key/识别间隔/自启/闭眼/清空记忆。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import autostart
from config import Config, PROVIDERS
from memory.store import MemoryStore


class SettingsView(QWidget):
    eyes_toggled = Signal(bool)
    memory_cleared = Signal()
    saved = Signal()

    def __init__(self, cfg: Config, store: MemoryStore, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.store = store
        self._build()
        self.load()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setSpacing(10)

        # 服务商
        self.provider_combo = QComboBox()
        for key, p in PROVIDERS.items():
            self.provider_combo.addItem(p["label"], key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # API key
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("粘贴 API key")
        self.key_note = QLabel()
        self.key_note.setWordWrap(True)
        self.key_note.setStyleSheet("color:#8a93a5; font-size:12px;")

        # 自定义接口（仅自定义服务商时显示）
        self.custom_box = QGroupBox("自定义接口")
        cf = QFormLayout(self.custom_box)
        self.custom_base = QLineEdit()
        self.custom_vision = QLineEdit()
        self.custom_chat = QLineEdit()
        cf.addRow("Base URL", self.custom_base)
        cf.addRow("视觉模型", self.custom_vision)
        cf.addRow("聊天模型", self.custom_chat)

        form.addRow("服务商", self.provider_combo)
        form.addRow("API Key", self.api_key)
        form.addRow(self.key_note)
        form.addRow(self.custom_box)

        # 识别
        self.interval = QSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setSuffix(" 分钟")
        self.probability = QSpinBox()
        self.probability.setRange(0, 100)
        self.probability.setSuffix(" %")
        self.probability.setToolTip("每次到时有多少概率真的调用模型吐槽")

        self.eyes = QCheckBox("开启屏幕识别（睁眼）")
        self.eyes.toggled.connect(self.eyes_toggled)

        form.addRow("识别间隔", self.interval)
        form.addRow("吐槽概率", self.probability)
        form.addRow(self.eyes)

        # 通用
        self.auto_start = QCheckBox("开机自启")
        self.pet_name = QLineEdit()
        self.personality = QPlainTextEdit()
        self.personality.setFixedHeight(70)
        form.addRow("开机自启", self.auto_start)
        form.addRow("宠物名字", self.pet_name)
        form.addRow("性格要求", self.personality)

        outer.addLayout(form)

        # 危险区
        clear_btn = QPushButton("清空全部记忆")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._on_clear_memory)
        outer.addWidget(clear_btn)

        priv = QLabel(
            "隐私说明：屏幕识别会把截图发送给你选择的 API 服务商；"
            "「闭眼」后彻底停止截屏。聊天与记忆都保存在本机。"
        )
        priv.setWordWrap(True)
        priv.setStyleSheet("color:#8a93a5; font-size:12px;")
        outer.addWidget(priv)
        outer.addStretch(1)

        btns = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.save)
        btns.addStretch(1)
        btns.addWidget(save_btn)
        outer.addLayout(btns)

    # --- 视图逻辑 ---

    def _on_provider_changed(self) -> None:
        is_custom = self.provider_combo.currentData() == "custom"
        self.custom_box.setVisible(is_custom)
        key = self.provider_combo.currentData()
        self.key_note.setText(PROVIDERS[key]["note"])

    def load(self) -> None:
        idx = self.provider_combo.findData(self.cfg.get("provider", "zhipu"))
        self.provider_combo.setCurrentIndex(max(0, idx))
        self._on_provider_changed()
        self.api_key.setText(self.cfg.get("api_key", ""))
        self.custom_base.setText(self.cfg.get("custom_base_url", ""))
        self.custom_vision.setText(self.cfg.get("custom_vision_model", ""))
        self.custom_chat.setText(self.cfg.get("custom_chat_model", ""))
        self.interval.setValue(int(self.cfg.get("observe_interval_minutes", 3)))
        self.probability.setValue(
            int(round(float(self.cfg.get("comment_probability", 0.4)) * 100))
        )
        self.eyes.setChecked(bool(self.cfg.get("eyes_open", True)))
        self.auto_start.setChecked(autostart.is_auto_start())
        self.pet_name.setText(self.cfg.get("pet_name", "Rant机"))
        self.personality.setPlainText(
            self.cfg.get(
                "personality",
                "毒舌但礼貌，不说脏话，不暴躁，偶尔吐槽用户屏幕上的内容",
            )
        )

    def save(self) -> None:
        self.cfg.set("provider", self.provider_combo.currentData())
        self.cfg.set("api_key", self.api_key.text().strip())
        self.cfg.set("custom_base_url", self.custom_base.text().strip())
        self.cfg.set("custom_vision_model", self.custom_vision.text().strip())
        self.cfg.set("custom_chat_model", self.custom_chat.text().strip())
        self.cfg.set("observe_interval_minutes", self.interval.value())
        self.cfg.set("comment_probability", self.probability.value() / 100.0)
        self.cfg.set("eyes_open", self.eyes.isChecked())
        self.cfg.set("pet_name", self.pet_name.text().strip() or "Rant机")
        self.cfg.set("personality", self.personality.toPlainText().strip())

        try:
            autostart.set_auto_start(self.auto_start.isChecked())
        except OSError as e:
            QMessageBox.warning(self, "开机自启", f"设置开机自启失败：{e}")

        self.saved.emit()

    def _on_clear_memory(self) -> None:
        if (
            QMessageBox.question(
                self,
                "清空记忆",
                "确定要清空全部对话记录和记忆要点吗？此操作不可恢复。",
            )
            == QMessageBox.Yes
        ):
            self.store.clear_all()
            self.memory_cleared.emit()
