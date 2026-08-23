import asyncio
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS


def _list_processes(sort_by: str = "cpu") -> list[dict]:
    """
    Return top-20 proses berdasarkan CPU atau RAM.
    sort_by: 'cpu' | 'ram'
    """
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            procs.append({
                "pid":    info["pid"],
                "name":   info["name"] or "?",
                "cpu":    round(info["cpu_percent"] or 0, 1),
                "ram":    round(info["memory_percent"] or 0, 1),
                "status": info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key = "cpu" if sort_by == "cpu" else "ram"
    procs.sort(key=lambda x: x[key], reverse=True)
    return procs[:20]


def _kill_by_name(name: str) -> tuple[int, list[str]]:
    """
    Kill semua proses dengan nama yang cocok (case-insensitive).
    Return (jumlah_killed, [error_messages]).
    """
    killed = 0
    errors = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == name.lower():
                p.kill()
                killed += 1
        except psutil.AccessDenied:
            errors.append(f"PID {p.pid}: akses ditolak")
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            errors.append(f"PID {p.pid}: {e}")
    return killed, errors


def _kill_by_pid(pid: int) -> str:
    """Kill proses by PID. Return pesan hasil."""
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.kill()
        return f"✅ Proses *{name}* (PID {pid}) berhasil dihentikan."
    except psutil.NoSuchProcess:
        return f"❌ PID {pid} tidak ditemukan."
    except psutil.AccessDenied:
        return f"❌ Akses ditolak untuk PID {pid}."
    except Exception as e:
        return f"❌ Gagal: {e}"


def _format_process_list(procs: list[dict], sort_by: str) -> str:
    sort_label = "CPU" if sort_by == "cpu" else "RAM"
    lines = [f"📋 *Top Proses (sort: {sort_label})*\n"]
    for i, p in enumerate(procs, 1):
        lines.append(
            f"{i:2}. `{p['name'][:20]:<20}` "
            f"PID:{p['pid']:<6} "
            f"CPU:{p['cpu']:>5}% "
            f"RAM:{p['ram']:>4}%"
        )
    lines.append("\nGunakan `/kill <nama>` atau `/kill <PID>` untuk menghentikan proses.")
    return "\n".join(lines)


def process_list_keyboard(sort_by: str) -> InlineKeyboardMarkup:
    cpu_label = "✅ Sort CPU" if sort_by == "cpu" else "Sort CPU"
    ram_label = "✅ Sort RAM" if sort_by == "ram" else "Sort RAM"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(cpu_label, callback_data="proc_sort_cpu"),
            InlineKeyboardButton(ram_label, callback_data="proc_sort_ram"),
        ],
        [InlineKeyboardButton("🔃 Refresh", callback_data=f"proc_refresh_{sort_by}")],
        [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
    ])


async def kill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /kill              — tampilkan daftar proses
    /kill <nama>       — kill proses by name
    /kill <pid>        — kill proses by PID
    """
    if not is_allowed(update):
        return

    if not context.args:
        # Tampilkan daftar proses
        loop = asyncio.get_running_loop()
        procs = await loop.run_in_executor(None, _list_processes, "cpu")
        text = _format_process_list(procs, "cpu")
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=process_list_keyboard("cpu")
        )
        return

    target = " ".join(context.args)
    loop = asyncio.get_running_loop()

    # Coba parse sebagai PID
    if target.isdigit():
        msg = await loop.run_in_executor(None, _kill_by_pid, int(target))
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        # Kill by name
        killed, errors = await loop.run_in_executor(None, _kill_by_name, target)
        if killed == 0 and not errors:
            await update.message.reply_text(f"❌ Tidak ada proses bernama `{target}` yang ditemukan.", parse_mode="Markdown")
        else:
            lines = [f"✅ Berhasil menghentikan *{killed}* proses `{target}`."]
            if errors:
                lines.append("⚠️ Error:")
                lines.extend(f"  • {e}" for e in errors)
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def process_callback(query, context):
    """
    Dipanggil dari button_handler di bot.py untuk callback_data
    yang diawali 'proc_'.
    """
    data = query.data
    loop = asyncio.get_running_loop()

    if data in ("proc_sort_cpu", "proc_refresh_cpu"):
        sort_by = "cpu"
    elif data in ("proc_sort_ram", "proc_refresh_ram"):
        sort_by = "ram"
    else:
        return

    try:
        procs = await loop.run_in_executor(None, _list_processes, sort_by)
        text = _format_process_list(procs, sort_by)
        try:
            await query.edit_message_text(
                text, parse_mode="Markdown",
                reply_markup=process_list_keyboard(sort_by)
            )
        except BadRequest as e:
            if "not modified" in str(e).lower():
                await query.answer("Daftar proses tidak berubah.")
            else:
                raise
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            await query.edit_message_text(f"❌ Gagal ambil daftar proses: {e}")
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal ambil daftar proses: {e}")
