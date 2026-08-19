import os
import subprocess
import ctypes
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

pending_shutdown = None

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def shutdown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    delay = int(context.args[0]) if context.args else 5
    await update.message.reply_text(f"PC akan shutdown dalam {delay} detik. Ketik /cancel untuk membatalkan.")
    os.system(f"shutdown /s /t {delay}")

async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    delay = int(context.args[0]) if context.args else 5
    await update.message.reply_text(f"PC akan restart dalam {delay} detik. Ketik /cancel untuk membatalkan.")
    os.system(f"shutdown /r /t {delay}")

async def sleep_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("PC akan masuk sleep mode...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("Layar dikunci.")
    ctypes.windll.user32.LockWorkStation()

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    result = subprocess.run("shutdown /a", capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        await update.message.reply_text("Shutdown/restart dibatalkan.")
    else:
        await update.message.reply_text("Tidak ada proses shutdown/restart yang pending.")
