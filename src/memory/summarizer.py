"""记忆整理：把新对话压缩成记忆要点，写入 memory_facts。

- 只处理自上次整理以来的新对话；
- store 侧精确去重，并保留最近 MAX_FACTS 条；
- 失败时静默跳过，等下次再触发。
"""

import threading

from config import Config
from llm import prompts
from llm.client import LLMClient
from memory.store import MemoryStore

MAX_FACTS = 30


class Summarizer:
    def __init__(self, cfg: Config, llm: LLMClient, store: MemoryStore):
        self.cfg = cfg
        self.llm = llm
        self.store = store
        self._running = False
        self._lock = threading.Lock()

    def run(self, max_messages: int = 40) -> bool:
        """整理未整理的对话。确实整理了返回 True。"""
        with self._lock:
            if self._running:
                return False
            self._running = True
        try:
            items, up_to_id = self.store.unsummarized_transcript(max_messages)
            if not items:
                return False
            lines = [f"{'用户' if r == 'user' else '宠物'}：{c}" for r, c in items]
            prompt = prompts.summarize_prompt(self.cfg, "\n".join(lines))
            raw = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=300,
            )
            if raw:
                for line in raw.splitlines():
                    self.store.add_fact(line.strip("-•* "))
            self.store.mark_summarized(up_to_id)
            self.store.trim_facts(MAX_FACTS)
            return True
        except Exception:  # noqa: BLE001 失败静默跳过，下次再触发
            return False
        finally:
            with self._lock:
                self._running = False
