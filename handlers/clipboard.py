import asyncio
import pyperclip
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS


def _read_clipboard() -> str:
    """Baca teks dari clipboard."""
    text = pyperclip.paste()
    return text if text else ""


def _write_clipboard(text: str) -> None:
    """Tulis teks ke clipboard."""
    pyperclip.copy(text)


def _clear_clipboard() -> None:
    """Kosongkan clipboard."""
    pyperclip.copy("")


async def clipboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /clipboard         — baca isi clipboard
    /clipboard clear   — kosongkan clipboard
    """
    if not is_allowed(update):
        return

    loop = asyncio.get_running_loop()

    if context.args and context.args[0].lower() == "clear":
        try:
            await loop.run_in_executor(None, _clear_clipboard)
            await update.message.reply_text("✅ Clipboard berhasil dikosongkan.")
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal kosongkan clipboard: {e}")
        return

    try:
        text = await loop.run_in_executor(None, _read_clipboard)
        if not text:
            await update.message.reply_text(
                "📋 Clipboard kosong atau tidak mengandung teks.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔃 Refresh", callback_data="clip_read")],
                    [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
                ])
            )
            return

        preview = text[:3500]
        truncated = len(text) > 3500
        suffix = f"\n\n_(terpotong, total {len(text)} karakter)_" if truncated else ""

        await update.message.reply_text(
            f"📋 *Isi Clipboard:*\n\n```\n{preview}\n```{suffix}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔃 Refresh",   callback_data="clip_read"),
                    InlineKeyboardButton("🗑 Kosongkan", callback_data="clip_clear"),
                ],
                [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
            ])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal baca clipboard: {e}")


async def setclip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setclip <teks>    — tulis teks ke clipboard PC
    """
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Penggunaan: `/setclip <teks>`\nContoh: `/setclip Hello World`",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _write_clipboard, text)
        preview = text[:200] + ("..." if len(text) > 200 else "")
        await update.message.reply_text(
            f"✅ Clipboard berhasil diisi:\n```\n{preview}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal tulis clipboard: {e}")


def _clipboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔃 Refresh",   callback_data="clip_read"),
            InlineKeyboardButton("🗑 Kosongkan", callback_data="clip_clear"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
    ])


def _clipboard_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔃 Refresh", callback_data="clip_read")],
        [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
    ])


async def clipboard_callback(query, context):
    """
    Dipanggil dari button_handler di bot.py untuk callback_data
    yang diawali 'clip_' atau 'menu_clipboard'.
    """
    data = query.data
    loop = asyncio.get_running_loop()

    if data in ("clip_read", "menu_clipboard"):
        try:
            text = await loop.run_in_executor(None, _read_clipboard)
            if not text:
                new_text = "📋 Clipboard kosong atau tidak mengandung teks."
                new_markup = _clipboard_empty_keyboard()
            else:
                preview = text[:3500]
                truncated = len(text) > 3500
                suffix = f"\n\n_(terpotong, total {len(text)} karakter)_" if truncated else ""
                new_text = f"📋 *Isi Clipboard:*\n\n```\n{preview}\n```{suffix}"
                new_markup = _clipboard_keyboard()

            try:
                await query.edit_message_text(
                    new_text,
                    parse_mode="Markdown",
                    reply_markup=new_markup,
                )
            except BadRequest as e:
                if "not modified" in str(e).lower():
                    await query.answer("✅ Clipboard tidak berubah.")
                else:
                    raise

        except BadRequest as e:
            if "not modified" not in str(e).lower():
                await query.edit_message_text(f"❌ Gagal baca clipboard: {e}")
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal baca clipboard: {e}")

    elif data == "clip_clear":
        try:
            await loop.run_in_executor(None, _clear_clipboard)
            try:
                await query.edit_message_text(
                    "✅ Clipboard berhasil dikosongkan.",
                    reply_markup=_clipboard_empty_keyboard(),
                )
            except BadRequest as e:
                if "not modified" in str(e).lower():
                    await query.answer("✅ Clipboard sudah kosong.")
                else:
                    raise
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                await query.edit_message_text(f"❌ Gagal kosongkan clipboard: {e}")
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal kosongkan clipboard: {e}")
