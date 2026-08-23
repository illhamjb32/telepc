import io
import os
import asyncio
import ctypes
import logging
import datetime
import subprocess
from concurrent.futures import ThreadPoolExecutor

import psutil
import speedtest as _speedtest
from PIL import ImageGrab
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN, ALLOWED_CHAT_IDS
from handlers.system import shutdown_handler, restart_handler, sleep_handler, lock_handler, cancel_handler
from handlers.screen import screenshot_handler
from handlers.apps import open_handler
from handlers.runner import run_handler
from handlers.sysinfo import sysinfo_handler
from handlers.netspeed import netspeed_handler
from handlers.camera import camera_handler, _capture_camera
from handlers.display import display_mode_handler, switch_display_mode, get_current_display_mode
from handlers.volume import volume_handler, volume_callback
from handlers.killer import kill_handler, process_callback
from handlers.filebrowser import files_handler, filebrowser_callback
from handlers.clipboard import clipboard_handler, setclip_handler, clipboard_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)

_executor = ThreadPoolExecutor(max_workers=2)

APP_MAP = {
    "app_chrome": "chrome",
    "app_notepad": "notepad",
    "app_explorer": "explorer",
    "app_calculator": "calc",
    "app_vscode": "code",
    "app_v380": r"C:\Program Files (x86)\V380\V380.exe",
}

HELP_RUN_TEXT = (
    "⚙️ *Contoh perintah /run:*\n\n"
    "*Jaringan:*\n"
    "`/run ipconfig` — info IP\n"
    "`/run ping google.com` — ping\n"
    "`/run netstat -an` — koneksi aktif\n\n"
    "*Sistem:*\n"
    "`/run tasklist` — daftar proses\n"
    "`/run systeminfo` — info sistem\n"
    "`/run wmic cpu get name` — info CPU\n"
    "`/run wmic memorychip get capacity` — info RAM\n\n"
    "*File:*\n"
    "`/run dir C:\\` — isi folder C\n"
    "`/run dir C:\\Users` — isi folder Users\n"
    "`/run type C:\\file.txt` — baca file\n\n"
    "*Lainnya:*\n"
    "`/run echo hello` — print teks\n"
    "`/run whoami` — user saat ini\n"
    "`/run hostname` — nama PC\n"
    "`/run ver` — versi Windows"
)


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS


def get_status_text() -> str:
    uptime_seconds = datetime.datetime.now().timestamp() - psutil.boot_time()
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"⏱ Uptime: {hours}j {minutes}m {seconds}d"


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
        [
            InlineKeyboardButton("🛠 Tools", callback_data="menu_tools"),
        ],
    ])


async def go_to_main_menu(query, text: str):
    markup = main_menu_keyboard()
    if query.message.photo or query.message.document or query.message.video:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


def tools_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔊 Volume", callback_data="menu_volume"),
            InlineKeyboardButton("⚡ Kill Process", callback_data="menu_kill"),
        ],
        [
            InlineKeyboardButton("📁 File Browser", callback_data="menu_files"),
            InlineKeyboardButton("📋 Clipboard", callback_data="menu_clipboard"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
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
            InlineKeyboardButton("📷 Camera", callback_data="action_camera"),
        ],
        [
            InlineKeyboardButton("📈 Sysinfo", callback_data="action_sysinfo"),
            InlineKeyboardButton("🌐 Net Speed", callback_data="action_netspeed"),
        ],
        [
            InlineKeyboardButton("🖥️ Change Display", callback_data="menu_display"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
    ])


def display_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💻 PC Screen Only", callback_data="display_internal"),
            InlineKeyboardButton("🖥️ Second Screen Only", callback_data="display_external"),
        ],
        [
            InlineKeyboardButton("🔄 Duplicate", callback_data="display_clone"),
            InlineKeyboardButton("↔️ Extend", callback_data="display_extend"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_monitor")],
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
            InlineKeyboardButton("📷 V380", callback_data="app_v380"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_main")],
    ])


def _take_screenshot() -> io.BytesIO:
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _run_speedtest() -> dict:
    st = _speedtest.Speedtest()
    st.get_best_server()
    return {
        "download": st.download() / 1_000_000,
        "upload": st.upload() / 1_000_000,
        "ping": st.results.ping,
        "server": st.results.server.get("name", "Unknown"),
    }


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(HELP_RUN_TEXT, parse_mode="Markdown")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Akses ditolak.")
        return
    msg = f"*TelePC Bot*\nChat ID kamu: `{update.effective_chat.id}`\n{get_status_text()}\n\nPilih kategori:"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def getchatid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID kamu: `{update.effective_chat.id}`", parse_mode="Markdown")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("Akses ditolak.")
        return

    data = query.data

    # ── Main menu ──────────────────────────────────────────────────────────────
    if data == "menu_main":
        await go_to_main_menu(query, f"*TelePC Bot*\n{get_status_text()}\n\nPilih kategori:")

    # ── System ─────────────────────────────────────────────────────────────────
    elif data == "menu_system":
        await query.edit_message_text("💻 *System Control*\nPilih aksi:", parse_mode="Markdown", reply_markup=system_menu_keyboard())

    elif data == "action_shutdown":
        await query.edit_message_text(
            "⏻ PC akan shutdown dalam 5 detik. Gunakan /cancel untuk membatalkan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_system")]])
        )
        os.system("shutdown /s /t 5")

    elif data == "action_restart":
        await query.edit_message_text(
            "🔄 PC akan restart dalam 5 detik. Gunakan /cancel untuk membatalkan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_system")]])
        )
        os.system("shutdown /r /t 5")

    elif data == "action_sleep":
        await query.edit_message_text(
            "💤 PC akan masuk sleep mode...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_system")]])
        )
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    elif data == "action_lock":
        await query.edit_message_text(
            "🔒 Layar dikunci.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_system")]])
        )
        ctypes.windll.user32.LockWorkStation()

    elif data == "action_cancel":
        result = subprocess.run("shutdown /a", capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            await query.edit_message_text("✅ Shutdown/restart dibatalkan.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_system")],
            ]))
        else:
            await query.edit_message_text("ℹ️ Tidak ada proses shutdown/restart yang pending.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_system")],
            ]))

    # ── Monitor ────────────────────────────────────────────────────────────────
    elif data == "menu_monitor":
        await query.edit_message_text("📊 *Monitor*\nPilih aksi:", parse_mode="Markdown", reply_markup=monitor_menu_keyboard())

    elif data == "action_screenshot":
        await query.edit_message_text("📸 Mengambil screenshot...")
        buf = await asyncio.get_running_loop().run_in_executor(_executor, _take_screenshot)
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buf,
            caption="Screenshot layar",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]])
        )

    elif data == "action_camera":
        await query.edit_message_text("📷 Mengambil gambar dari kamera...")
        try:
            buf = await asyncio.get_running_loop().run_in_executor(_executor, _capture_camera)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=buf,
                caption="📷 Capture kamera",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]])
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Gagal capture kamera: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_monitor")]])
            )

    elif data == "action_sysinfo":
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        msg = (
            f"📈 *System Info*\n\n"
            f"*CPU:* {cpu}%\n"
            f"*RAM:* {ram.used / (1024**3):.1f} GB / {ram.total / (1024**3):.1f} GB ({ram.percent}%)\n"
            f"*Disk (C:):* {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB ({disk.percent}%)"
        )
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔃 Refresh", callback_data="action_sysinfo")],
            [InlineKeyboardButton("« Kembali", callback_data="menu_monitor")],
        ]))

    elif data == "action_netspeed":
        await query.edit_message_text("🌐 Mengecek kecepatan internet, harap tunggu...")
        try:
            result = await asyncio.get_running_loop().run_in_executor(_executor, _run_speedtest)
            msg = (
                f"🌐 *Internet Speed Test*\n\n"
                f"*Download:* {result['download']:.2f} Mbps\n"
                f"*Upload:* {result['upload']:.2f} Mbps\n"
                f"*Ping:* {result['ping']:.1f} ms\n"
                f"*Server:* {result['server']}"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id, text=msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_monitor")]])
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Gagal cek speed: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_monitor")]])
            )

    # ── Display ────────────────────────────────────────────────────────────────
    elif data == "menu_display":
        current_mode = get_current_display_mode()
        await query.edit_message_text(
            f"🖥️ *Change Display Mode*\n\nMode saat ini: {current_mode}\n\nPilih mode display:",
            parse_mode="Markdown",
            reply_markup=display_menu_keyboard()
        )

    elif data == "display_internal":
        success = await asyncio.get_running_loop().run_in_executor(_executor, lambda: switch_display_mode(1))
        msg = "✅ Display mode: PC Screen Only" if success else "❌ Gagal mengubah display mode"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_display")]]))

    elif data == "display_external":
        success = await asyncio.get_running_loop().run_in_executor(_executor, lambda: switch_display_mode(4))
        msg = "✅ Display mode: Second Screen Only" if success else "❌ Gagal mengubah display mode"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_display")]]))

    elif data == "display_clone":
        success = await asyncio.get_running_loop().run_in_executor(_executor, lambda: switch_display_mode(2))
        msg = "✅ Display mode: Duplicate" if success else "❌ Gagal mengubah display mode"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_display")]]))

    elif data == "display_extend":
        success = await asyncio.get_running_loop().run_in_executor(_executor, lambda: switch_display_mode(3))
        msg = "✅ Display mode: Extend" if success else "❌ Gagal mengubah display mode"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_display")]]))

    # ── Apps ───────────────────────────────────────────────────────────────────
    elif data == "menu_apps":
        await query.edit_message_text("📱 *Buka Aplikasi*\nPilih aplikasi:", parse_mode="Markdown", reply_markup=apps_menu_keyboard())

    elif data.startswith("app_"):
        cmd = APP_MAP.get(data, "")
        app_name = data.replace("app_", "").capitalize()
        if cmd:
            subprocess.Popen(cmd, shell=True)
            await query.edit_message_text(f"✅ Membuka {app_name}...", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_apps")],
            ]))

    # ── Run Command ────────────────────────────────────────────────────────────
    elif data == "menu_run":
        await query.edit_message_text(
            "⚙️ *Run Command*\n\nGunakan command:\n`/run <perintah>`\n\nContoh:\n`/run ipconfig`\n`/run tasklist`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="menu_main")]])
        )

    # ── Tools menu ─────────────────────────────────────────────────────────────
    elif data == "menu_tools":
        await query.edit_message_text("🛠 *Tools*\nPilih fitur:", parse_mode="Markdown", reply_markup=tools_menu_keyboard())

    # ── Volume ─────────────────────────────────────────────────────────────────
    elif data == "menu_volume":
        await volume_callback(query, context)

    elif data.startswith("vol_"):
        await volume_callback(query, context)

    # ── Kill Process ───────────────────────────────────────────────────────────
    elif data == "menu_kill":
        loop = asyncio.get_running_loop()
        from handlers.killer import _list_processes, _format_process_list, process_list_keyboard
        procs = await loop.run_in_executor(None, _list_processes, "cpu")
        text = _format_process_list(procs, "cpu")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=process_list_keyboard("cpu"))

    elif data.startswith("proc_"):
        await process_callback(query, context)

    # ── File Browser ───────────────────────────────────────────────────────────
    elif data == "menu_files":
        from handlers.filebrowser import _bookmarks_keyboard
        await query.edit_message_text(
            "📁 *File Browser*\n\nPilih lokasi:",
            parse_mode="Markdown",
            reply_markup=_bookmarks_keyboard()
        )

    elif data.startswith("fb_"):
        await filebrowser_callback(query, context)

    # ── Clipboard ──────────────────────────────────────────────────────────────
    elif data == "menu_clipboard" or data.startswith("clip_"):
        await clipboard_callback(query, context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("getchatid", getchatid_handler))
    app.add_handler(CommandHandler("screenshot", screenshot_handler))
    app.add_handler(CommandHandler("camera", camera_handler))
    app.add_handler(CommandHandler("sysinfo", sysinfo_handler))
    app.add_handler(CommandHandler("netspeed", netspeed_handler))
    app.add_handler(CommandHandler("open", open_handler))
    app.add_handler(CommandHandler("run", run_handler))
    app.add_handler(CommandHandler("shutdown", shutdown_handler))
    app.add_handler(CommandHandler("restart", restart_handler))
    app.add_handler(CommandHandler("sleep", sleep_handler))
    app.add_handler(CommandHandler("lock", lock_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))
    app.add_handler(CommandHandler("display", display_mode_handler))
    app.add_handler(CommandHandler("volume", volume_handler))
    app.add_handler(CommandHandler("kill", kill_handler))
    app.add_handler(CommandHandler("files", files_handler))
    app.add_handler(CommandHandler("clipboard", clipboard_handler))
    app.add_handler(CommandHandler("setclip", setclip_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot berjalan...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
