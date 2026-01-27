# 🚀 Deployment Guide - Telegram Video Protection Bot

This guide will walk you through deploying the bot on a VPS (Ubuntu/Amazon Linux).

---

## 📋 Prerequisites

Before starting, you need:

1. **A VPS/Server** (Ubuntu 20.04+, Amazon Linux 2023, or similar)
2. **Telegram Account** for creating the bot
3. **Basic terminal/SSH knowledge**

---

## 🔧 STEP 1: Get Telegram API Credentials

### 1.1 Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the instructions:
   - Choose a name for your bot (e.g., "My Video Protector")
   - Choose a username (must end in 'bot', e.g., "my_video_protector_bot")
4. **Save the BOT_TOKEN** - it looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 1.2 Get API_ID and API_HASH

1. Go to https://my.telegram.org/apps
2. Login with your phone number
3. Click "API development tools"
4. Fill in the form:
   - App title: Any name (e.g., "Video Protector")
   - Short name: Any short name
   - Platform: Other
5. Click "Create application"
6. **Save your API_ID and API_HASH**

### 1.3 Get Your Admin ID

1. Open Telegram and search for `@userinfobot`
2. Start the bot and send `/start`
3. It will reply with your user ID
4. **Save this number** - this is your ADMIN_ID

### 1.4 Get Your Channel ID

**Option A: If your channel has a username**
- Your CHANNEL_ID is: `@your_channel_username`

**Option B: If your channel doesn't have a username**
1. Forward any message from your channel to `@userinfobot`
2. It will show the channel ID (looks like `-100123456789`)
3. **Save this number** - this is your CHANNEL_ID

### 1.5 Add Bot to Your Channel

1. Go to your channel settings
2. Click "Administrators"
3. Click "Add Administrator"
4. Search for your bot username
5. Give it these permissions:
   - ✅ Post messages
   - ✅ Edit messages
   - ✅ Delete messages
6. Save

---

## 💻 STEP 2: Server Setup

### 2.1 Connect to Your VPS

```bash
ssh root@your_server_ip
# or
ssh your_username@your_server_ip
```

### 2.2 Update System

**For Ubuntu/Debian:**
```bash
sudo apt update
sudo apt upgrade -y
```

**For Amazon Linux 2023:**
```bash
sudo dnf update -y
```

### 2.3 Install Python 3.9+

**Ubuntu/Debian:**
```bash
sudo apt install python3 python3-pip python3-venv -y
```

**Amazon Linux 2023:**
```bash
sudo dnf install python3 python3-pip -y
```

Verify installation:
```bash
python3 --version
# Should show Python 3.9 or higher
```

### 2.4 Install FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg -y
```

**Amazon Linux 2023:**
```bash
sudo dnf install ffmpeg -y
```

Verify installation:
```bash
ffmpeg -version
# Should show FFmpeg version info
```

---

## 📦 STEP 3: Install the Bot

### 3.1 Create Bot Directory

```bash
# Create a directory for the bot
mkdir -p ~/telegram-video-bot
cd ~/telegram-video-bot
```

### 3.2 Upload Bot Files

**Option A: Using Git (if you have the code in a repository)**
```bash
git clone https://github.com/yourusername/telegram-video-bot.git .
```

**Option B: Manual Upload**
Upload these files to the server using SCP or SFTP:
- `bot.py`
- `config.py`
- `video_processor.py`
- `requirements.txt`
- `.env.example`

**Using SCP from your local machine:**
```bash
scp bot.py config.py video_processor.py requirements.txt .env.example \
    user@your_server_ip:~/telegram-video-bot/
```

### 3.3 Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Your prompt should now show (venv)
```

### 3.4 Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- Pyrogram (Telegram library)
- TgCrypto (Encryption for Pyrogram)
- python-dotenv (Environment variables)

---

## ⚙️ STEP 4: Configure the Bot

### 4.1 Create .env File

```bash
# Copy the example file
cp .env.example .env

# Edit the file
nano .env
```

### 4.2 Fill in Your Credentials

Replace the placeholder values with your actual credentials:

```env
API_ID=12345678
API_HASH=your_api_hash_here
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
CHANNEL_ID=@your_channel
SESSION_NAME=video_protector_bot
```

**Save and exit:**
- Press `Ctrl + X`
- Press `Y` to confirm
- Press `Enter` to save

---

## 🧪 STEP 5: Test the Bot

### 5.1 Run the Bot Manually

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the bot
python3 bot.py
```

You should see:
```
✓ Environment variables loaded successfully
✓ Telegram client initialized
🚀 Starting bot...
```

### 5.2 Test Commands

1. Open Telegram and find your bot
2. Send `/start` - you should get a welcome message
3. Send `/status` - you should see current settings
4. Press `Ctrl + C` to stop the bot

If everything works, proceed to the next step!

---

## 🔄 STEP 6: Run Bot Permanently (Using systemd)

To keep the bot running 24/7, even after server restart:

### 6.1 Create Systemd Service File

```bash
sudo nano /etc/systemd/system/telegram-video-bot.service
```

### 6.2 Add This Configuration

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

**Important:** Replace `YOUR_USERNAME` with your actual username!

To find your username:
```bash
whoami
```

**Save and exit** (Ctrl+X, Y, Enter)

### 6.3 Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable telegram-video-bot

# Start the service now
sudo systemctl start telegram-video-bot

# Check status
sudo systemctl status telegram-video-bot
```

You should see "active (running)" in green.

### 6.4 Useful Service Commands

```bash
# Stop the bot
sudo systemctl stop telegram-video-bot

# Restart the bot
sudo systemctl restart telegram-video-bot

# View logs (last 50 lines)
sudo journalctl -u telegram-video-bot -n 50

# View logs in real-time
sudo journalctl -u telegram-video-bot -f

# Check if bot is running
sudo systemctl status telegram-video-bot
```

---

## 📱 STEP 7: Using the Bot

### 7.1 Setup Protection Clip

1. Open Telegram and start your bot
2. Send `/setclip`
3. Upload a short video (2-10 seconds) - this is your protection clip
4. Wait for confirmation

### 7.2 Configure Settings

```
/setposition start    # Insert clip at the beginning
/setposition middle   # Insert clip in the middle
/setposition end      # Insert clip at the end
/setposition random   # Random position each time

/setaudio mix         # Mix both audios
/setaudio clip        # Use only clip audio
/setaudio original    # Use only original audio
```

### 7.3 Enable Protection

```
/on    # Enable automatic protection
/off   # Disable protection
```

### 7.4 Check Status

```
/status   # View current configuration
```

### 7.5 Post Videos

Now when you post a video to your channel:
1. Bot will automatically download it
2. Insert your protection clip
3. Re-upload the protected version
4. Delete the original
5. Notify you when done

---

## 🎯 STEP 8: Optimization Tips

### 8.1 CPU & RAM Optimization

**For Low-End VPS (1GB RAM):**

Edit `video_processor.py` and change FFmpeg preset:
```python
'-preset', 'ultrafast',  # Instead of 'medium'
```

This trades quality for speed.

**For High-End VPS (4GB+ RAM):**
```python
'-preset', 'slow',       # Better quality
'-crf', '20',            # Higher quality (lower number = better)
```

### 8.2 Disk Space Management

The bot automatically cleans up temporary files, but you can add a cron job to clean old session files:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 3 AM)
0 3 * * * find ~/telegram-video-bot -name "*.session-journal" -mtime +7 -delete
```

### 8.3 Monitor Resource Usage

```bash
# Check CPU and RAM usage
htop

# Check disk space
df -h

# Check bot process
ps aux | grep bot.py
```

---

## 🐛 Troubleshooting

### Bot Won't Start

**Check logs:**
```bash
sudo journalctl -u telegram-video-bot -n 100
```

**Common issues:**

1. **"Missing environment variables"**
   - Check your `.env` file has all values filled in
   - Make sure there are no spaces around `=`

2. **"FFmpeg not found"**
   - Install FFmpeg: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

3. **"Permission denied"**
   - Check file permissions: `chmod +x bot.py`
   - Check service user in systemd file

### Bot Doesn't Process Videos

1. **Check if protection is enabled:**
   - Send `/status` to the bot
   - If disabled, send `/on`

2. **Check if clip is set:**
   - Send `/status`
   - If no clip, send `/setclip` and upload one

3. **Check bot permissions in channel:**
   - Bot must be admin
   - Must have "Post messages" and "Delete messages" permissions

### Videos Take Too Long to Process

1. **Use faster preset:**
   - Edit `video_processor.py`
   - Change `'-preset', 'medium'` to `'-preset', 'ultrafast'`

2. **Upgrade VPS:**
   - More CPU cores = faster processing
   - Recommended: 2+ CPU cores for smooth operation

### Bot Crashes or Restarts

**Check logs:**
```bash
sudo journalctl -u telegram-video-bot -n 200
```

**Common causes:**
- Out of memory (upgrade VPS or optimize settings)
- Network issues (check internet connection)
- Telegram API rate limits (bot will auto-retry)

---

## 🔒 Security Best Practices

1. **Protect your .env file:**
   ```bash
   chmod 600 .env
   ```

2. **Never share your credentials:**
   - Don't commit `.env` to Git
   - Don't share BOT_TOKEN or API_HASH

3. **Use firewall:**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 443
   ```

4. **Regular updates:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   pip install --upgrade -r requirements.txt
   ```

---

## 📊 Monitoring

### Check Bot Status

```bash
# Is bot running?
sudo systemctl status telegram-video-bot

# View recent logs
sudo journalctl -u telegram-video-bot -n 50

# Follow logs in real-time
sudo journalctl -u telegram-video-bot -f
```

### Check Resource Usage

```bash
# CPU and RAM
htop

# Disk space
df -h

# Network usage
iftop
```

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs first:**
   ```bash
   sudo journalctl -u telegram-video-bot -n 100
   ```

2. **Verify configuration:**
   ```bash
   cat .env
   ```

3. **Test FFmpeg:**
   ```bash
   ffmpeg -version
   ```

4. **Test Python:**
   ```bash
   python3 --version
   pip list
   ```

---

## 🎉 Success!

Your Telegram Video Protection Bot is now running 24/7!

**What happens now:**
- Bot monitors your channel
- When you post a video, it's automatically protected
- Protected video is re-uploaded
- Original is deleted
- You get notified of the process

**Enjoy your protected content! 🛡️**
