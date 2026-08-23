import subprocess
import ctypes
import ctypes.wintypes
import winreg
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

def get_current_display_mode() -> str:
    """
    Deteksi mode display aktual dengan menghitung monitor aktif via
    EnumDisplayMonitors (Win32 API). Lebih akurat dari registry karena
    registry hanya simpan mode terakhir yang di-set via DisplaySwitch,
    bukan state aktual hardware saat ini.
    """
    try:
        user32 = ctypes.windll.user32

        # Hitung jumlah monitor yang sedang aktif
        monitor_count = ctypes.c_int(0)

        @ctypes.WINFUNCTYPE(ctypes.c_bool,
                            ctypes.wintypes.HMONITOR,
                            ctypes.wintypes.HDC,
                            ctypes.POINTER(ctypes.wintypes.RECT),
                            ctypes.wintypes.LPARAM)
        def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            monitor_count.value += 1
            return True

        user32.EnumDisplayMonitors(None, None, _monitor_enum_proc, 0)
        count = monitor_count.value

        if count <= 1:
            # Satu monitor aktif — bisa PC Only atau Second Only
            # Bedakan dengan cek registry sebagai petunjuk tambahan
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Projection"
                )
                value, _ = winreg.QueryValueEx(key, "ProjectionMode")
                winreg.CloseKey(key)
                if value == 4:
                    return "Second Screen Only (1 monitor aktif)"
            except Exception:
                pass
            return "PC Screen Only (1 monitor aktif)"
        elif count == 2:
            # Dua monitor — bisa Duplicate atau Extend
            # Bedakan: Duplicate => resolusi kedua monitor sama persis
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Projection"
                )
                value, _ = winreg.QueryValueEx(key, "ProjectionMode")
                winreg.CloseKey(key)
                mode_hint = {1: "Duplicate", 2: "Extend", 3: "Extend"}.get(value, "Extend")
                return f"{mode_hint} (2 monitor aktif)"
            except Exception:
                return "Extend / Duplicate (2 monitor aktif)"
        else:
            return f"Extend ({count} monitor aktif)"

    except Exception as e:
        return f"Unknown (error: {e})"

def switch_display_mode(mode: int) -> bool:
    try:
        mode_args = {
            1: "/internal",
            2: "/clone",
            3: "/extend",
            4: "/external"
        }
        arg = mode_args.get(mode)
        if not arg:
            return False
        subprocess.Popen([r"C:\Windows\System32\DisplaySwitch.exe", arg])
        return True
    except Exception:
        return False

async def display_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Gunakan: /display <mode>\n"
            "Mode: internal, external, extend, clone"
        )
        return

    mode_map = {
        "internal": 1,
        "clone": 2,
        "extend": 3,
        "external": 4
    }

    mode_name = context.args[0].lower()
    if mode_name not in mode_map:
        await update.message.reply_text(
            "Mode tidak valid. Gunakan: internal, external, extend, atau clone"
        )
        return

    if switch_display_mode(mode_map[mode_name]):
        await update.message.reply_text(f"✅ Display mode diubah ke {mode_name}")
    else:
        await update.message.reply_text("❌ Gagal mengubah display mode")
