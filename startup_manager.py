"""
startup_manager.py — Windows startup toggle
Strategy: Task Scheduler (primary) → Registry fallback
- Task Scheduler: chạy sau login 10s, không bị Group Policy block
- Registry HKCU\\Run: fallback nếu schtasks không available
"""
import subprocess
import sys
import winreg
from pathlib import Path

APP_NAME = "LightOnOCR"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
TASK_DELAY = "PT10S"  # 10 giây sau login


# ── Helpers ────────────────────────────────────────────────────

def _get_exe_path() -> str:
  if getattr(sys, "frozen", False):
    return sys.executable
  pythonw = Path(sys.executable).parent / "pythonw.exe"
  script = Path(__file__).parent / "main.py"
  return f'"{pythonw}" "{script}"'


def _schtasks(*args: str) -> subprocess.CompletedProcess:
  return subprocess.run(
    ["schtasks", *args],
    capture_output=True, text=True, creationflags=0x08000000,  # CREATE_NO_WINDOW
  )


# ── Task Scheduler ─────────────────────────────────────────────

def _task_exists() -> bool:
  r = _schtasks("/Query", "/TN", APP_NAME, "/FO", "LIST")
  return r.returncode == 0


def _enable_task() -> bool:
  """Create scheduled task: run at logon with 10s delay. Returns success."""
  exe = _get_exe_path()
  xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>{TASK_DELAY}</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe}</Command>
    </Exec>
  </Actions>
</Task>"""

  # Write XML to temp file (schtasks /Create /XML requires a file path)
  import tempfile, os
  tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w", encoding="utf-16")
  tmp.write(xml)
  tmp.close()

  try:
    r = _schtasks("/Create", "/TN", APP_NAME, "/XML", tmp.name, "/F")
    return r.returncode == 0
  finally:
    os.unlink(tmp.name)


def _disable_task() -> None:
  _schtasks("/Delete", "/TN", APP_NAME, "/F")


# ── Registry (fallback) ────────────────────────────────────────

def _reg_enabled() -> bool:
  try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
    winreg.QueryValueEx(key, APP_NAME)
    winreg.CloseKey(key)
    return True
  except FileNotFoundError:
    return False


def _reg_enable() -> None:
  key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
  winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
  winreg.CloseKey(key)


def _reg_disable() -> None:
  try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.DeleteValue(key, APP_NAME)
    winreg.CloseKey(key)
  except FileNotFoundError:
    pass


# ── Public API ─────────────────────────────────────────────────

def is_startup_enabled() -> bool:
  return _task_exists() or _reg_enabled()


def enable_startup() -> None:
  """Enable startup via Task Scheduler; fallback to Registry."""
  success = _enable_task()
  if not success:
    _reg_enable()
  else:
    # Clean up registry entry if task succeeded
    _reg_disable()


def disable_startup() -> None:
  _disable_task()
  _reg_disable()


def get_startup_method() -> str | None:
  """Return which method is active: 'task', 'registry', or None."""
  if _task_exists():
    return "task"
  if _reg_enabled():
    return "registry"
  return None
