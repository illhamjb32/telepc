# TelePC — Kontrol PC via Telegram Bot

Aplikasi Python yang memungkinkan kamu mengontrol PC dari mana saja melalui Telegram bot.

## Stack

| Library | Fungsi |
|---|---|
| `python-telegram-bot==20.x` | Framework Telegram Bot (async) |
| `Pillow` | Screenshot via `ImageGrab` |
| `psutil` | Info CPU, RAM, disk |
| `speedtest-cli` | Cek internet speed |

## Struktur Proyek

```
Telepc/
├── bot.py                  # Entry point, setup bot & register handlers
├── config.py               # BOT_TOKEN, ALLOWED_CHAT_IDS (di .gitignore)
├── requirements.txt
├── .gitignore
└── handlers/
    ├── __init__.py
    ├── system.py           # Shutdown, restart, sleep, lock screen
    ├── screen.py           # Screenshot
    ├── apps.py             # Buka aplikasi
    ├── runner.py           # Jalankan command PowerShell/CMD
    ├── sysinfo.py          # Info CPU, RAM, disk
    └── netspeed.py         # Cek internet speed
```

## Daftar Command

| Command | Fungsi |
|---|---|
| `/start` | Tampilkan daftar command |
| `/shutdown [detik]` | Matiin PC (default delay 5 detik) |
| `/restart [detik]` | Restart PC (default delay 5 detik) |
| `/sleep` | Sleep mode |
| `/lock` | Kunci layar Windows |
| `/cancel` | Batalkan shutdown/restart yang pending |
| `/screenshot` | Capture & kirim screenshot layar |
| `/open <app>` | Buka aplikasi (contoh: `/open chrome`) |
| `/run <cmd>` | Jalankan command PowerShell/CMD |
| `/sysinfo` | Info CPU usage, RAM, disk |
| `/netspeed` | Cek download & upload speed |

## Keamanan

- Semua command dicek terhadap whitelist `ALLOWED_CHAT_IDS` di `config.py`
- Hanya `chat_id` yang terdaftar yang bisa mengirim perintah
- `config.py` masuk `.gitignore` agar token & ID tidak ter-commit ke repo

## Setup

1. Buat bot via [@BotFather](https://t.me/botfather), copy token
2. Copy `config.py.example` ke `config.py`, isi `BOT_TOKEN` dan `ALLOWED_CHAT_IDS`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan bot:
   ```bash
   python bot.py
   ```

## Flow Keamanan

```
User kirim command
      │
      ▼
Cek chat_id ada di ALLOWED_CHAT_IDS?
      │
   ┌──┴──┐
  Ya    Tidak
   │      │
   ▼      ▼
Eksekusi  Tolak (silent / pesan error)
```
