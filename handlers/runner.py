import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: /run <perintah>\nContoh: /run dir C:\\")
        return
    cmd = " ".join(context.args)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout or result.stderr or "(tidak ada output)"
        if len(output) > 4000:
            output = output[:4000] + "\n... (output terpotong)"
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("Perintah timeout (>30 detik).")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
