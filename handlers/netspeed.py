import speedtest
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

async def netspeed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("Mengecek kecepatan internet, harap tunggu...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000
        upload = st.upload() / 1_000_000
        ping = st.results.ping
        server = st.results.server.get("name", "Unknown")

        msg = (
            f"*Internet Speed Test*\n\n"
            f"*Download:* {download:.2f} Mbps\n"
            f"*Upload:* {upload:.2f} Mbps\n"
            f"*Ping:* {ping:.1f} ms\n"
            f"*Server:* {server}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Gagal cek speed: {e}")
