"""聊天引擎：把记忆 + 近期对话注入上下文，调 LLM 回复。"""

from config import Config
from llm import prompts
from llm.client import LLMClient
from memory.store import MemoryStore


class ChatEngine:
    def __init__(self, cfg: Config, llm: LLMClient, store: MemoryStore):
        self.cfg = cfg
        self.llm = llm
        self.store = store

    def _system(self) -> dict:
        return {
            "role": "system",
            "content": prompts.system_prompt(self.cfg, self.store.facts()),
        }

    def ask(self, user_text: str) -> str:
        self.store.add_message("user", user_text)
        messages = [self._system()]
        for role, content in self.store.recent_messages(10):
            messages.append({"role": role, "content": content})
        reply = self.llm.chat(messages)
        self.store.add_message("assistant", reply)
        return reply
