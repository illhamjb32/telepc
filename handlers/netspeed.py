import asyncio
import speedtest as _speedtest
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

_executor = None

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

def _run_speedtest() -> dict:
    st = _speedtest.Speedtest()
    st.get_best_server()
    return {
        "download": st.download() / 1_000_000,
        "upload": st.upload() / 1_000_000,
        "ping": st.results.ping,
        "server": st.results.server.get("name", "Unknown"),
    }

async def netspeed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("Mengecek kecepatan internet, harap tunggu...")
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _run_speedtest)
        msg = (
            f"*Internet Speed Test*\n\n"
            f"*Download:* {result['download']:.2f} Mbps\n"
            f"*Upload:* {result['upload']:.2f} Mbps\n"
            f"*Ping:* {result['ping']:.1f} ms\n"
            f"*Server:* {result['server']}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Gagal cek speed: {e}")
