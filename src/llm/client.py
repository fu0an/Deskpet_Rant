"""统一 OpenAI 兼容客户端：聊天 + 视觉识别。"""

import base64

from openai import OpenAI

from config import Config


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client: OpenAI | None = None

    def _ensure(self) -> OpenAI:
        key = self.cfg.get("api_key", "").strip()
        if not key:
            raise LLMError("还没有配置 API key，请先在设置里填入。")
        if self._client is None:
            self._client = OpenAI(
                api_key=key, base_url=self.cfg.base_url(), timeout=90
            )
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
            raise LLMError(f"屏幕识别调用失败：{e}") from e
        return self._content(resp)
