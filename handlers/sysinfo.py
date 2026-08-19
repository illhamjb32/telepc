import psutil
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def sysinfo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    ram_total = ram.total / (1024 ** 3)
    ram_used = ram.used / (1024 ** 3)
    ram_pct = ram.percent

    disk_total = disk.total / (1024 ** 3)
    disk_used = disk.used / (1024 ** 3)
    disk_pct = disk.percent

    msg = (
        f"*System Info*\n\n"
        f"*CPU:* {cpu}%\n"
        f"*RAM:* {ram_used:.1f} GB / {ram_total:.1f} GB ({ram_pct}%)\n"
        f"*Disk (C:):* {disk_used:.1f} GB / {disk_total:.1f} GB ({disk_pct}%)"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
