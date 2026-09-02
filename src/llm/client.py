"""统一 OpenAI 兼容客户端：聊天 + 视觉识别。"""

import base64
import logging

from openai import APIStatusError, OpenAI

from config import Config

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class ContentBlocked(LLMError):
    """请求被服务商的内容审核拦截（画面/文本含不当内容）。"""


# 常见内容审核拦截特征：服务商返回 400/403，或错误信息含这些词。
_BLOCKED_HINTS = (
    "content",
    "filter",
    "moderation",
    "sensitive",
    "safety",
    "审核",
    "敏感",
    "违规",
    "合规",
    "不合规",
)


def _is_content_blocked(exc: Exception) -> bool:
    if isinstance(exc, ContentBlocked):
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(exc, APIStatusError) and status in (400, 403):
        return True
    lowered = str(exc).lower()
    return any(h in lowered for h in _BLOCKED_HINTS)


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client: OpenAI | None = None
        self._fp: str | None = None  # (api_key, base_url) 指纹，变了就重建

    def reset(self) -> None:
        """丢弃缓存的客户端，下次调用按新配置重建（切换服务商/key 后调用）。"""
        self._client = None
        self._fp = None

    def _ensure(self) -> OpenAI:
        key = self.cfg.get("api_key", "").strip()
        if not key:
            raise LLMError("还没有配置 API key，请先在设置里填入。")
        base_url = self.cfg.base_url()
        fp = f"{key}\x1f{base_url}"
        if self._client is None or self._fp != fp:
            log.info("重建 OpenAI 客户端：base_url=%s", base_url)
            self._client = OpenAI(api_key=key, base_url=base_url, timeout=90)
            self._fp = fp
        return self._client

    @staticmethod
    def _content(resp) -> str:
        try:
            return (resp.choices[0].message.content or "").strip()
        except (IndexError, AttributeError) as e:
            raise LLMError(f"模型返回异常：{e}") from e

    def chat(self, messages, *, temperature=0.85, max_tokens=400) -> str:
        client = self._ensure()
        model = self.cfg.chat_model()
        if not model:
            raise LLMError("当前服务商不支持聊天。")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("聊天接口异常：%s", e)
            if _is_content_blocked(e):
                raise ContentBlocked("内容被服务商审核拦截，换个说法再试试。") from e
            raise LLMError(f"聊天接口调用失败：{e}") from e
        return self._content(resp)

    def vision_chat(
        self, text: str, jpeg_bytes: bytes, *, temperature=0.9, max_tokens=200
    ) -> str:
        client = self._ensure()
        model = self.cfg.vision_model()
        if not model:
            raise LLMError("当前服务商不支持屏幕识别。")
        b64 = base64.b64encode(jpeg_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ]
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("屏幕识别异常：%s", e)
            if _is_content_blocked(e):
                raise ContentBlocked("画面内容被服务商审核拦截。") from e
            raise LLMError(f"屏幕识别调用失败：{e}") from e
        return self._content(resp)
