"""Rant机 配置模块：读取/写入用户设置，以及服务商预设。"""

import json
import os
import sys
from pathlib import Path

APP_NAME = "DeskpetRant"


def data_dir() -> Path:
    """用户数据目录（设置、记忆、日志都放这里）。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


# 服务商预设。vision_model / chat_model 为 None 表示该服务商不支持对应能力。
PROVIDERS = {
    "zhipu": {
        "label": "智谱 GLM（推荐）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "vision_model": "glm-4v-flash",
        "chat_model": "glm-4-flash",
        "note": "免费额度大，一个 key 同时支持识别与聊天",
    },
    "qwen": {
        "label": "阿里云百炼 Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "vision_model": "qwen-vl-plus",
        "chat_model": "qwen-plus",
        "note": "需要阿里云账号开通百炼并创建 API key",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "vision_model": "gpt-4o-mini",
        "chat_model": "gpt-4o-mini",
        "note": "国内访问需要网络代理",
    },
    "moonshot": {
        "label": "Moonshot Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "vision_model": "moonshot-v1-8k-vision-preview",
        "chat_model": "moonshot-v1-8k",
        "note": "中文对话表现好",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "vision_model": None,
        "chat_model": "deepseek-chat",
        "note": "仅支持聊天，屏幕识别需搭配其它服务商",
    },
    "custom": {
        "label": "自定义（OpenAI 兼容）",
        "base_url": "",
        "vision_model": "",
        "chat_model": "",
        "note": "填任意 OpenAI 兼容接口",
    },
}

DEFAULTS = {
    "provider": "zhipu",
    "api_key": "",
    "custom_base_url": "",
    "custom_vision_model": "",
    "custom_chat_model": "",
    "pet_name": "Rant机",
    "observe_interval_minutes": 3,
    "comment_probability": 0.4,
    "auto_start": False,
    "eyes_open": True,
    "window_x": None,
    "window_y": None,
    "personality": "毒舌但礼貌，不说脏话，不暴躁，偶尔吐槽用户屏幕上的内容",
}


class Config:
    def __init__(self, path: Path | None = None):
        self.path = path or (data_dir() / "config.json")
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                for k, v in raw.items():
                    if k in DEFAULTS:
                        self.data[k] = v
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        if key in DEFAULTS:
            self.data[key] = value
        self.save()

    # --- 便捷访问 ---

    @property
    def provider(self) -> dict:
        return PROVIDERS.get(self.get("provider"), PROVIDERS["zhipu"])

    def base_url(self) -> str:
        if self.get("provider") == "custom":
            return self.get("custom_base_url", "").strip() or PROVIDERS["custom"]["base_url"]
        return self.provider["base_url"]

    def vision_model(self) -> str | None:
        if self.get("provider") == "custom":
            return self.get("custom_vision_model", "").strip() or None
        return self.provider["vision_model"]

    def chat_model(self) -> str | None:
        if self.get("provider") == "custom":
            return self.get("custom_chat_model", "").strip() or None
        return self.provider["chat_model"]
