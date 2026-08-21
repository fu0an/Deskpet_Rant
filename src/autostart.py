"""Windows 开机自启：写入 HKCU Run 键。"""

import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DeskpetRant"


def _startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pythonw = exe[:-len("python.exe")] + "pythonw.exe"
    if exe.lower().endswith("python.exe") and os.path.exists(pythonw):
        exe = pythonw
    script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "main.py")
    )
    return f'"{exe}" "{script}"'


def is_auto_start() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False


def set_auto_start(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except OSError:
                pass
