# 🛡️ Telegram Video Protection Bot

A powerful Telegram bot that automatically protects your channel videos by injecting a custom protection clip, preventing unauthorized reuse and video theft.

---

## 🌟 Features

- ✅ **Automatic Video Protection** - Monitors your channel and processes videos automatically
- 🎬 **Custom Protection Clip** - Inject your own watermark/logo video
- 📍 **Flexible Positioning** - Insert clip at start, middle, end, or random position
- 🔊 **Audio Control** - Mix, replace, or preserve original audio
- 🔐 **Admin-Only Access** - Secure bot restricted to authorized admin
- 🚀 **Fast Processing** - Optimized FFmpeg commands for quick video processing
- 🧹 **Auto Cleanup** - Automatically removes temporary files
- 📊 **Status Monitoring** - Real-time status and configuration display
- 💾 **Persistent Settings** - Configuration saved across restarts

---

## 📋 How It Works

1. **Admin uploads a protection clip** (2-10 seconds) containing watermark/logo
2. **Bot monitors the channel** for new video posts
3. **When a video is posted:**
   - Bot downloads the original video
   - Inserts the protection clip at configured position
   - Processes audio according to settings
   - Uploads the protected version
   - Deletes the original video
   - Notifies admin of completion
4. **Result:** Video hash is changed, preventing unauthorized reuse

---

## 🎯 Use Cases

- **Content Creators** - Protect your original videos from theft
- **News Channels** - Add branding to all video content
- **Educational Channels** - Watermark your tutorials
- **Business Channels** - Add company intro/outro to videos
- **Media Agencies** - Automatic branding for client content

---

## 📁 Project Structure

```
telegram-video-bot/
├── bot.py                  # Main bot application
├── config.py               # Configuration management
├── video_processor.py      # Video processing with FFmpeg
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── DEPLOYMENT_GUIDE.md    # Detailed deployment instructions
└── README.md              # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- FFmpeg installed on your system
- Telegram account
- VPS/Server (for 24/7 operation)

### Installation

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg:**
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Amazon Linux: `sudo dnf install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Download from https://ffmpeg.org/

4. **Configure the bot:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

5. **Run the bot:**
   ```bash
   python3 bot.py
   ```

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Get from https://my.telegram.org/apps
API_ID=12345678
API_HASH=your_api_hash_here

# Get from @BotFather
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Your Telegram user ID (get from @userinfobot)
ADMIN_ID=123456789

# Your channel username or ID
CHANNEL_ID=@your_channel

# Session name (any name)
SESSION_NAME=video_protector_bot
```

### Bot Settings (Configured via commands)

- **Protection Clip** - Your custom watermark video (2-10 seconds)
- **Position** - Where to insert: `start`, `middle`, `end`, `random`
- **Audio Mode** - How to handle audio: `mix`, `clip`, `original`
- **Protection Status** - Enable/disable automatic protection

---

## 📱 Bot Commands

### Admin Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and introduction |
| `/help` | Detailed help and instructions |
| `/status` | Show current configuration |
| `/setclip` | Upload protection clip (2-10 seconds) |
| `/setposition <mode>` | Set insertion position (start/middle/end/random) |
| `/setaudio <mode>` | Set audio mode (mix/clip/original) |
| `/on` | Enable automatic protection |
| `/off` | Disable automatic protection |

### Usage Examples

```
# Upload protection clip
/setclip
[Upload your 2-10 second video]

# Configure position
/setposition start     # Insert at beginning
/setposition middle    # Insert in middle
/setposition end       # Insert at end
/setposition random    # Random position each time

# Configure audio
/setaudio mix          # Mix both audios together
/setaudio clip         # Use only protection clip audio
/setaudio original     # Use only original video audio

# Enable protection
/on

# Check status
/status
```

---

## 🎬 Video Processing Details

### FFmpeg Processing Pipeline

The bot uses FFmpeg to process videos with the following steps:

1. **Validation** - Checks video integrity and duration
2. **Position Calculation** - Determines where to insert clip
3. **Video Merging** - Concatenates or splits videos as needed
4. **Audio Processing** - Handles audio according to settings
5. **Encoding** - Re-encodes with H.264/AAC for compatibility
6. **Thumbnail Generation** - Extracts thumbnail from processed video

### Encoding Settings

Default settings (balanced quality/speed):
```python
Video Codec: H.264 (libx264)
Preset: medium
CRF: 23 (quality)
Audio Codec: AAC
Audio Bitrate: 128k
```

### Optimization Options

**For faster processing (lower quality):**
- Change preset to `ultrafast` or `veryfast`
- Increase CRF to 25-28

**For better quality (slower processing):**
- Change preset to `slow` or `veryslow`
- Decrease CRF to 18-20

Edit these values in `video_processor.py`

---

## 🔧 Advanced Features

### Position Modes Explained

- **start** - Clip plays before original video (recommended for intros)
- **middle** - Clip inserted at 50% mark (good for watermarking)
- **end** - Clip plays after original video (good for outros)
- **random** - Random position between 10%-90% (unpredictable, harder to remove)

### Audio Modes Explained

- **mix** - Both audios play together (default, preserves both)
- **clip** - Only protection clip audio (replaces original audio)
- **original** - Only original video audio (silent protection clip)

### Multi-Admin Support (Optional)

To add multiple admins, modify `bot.py`:

```python
# Change this line:
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# To this:
ADMIN_IDS = [123456789, 987654321, 555555555]  # Add all admin IDs

# Then update the admin_only decorator to check:
if message.from_user.id not in ADMIN_IDS:
```

---

## 📊 Resource Requirements

### Minimum Requirements
- **CPU:** 1 core
- **RAM:** 512 MB
- **Disk:** 5 GB free space
- **Network:** Stable internet connection

### Recommended Requirements
- **CPU:** 2+ cores
- **RAM:** 2 GB
- **Disk:** 20 GB free space
- **Network:** 10+ Mbps

### Processing Time Estimates

| Video Length | Processing Time (2 cores) |
|--------------|---------------------------|
| 1 minute     | ~10-20 seconds            |
| 5 minutes    | ~30-60 seconds            |
| 10 minutes   | ~1-2 minutes              |
| 30 minutes   | ~3-5 minutes              |

*Times vary based on server specs and encoding settings*

---

## 🐛 Troubleshooting

### Common Issues

**1. Bot doesn't respond to commands**
- Check if bot is running: `sudo systemctl status telegram-video-bot`
- Verify ADMIN_ID is correct
- Check bot token is valid

**2. Videos not being processed**
- Ensure protection is enabled (`/on`)
- Check if protection clip is set (`/status`)
- Verify bot has admin permissions in channel
- Check logs: `sudo journalctl -u telegram-video-bot -f`

**3. FFmpeg errors**
- Verify FFmpeg is installed: `ffmpeg -version`
- Check video format compatibility
- Ensure sufficient disk space

**4. Out of memory errors**
- Reduce video quality settings
- Use faster preset (ultrafast)
- Upgrade VPS RAM

**5. Bot crashes frequently**
- Check logs for errors
- Verify all dependencies are installed
- Ensure stable internet connection

### Debug Mode

To see detailed logs, run bot manually:
```bash
python3 bot.py
```

This shows all processing steps in real-time.

---

## 🔒 Security Considerations

1. **Keep credentials secret** - Never share your `.env` file
2. **Restrict admin access** - Only authorized users should control the bot
3. **Use strong passwords** - For your VPS and Telegram account
4. **Regular updates** - Keep Python packages and system updated
5. **Monitor logs** - Check for suspicious activity
6. **Backup settings** - Keep a copy of `bot_settings.json`

---

## 📈 Performance Tips

### CPU Optimization
- Use `ultrafast` preset for low-end servers
- Process videos during off-peak hours
- Limit concurrent processing (bot processes one at a time)

### RAM Optimization
- Close unnecessary services
- Use swap space if needed
- Monitor with `htop` or `top`

### Disk Optimization
- Ensure auto-cleanup is working
- Use SSD for faster I/O
- Monitor disk usage: `df -h`

### Network Optimization
- Use server close to Telegram servers (Europe recommended)
- Ensure stable connection
- Monitor bandwidth usage

---

## 🛠️ Customization

### Change Video Quality

Edit `video_processor.py`:
```python
# Find these lines and modify:
'-crf', '23',          # Change to 18-28 (lower = better quality)
'-preset', 'medium',   # Change to ultrafast/fast/slow/veryslow
```

### Change Clip Duration Limits

Edit `config.py`:
```python
# Modify validation in receive_clip function:
if duration < 2:    # Change minimum duration
if duration > 10:   # Change maximum duration
```

### Add Custom Commands

Add new commands in `bot.py`:
```python
@app.on_message(filters.command("yourcommand") & filters.private)
@admin_only
async def your_command(client: Client, message: Message):
    await message.reply_text("Your response here")
```

---

## 📚 Technical Details

### Libraries Used

- **Pyrogram** - Modern Telegram MTProto API framework
- **TgCrypto** - Fast cryptography for Pyrogram
- **python-dotenv** - Environment variable management
- **FFmpeg** - Video processing (external dependency)

### File Formats Supported

- **Input:** MP4, MOV, AVI, MKV, WebM, and most video formats
- **Output:** MP4 (H.264 video, AAC audio)

### Limitations

- Maximum video size: Limited by Telegram (2 GB for bots)
- Processing time: Depends on video length and server specs
- Concurrent processing: One video at a time (prevents overload)

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs** - Open an issue with details
2. **Suggest features** - Share your ideas
3. **Improve documentation** - Fix typos, add examples
4. **Optimize code** - Submit performance improvements

---

## 📄 License

This project is provided as-is for educational and personal use.

**Important:** 
- Respect Telegram's Terms of Service
- Don't use for spam or malicious purposes
- Ensure you have rights to the content you're protecting

---

## 🙏 Acknowledgments

- **Pyrogram** - Excellent Telegram library
- **FFmpeg** - Powerful video processing tool
- **Telegram** - For the Bot API

---

## 📞 Support

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

For issues and questions:
1. Check the troubleshooting section
2. Review the deployment guide
3. Check bot logs for errors
4. Verify all configuration is correct

---

## 🎓 Learning Resources

### Understanding the Code

Each file is heavily commented for beginners:

- **bot.py** - Main bot logic with step-by-step comments
- **config.py** - Settings management explained
- **video_processor.py** - FFmpeg commands with detailed explanations

### FFmpeg Resources

- [FFmpeg Official Documentation](https://ffmpeg.org/documentation.html)
- [FFmpeg Wiki](https://trac.ffmpeg.org/wiki)

### Pyrogram Resources

- [Pyrogram Documentation](https://docs.pyrogram.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

## 🚀 Future Enhancements

Potential features to add:

- [ ] Multiple protection clips (random selection)
- [ ] Scheduled protection (specific times)
- [ ] Quality presets (low/medium/high)
- [ ] Progress bar during processing
- [ ] Statistics tracking
- [ ] Multi-channel support
- [ ] Web dashboard
- [ ] Backup/restore settings

---

**Made with ❤️ for content creators**

*Protect your content, protect your work!* 🛡️
