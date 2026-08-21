"""聊天引擎：把记忆 + 近期对话注入上下文，调 LLM 回复。

回复返回 (文本, 表情)：模型附带情绪标签，解析失败用关键词兜底。
新对话攒够阈值时自动触发记忆整理。
"""

from config import Config
from llm import prompts
from llm.client import LLMClient
from memory.store import MemoryStore
from memory.summarizer import Summarizer
from pet.expressions import split_emotion

SUMMARIZE_EVERY = 20  # 每攒够这么多条未整理对话就整理一次


class ChatEngine:
    def __init__(self, cfg: Config, llm: LLMClient, store: MemoryStore):
        self.cfg = cfg
        self.llm = llm
        self.store = store
        self.summarizer = Summarizer(cfg, llm, store)

    def _system(self) -> dict:
        return {
            "role": "system",
            "content": prompts.system_prompt(self.cfg, self.store.facts()),
        }

    def ask(self, user_text: str) -> tuple[str, str]:
        """返回 (回复文本, 情绪名 happy|normal|speechless)。"""
        self.store.add_message("user", user_text)
        messages = [self._system()]
        for role, content in self.store.recent_messages(10):
            messages.append({"role": role, "content": content})
        reply = self.llm.chat(messages)
        text, expr = split_emotion(reply)
        self.store.add_message("assistant", text)
        self._maybe_summarize()
        return text, expr.value

    def _maybe_summarize(self) -> None:
        if self.store.unsummarized_count() >= SUMMARIZE_EVERY:
            self.summarizer.run()
