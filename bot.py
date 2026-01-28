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
from pathlib import Path
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup

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
CLIP_FILE = DATA_DIR / "clip.mp4"

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

def load_settings() -> dict:
    """Load settings from JSON or return defaults."""
    defaults = {
        "enabled": False,
        "position": "start",        # start | middle | end | random
        "audio": "clip",            # mix | clip | original
        "protect_thumbnail": True,   # modify first frame slightly
        "delete_original": True,     # delete original channel post before re-upload
        "multi_admin": True,         # allow multiple admins
        "target_channel_id": None,   # set via /setchannel (overrides env)
        "delete_images": False,      # delete incoming channel images
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


def main_keyboard() -> ReplyKeyboardMarkup:
    """Simple reply keyboard for quick admin actions."""
    return ReplyKeyboardMarkup(
        [
            ["/status", "/setclip"],
            ["/setposition", "/setaudio"],
            ["/setchannel", "/delimage"],
            ["/on", "/off"],
        ],
        resize_keyboard=True,
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
        status_msg.edit_text(f"{label}... {percent:.1f}% ({mb_cur:.1f}/{mb_total:.1f} MB)")
    except Exception:
        pass


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
        "Use the buttons below to configure protection settings.",
        reply_markup=main_keyboard(),
    )


@app.on_message(filters.command("setclip"))
def setclip_handler(client: Client, message: Message):
    """
    /setclip
    Admin uploads a short protection clip (under 10 seconds).
    The clip must be attached in the SAME message (video or document).
    """
    if not require_admin(message):
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
    path = client.download_media(media, file_name=str(CLIP_FILE))
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

    message.reply_text(
        f"Clip saved successfully ({duration:.2f}s).",
        reply_markup=main_keyboard(),
    )


@app.on_message(filters.command("setposition"))
def setposition_handler(client: Client, message: Message):
    """/setposition start|middle|end|random"""
    if not require_admin(message):
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /setposition start|middle|end|random")
        return

    position = parts[1].strip().lower()
    if position not in {"start", "middle", "end", "random"}:
        message.reply_text("Invalid option. Choose start|middle|end|random.")
        return

    settings = load_settings()
    settings["position"] = position
    save_settings(settings)
    message.reply_text(f"Position set to {position}.", reply_markup=main_keyboard())


@app.on_message(filters.command("setaudio"))
def setaudio_handler(client: Client, message: Message):
    """/setaudio mix|clip|original"""
    if not require_admin(message):
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /setaudio mix|clip|original")
        return

    audio = parts[1].strip().lower()
    if audio not in {"mix", "clip", "original"}:
        message.reply_text("Invalid option. Choose mix|clip|original.")
        return

    settings = load_settings()
    settings["audio"] = audio
    save_settings(settings)
    message.reply_text(f"Audio mode set to {audio}.", reply_markup=main_keyboard())


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

    # Allow @username or numeric ID
    if value.startswith("@"):
        settings["target_channel_id"] = value
    else:
        try:
            settings["target_channel_id"] = int(value)
        except ValueError:
            message.reply_text("Invalid channel. Use @username or numeric ID like -1001234567890.")
            return

    save_settings(settings)
    message.reply_text(
        f"Target channel set to {settings['target_channel_id']}.",
        reply_markup=main_keyboard(),
    )


@app.on_message(filters.command("on"))
def on_handler(client: Client, message: Message):
    """Enable protection mode."""
    if not require_admin(message):
        return

    settings = load_settings()
    settings["enabled"] = True
    save_settings(settings)
    message.reply_text("Protection enabled.", reply_markup=main_keyboard())


@app.on_message(filters.command("off"))
def off_handler(client: Client, message: Message):
    """Disable protection mode."""
    if not require_admin(message):
        return

    settings = load_settings()
    settings["enabled"] = False
    save_settings(settings)
    message.reply_text("Protection disabled.", reply_markup=main_keyboard())


@app.on_message(filters.command("status"))
def status_handler(client: Client, message: Message):
    """Show current settings with explanations."""
    if not require_admin(message):
        return

    settings = load_settings()
    target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
    status_text = (
        "Current Settings:\n"
        f"- Enabled: {settings['enabled']}\n"
        f"- Position: {settings['position']} (where the clip is inserted)\n"
        f"- Audio: {settings['audio']} (how clip audio is handled)\n"
        f"- Protect Thumbnail: {settings['protect_thumbnail']} (modifies first frame)\n"
        f"- Delete Original: {settings['delete_original']}\n"
        f"- Target Channel: {target_channel}\n"
        f"- Delete Images: {settings.get('delete_images', False)}\n"
    )
    message.reply_text(status_text, reply_markup=main_keyboard())


# Emergency stop command (optional advanced feature)
@app.on_message(filters.command("stop"))
def stop_handler(client: Client, message: Message):
    """Immediate emergency stop (same as /off)."""
    if not require_admin(message):
        return

    settings = load_settings()
    settings["enabled"] = False
    save_settings(settings)
    message.reply_text("Emergency stop activated. Protection disabled.", reply_markup=main_keyboard())


@app.on_message(filters.command("delimage"))
def delimage_handler(client: Client, message: Message):
    """/delimage on|off"""
    if not require_admin(message):
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        message.reply_text("Usage: /delimage on|off")
        return

    value = parts[1].strip().lower()
    if value not in {"on", "off"}:
        message.reply_text("Usage: /delimage on|off")
        return

    settings = load_settings()
    settings["delete_images"] = (value == "on")
    save_settings(settings)
    message.reply_text(
        f"Delete images set to {settings['delete_images']}.",
        reply_markup=main_keyboard(),
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

    # Only operate on the target channel (settings override env)
    target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
    if target_channel and message.chat:
        # If target is a username like "@mychannel"
        if isinstance(target_channel, str) and target_channel.startswith("@"):
            if not message.chat.username or f"@{message.chat.username}".lower() != target_channel.lower():
                return
        # If target is a numeric ID
        elif message.chat.id != target_channel:
            return

    # If protection is turned off, ignore
    if not settings.get("enabled"):
        return

    # If clip is missing, we can't process
    if not CLIP_FILE.exists():
        logger.warning("Clip not set. Skipping.")
        return

    # Notify the first admin if possible
    if ADMIN_IDS:
        try:
            admin_msg = client.send_message(ADMIN_IDS[0], "Processing new channel video...")
        except Exception:
            admin_msg = None
    else:
        admin_msg = None

    # Download the original video to a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        original_path = tmpdir / "original.mp4"
        processed_path = tmpdir / "processed.mp4"
        thumb_path = tmpdir / "thumb.jpg"

        dl_state = {"last": 0.0}
        message.download(
            file_name=str(original_path),
            progress=progress_callback,
            progress_args=(admin_msg, "Downloading", dl_state),
        )

        # Delete original post BEFORE processing/upload (as requested).
        # This is riskier if processing fails, but ensures the original is removed.
        if settings.get("delete_original"):
            try:
                client.delete_messages(message.chat.id, message.id)
            except Exception:
                pass

        try:
            process_video(
                original_path=original_path,
                clip_path=CLIP_FILE,
                output_path=processed_path,
                settings=settings,
            )

            # Create a thumbnail from the processed video (first frame)
            extract_clip_thumbnail(processed_path, thumb_path)

            # Upload back to channel
            caption = message.caption or ""
            up_state = {"last": 0.0}
            client.send_video(
                chat_id=message.chat.id,
                video=str(processed_path),
                caption=caption,
                thumb=str(thumb_path),
                supports_streaming=True,
                progress=progress_callback,
                progress_args=(admin_msg, "Uploading", up_state),
            )

            # Original post deletion was handled earlier.

            # Extra safety cleanup (tempdir will also remove these)
            for p in (original_path, processed_path, thumb_path):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

            # Notify admin then remove progress message
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


@app.on_message(filters.channel & filters.photo)
def channel_photo_handler(client: Client, message: Message):
    settings = load_settings()

    # Only operate on the target channel (settings override env)
    target_channel = settings.get("target_channel_id") or TARGET_CHANNEL_ID
    if target_channel and message.chat:
        if isinstance(target_channel, str) and target_channel.startswith("@"):
            if not message.chat.username or f"@{message.chat.username}".lower() != target_channel.lower():
                return
        elif message.chat.id != target_channel:
            return

    # If delete_images is off, ignore
    if not settings.get("delete_images"):
        return

    # Delete incoming images from the channel
    try:
        client.delete_messages(message.chat.id, message.id)
    except Exception:
        pass


# ------------------------
# STEP 5: VIDEO PROCESSING (MAIN LOGIC)
# ------------------------

def process_video(original_path: Path, clip_path: Path, output_path: Path, settings: dict):
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
    # We read clip duration so you can extend the logic later if needed.
    # (Example: avoid inserting the clip too close to the end.)
    clip_duration = get_duration_seconds(clip_path)
    # Read original video properties so we can fit the clip to it
    orig_w, orig_h, orig_fps = get_video_props(original_path)

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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
    vf = "drawbox=x=0:y=0:w=2:h=2:color=black@0.01:t=fill:enable='eq(n,0)'" if protect_thumb else "null"

    run_cmd([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ])


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
    app.run()
