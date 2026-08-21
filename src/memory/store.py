"""本地记忆：SQLite 存对话历史与记忆要点。全部数据都在用户本地。"""

import sqlite3
import threading
import time

from config import data_dir


class MemoryStore:
    def __init__(self, db_path=None):
        self._lock = threading.Lock()
        # check_same_thread=False：聊天在后台线程读写，由 self._lock 串行保护
        self.conn = sqlite3.connect(
            str(db_path or (data_dir() / "memory.db")),
            check_same_thread=False,
        )
        self._init()

    def _init(self) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS conversations ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " ts REAL NOT NULL,"
                " role TEXT NOT NULL,"
                " content TEXT NOT NULL)"
            )
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_facts ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " ts REAL NOT NULL,"
                " content TEXT NOT NULL)"
            )
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS meta ("
                " key TEXT PRIMARY KEY,"
                " value INTEGER NOT NULL)"
            )

    # --- 内部 meta（整理进度等）---

    def _get_meta(self, key: str) -> int:
        cur = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def _set_meta(self, key: str, value: int) -> None:
        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    # --- 对话 ---

    def add_message(self, role: str, content: str) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT INTO conversations (ts, role, content) VALUES (?, ?, ?)",
                (time.time(), role, content),
            )

    def recent_messages(self, limit: int = 10) -> list[tuple[str, str]]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT role, content FROM conversations"
                " ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return [(r[0], r[1]) for r in reversed(rows)]

    def count_messages(self) -> int:
        with self._lock:
            cur = self.conn.execute("SELECT COUNT(*) FROM conversations")
            return int(cur.fetchone()[0])

    def clear_messages(self) -> None:
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM conversations")
            self._set_meta("last_summarized_id", 0)

    # --- 未整理对话（供记忆整理使用）---

    def unsummarized_count(self) -> int:
        with self._lock:
            last = self._get_meta("last_summarized_id")
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE id > ?", (last,)
            )
            return int(cur.fetchone()[0])

    def unsummarized_transcript(
        self, limit: int = 40
    ) -> tuple[list[tuple[str, str]], int]:
        """返回 (对话列表[(role, content)], 本次包含的最大消息 id)。"""
        with self._lock:
            last = self._get_meta("last_summarized_id")
            cur = self.conn.execute(
                "SELECT id, role, content FROM conversations"
                " WHERE id > ? ORDER BY id ASC LIMIT ?",
                (last, limit),
            )
            rows = cur.fetchall()
        items = [(r[1], r[2]) for r in rows]
        max_id = rows[-1][0] if rows else last
        return items, max_id

    def mark_summarized(self, up_to_id: int) -> None:
        with self._lock, self.conn:
            self._set_meta("last_summarized_id", up_to_id)

    # --- 记忆要点 ---

    def add_fact(self, content: str) -> None:
        content = content.strip()
        if not content:
            return
        with self._lock, self.conn:
            cur = self.conn.execute(
                "SELECT 1 FROM memory_facts WHERE content = ? LIMIT 1", (content,)
            )
            if cur.fetchone() is None:
                self.conn.execute(
                    "INSERT INTO memory_facts (ts, content) VALUES (?, ?)",
                    (time.time(), content),
                )

    def facts(self) -> list[str]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT content FROM memory_facts ORDER BY id"
            )
            return [r[0] for r in cur.fetchall()]

    def trim_facts(self, keep: int) -> None:
        """只保留最近 keep 条要点，删掉更早的。"""
        with self._lock, self.conn:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM memory_facts"
            )
            if int(cur.fetchone()[0]) <= keep:
                return
            self.conn.execute(
                "DELETE FROM memory_facts WHERE id IN ("
                " SELECT id FROM memory_facts ORDER BY id DESC LIMIT -1 OFFSET ?"
                ")",
                (keep,),
            )

    def clear_facts(self) -> None:
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM memory_facts")

    def clear_all(self) -> None:
        self.clear_messages()
        self.clear_facts()

    def close(self) -> None:
        with self._lock:
            self.conn.close()
