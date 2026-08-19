import io
import asyncio
import cv2
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

def _capture_camera() -> io.BytesIO:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Kamera tidak ditemukan atau tidak bisa dibuka.")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Gagal mengambil frame dari kamera.")
    ret, buf = cv2.imencode(".jpg", frame)
    if not ret:
        raise RuntimeError("Gagal encode gambar kamera.")
    return io.BytesIO(buf.tobytes())

async def camera_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("📷 Mengambil gambar dari kamera...")
    try:
        buf = await asyncio.get_event_loop().run_in_executor(None, _capture_camera)
        await update.message.reply_photo(photo=buf, caption="📷 Capture kamera")
    except Exception as e:
        await update.message.reply_text(f"Gagal capture kamera: {e}")
