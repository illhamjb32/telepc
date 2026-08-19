import subprocess
import winreg
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return update.effective_chat.id in ALLOWED_CHAT_IDS

def get_current_display_mode() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Projection")
        value, _ = winreg.QueryValueEx(key, "ProjectionMode")
        winreg.CloseKey(key)
        
        modes = {
            0: "PC Screen Only",
            1: "Duplicate",
            2: "Extend", 
            4: "Second Screen Only"
        }
        return modes.get(value, "Unknown")
    except:
        return "Unknown"

def switch_display_mode(mode: int) -> bool:
    try:
        mode_args = {
            1: "/internal",
            2: "/clone", 
            3: "/extend",
            4: "/external"
        }
        arg = mode_args.get(mode)
        if not arg:
            return False
        subprocess.Popen([r"C:\Windows\System32\DisplaySwitch.exe", arg])
        return True
    except:
        return False

async def display_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Gunakan: /display <mode>\n"
            "Mode: internal, external, extend, clone"
        )
        return
    
    mode_map = {
        "internal": 1,
        "clone": 2,
        "extend": 3,
        "external": 4
    }
    
    mode_name = context.args[0].lower()
    if mode_name not in mode_map:
        await update.message.reply_text("Mode tidak valid. Gunakan: internal, external, extend, atau clone")
        return
    
    if switch_display_mode(mode_map[mode_name]):
        await update.message.reply_text(f"✅ Display mode diubah ke {mode_name}")
    else:
        await update.message.reply_text("❌ Gagal mengubah display mode")


async def display_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Gunakan: /display <mode>\n"
            "Mode: internal, external, extend, clone"
        )
        return
    
    mode_map = {
        "internal": 1,
        "clone": 2,
        "extend": 3,
        "external": 4
    }
    
    mode_name = context.args[0].lower()
    if mode_name not in mode_map:
        await update.message.reply_text("Mode tidak valid. Gunakan: internal, external, extend, atau clone")
        return
    
    if switch_display_mode(mode_map[mode_name]):
        await update.message.reply_text(f"✅ Display mode diubah ke {mode_name}")
    else:
        await update.message.reply_text("❌ Gagal mengubah display mode")
