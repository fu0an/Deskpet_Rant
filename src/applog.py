"""日志：输出到用户数据目录的 app.log，便于发布后定位问题。

异常路径保持"静默给用户、细节进日志"的策略，不打扰使用。
"""

import logging
from logging.handlers import RotatingFileHandler

from config import data_dir

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    root.setLevel(level)
    handler = RotatingFileHandler(
        data_dir() / "app.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
