import io
from PIL import ImageGrab
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("Mengambil screenshot...")
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await update.message.reply_photo(photo=buf, caption="Screenshot layar")
