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

    # --- 记忆要点 ---

    def add_fact(self, content: str) -> None:
        with self._lock, self.conn:
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

    def clear_facts(self) -> None:
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM memory_facts")

    def clear_all(self) -> None:
        self.clear_messages()
        self.clear_facts()

    def close(self) -> None:
        with self._lock:
            self.conn.close()
