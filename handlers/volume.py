import asyncio
import ctypes
from ctypes import POINTER, cast
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

# pycaw imports — tersedia setelah: pip install pycaw
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS


def _get_volume_interface():
    """Ambil interface IAudioEndpointVolume untuk default audio device."""
    if not _PYCAW_OK:
        raise RuntimeError("pycaw tidak terinstall. Jalankan: pip install pycaw")
    speakers = AudioUtilities.GetSpeakers()
    return speakers.EndpointVolume


def get_volume() -> dict:
    """Return {'level': 0-100, 'muted': bool}"""
    vol = _get_volume_interface()
    level = round(vol.GetMasterVolumeLevelScalar() * 100)
    muted = bool(vol.GetMute())
    return {"level": level, "muted": muted}


def set_volume(level: int) -> dict:
    """Set volume 0-100, return state baru."""
    level = max(0, min(100, level))
    vol = _get_volume_interface()
    vol.SetMasterVolumeLevelScalar(level / 100.0, None)
    muted = bool(vol.GetMute())
    return {"level": level, "muted": muted}


def toggle_mute() -> dict:
    """Toggle mute, return state baru."""
    vol = _get_volume_interface()
    new_mute = not bool(vol.GetMute())
    vol.SetMute(int(new_mute), None)
    level = round(vol.GetMasterVolumeLevelScalar() * 100)
    return {"level": level, "muted": new_mute}


def volume_keyboard(level: int, muted: bool) -> InlineKeyboardMarkup:
    mute_label = "🔇 Unmute" if muted else "🔇 Mute"
    status = "🔇 MUTED" if muted else f"🔊 {level}%"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ +10%", callback_data="vol_up10"),
            InlineKeyboardButton("➕ +5%",  callback_data="vol_up5"),
        ],
        [
            InlineKeyboardButton("➖ -5%",  callback_data="vol_dn5"),
            InlineKeyboardButton("➖ -10%", callback_data="vol_dn10"),
        ],
        [
            InlineKeyboardButton(mute_label, callback_data="vol_mute"),
            InlineKeyboardButton("🔃 Refresh", callback_data="vol_refresh"),
        ],
        [
            InlineKeyboardButton("🔈 0%",   callback_data="vol_set0"),
            InlineKeyboardButton("🔉 25%",  callback_data="vol_set25"),
            InlineKeyboardButton("🔊 50%",  callback_data="vol_set50"),
            InlineKeyboardButton("🔊 75%",  callback_data="vol_set75"),
            InlineKeyboardButton("🔊 100%", callback_data="vol_set100"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="menu_tools")],
    ])


def _volume_text(level: int, muted: bool) -> str:
    bar_filled = round(level / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    status = "🔇 MUTED" if muted else f"🔊 {level}%"
    return f"🔊 *Volume Control*\n\n{status}\n`[{bar}]`"


async def volume_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /volume — tampilkan status + kontrol inline."""
    if not is_allowed(update):
        return
    try:
        state = await asyncio.get_running_loop().run_in_executor(None, get_volume)
        text = _volume_text(state["level"], state["muted"])
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=volume_keyboard(state["level"], state["muted"])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal baca volume: {e}")


async def volume_callback(query, context):
    """
    Dipanggil dari button_handler di bot.py untuk semua callback_data
    yang diawali 'vol_'.
    """
    data = query.data
    try:
        loop = asyncio.get_running_loop()

        if data == "vol_refresh":
            state = await loop.run_in_executor(None, get_volume)

        elif data == "vol_mute":
            state = await loop.run_in_executor(None, toggle_mute)

        elif data == "vol_up10":
            cur = await loop.run_in_executor(None, get_volume)
            state = await loop.run_in_executor(None, set_volume, cur["level"] + 10)

        elif data == "vol_up5":
            cur = await loop.run_in_executor(None, get_volume)
            state = await loop.run_in_executor(None, set_volume, cur["level"] + 5)

        elif data == "vol_dn5":
            cur = await loop.run_in_executor(None, get_volume)
            state = await loop.run_in_executor(None, set_volume, cur["level"] - 5)

        elif data == "vol_dn10":
            cur = await loop.run_in_executor(None, get_volume)
            state = await loop.run_in_executor(None, set_volume, cur["level"] - 10)

        elif data == "vol_set0":
            state = await loop.run_in_executor(None, set_volume, 0)

        elif data == "vol_set25":
            state = await loop.run_in_executor(None, set_volume, 25)

        elif data == "vol_set50":
            state = await loop.run_in_executor(None, set_volume, 50)

        elif data == "vol_set75":
            state = await loop.run_in_executor(None, set_volume, 75)

        elif data == "vol_set100":
            state = await loop.run_in_executor(None, set_volume, 100)

        else:
            return

        text = _volume_text(state["level"], state["muted"])
        try:
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=volume_keyboard(state["level"], state["muted"])
            )
        except BadRequest as e:
            if "not modified" in str(e).lower():
                await query.answer("Volume tidak berubah.")
            else:
                raise

    except BadRequest as e:
        if "not modified" not in str(e).lower():
            await query.edit_message_text(
                f"❌ Gagal kontrol volume: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Kembali", callback_data="menu_tools")]
                ])
            )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Gagal kontrol volume: {e}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="menu_tools")]
            ])
        )
