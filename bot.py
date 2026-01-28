# Telegram Video Protection Bot (Pyrogram + FFmpeg)
# ---------------------------------------------------
# This script injects a short admin-provided clip into every channel video
# to change the video hash and reduce reuse/reupload. It is intentionally
# verbose and beginner-friendly, with comments for every important step.
#
# STEP-BY-STEP OVERVIEW
# 1) Admin uploads a short clip via /setclip (2-4 seconds)
# 2) Admin sets position and audio mode
# 3) Bot watches a channel for new videos
# 4) Bot downloads the video, inserts the clip, tweaks the first frame,
#    and re-uploads the processed file
#
# NOTE: You must have FFmpeg installed and accessible in PATH.

import os
import json
import random
import logging
import tempfile
import subprocess
import time
import threading
import queue
from pathlib import Path
from typing import Optional

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# ------------------------
# STEP 1: BASIC SETUP
# ------------------------
# 1) Create a bot via BotFather:
#    - Open Telegram, search for @BotFather
#    - Send /newbot
#    - Choose a name and username
#    - BotFather will give you a BOT TOKEN (keep it secret)
#
# 2) Get API_ID and API_HASH:
#    - Visit https://my.telegram.org
#    - Log in with your Telegram account
#    - Go to "API development tools"
#    - Create a new app to get API_ID and API_HASH
#
# 3) Install required libraries:
#    - Python 3.10+ recommended
#    - pip install pyrogram tgcrypto
#    - Install FFmpeg (system dependency)
#      Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg
#
# We load credentials from environment variables for safety.

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admins: comma-separated user IDs (numbers) e.g. "123,456"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
# Optional single owner/admin ID for convenience
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
if OWNER_ID and OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(OWNER_ID)

# Target channel ID to monitor (e.g. -1001234567890)
_target_env = os.getenv("TARGET_CHANNEL_ID", "").strip()
TARGET_CHANNEL_ID = int(_target_env) if _target_env.lstrip("-").isdigit() else 0

# Where we store bot data
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
CLIPS_DIR = DATA_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)

DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Background processing queue (multiple workers if needed)
WORKER_COUNT = int(os.getenv("WORKER_COUNT", "1") or "1")
QUEUE_LIMIT = int(os.getenv("QUEUE_LIMIT", "50") or "50")
VIDEO_QUEUE: "queue.Queue[dict]" = queue.Queue(maxsize=QUEUE_LIMIT)
QUEUE_COUNTER = {
    "enqueued": 0,
    "processed": 0,
    "lock": threading.Lock(),
}
COUNTERS = {
    "running": 0,
    "downloading": 0,
    "uploading": 0,
    "lock": threading.Lock(),
}

# In-memory pending actions (per admin)
PENDING = {
    "addchannel": set(),
    "watermark": {},  # user_id -> {"stage": str}
}

# Basic logging so we can debug issues later
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------
# STEP 2: BOT INITIALIZATION
# ------------------------
# The session name identifies the local session file that stores login info.
# Because this is a bot, you only need API_ID, API_HASH, and BOT_TOKEN.
#
# Admin IDs are used to restrict commands so random users cannot control settings.

app = Client(
    "video_protection_bot",  # session name (creates a local .session file)
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ------------------------
# Helpers: settings storage
# ------------------------

def channel_defaults() -> dict:
    """Default per-channel settings."""
    return {
        "enabled": False,
        "position": "start",         # start | middle | end | random
        "audio": "clip",             # mix | clip | original
        "protect_thumbnail": True,   # modify first frame slightly
        "delete_original": True,     # delete original channel post before re-upload
        "delete_images": False,      # delete incoming channel images
        "clip_set": False,
        "watermark_text": "",        # text watermark (empty = off)
        "watermark_position": "bottom_right",  # tl/tr/bl/br/center
        "watermark_opacity": 0.5,
        "watermark_size": 24,
        "watermark_style": "shadow",  # shadow | plain
    }


def load_settings() -> dict:
    """Load settings from JSON or return defaults."""
    defaults = {
        "multi_admin": True,         # allow multiple admins
        "target_channel_id": None,   # legacy single-channel mode
        "active_channel": None,      # selected channel for admin commands
        "channels": {},              # channel_id -> {title, username, settings}
    }
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update(data)
        except Exception as exc:
            logger.warning("Failed to read settings.json: %s", exc)
    return defaults


def save_settings(data: dict) -> None:
    """Save settings to JSON."""
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def channel_key_from_chat(chat) -> str:
    """Use numeric chat.id as the stable key."""
    return str(chat.id)


def ensure_channel(settings: dict, chat) -> dict:
    """Ensure a channel entry exists in settings and return it."""
    key = channel_key_from_chat(chat)
    channels = settings.setdefault("channels", {})
    if key not in channels:
        channels[key] = {
            "title": getattr(chat, "title", "") or "",
            "username": getattr(chat, "username", "") or "",
            "settings": channel_defaults(),
        }
    return channels[key]


def get_active_channel_entry(settings: dict) -> Optional[dict]:
    """Return active channel entry or None."""
    key = settings.get("active_channel")
    if not key:
        return None
    return settings.get("channels", {}).get(key)


def get_clip_path(channel_key: str) -> Path:
    """Clip file path per channel."""
    safe_key = channel_key.replace("-", "m")
    return CLIPS_DIR / f"clip_{safe_key}.mp4"


# ------------------------
# Helpers: admin checks
# ------------------------

def is_admin(user_id: int) -> bool:
    """Check if a user is allowed to use admin commands."""
    if not ADMIN_IDS:
        return False
    return user_id in ADMIN_IDS


def require_admin(message: Message) -> bool:
    """Return True if admin, else reply with a warning."""
    if not message.from_user:
        return False
    if not is_admin(message.from_user.id):
        message.reply_text("Access denied. Admins only.")
        return False
    return True


# ------------------------
# Helpers: FFmpeg/FFprobe
# ------------------------

def run_cmd(cmd: list) -> None:
    """Run a subprocess command and raise if it fails."""
    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def get_duration_seconds(path: Path) -> float:
    """Use ffprobe to get media duration in seconds."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def get_video_props(path: Path) -> tuple[int, int, float]:
    """Get width, height, and fps from the first video stream."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = [x.strip() for x in result.stdout.strip().splitlines() if x.strip()]
    width = int(lines[0])
    height = int(lines[1])
    # r_frame_rate is like "30000/1001"
    num, den = lines[2].split("/")
    fps = float(num) / float(den) if float(den) != 0 else 25.0
    return width, height, fps


def extract_clip_thumbnail(video_path: Path, thumb_path: Path) -> None:
    """Extract the first frame as a thumbnail for upload."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(thumb_path),
    ]
    run_cmd(cmd)


def start_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline buttons for quick setup."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add Channel", callback_data="addchannel")],
            [InlineKeyboardButton("Setup", callback_data="setup")],
        ]
    )

def progress_callback(current: int, total: int, status_msg: Optional[Message], label: str, state: dict) -> None:
    """Edit a status message with progress percentage (throttled)."""
    if not status_msg or total == 0:
        return
    now = time.time()
    if now - state["last"] < 2.0:  # update every ~2 seconds
        return
    state["last"] = now
    percent = (current / total) * 100
    try:
        mb_cur = current / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        bar_len = 10
        filled = int((percent / 100) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        with COUNTERS["lock"]:
            running = COUNTERS["running"]
            downloading = COUNTERS["downloading"]
            uploading = COUNTERS["uploading"]
        qsize = VIDEO_QUEUE.qsize()
        status_msg.edit_text(
            f"Progress : {bar} {percent:.0f}%\n\n"
            f"Running     : {running}\n"
            f"Downloading : {downloading}\n"
            f"Uploading   : {uploading}\n"
            f"Queue       : {qsize}\n\n"
            f"{label}... {percent:.1f}% ({mb_cur:.1f}/{mb_total:.1f} MB)"
        )
    except Exception:
        pass


def channel_list_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Inline buttons for selecting a channel."""
    buttons = []
    for key, info in settings.get("channels", {}).items():
        title = info.get("title") or info.get("username") or key
        buttons.append([InlineKeyboardButton(title, callback_data=f"select:{key}")])
    if not buttons:
        buttons = [[InlineKeyboardButton("No channels added", callback_data="noop")]]
    return InlineKeyboardMarkup(buttons)


def channel_actions_keyboard(channel_key: str) -> InlineKeyboardMarkup:
    """Inline buttons for channel-specific actions."""
    settings = load_settings()
    ch = settings.get("channels", {}).get(channel_key, {})
    chs = ch.get("settings", {})

    def done(label: str, ok: bool) -> str:
        return f"{label} ✅" if ok else label

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(done("Set Clip", chs.get("clip_set", False)), callback_data=f"action:setclip:{channel_key}")],
            [InlineKeyboardButton(done("Add Watermark", bool(chs.get("watermark_text"))), callback_data=f"action:watermark:{channel_key}")],
            [InlineKeyboardButton("Set Position", callback_data=f"action:position:{channel_key}")],
            [InlineKeyboardButton("Set Audio", callback_data=f"action:audio:{channel_key}")],
            [InlineKeyboardButton(done("Enable", chs.get("enabled", False)), callback_data=f"action:on:{channel_key}"),
             InlineKeyboardButton("Disable", callback_data=f"action:off:{channel_key}")],
            [InlineKeyboardButton(done("Delete Images", chs.get("delete_images", False)), callback_data=f"action:delimage:{channel_key}")],
        ]
    )

# ------------------------
# STEP 3: ADMIN COMMAND SYSTEM
# ------------------------

@app.on_message(filters.command("start"))
def start_handler(client: Client, message: Message):
    """Professional welcome and quick actions."""
    if not require_admin(message):
        return
    message.reply_text(
        "Welcome to Az Protection Bot.\n"
        "Use /addchannel to add a channel and /setup to configure it.",
    )
    message.reply_text(
        "Quick setup:",
        reply_markup=start_inline_keyboard(),
    )


@app.on_message(filters.command("addchannel"))
def addchannel_command(client: Client, message: Message):
    """Start add-channel flow."""
    if not require_admin(message):
        return
    PENDING["addchannel"].add(message.from_user.id)
    message.reply_text(
        "Please send the channel @username or numeric ID (e.g., -1001234567890).",
    )


@app.on_message(filters.command("setup"))
def setup_command(client: Client, message: Message):
    """Show added channels and let admin pick one."""
    if not require_admin(message):
        return
    settings = load_settings()
    message.reply_text(
        "Select a channel to configure:",
        reply_markup=channel_list_keyboard(settings),
    )


@app.on_message(filters.command("addwatermark"))
def addwatermark_command(client: Client, message: Message):
    """Prompt for watermark text for active channel."""
    if not require_admin(message):
        return
    settings = load_settings()
    active = settings.get("active_channel")
    if not active:
        message.reply_text("Please select a channel first using /setup.")
        return
    PENDING["watermark"][message.from_user.id] = {"stage": "text"}
    message.reply_text(
        "Send watermark text (or type OFF to disable watermark).",
    )


@app.on_message(filters.text & filters.private & ~filters.regex(r"^/"))
def pending_text_handler(client: Client, message: Message):
    """Handle pending admin prompts for addchannel/watermark."""
    if not require_admin(message):
        return
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in PENDING["addchannel"]:
        PENDING["addchannel"].discard(user_id)
        try:
            # Resolve chat
            chat_ref = int(text) if text.lstrip("-").isdigit() else text
            chat = client.get_chat(chat_ref)

            # Verify bot admin in the channel
            me = client.get_me()
            member = client.get_chat_member(chat.id, me.id)
            status = getattr(member, "status", "")
            if status not in {
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
                "administrator",
                "creator",
                "owner",
            }:
                message.reply_text(
                    "Bot is not an admin in that channel. Please add it as admin and retry."
                )
                return

            settings = load_settings()
            entry = ensure_channel(settings, chat)
            key = channel_key_from_chat(chat)
            settings["active_channel"] = key
            save_settings(settings)

            title = entry.get("title") or entry.get("username") or key
            message.reply_text(
                f"Channel added and selected: {title}",
                reply_markup=channel_actions_keyboard(key),
            )
        except Exception as exc:
            message.reply_text(f"Failed to add channel: {exc}")
        return

    if user_id in PENDING["watermark"]:
        settings = load_settings()
        active = settings.get("active_channel")
        if not active or active not in settings.get("channels", {}):
            message.reply_text("Please select a channel first using /setup.")
            PENDING["watermark"].pop(user_id, None)
            return

        stage = PENDING["watermark"][user_id].get("stage")
        ch_settings = settings["channels"][active]["settings"]

        if stage == "text":
            if text.lower() == "off":
                ch_settings["watermark_text"] = ""
                save_settings(settings)
                PENDING["watermark"].pop(user_id, None)
                message.reply_text("Watermark disabled.")
                return
            ch_settings["watermark_text"] = text
            save_settings(settings)
            PENDING["watermark"][user_id]["stage"] = "position"
            message.reply_text(
                "Choose watermark position: top_left, top_right, bottom_left, bottom_right, center, moving, random",
            )
            return

        if stage == "position":
            if text not in {"top_left", "top_right", "bottom_left", "bottom_right", "center", "moving", "random"}:
                message.reply_text(
                    "Invalid position. Use: top_left, top_right, bottom_left, bottom_right, center, moving, random"
                )
                return
            ch_settings["watermark_position"] = text
            save_settings(settings)
            PENDING["watermark"][user_id]["stage"] = "opacity"
            message.reply_text("Set opacity (0.1 to 1.0).")
            return

        if stage == "opacity":
            try:
                val = float(text)
            except ValueError:
                message.reply_text("Invalid opacity. Send a number between 0.1 and 1.0.")
                return
            if not (0.1 <= val <= 1.0):
                message.reply_text("Opacity must be between 0.1 and 1.0.")
                return
            ch_settings["watermark_opacity"] = val
            save_settings(settings)
            PENDING["watermark"][user_id]["stage"] = "size"
            message.reply_text("Set font size (e.g., 24).")
            return

        if stage == "size":
            try:
                size = int(text)
            except ValueError:
                message.reply_text("Invalid size. Send an integer like 24.")
                return
            if size < 10 or size > 200:
                message.reply_text("Font size must be between 10 and 200.")
                return
            ch_settings["watermark_size"] = size
            save_settings(settings)
            PENDING["watermark"][user_id]["stage"] = "style"
            message.reply_text("Set style: shadow or plain")
            return

        if stage == "style":
            if text not in {"shadow", "plain"}:
                message.reply_text("Invalid style. Use: shadow or plain.")
                return
            ch_settings["watermark_style"] = text
            save_settings(settings)
            PENDING["watermark"].pop(user_id, None)
            message.reply_text("Watermark saved.")
            return


@app.on_callback_query(filters.regex("^addchannel$"))
def addchannel_cb(client: Client, callback_query: CallbackQuery):
    if not callback_query.from_user or not is_admin(callback_query.from_user.id):
        callback_query.answer("Admins only.", show_alert=True)
        return
    PENDING["addchannel"].add(callback_query.from_user.id)
    callback_query.message.reply_text(
        "Please send the channel @username or numeric ID (e.g., -1001234567890).",
    )
    callback_query.answer("Send channel ID or @username.")


@app.on_callback_query(filters.regex("^setup$"))
def setup_cb(client: Client, callback_query: CallbackQuery):
    if not callback_query.from_user or not is_admin(callback_query.from_user.id):
        callback_query.answer("Admins only.", show_alert=True)
        return
    settings = load_settings()
    callback_query.message.edit_text(
        "Select a channel to configure:",
        reply_markup=channel_list_keyboard(settings),
    )
    callback_query.answer()


@app.on_callback_query(filters.regex("^select:(.+)"))
def select_channel_cb(client: Client, callback_query: CallbackQuery):
    if not callback_query.from_user or not is_admin(callback_query.from_user.id):
        callback_query.answer("Admins only.", show_alert=True)
        return
    channel_key = callback_query.data.split(":", 1)[1]
    settings = load_settings()
    if channel_key not in settings.get("channels", {}):
        callback_query.answer("Channel not found.", show_alert=True)
        return
    settings["active_channel"] = channel_key
    save_settings(settings)
    title = settings["channels"][channel_key].get("title") or channel_key
    callback_query.message.edit_text(
        f"Channel selected: {title}",
        reply_markup=channel_actions_keyboard(channel_key),
    )
    callback_query.answer()


@app.on_callback_query(filters.regex("^action:(.+)"))
def action_cb(client: Client, callback_query: CallbackQuery):
    if not callback_query.from_user or not is_admin(callback_query.from_user.id):
        callback_query.answer("Admins only.", show_alert=True)
        return
    _, action, channel_key = callback_query.data.split(":", 2)
    settings = load_settings()
    if channel_key not in settings.get("channels", {}):
        callback_query.answer("Channel not found.", show_alert=True)
        return
    settings["active_channel"] = channel_key
    ch_settings = settings["channels"][channel_key]["settings"]

    if action == "setclip":
        callback_query.message.reply_text(
            "Send /setclip with the clip attached in the same message.",
        )
    elif action == "watermark":
        PENDING["watermark"][callback_query.from_user.id] = {"stage": "text"}
        callback_query.message.reply_text(
            "Send watermark text (or type OFF to disable watermark).",
        )
    elif action == "position":
        callback_query.message.reply_text(
            "Use /setposition start|middle|end|random",
        )
    elif action == "audio":
        callback_query.message.reply_text(
            "Use /setaudio mix|clip|original",
        )
    elif action == "on":
        ch_settings["enabled"] = True
        callback_query.message.reply_text("Protection enabled.")
    elif action == "off":
        ch_settings["enabled"] = False
        callback_query.message.reply_text("Protection disabled.")
    elif action == "delimage":
        ch_settings["delete_images"] = not ch_settings.get("delete_images", False)
        callback_query.message.reply_text(
            f"Delete images set to {ch_settings['delete_images']}.",
        )

    save_settings(settings)
    callback_query.answer()
@app.on_message(filters.command("setclip"))
def setclip_handler(client: Client, message: Message):
    """
    /setclip
    Admin uploads a short protection clip (under 10 seconds).
    The clip must be attached in the SAME message (video or document).
    """
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return

    # We expect a video or document attached to this command message
    media = message.video or message.document
    if not media:
        message.reply_text(
            "Please send /setclip with a short video attached (under 10 seconds)."
        )
        return

    # Download the clip to our data folder
    message.reply_text("Downloading clip, please wait...")
    clip_path = get_clip_path(active)
    path = client.download_media(media, file_name=str(clip_path))
    clip_path = Path(path)

    try:
        duration = get_duration_seconds(clip_path)
    except Exception as exc:
        clip_path.unlink(missing_ok=True)
        message.reply_text(f"Could not read clip duration: {exc}")
        return

    # Validate duration (max 10 seconds)
    if duration > 10:
        clip_path.unlink(missing_ok=True)
        message.reply_text("Clip must be under 10 seconds.")
        return

    # Mark clip as set for this channel
    settings["channels"][active]["settings"]["clip_set"] = True
    save_settings(settings)

    message.reply_text(
        f"Clip saved successfully ({duration:.2f}s).",
    )


@app.on_message(filters.command("setposition"))
def setposition_handler(client: Client, message: Message):
    """/setposition start|middle|end|random"""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /setposition start|middle|end|random")
        return

    position = parts[1].strip().lower()
    if position not in {"start", "middle", "end", "random"}:
        message.reply_text("Invalid option. Choose start|middle|end|random.")
        return

    settings["channels"][active]["settings"]["position"] = position
    save_settings(settings)
    message.reply_text(f"Position set to {position}.")


@app.on_message(filters.command("setaudio"))
def setaudio_handler(client: Client, message: Message):
    """/setaudio mix|clip|original"""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /setaudio mix|clip|original")
        return

    audio = parts[1].strip().lower()
    if audio not in {"mix", "clip", "original"}:
        message.reply_text("Invalid option. Choose mix|clip|original.")
        return

    settings["channels"][active]["settings"]["audio"] = audio
    save_settings(settings)
    message.reply_text(f"Audio mode set to {audio}.")


@app.on_message(filters.command("setchannel"))
def setchannel_handler(client: Client, message: Message):
    """/setchannel <channel_id_or_username> | /setchannel off"""
    if not require_admin(message):
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /setchannel <channel_id_or_username> or /setchannel off")
        return

    value = parts[1].strip()
    settings = load_settings()

    if value.lower() == "off":
        settings["target_channel_id"] = None
        save_settings(settings)
        message.reply_text("Target channel cleared. Using TARGET_CHANNEL_ID env value.")
        return

    # If channel exists, just set active
    channel_key = value if value.lstrip("-").isdigit() else None
    if channel_key and channel_key in settings.get("channels", {}):
        settings["active_channel"] = channel_key
        save_settings(settings)
        message.reply_text(
            f"Active channel set to {channel_key}.",
        )
        return
    message.reply_text("Use /addchannel to add and verify the channel first.")


@app.on_message(filters.command("on"))
def on_handler(client: Client, message: Message):
    """Enable protection mode."""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return
    settings["channels"][active]["settings"]["enabled"] = True
    save_settings(settings)
    message.reply_text("Protection enabled.")


@app.on_message(filters.command("off"))
def off_handler(client: Client, message: Message):
    """Disable protection mode."""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return
    settings["channels"][active]["settings"]["enabled"] = False
    save_settings(settings)
    message.reply_text("Protection disabled.")


@app.on_message(filters.command("status"))
def status_handler(client: Client, message: Message):
    """Show current settings with explanations."""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    entry = settings.get("channels", {}).get(active) if active else None
    ch_settings = entry.get("settings") if entry else None
    title = entry.get("title") if entry else "None"
    target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
    status_text = (
        "Current Settings:\n"
        f"- Active Channel: {title}\n"
        f"- Enabled: {ch_settings['enabled'] if ch_settings else False}\n"
        f"- Position: {ch_settings['position'] if ch_settings else 'start'}\n"
        f"- Audio: {ch_settings['audio'] if ch_settings else 'clip'}\n"
        f"- Protect Thumbnail: {ch_settings['protect_thumbnail'] if ch_settings else True}\n"
        f"- Delete Original: {ch_settings['delete_original'] if ch_settings else True}\n"
        f"- Watermark: {('ON' if (ch_settings and ch_settings.get('watermark_text')) else 'OFF')}\n"
        f"- Clip Set: {ch_settings.get('clip_set', False) if ch_settings else False}\n"
        f"- Target Channel: {target_channel}\n"
        f"- Delete Images: {ch_settings.get('delete_images', False) if ch_settings else False}\n"
    )
    message.reply_text(status_text)


# Emergency stop command (optional advanced feature)
@app.on_message(filters.command("stop"))
def stop_handler(client: Client, message: Message):
    """Immediate emergency stop (same as /off)."""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if active and active in settings.get("channels", {}):
        settings["channels"][active]["settings"]["enabled"] = False
    save_settings(settings)
    message.reply_text("Emergency stop activated. Protection disabled.")


@app.on_message(filters.command("delimage"))
def delimage_handler(client: Client, message: Message):
    """/delimage on|off"""
    if not require_admin(message):
        return

    settings = load_settings()
    active = settings.get("active_channel")
    if not active or active not in settings.get("channels", {}):
        message.reply_text("Please select a channel first using /setup.")
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /delimage on|off")
        return

    value = parts[1].strip().lower()
    if value not in {"on", "off"}:
        message.reply_text("Usage: /delimage on|off")
        return

    settings["channels"][active]["settings"]["delete_images"] = (value == "on")
    save_settings(settings)
    message.reply_text(
        f"Delete images set to {settings['channels'][active]['settings']['delete_images']}.",
    )


# ------------------------
# STEP 4: CHANNEL MONITORING
# ------------------------
# We listen for new videos in the target channel.
# - filters.channel ensures we only get channel posts
# - filters.video ensures the message has a video
# - We also check TARGET_CHANNEL_ID to avoid touching other channels

@app.on_message(filters.channel & filters.video)
def channel_video_handler(client: Client, message: Message):
    settings = load_settings()

    channel_key = channel_key_from_chat(message.chat)

    # If channels are configured, only process configured channels
    if settings.get("channels"):
        if channel_key not in settings["channels"]:
            return
    else:
        # Legacy single-channel mode
        target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
        if target_channel and message.chat:
            if isinstance(target_channel, str) and target_channel.startswith("@"):
                if not message.chat.username or f"@{message.chat.username}".lower() != target_channel.lower():
                    return
            elif message.chat.id != target_channel:
                return

    entry = ensure_channel(settings, message.chat)
    ch_settings = entry["settings"]

    # If protection is turned off, ignore
    if not ch_settings.get("enabled"):
        return

    # Clip is optional now; watermark-only is allowed
    clip_path = get_clip_path(channel_key)
    has_clip = clip_path.exists()
    has_watermark = bool(ch_settings.get("watermark_text", "").strip())
    if not has_clip and not has_watermark:
        logger.warning("Clip and watermark both missing. Skipping.")
        return

    # Enqueue job for background workers
    queue_pos = VIDEO_QUEUE.qsize() + 1
    try:
        with QUEUE_COUNTER["lock"]:
            QUEUE_COUNTER["enqueued"] += 1
        VIDEO_QUEUE.put(
            {
                "message": message,
                "channel_key": channel_key,
                "settings": ch_settings,
                "has_clip": has_clip,
                "queue_pos": queue_pos,
            },
            block=False,
        )
    except queue.Full:
        logger.warning("Queue full. Dropping new video.")
        if ADMIN_IDS:
            try:
                client.send_message(ADMIN_IDS[0], "Queue full. New video skipped.")
            except Exception:
                pass
        return

    if ADMIN_IDS:
        try:
            qsize = VIDEO_QUEUE.qsize()
            client.send_message(
                ADMIN_IDS[0],
                f"Video queued (position {queue_pos}). Queue: {qsize}/{QUEUE_LIMIT}.",
            )
        except Exception:
            pass


@app.on_message(filters.channel & filters.photo)
def channel_photo_handler(client: Client, message: Message):
    settings = load_settings()

    channel_key = channel_key_from_chat(message.chat)

    if settings.get("channels"):
        if channel_key not in settings["channels"]:
            return
    else:
        target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
        if target_channel and message.chat:
            if isinstance(target_channel, str) and target_channel.startswith("@"):
                if not message.chat.username or f"@{message.chat.username}".lower() != target_channel.lower():
                    return
            elif message.chat.id != target_channel:
                return

    entry = ensure_channel(settings, message.chat)
    ch_settings = entry["settings"]

    if not ch_settings.get("delete_images"):
        return

    # Delete incoming images from the channel
    try:
        client.delete_messages(message.chat.id, message.id)
    except Exception:
        pass


# ------------------------
# STEP 5: VIDEO PROCESSING (MAIN LOGIC)
# ------------------------

def process_video(original_path: Path, clip_path: Optional[Path], output_path: Path, settings: dict):
    """
    STEP-BY-STEP LOGIC:
    1) Read original video
    2) Read protection clip
    3) Decide insertion position
    4) Merge / concat clip
    5) Handle audio based on admin setting
    6) Slightly modify first frame if enabled
    """

    # 1) Read durations
    original_duration = get_duration_seconds(original_path)
    # Read original video properties so we can fit the clip to it
    orig_w, orig_h, orig_fps = get_video_props(original_path)

    # If no clip is provided, just apply watermark/protection to original and return
    if clip_path is None:
        protect_thumb = settings.get("protect_thumbnail", True)
        vf_parts = []
        if protect_thumb:
            vf_parts.append("drawbox=x=0:y=0:w=2:h=2:color=black@0.01:t=fill:enable='eq(n,0)'")

        wm_text = settings.get("watermark_text", "").strip()
        if wm_text:
            safe_text = wm_text.replace(":", r"\:").replace("'", r"\'")
            wm_pos = settings.get("watermark_position", "bottom_right")
            wm_opacity = settings.get("watermark_opacity", 0.5)
            wm_size = settings.get("watermark_size", 24)
            if wm_pos == "top_left":
                x, y = "10", "10"
            elif wm_pos == "top_right":
                x, y = "w-tw-10", "10"
            elif wm_pos == "bottom_left":
                x, y = "10", "h-th-10"
            elif wm_pos == "center":
                x, y = "(w-tw)/2", "(h-th)/2"
            elif wm_pos == "random":
                # Fixed random position per video (computed in Python)
                rx = random.random()
                ry = random.random()
                x, y = f"(w-tw)*{rx:.4f}", f"(h-th)*{ry:.4f}"
            elif wm_pos == "moving":
                period = 12.0
                x = f"(w-tw)*((t/{period})-floor(t/{period}))"
                y = f"(h-th)*((t/{period})-floor(t/{period}))"
            else:
                x, y = "w-tw-10", "h-th-10"
            wm_style = settings.get("watermark_style", "shadow")
            shadow = "shadowx=2:shadowy=2:shadowcolor=black@0.5" if wm_style == "shadow" else ""
            eval_part = "eval=frame" if wm_pos == "moving" else ""
            extra = f":{eval_part}" + (f":{shadow}" if shadow else "")
            if eval_part == "":
                extra = (f":{shadow}" if shadow else "")
            vf_parts.append(
                f"drawtext=fontfile={DEFAULT_FONT}:text='{safe_text}':"
                f"x={x}:y={y}:fontsize={wm_size}:fontcolor=white@{wm_opacity}"
                f"{extra}"
            )

        vf = ",".join(vf_parts) if vf_parts else "null"
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(original_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path),
        ])
        return

    # We read clip duration so you can extend the logic later if needed.
    # (Example: avoid inserting the clip too close to the end.)
    clip_duration = get_duration_seconds(clip_path)

    # 2) Decide insertion position (in seconds)
    position = settings.get("position", "start")
    if position == "start":
        insert_time = 0.0
    elif position == "middle":
        insert_time = max(0.0, original_duration / 2.0)
    elif position == "end":
        insert_time = max(0.0, original_duration)  # insert at the end
    else:  # random
        # Keep a safe range so we don't insert too close to the end
        max_pos = max(0.0, original_duration - clip_duration)
        insert_time = random.uniform(0.0, max_pos)

    # 3) Prepare temp files
    workdir = output_path.parent
    pre_path = workdir / "pre.mp4"
    post_path = workdir / "post.mp4"
    clip_use_path = workdir / "clip_use.mp4"
    concat_list = workdir / "concat.txt"

    # 4) Split the original into pre and post parts
    #    We re-encode to ensure the files can be concatenated reliably.
    if insert_time > 0.01:
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(original_path),
            "-t", str(insert_time),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "128k",
            str(pre_path),
        ])
    else:
        pre_path = None

    # Post part (from insert_time to end)
    if insert_time < original_duration - 0.01:
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(original_path),
            "-ss", str(insert_time),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "128k",
            str(post_path),
        ])
    else:
        post_path = None

    # 5) Handle audio based on admin setting
    #    IMPORTANT: We fit the clip to the original video size (not the other way around).
    #    This keeps the original video's frames untouched.
    clip_vf = (
        f"scale={orig_w}:{orig_h}:force_original_aspect_ratio=decrease,"
        f"pad={orig_w}:{orig_h}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1,format=yuv420p"
    )
    audio_mode = settings.get("audio", "clip")
    if audio_mode == "original":
        # Mute clip audio (so only original audio plays, clip is silent)
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", clip_vf,
            "-r", f"{orig_fps:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-an",
            str(clip_use_path),
        ])
    elif audio_mode == "mix":
        # Simple mix approach: reduce clip audio volume to avoid harsh overlap
        # (If you want a true overlay with original audio, implement a more
        # advanced filter pipeline here.)
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", clip_vf,
            "-r", f"{orig_fps:.3f}",
            "-filter:a", "volume=0.6",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "128k",
            str(clip_use_path),
        ])
    else:
        # Use clip audio as-is
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", clip_vf,
            "-r", f"{orig_fps:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "128k",
            str(clip_use_path),
        ])

    # 6) Build concat list in the correct order
    lines = []
    if pre_path:
        lines.append(f"file '{pre_path.as_posix()}'")
    lines.append(f"file '{clip_use_path.as_posix()}'")
    if post_path:
        lines.append(f"file '{post_path.as_posix()}'")
    concat_list.write_text("\n".join(lines), encoding="utf-8")

    # 7) Concatenate and optionally modify the first frame
    #    We re-encode for safety and to allow thumbnail protection.
    protect_thumb = settings.get("protect_thumbnail", True)

    # A tiny drawbox only on the first frame changes the hash without visible impact.
    vf_parts = []
    if protect_thumb:
        vf_parts.append("drawbox=x=0:y=0:w=2:h=2:color=black@0.01:t=fill:enable='eq(n,0)'")

    # Optional watermark text on final output
    wm_text = settings.get("watermark_text", "").strip()
    if wm_text:
        # Escape characters that break drawtext
        safe_text = wm_text.replace(":", r"\:").replace("'", r"\'")
        wm_pos = settings.get("watermark_position", "bottom_right")
        wm_opacity = settings.get("watermark_opacity", 0.5)
        wm_size = settings.get("watermark_size", 24)

        if wm_pos == "top_left":
            x, y = "10", "10"
        elif wm_pos == "top_right":
            x, y = "w-tw-10", "10"
        elif wm_pos == "bottom_left":
            x, y = "10", "h-th-10"
        elif wm_pos == "center":
            x, y = "(w-tw)/2", "(h-th)/2"
        elif wm_pos == "random":
            # Fixed random position per video (computed in Python)
            rx = random.random()
            ry = random.random()
            x, y = f"(w-tw)*{rx:.4f}", f"(h-th)*{ry:.4f}"
        elif wm_pos == "moving":
            # Smooth diagonal movement (top-left -> bottom-right -> loop)
            # Period controls speed (bigger = slower)
            period = 12.0
            x = f"(w-tw)*((t/{period})-floor(t/{period}))"
            y = f"(h-th)*((t/{period})-floor(t/{period}))"
        else:
            x, y = "w-tw-10", "h-th-10"

        wm_style = settings.get("watermark_style", "shadow")
        shadow = "shadowx=2:shadowy=2:shadowcolor=black@0.5" if wm_style == "shadow" else ""
        eval_part = "eval=frame" if wm_pos == "moving" else ""
        extra = f":{eval_part}" + (f":{shadow}" if shadow else "")
        if eval_part == "":
            extra = (f":{shadow}" if shadow else "")
        vf_parts.append(
            f"drawtext=fontfile={DEFAULT_FONT}:text='{safe_text}':"
            f"x={x}:y={y}:fontsize={wm_size}:fontcolor=white@{wm_opacity}"
            f"{extra}"
        )

    vf = ",".join(vf_parts) if vf_parts else "null"

    run_cmd([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ])


def process_video_job(client: Client, job: dict) -> None:
    """Worker function to process a queued video job."""
    message = job["message"]
    channel_key = job["channel_key"]
    ch_settings = job["settings"]
    worker_label = job.get("worker_label", "worker")

    # Notify admin if possible
    admin_msg = None
    if ADMIN_IDS:
        try:
            qsize = VIDEO_QUEUE.qsize()
            admin_msg = client.send_message(
                ADMIN_IDS[0],
                f"{worker_label}: processing queue #{job['queue_pos']} | queue {qsize}/{QUEUE_LIMIT}",
            )
        except Exception:
            admin_msg = None

    with COUNTERS["lock"]:
        COUNTERS["running"] += 1
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            original_path = tmpdir / "original.mp4"
            processed_path = tmpdir / "processed.mp4"
            thumb_path = tmpdir / "thumb.jpg"

            dl_state = {"last": 0.0}
            with COUNTERS["lock"]:
                COUNTERS["downloading"] += 1
            message.download(
                file_name=str(original_path),
                progress=progress_callback,
                progress_args=(admin_msg, "Downloading", dl_state),
            )
            with COUNTERS["lock"]:
                COUNTERS["downloading"] -= 1

            # Delete original post BEFORE processing/upload (as requested).
            if ch_settings.get("delete_original"):
                try:
                    client.delete_messages(message.chat.id, message.id)
                except Exception:
                    pass

            clip_path = get_clip_path(channel_key) if job["has_clip"] else None

            try:
                process_video(
                    original_path=original_path,
                    clip_path=clip_path,
                    output_path=processed_path,
                    settings=ch_settings,
                )

                extract_clip_thumbnail(processed_path, thumb_path)

                caption = message.caption or ""
                up_state = {"last": 0.0}
                with COUNTERS["lock"]:
                    COUNTERS["uploading"] += 1
                client.send_video(
                    chat_id=message.chat.id,
                    video=str(processed_path),
                    caption=caption,
                    thumb=str(thumb_path),
                    supports_streaming=True,
                    progress=progress_callback,
                    progress_args=(admin_msg, "Uploading", up_state),
                )
                with COUNTERS["lock"]:
                    COUNTERS["uploading"] -= 1

                # Extra safety cleanup (tempdir will also remove these)
                for p in (original_path, processed_path, thumb_path):
                    try:
                        p.unlink(missing_ok=True)
                    except Exception:
                        pass

                if ADMIN_IDS:
                    try:
                        client.send_message(ADMIN_IDS[0], "Video processed and uploaded.")
                    except Exception:
                        pass
                if admin_msg:
                    try:
                        admin_msg.delete()
                    except Exception:
                        pass

            except Exception as exc:
                logger.exception("Processing failed: %s", exc)
                if ADMIN_IDS:
                    try:
                        client.send_message(ADMIN_IDS[0], f"Processing failed: {exc}")
                    except Exception:
                        pass
            finally:
                with QUEUE_COUNTER["lock"]:
                    QUEUE_COUNTER["processed"] += 1
    finally:
        with COUNTERS["lock"]:
            COUNTERS["running"] -= 1


def worker_loop(client: Client, worker_id: int) -> None:
    """Background worker that processes queued jobs."""
    while True:
        job = VIDEO_QUEUE.get()
        try:
            job["worker_label"] = f"worker-{worker_id}"
            process_video_job(client, job)
        finally:
            VIDEO_QUEUE.task_done()


# ------------------------
# STEP 6: THUMBNAIL & METADATA PROTECTION
# ------------------------
# The drawbox filter above modifies the first frame slightly. This changes
# the visual hash and makes duplicate detection harder. We also generate
# a new thumbnail from the processed video so it doesn't reuse the original.


# ------------------------
# STEP 7: RE-UPLOAD SYSTEM
# ------------------------
# The channel handler above uploads the processed video and optionally deletes
# the original message. Progress messages are sent to the first admin.
# We avoid spamming by sending only a few messages per video.


# ------------------------
# STEP 8: CLEANUP & SAFETY
# ------------------------
# Temporary files are created inside a TemporaryDirectory, which is automatically
# deleted when processing is finished. Errors are caught and logged.
# This avoids leaving large files on disk.


# ------------------------
# STEP 9: OPTIONAL ADVANCED FEATURES
# ------------------------
# - Randomize clip timing: already supported via /setposition random
# - Emergency stop: /stop
# - Multi-admin support: ADMIN_IDS can contain multiple IDs
# - To extend: add new commands or settings in load_settings()


if __name__ == "__main__":
    # Basic checks to help beginners
    if API_ID == 0 or not API_HASH or not BOT_TOKEN:
        print("ERROR: Please set API_ID, API_HASH, and BOT_TOKEN env vars.")
        raise SystemExit(1)
    if TARGET_CHANNEL_ID == 0:
        print("WARNING: TARGET_CHANNEL_ID is not set. Bot will process all channels.")

    print("Bot starting...")
    # Start background workers
    for i in range(max(1, WORKER_COUNT)):
        t = threading.Thread(target=worker_loop, args=(app, i), daemon=True)
        t.start()
    app.run()
