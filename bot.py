import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
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

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💻 System", callback_data="menu_system"),
            InlineKeyboardButton("📊 Monitor", callback_data="menu_monitor"),
        ],
        [
            InlineKeyboardButton("📱 Apps", callback_data="menu_apps"),
            InlineKeyboardButton("⚙️ Run Command", callback_data="menu_run"),
        ],
    ])

def system_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏻ Shutdown", callback_data="action_shutdown"),
            InlineKeyboardButton("🔄 Restart", callback_data="action_restart"),
        ],
        [
            InlineKeyboardButton("💤 Sleep", callback_data="action_sleep"),
            InlineKeyboardButton("🔒 Lock", callback_data="action_lock"),
        ],
        [
            InlineKeyboardButton("❌ Cancel Shutdown", callback_data="action_cancel"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
    ])

def monitor_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖥 Screenshot", callback_data="action_screenshot"),
            InlineKeyboardButton("📈 Sysinfo", callback_data="action_sysinfo"),
        ],
        [
            InlineKeyboardButton("🌐 Net Speed", callback_data="action_netspeed"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
    ])

def apps_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Chrome", callback_data="app_chrome"),
            InlineKeyboardButton("📝 Notepad", callback_data="app_notepad"),
        ],
        [
            InlineKeyboardButton("📁 Explorer", callback_data="app_explorer"),
            InlineKeyboardButton("🧮 Calculator", callback_data="app_calculator"),
        ],
        [
            InlineKeyboardButton("💻 VS Code", callback_data="app_vscode"),
            InlineKeyboardButton("🎵 Spotify", callback_data="app_spotify"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
    ])

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Akses ditolak.")
        return
    chat_id = update.effective_chat.id
    msg = f"*TelePC Bot*\nChat ID kamu: `{chat_id}`\n\nPilih kategori:"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def getchatid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID kamu: `{chat_id}`", parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("Akses ditolak.")
        return

    data = query.data

    if data == "menu_main":
        await query.edit_message_text("Pilih kategori:", reply_markup=main_menu_keyboard())

    elif data == "menu_system":
        await query.edit_message_text("💻 *System Control*\nPilih aksi:", parse_mode="Markdown", reply_markup=system_menu_keyboard())

    elif data == "menu_monitor":
        await query.edit_message_text("📊 *Monitor*\nPilih aksi:", parse_mode="Markdown", reply_markup=monitor_menu_keyboard())

    elif data == "menu_apps":
        await query.edit_message_text("📱 *Buka Aplikasi*\nPilih aplikasi:", parse_mode="Markdown", reply_markup=apps_menu_keyboard())

    elif data == "menu_run":
        await query.edit_message_text(
            "⚙️ *Run Command*\n\nGunakan command:\n`/run <perintah>`\n\nContoh:\n`/run ipconfig`\n`/run tasklist`",
            parse_mode="Markdown"
        )

    elif data == "action_shutdown":
        await query.edit_message_text("⏻ PC akan shutdown dalam 5 detik. Gunakan /cancel untuk membatalkan.")
        import os; os.system("shutdown /s /t 5")

    elif data == "action_restart":
        await query.edit_message_text("🔄 PC akan restart dalam 5 detik. Gunakan /cancel untuk membatalkan.")
        import os; os.system("shutdown /r /t 5")

    elif data == "action_sleep":
        await query.edit_message_text("💤 PC akan masuk sleep mode...")
        import os; os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    elif data == "action_lock":
        await query.edit_message_text("🔒 Layar dikunci.")
        import ctypes; ctypes.windll.user32.LockWorkStation()

    elif data == "action_cancel":
        import subprocess
        result = subprocess.run("shutdown /a", capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            await query.edit_message_text("✅ Shutdown/restart dibatalkan.")
        else:
            await query.edit_message_text("ℹ️ Tidak ada proses shutdown/restart yang pending.")

    elif data == "action_screenshot":
        await query.edit_message_text("📸 Mengambil screenshot...")
        import io
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption="Screenshot layar")

    elif data == "action_sysinfo":
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        msg = (
            f"📈 *System Info*\n\n"
            f"*CPU:* {cpu}%\n"
            f"*RAM:* {ram.used / (1024**3):.1f} GB / {ram.total / (1024**3):.1f} GB ({ram.percent}%)\n"
            f"*Disk:* {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB ({disk.percent}%)"
        )
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔃 Refresh", callback_data="action_sysinfo")],
            [InlineKeyboardButton("« Kembali", callback_data="menu_monitor")],
        ]))

    elif data == "action_netspeed":
        await query.edit_message_text("🌐 Mengecek kecepatan internet, harap tunggu...")
        try:
            import speedtest
            st = speedtest.Speedtest()
            st.get_best_server()
            dl = st.download() / 1_000_000
            ul = st.upload() / 1_000_000
            ping = st.results.ping
            server = st.results.server.get("name", "Unknown")
            msg = (
                f"🌐 *Internet Speed Test*\n\n"
                f"*Download:* {dl:.2f} Mbps\n"
                f"*Upload:* {ul:.2f} Mbps\n"
                f"*Ping:* {ping:.1f} ms\n"
                f"*Server:* {server}"
            )
            await context.bot.send_message(chat_id=query.message.chat_id, text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_monitor")],
            ]))
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Gagal cek speed: {e}")

    elif data.startswith("app_"):
        app_map = {
            "app_chrome": "chrome",
            "app_notepad": "notepad",
            "app_explorer": "explorer",
            "app_calculator": "calc",
            "app_vscode": "code",
            "app_spotify": "spotify",
        }
        cmd = app_map.get(data, "")
        app_name = data.replace("app_", "").capitalize()
        if cmd:
            import subprocess
            subprocess.Popen(cmd, shell=True)
            await query.edit_message_text(f"✅ Membuka {app_name}...", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_apps")],
            ]))

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
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
