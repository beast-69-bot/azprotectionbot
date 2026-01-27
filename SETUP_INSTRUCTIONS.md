# 🎯 Quick Setup Instructions

Follow these steps to get your bot running in 15 minutes!

---

## 📝 Step 1: Get Telegram Credentials (5 minutes)

### A. Create Bot with BotFather

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose a name: `My Video Protector`
5. Choose username: `my_video_protector_bot`
6. **Copy the BOT_TOKEN** (looks like `123456789:ABCdef...`)

### B. Get API Credentials

1. Visit https://my.telegram.org/apps
2. Login with your phone
3. Click "API development tools"
4. Create new application
5. **Copy API_ID and API_HASH**

### C. Get Your Admin ID

1. Search `@userinfobot` in Telegram
2. Send `/start`
3. **Copy your user ID number**

### D. Get Channel ID

**If channel has username:**
- Use `@your_channel_username`

**If no username:**
1. Forward a message from channel to `@userinfobot`
2. **Copy the channel ID** (like `-100123456789`)

### E. Add Bot to Channel

1. Go to channel settings → Administrators
2. Add your bot as admin
3. Give permissions:
   - ✅ Post messages
   - ✅ Edit messages  
   - ✅ Delete messages

---

## 💻 Step 2: Install on Server (5 minutes)

### Ubuntu/Debian

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and FFmpeg
sudo apt install python3 python3-pip python3-venv ffmpeg -y

# Create directory
mkdir ~/telegram-video-bot
cd ~/telegram-video-bot

# Upload files (bot.py, config.py, video_processor.py, requirements.txt, .env.example)
# Or clone from git if you have a repository

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Amazon Linux 2023

```bash
# Update system
sudo dnf update -y

# Install Python and FFmpeg
sudo dnf install python3 python3-pip ffmpeg -y

# Create directory
mkdir ~/telegram-video-bot
cd ~/telegram-video-bot

# Upload files or clone repository

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Step 3: Configure Bot (2 minutes)

```bash
# Copy example config
cp .env.example .env

# Edit config
nano .env
```

Fill in your values:
```env
API_ID=12345678
API_HASH=your_api_hash_here
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
CHANNEL_ID=@your_channel
SESSION_NAME=video_protector_bot
```

Save: `Ctrl+X`, then `Y`, then `Enter`

---

## 🧪 Step 4: Test Bot (2 minutes)

```bash
# Make sure venv is activated
source venv/bin/activate

# Run bot
python3 bot.py
```

You should see:
```
✓ Environment variables loaded successfully
✓ Telegram client initialized
🚀 Starting bot...
```

**Test in Telegram:**
1. Find your bot
2. Send `/start`
3. You should get a welcome message!

Press `Ctrl+C` to stop.

---

## 🔄 Step 5: Run 24/7 (3 minutes)

### Create Service

```bash
sudo nano /etc/systemd/system/telegram-video-bot.service
```

Paste this (replace `YOUR_USERNAME` with your username from `whoami`):

```ini
[Unit]
Description=Telegram Video Protection Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/telegram-video-bot
Environment="PATH=/home/YOUR_USERNAME/telegram-video-bot/venv/bin"
ExecStart=/home/YOUR_USERNAME/telegram-video-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit.

### Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable telegram-video-bot

# Start now
sudo systemctl start telegram-video-bot

# Check status
sudo systemctl status telegram-video-bot
```

Should show "active (running)" in green!

---

## 🎬 Step 6: Setup Protection (2 minutes)

In Telegram:

```
1. Send /setclip to your bot
2. Upload a 2-10 second video (your watermark/logo)
3. Wait for confirmation

4. Send /setposition start

5. Send /setaudio mix

6. Send /on to enable protection

7. Send /status to verify everything is set
```

---

## ✅ Done! Test It

1. Post a video to your channel
2. Bot will automatically:
   - Download it
   - Add your protection clip
   - Re-upload protected version
   - Delete original
   - Notify you

**You're all set! 🎉**

---

## 🔧 Useful Commands

```bash
# View logs
sudo journalctl -u telegram-video-bot -f

# Restart bot
sudo systemctl restart telegram-video-bot

# Stop bot
sudo systemctl stop telegram-video-bot

# Check status
sudo systemctl status telegram-video-bot
```

---

## ❓ Problems?

**Bot not responding?**
- Check logs: `sudo journalctl -u telegram-video-bot -n 50`
- Verify .env file has correct values
- Make sure bot is running: `sudo systemctl status telegram-video-bot`

**Videos not processing?**
- Send `/status` - is protection enabled?
- Is protection clip set?
- Is bot admin in channel?

**Need more help?**
- See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions
- See [README.md](README.md) for full documentation

---

**Total Time: ~15 minutes** ⏱️

**Enjoy your protected videos! 🛡️**
