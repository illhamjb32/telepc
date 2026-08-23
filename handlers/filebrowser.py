import os
import asyncio
import math
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

# Batas ukuran file yang bisa langsung dikirim via Telegram (50 MB)
MAX_SEND_SIZE = 50 * 1024 * 1024

# Bookmarks direktori umum
BOOKMARKS = {
    "🏠 Home":       str(Path.home()),
    "🖥 Desktop":    str(Path.home() / "OneDrive" / "Desktop"),
    "📄 Documents":  str(Path.home() / "OneDrive" / "Documents"),
    "⬇ Downloads":  str(Path.home() / "Downloads"),
    "🖼 Pictures":   str(Path.home() / "OneDrive" / "Pictures"),
    "🎵 Music":      str(Path.home() / "Music"),
    "🎬 Videos":     str(Path.home() / "Videos"),
    "💾 C:":         "C:\\",
}

# Ekstensi yang aman ditampilkan sebagai teks
TEXT_EXTENSIONS = {
    ".txt", ".log", ".md", ".py", ".js", ".ts", ".json", ".xml",
    ".yaml", ".yml", ".ini", ".cfg", ".toml", ".csv", ".html",
    ".htm", ".css", ".sh", ".bat", ".ps1",
}

# Jumlah item per halaman di listing direktori
PAGE_SIZE = 8


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS


def _safe_path(raw: str) -> Path:
    """Resolve path, tolak path yang tidak ada."""
    p = Path(raw).resolve()
    return p


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 ** 3:
        return f"{size / 1024**2:.1f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"


def _list_dir(path: Path, page: int = 0) -> dict:
    """
    List isi direktori dengan pagination.
    Return {entries, total, page, total_pages, path_str}
    """
    try:
        items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return {"error": "Akses ditolak ke direktori ini."}
    except Exception as e:
        return {"error": str(e)}

    total = len(items)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    entries = items[start: start + PAGE_SIZE]

    result = []
    for item in entries:
        try:
            is_dir = item.is_dir()
            size = "" if is_dir else _format_size(item.stat().st_size)
            result.append({
                "name": item.name,
                "is_dir": is_dir,
                "size": size,
                "path": str(item),
            })
        except Exception:
            result.append({"name": item.name, "is_dir": False, "size": "?", "path": str(item)})

    return {
        "entries":     result,
        "total":       total,
        "page":        page,
        "total_pages": total_pages,
        "path_str":    str(path),
    }


def _dir_keyboard(listing: dict) -> InlineKeyboardMarkup:
    """Buat inline keyboard dari hasil _list_dir."""
    buttons = []
    for entry in listing["entries"]:
        icon = "📁" if entry["is_dir"] else "📄"
        label = f"{icon} {entry['name']}"
        if entry["size"]:
            label += f" ({entry['size']})"
        # Encode path ke callback_data — Telegram batas 64 byte,
        # jadi kita pakai index dalam listing bukan full path
        cb = f"fb_open:{entry['path']}"
        # Jika path terlalu panjang untuk callback_data (>64 byte),
        # potong dan simpan ke context (ditangani di bot.py)
        if len(cb.encode()) <= 64:
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        else:
            # Pakai hash sebagai key, path disimpan di context.bot_data
            import hashlib
            key = "fb_" + hashlib.md5(entry["path"].encode()).hexdigest()[:8]
            buttons.append([InlineKeyboardButton(label, callback_data=f"fb_open:{key}")])

    # Navigasi halaman
    page       = listing["page"]
    total_pages = listing["total_pages"]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"fb_page:{listing['path_str']}:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="fb_noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"fb_page:{listing['path_str']}:{page + 1}"))
    if nav:
        buttons.append(nav)

    # Tombol naik direktori + bookmark + kembali ke menu
    parent = str(Path(listing["path_str"]).parent)
    extra = []
    if parent != listing["path_str"]:
        extra.append(InlineKeyboardButton("⬆ Naik", callback_data=f"fb_open:{parent}"))
    extra.append(InlineKeyboardButton("🔖 Bookmark", callback_data="fb_bookmarks"))
    buttons.append(extra)
    buttons.append([InlineKeyboardButton("« Kembali", callback_data="menu_tools")])

    return InlineKeyboardMarkup(buttons)


def _bookmarks_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(label, callback_data=f"fb_open:{path}")]
               for label, path in BOOKMARKS.items()]
    buttons.append([InlineKeyboardButton("« Kembali", callback_data="menu_tools")])
    return InlineKeyboardMarkup(buttons)


async def files_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /files             — tampilkan bookmark
    /files <path>      — buka direktori atau download file
    """
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "📁 *File Browser*\n\nPilih lokasi:",
            parse_mode="Markdown",
            reply_markup=_bookmarks_keyboard()
        )
        return

    path_str = " ".join(context.args)
    await _open_path(update.message, path_str, context, is_query=False)


async def _open_path(target, path_str: str, context, is_query: bool = True, page: int = 0):
    """
    Buka path: kalau direktori → tampilkan listing,
    kalau file → kirim file.
    """
    try:
        path = _safe_path(path_str)
    except Exception as e:
        text = f"❌ Path tidak valid: {e}"
        if is_query:
            await target.edit_message_text(text)
        else:
            await target.reply_text(text)
        return

    if not path.exists():
        text = f"❌ Path tidak ditemukan:\n`{path}`"
        if is_query:
            await target.edit_message_text(text, parse_mode="Markdown")
        else:
            await target.reply_text(text, parse_mode="Markdown")
        return

    if path.is_dir():
        loop = asyncio.get_running_loop()
        listing = await loop.run_in_executor(None, _list_dir, path, page)

        if "error" in listing:
            text = f"❌ {listing['error']}"
            if is_query:
                await target.edit_message_text(text)
            else:
                await target.reply_text(text)
            return

        total = listing["total"]
        text = (
            f"📁 *{path.name or str(path)}*\n"
            f"`{path}`\n\n"
            f"{total} item  •  Hal. {listing['page'] + 1}/{listing['total_pages']}"
        )
        keyboard = _dir_keyboard(listing)

        if is_query:
            await target.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await target.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    else:
        # File — kirim langsung
        size = path.stat().st_size
        if size > MAX_SEND_SIZE:
            text = (
                f"❌ File terlalu besar untuk dikirim via Telegram.\n"
                f"Ukuran: {_format_size(size)} (maks 50 MB)"
            )
            if is_query:
                await target.edit_message_text(text)
            else:
                await target.reply_text(text)
            return

        chat_id = target.message.chat_id if is_query else target.chat_id
        if is_query:
            await target.edit_message_text(f"📤 Mengirim file `{path.name}`...", parse_mode="Markdown")

        try:
            with open(path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    filename=path.name,
                    caption=f"📄 `{path}`\n{_format_size(size)}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📁 Buka Folder", callback_data=f"fb_open:{path.parent}")],
                        [InlineKeyboardButton("« Menu Tools", callback_data="menu_tools")],
                    ])
                )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Gagal kirim file: {e}"
            )


async def filebrowser_callback(query, context):
    """
    Dipanggil dari button_handler di bot.py untuk callback_data
    yang diawali 'fb_'.
    """
    data = query.data

    if data == "fb_bookmarks":
        await query.edit_message_text(
            "📁 *File Browser*\n\nPilih lokasi:",
            parse_mode="Markdown",
            reply_markup=_bookmarks_keyboard()
        )
        return

    if data == "fb_noop":
        return

    if data.startswith("fb_open:"):
        path_str = data[len("fb_open:"):]
        await _open_path(query, path_str, context, is_query=True)
        return

    if data.startswith("fb_page:"):
        # format: fb_page:<path>:<page>
        parts = data[len("fb_page:"):].rsplit(":", 1)
        if len(parts) == 2:
            path_str, page_str = parts
            try:
                page = int(page_str)
            except ValueError:
                page = 0
            await _open_path(query, path_str, context, is_query=True, page=page)
        return
