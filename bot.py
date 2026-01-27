"""
========================
TELEGRAM VIDEO PROTECTION BOT
========================
This bot automatically protects channel videos by injecting
a protection clip into every video before publishing.

Author: Expert Python Developer
Purpose: Prevent video theft and unauthorized reuse
"""

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Import our custom modules
from config import config
from video_processor import process_video, get_video_duration, validate_video, extract_thumbnail

# ========================
# STEP 1: LOAD ENVIRONMENT VARIABLES
# ========================
# Load API keys and secrets from .env file
# This keeps sensitive information out of the code
load_dotenv()

# Get configuration from environment
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")
SESSION_NAME = os.getenv("SESSION_NAME", "video_protector_bot")

# Validate that all required variables are set
if not all([API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, CHANNEL_ID]):
    print("❌ ERROR: Missing required environment variables!")
    print("Please check your .env file and ensure all values are set.")
    exit(1)

print("✓ Environment variables loaded successfully")
print(f"  Admin ID: {ADMIN_ID}")
print(f"  Channel: {CHANNEL_ID}")

# ========================
# STEP 2: INITIALIZE TELEGRAM CLIENT
# ========================
# Create Pyrogram client instance
# This is the main bot object that handles all Telegram interactions
app = Client(
    name=SESSION_NAME,           # Session name (creates a .session file)
    api_id=API_ID,               # Your API ID from my.telegram.org
    api_hash=API_HASH,           # Your API Hash from my.telegram.org
    bot_token=BOT_TOKEN,         # Bot token from @BotFather
    workdir=".",                 # Where to store session files
)

print("✓ Telegram client initialized")

# ========================
# HELPER: ADMIN-ONLY DECORATOR
# ========================
# This ensures only the admin can use bot commands
def admin_only(func):
    """
    Decorator to restrict commands to admin only.
    Checks if message sender is the authorized admin.
    """
    async def wrapper(client, message: Message):
        # Check if sender is admin
        if message.from_user.id != ADMIN_ID:
            await message.reply_text(
                "❌ **Access Denied**\n\n"
                "This bot is restricted to authorized admin only.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # If admin, execute the command
        return await func(client, message)
    return wrapper


# ========================
# HELPER: DOWNLOAD PROGRESS CALLBACK
# ========================
async def progress_callback(current, total, message: Message, action: str):
    """
    Show download/upload progress to admin.
    Updates message every 5% to avoid spam.
    
    Args:
        current: Current bytes transferred
        total: Total bytes to transfer
        message: Message to update
        action: "Downloading" or "Uploading"
    """
    # Calculate percentage
    percent = (current / total) * 100
    
    # Update every 5% to avoid too many edits
    if int(percent) % 5 == 0:
        try:
            await message.edit_text(
                f"{action}... {percent:.1f}%\n"
                f"📊 {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB"
            )
        except:
            pass  # Ignore errors (e.g., message not modified)


# ========================
# COMMAND: /start
# ========================
@app.on_message(filters.command("start") & filters.private)
@admin_only
async def start_command(client: Client, message: Message):
    """
    Welcome message and bot introduction.
    Shows when admin starts the bot.
    """
    welcome_text = """
🛡️ **Video Protection Bot**

Welcome! This bot automatically protects your channel videos by injecting a protection clip.

**How it works:**
1. Set a protection clip with /setclip
2. Configure position and audio with /setposition and /setaudio
3. Enable protection with /on
4. Post videos to your channel - they'll be auto-protected!

**Available Commands:**
/setclip - Upload protection clip (2-10 seconds)
/setposition - Set where to insert clip
/setaudio - Set audio mixing mode
/on - Enable protection mode
/off - Disable protection mode
/status - Show current settings
/help - Show this help message

**Current Status:**
Protection is currently **{}**

Use /status to see detailed settings.
    """.format("ENABLED ✅" if config.get("protection_enabled") else "DISABLED ❌")
    
    await message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


# ========================
# COMMAND: /help
# ========================
@app.on_message(filters.command("help") & filters.private)
@admin_only
async def help_command(client: Client, message: Message):
    """
    Show detailed help information.
    """
    help_text = """
📚 **Detailed Help**

**Setup Steps:**
1️⃣ Upload a protection clip (2-10 seconds) using /setclip
2️⃣ Choose insertion position using /setposition
3️⃣ Choose audio mode using /setaudio
4️⃣ Enable protection using /on

**Commands Explained:**

**/setclip**
Upload a short video clip (2-10 seconds) that will be inserted into all channel videos.
This clip should contain your watermark, logo, or protection message.

**/setposition**
Choose where to insert the protection clip:
• `start` - At the beginning (recommended)
• `middle` - In the middle of the video
• `end` - At the end
• `random` - Random position (different each time)

**/setaudio**
Choose how to handle audio:
• `mix` - Mix both audios together
• `clip` - Use only protection clip audio
• `original` - Use only original video audio

**/on** - Enable automatic protection
**/off** - Disable automatic protection
**/status** - View current configuration

**How Protection Works:**
When you post a video to your channel, the bot will:
1. Download the original video
2. Insert your protection clip
3. Re-upload the protected version
4. Delete the original (optional)

This changes the video hash, preventing unauthorized reuse.
    """
    
    await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


# ========================
# COMMAND: /status
# ========================
@app.on_message(filters.command("status") & filters.private)
@admin_only
async def status_command(client: Client, message: Message):
    """
    Show current bot configuration and status.
    """
    status_text = config.get_status_text()
    await message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


# ========================
# COMMAND: /setclip
# ========================
@app.on_message(filters.command("setclip") & filters.private)
@admin_only
async def setclip_command(client: Client, message: Message):
    """
    Initiate protection clip upload process.
    Admin needs to send a video after this command.
    """
    await message.reply_text(
        "📹 **Upload Protection Clip**\n\n"
        "Please send me a video file (2-10 seconds) that will be used as the protection clip.\n\n"
        "**Requirements:**\n"
        "• Duration: 2-10 seconds\n"
        "• Format: MP4, MOV, or any video format\n"
        "• Size: Under 50 MB recommended\n\n"
        "Send the video now...",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================
# HANDLER: RECEIVE PROTECTION CLIP
# ========================
@app.on_message(filters.video & filters.private)
@admin_only
async def receive_clip(client: Client, message: Message):
    """
    Handle protection clip upload from admin.
    Validates and saves the clip.
    """
    status_msg = await message.reply_text("⏳ Processing your clip...")
    
    try:
        # Get video info
        video = message.video
        duration = video.duration
        
        # Validate duration (2-10 seconds)
        if duration < 2:
            await status_msg.edit_text(
                "❌ **Clip Too Short**\n\n"
                f"Your clip is {duration}s long.\n"
                "Minimum duration: 2 seconds\n\n"
                "Please send a longer clip."
            )
            return
        
        if duration > 10:
            await status_msg.edit_text(
                "❌ **Clip Too Long**\n\n"
                f"Your clip is {duration}s long.\n"
                "Maximum duration: 10 seconds\n\n"
                "Please send a shorter clip."
            )
            return
        
        # Download the clip
        await status_msg.edit_text("⬇️ Downloading clip...")
        
        clip_path = "protection_clip.mp4"
        await message.download(
            file_name=clip_path,
            progress=progress_callback,
            progress_args=(status_msg, "Downloading")
        )
        
        # Validate the downloaded file
        await status_msg.edit_text("🔍 Validating clip...")
        valid, msg = validate_video(clip_path, max_duration=10)
        
        if not valid:
            await status_msg.edit_text(f"❌ **Validation Failed**\n\n{msg}")
            return
        
        # Save clip info to config
        config.set("clip_path", clip_path)
        config.set("clip_duration", duration)
        
        await status_msg.edit_text(
            f"✅ **Protection Clip Saved!**\n\n"
            f"📊 Duration: {duration:.1f} seconds\n"
            f"📁 Size: {video.file_size / (1024*1024):.2f} MB\n\n"
            f"Your protection clip is ready to use.\n"
            f"Use /on to enable protection mode.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")


# ========================
# COMMAND: /setposition
# ========================
@app.on_message(filters.command("setposition") & filters.private)
@admin_only
async def setposition_command(client: Client, message: Message):
    """
    Set where to insert the protection clip.
    """
    # Check if position is provided in command
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        # No position provided, show options
        await message.reply_text(
            "📍 **Set Clip Position**\n\n"
            "Choose where to insert the protection clip:\n\n"
            "**Options:**\n"
            "`/setposition start` - At the beginning (recommended)\n"
            "`/setposition middle` - In the middle\n"
            "`/setposition end` - At the end\n"
            "`/setposition random` - Random position each time\n\n"
            f"**Current:** {config.get('position', 'start')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get position from command
    position = parts[1].lower().strip()
    
    # Validate position
    valid_positions = ["start", "middle", "end", "random"]
    if position not in valid_positions:
        await message.reply_text(
            f"❌ Invalid position: `{position}`\n\n"
            f"Valid options: {', '.join(valid_positions)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Save position
    config.set("position", position)
    
    await message.reply_text(
        f"✅ **Position Updated**\n\n"
        f"Clip will be inserted at: **{position}**",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================
# COMMAND: /setaudio
# ========================
@app.on_message(filters.command("setaudio") & filters.private)
@admin_only
async def setaudio_command(client: Client, message: Message):
    """
    Set audio mixing mode.
    """
    # Check if mode is provided in command
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        # No mode provided, show options
        await message.reply_text(
            "🔊 **Set Audio Mode**\n\n"
            "Choose how to handle audio:\n\n"
            "**Options:**\n"
            "`/setaudio mix` - Mix both audios together\n"
            "`/setaudio clip` - Use only protection clip audio\n"
            "`/setaudio original` - Use only original video audio\n\n"
            f"**Current:** {config.get('audio_mode', 'mix')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get mode from command
    audio_mode = parts[1].lower().strip()
    
    # Validate mode
    valid_modes = ["mix", "clip", "original"]
    if audio_mode not in valid_modes:
        await message.reply_text(
            f"❌ Invalid audio mode: `{audio_mode}`\n\n"
            f"Valid options: {', '.join(valid_modes)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Save mode
    config.set("audio_mode", audio_mode)
    
    await message.reply_text(
        f"✅ **Audio Mode Updated**\n\n"
        f"Audio mode: **{audio_mode}**",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================
# COMMAND: /on
# ========================
@app.on_message(filters.command("on") & filters.private)
@admin_only
async def enable_protection(client: Client, message: Message):
    """
    Enable automatic video protection.
    """
    # Check if clip is set
    clip_path = config.get("clip_path")
    if not clip_path or not os.path.exists(clip_path):
        await message.reply_text(
            "❌ **Cannot Enable Protection**\n\n"
            "You must set a protection clip first!\n"
            "Use /setclip to upload a clip.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Enable protection
    config.set("protection_enabled", True)
    
    await message.reply_text(
        "🟢 **Protection Enabled!**\n\n"
        "All videos posted to your channel will now be automatically protected.\n\n"
        f"**Settings:**\n"
        f"• Position: {config.get('position')}\n"
        f"• Audio: {config.get('audio_mode')}\n"
        f"• Clip: {config.get('clip_duration'):.1f}s\n\n"
        "Use /off to disable protection.",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================
# COMMAND: /off
# ========================
@app.on_message(filters.command("off") & filters.private)
@admin_only
async def disable_protection(client: Client, message: Message):
    """
    Disable automatic video protection.
    """
    config.set("protection_enabled", False)
    
    await message.reply_text(
        "🔴 **Protection Disabled**\n\n"
        "Videos will no longer be automatically protected.\n"
        "Use /on to re-enable protection.",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================
# MAIN HANDLER: CHANNEL VIDEO MONITORING
# ========================
@app.on_message(filters.video & filters.channel)
async def handle_channel_video(client: Client, message: Message):
    """
    Main handler for channel videos.
    This is triggered whenever a video is posted to the channel.
    
    Process:
    1. Check if protection is enabled
    2. Download original video
    3. Process with protection clip
    4. Upload protected version
    5. Delete original
    6. Cleanup temp files
    """
    
    # Check if this is our target channel
    if message.chat.username != CHANNEL_ID.replace("@", "") and str(message.chat.id) != CHANNEL_ID:
        return  # Not our channel, ignore
    
    # Check if protection is enabled
    if not config.get("protection_enabled"):
        print(f"⚠ Video posted but protection is disabled. Skipping.")
        return
    
    # Check if clip is set
    clip_path = config.get("clip_path")
    if not clip_path or not os.path.exists(clip_path):
        print(f"⚠ Video posted but no protection clip set. Skipping.")
        # Notify admin
        try:
            await client.send_message(
                ADMIN_ID,
                "⚠️ **Warning:** Video posted to channel but no protection clip is set!\n"
                "Use /setclip to set a protection clip."
            )
        except:
            pass
        return
    
    print(f"\n{'='*60}")
    print(f"🎬 NEW VIDEO DETECTED IN CHANNEL")
    print(f"{'='*60}")
    
    # Notify admin that processing started
    try:
        admin_msg = await client.send_message(
            ADMIN_ID,
            "🔄 **Processing Video**\n\n"
            "A new video was posted to the channel.\n"
            "Starting protection process...",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        admin_msg = None
    
    try:
        # ========================
        # STEP 1: DOWNLOAD ORIGINAL VIDEO
        # ========================
        print("[1/6] Downloading original video...")
        if admin_msg:
            await admin_msg.edit_text("⬇️ **Downloading original video...**")
        
        original_path = f"original_{message.id}.mp4"
        await message.download(file_name=original_path)
        
        print(f"  ✓ Downloaded: {original_path}")
        
        # ========================
        # STEP 2: PROCESS VIDEO
        # ========================
        print("[2/6] Processing video with protection clip...")
        if admin_msg:
            await admin_msg.edit_text("⚙️ **Processing video with protection clip...**\n\nThis may take a few minutes...")
        
        output_path = f"protected_{message.id}.mp4"
        position = config.get("position", "start")
        audio_mode = config.get("audio_mode", "mix")
        
        success, msg = process_video(
            original_path=original_path,
            clip_path=clip_path,
            output_path=output_path,
            position=position,
            audio_mode=audio_mode
        )
        
        if not success:
            raise Exception(f"Processing failed: {msg}")
        
        print(f"  ✓ {msg}")
        
        # ========================
        # STEP 3: EXTRACT THUMBNAIL
        # ========================
        print("[3/6] Extracting thumbnail...")
        if admin_msg:
            await admin_msg.edit_text("🖼️ **Generating thumbnail...**")
        
        thumb_path = f"thumb_{message.id}.jpg"
        # Extract thumbnail from 1 second into the protected video
        extract_thumbnail(output_path, thumb_path, time=1.0)
        
        # ========================
        # STEP 4: UPLOAD PROTECTED VIDEO
        # ========================
        print("[4/6] Uploading protected video to channel...")
        if admin_msg:
            await admin_msg.edit_text("⬆️ **Uploading protected video...**")
        
        # Get original caption if any
        caption = message.caption if message.caption else ""
        
        # Upload the protected video
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            caption=caption,
            thumb=thumb_path if os.path.exists(thumb_path) else None,
            duration=int(get_video_duration(output_path)),
            supports_streaming=True
        )
        
        print(f"  ✓ Protected video uploaded")
        
        # ========================
        # STEP 5: DELETE ORIGINAL VIDEO
        # ========================
        print("[5/6] Deleting original video...")
        if admin_msg:
            await admin_msg.edit_text("🗑️ **Removing original video...**")
        
        try:
            await message.delete()
            print(f"  ✓ Original video deleted")
        except Exception as e:
            print(f"  ⚠ Could not delete original: {e}")
            # This might fail if bot doesn't have delete permissions
        
        # ========================
        # STEP 6: CLEANUP TEMP FILES
        # ========================
        print("[6/6] Cleaning up temporary files...")
        
        temp_files = [original_path, output_path, thumb_path]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"  ✓ Removed {temp_file}")
        
        # ========================
        # SUCCESS NOTIFICATION
        # ========================
        print(f"{'='*60}")
        print(f"✅ VIDEO PROTECTION COMPLETED SUCCESSFULLY")
        print(f"{'='*60}\n")
        
        if admin_msg:
            await admin_msg.edit_text(
                "✅ **Video Protected Successfully!**\n\n"
                f"📊 **Details:**\n"
                f"• Position: {position}\n"
                f"• Audio: {audio_mode}\n"
                f"• Processing time: ~{int(get_video_duration(output_path))}s\n\n"
                "The protected video has been posted to your channel.",
                parse_mode=ParseMode.MARKDOWN
            )
        
    except Exception as e:
        # ========================
        # ERROR HANDLING
        # ========================
        print(f"\n❌ ERROR: {str(e)}\n")
        
        # Notify admin of error
        if admin_msg:
            await admin_msg.edit_text(
                f"❌ **Processing Failed**\n\n"
                f"Error: {str(e)[:200]}\n\n"
                "The original video was not modified.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Cleanup any temp files
        temp_files = [
            f"original_{message.id}.mp4",
            f"protected_{message.id}.mp4",
            f"thumb_{message.id}.jpg"
        ]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass


# ========================
# MAIN: START THE BOT
# ========================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🛡️  TELEGRAM VIDEO PROTECTION BOT")
    print("="*60)
    print(f"Admin ID: {ADMIN_ID}")
    print(f"Channel: {CHANNEL_ID}")
    print(f"Protection: {'ENABLED' if config.get('protection_enabled') else 'DISABLED'}")
    print("="*60 + "\n")
    
    print("🚀 Starting bot...")
    print("Press Ctrl+C to stop\n")
    
    # Run the bot
    app.run()
