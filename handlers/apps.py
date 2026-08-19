import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

APP_MAP = {
    "chrome": "chrome",
    "firefox": "firefox",
    "notepad": "notepad",
    "explorer": "explorer",
    "calculator": "calc",
    "cmd": "cmd",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "vscode": "code",
    "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    "v380": r"C:\Program Files (x86)\V380\V380.exe",
    "word": "winword",
    "excel": "excel",
}

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def open_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: /open <nama_aplikasi>\nContoh: /open chrome")
        return
    app_name = " ".join(context.args).lower()
    cmd = APP_MAP.get(app_name, app_name)
    try:
        subprocess.Popen(cmd, shell=True)
        await update.message.reply_text(f"Membuka: {app_name}")
    except Exception as e:
        await update.message.reply_text(f"Gagal membuka aplikasi: {e}")
