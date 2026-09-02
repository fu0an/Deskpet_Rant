"""单实例守卫：确保同一时间只有一个 Rant机 在运行。

基于 QLocalServer/QLocalSocket：后启动的实例探测到已有实例后自动退出，
并通知已有实例把自己唤起到前台（方便用户重新点开 exe 找回宠物）。
Windows 下 QLocalServer 的名字空间按用户隔离，不同用户互不干扰。
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

KEY = "DeskpetRant-SingleInstance"


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, key: str = KEY, parent=None):
        super().__init__(parent)
        self._key = key
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        """尝试成为唯一实例。成功返回 True；已存在其它实例返回 False。"""
        probe = QLocalSocket(self)
        probe.connectToServer(self._key)
        if probe.waitForConnected(400):
            probe.disconnectFromServer()
            return False  # 已有实例在运行
        probe.abort()

        # 清理上次异常退出可能残留的句柄（Unix socket 场景必需）
        QLocalServer.removeServer(self._key)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(self._key):
            return False  # 窗口期竞争，当作已有实例处理
        return True

    def _on_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn is not None:
            conn.disconnected.connect(conn.deleteLater)
            self.activated.emit()
