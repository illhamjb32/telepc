import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ALLOWED_CHAT_IDS
from handlers.system import shutdown_handler, restart_handler, sleep_handler, lock_handler, cancel_handler
from handlers.screen import screenshot_handler
from handlers.apps import open_handler
from handlers.runner import run_handler
from handlers.sysinfo import sysinfo_handler
from handlers.netspeed import netspeed_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_CHAT_IDS and update.effective_chat.id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text("Akses ditolak.")
        return

    chat_id = update.effective_chat.id
    msg = (
        f"*TelePC Bot*\n"
        f"Chat ID kamu: `{chat_id}`\n\n"
        f"*Command tersedia:*\n"
        f"/screenshot — Ambil screenshot layar\n"
        f"/sysinfo — Info CPU, RAM, Disk\n"
        f"/netspeed — Cek kecepatan internet\n"
        f"/open <app> — Buka aplikasi\n"
        f"/run <cmd> — Jalankan perintah\n"
        f"/shutdown \[detik\] — Matiin PC\n"
        f"/restart \[detik\] — Restart PC\n"
        f"/sleep — Sleep mode\n"
        f"/lock — Kunci layar\n"
        f"/cancel — Batalkan shutdown/restart"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def getchatid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID kamu: `{chat_id}`", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("getchatid", getchatid_handler))
    app.add_handler(CommandHandler("screenshot", screenshot_handler))
    app.add_handler(CommandHandler("sysinfo", sysinfo_handler))
    app.add_handler(CommandHandler("netspeed", netspeed_handler))
    app.add_handler(CommandHandler("open", open_handler))
    app.add_handler(CommandHandler("run", run_handler))
    app.add_handler(CommandHandler("shutdown", shutdown_handler))
    app.add_handler(CommandHandler("restart", restart_handler))
    app.add_handler(CommandHandler("sleep", sleep_handler))
    app.add_handler(CommandHandler("lock", lock_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
