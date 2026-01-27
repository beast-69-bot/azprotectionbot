# ⚡ Quick Start Guide

Get your bot running in 5 minutes!

---

## 🎯 What You Need

- [ ] Telegram account
- [ ] VPS/Server with Ubuntu or Amazon Linux
- [ ] 15 minutes of time

---

## 📝 Step 1: Get Credentials (5 min)

### Create Bot
1. Open Telegram → Search `@BotFather`
2. Send `/newbot` → Follow instructions
3. **Copy BOT_TOKEN**

### Get API Keys
1. Visit https://my.telegram.org/apps
2. Login → Create application
3. **Copy API_ID and API_HASH**

### Get Your ID
1. Search `@userinfobot` in Telegram
2. Send `/start`
3. **Copy your user ID**

### Setup Channel
1. Add bot to your channel as admin
2. Give permissions: Post, Edit, Delete messages
3. **Copy channel username** (e.g., @mychannel)

---

## 💻 Step 2: Install (5 min)

```bash
# Install dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg -y

# Create directory
mkdir ~/telegram-video-bot
cd ~/telegram-video-bot

# Upload files (or git clone)
# Then:

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Step 3: Configure (2 min)

```bash
# Create config
cp .env.example .env
nano .env
```

Fill in:
```env
API_ID=YOUR_API_ID
API_HASH=YOUR_API_HASH
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=YOUR_USER_ID
CHANNEL_ID=@your_channel
SESSION_NAME=video_protector_bot
```

Save: `Ctrl+X` → `Y` → `Enter`

---

## 🧪 Step 4: Test (2 min)

```bash
# Verify setup
python3 test_setup.py

# Run bot
python3 bot.py
```

In Telegram:
- Find your bot
- Send `/start`
- Should get welcome message!

Press `Ctrl+C` to stop.

---

## 🔄 Step 5: Run 24/7 (3 min)

```bash
# Edit service file
sudo nano /etc/systemd/system/telegram-video-bot.service
```

Paste (replace YOUR_USERNAME):
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

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-video-bot
sudo systemctl start telegram-video-bot
sudo systemctl status telegram-video-bot
```

Should show "active (running)" ✅

---

## 🎬 Step 6: Setup Protection (2 min)

In Telegram with your bot:

```
/setclip
[Upload 2-10 second video]

/setposition start

/setaudio mix

/on

/status
```

---

## ✅ Done!

Post a video to your channel → Bot will protect it automatically!

---

## 🆘 Problems?

**Bot not responding?**
```bash
sudo systemctl status telegram-video-bot
sudo journalctl -u telegram-video-bot -n 50
```

**Need help?**
- See [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)
- See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- See [README.md](README.md)

---

**Total Time: ~15 minutes** ⏱️

**Enjoy! 🎉**
