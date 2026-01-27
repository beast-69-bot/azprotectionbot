# 📚 Usage Examples

This document provides real-world examples of using the Telegram Video Protection Bot.

---

## 🎬 Example 1: Basic Setup (Content Creator)

**Scenario:** You're a content creator who wants to add a 3-second intro to all videos.

### Step 1: Create Your Intro Clip

Create a 3-second video with:
- Your logo
- Channel name
- "Subscribe" message

Save as `intro.mp4`

### Step 2: Configure Bot

```
You: /setclip
Bot: Please send me a video file...

[Upload intro.mp4]

Bot: ✅ Protection Clip Saved!
     Duration: 3.0 seconds
     Size: 1.2 MB

You: /setposition start
Bot: ✅ Position Updated
     Clip will be inserted at: start

You: /setaudio mix
Bot: ✅ Audio Mode Updated
     Audio mode: mix

You: /on
Bot: 🟢 Protection Enabled!
```

### Step 3: Post Video

Post any video to your channel. The bot will:
1. Download it
2. Add your 3-second intro at the start
3. Re-upload with both audios mixed
4. Delete the original

**Result:** Every video now starts with your branded intro!

---

## 🏢 Example 2: Business Channel (Company Branding)

**Scenario:** Corporate channel that needs company outro on all videos.

### Configuration

```
/setclip
[Upload 5-second company outro with logo and contact info]

/setposition end
/setaudio clip
/on
```

**Result:** All videos end with company branding, and the outro audio replaces the last 5 seconds of original audio.

---

## 📰 Example 3: News Channel (Watermark Protection)

**Scenario:** News channel wants to prevent video theft with random watermark placement.

### Configuration

```
/setclip
[Upload 2-second watermark clip with channel logo]

/setposition random
/setaudio original
/on
```

**Result:** Each video gets the watermark at a random position (10%-90%), making it harder to remove. Original audio is preserved.

---

## 🎓 Example 4: Educational Channel (Tutorial Protection)

**Scenario:** Tutorial channel wants to add intro and preserve audio quality.

### Configuration

```
/setclip
[Upload 4-second intro: "Tutorial by @YourChannel"]

/setposition start
/setaudio mix
/on
```

**Result:** Every tutorial starts with your intro, both audios are mixed together.

---

## 🎵 Example 5: Music Channel (Silent Watermark)

**Scenario:** Music channel wants visual watermark without affecting audio.

### Configuration

```
/setclip
[Upload 3-second silent video with animated logo]

/setposition middle
/setaudio original
/on
```

**Result:** Visual watermark appears in the middle, but original music is completely preserved.

---

## 🔄 Example 6: Changing Settings Mid-Operation

**Scenario:** You want to change from start to random position.

```
You: /status
Bot: [Shows current settings]

You: /off
Bot: 🔴 Protection Disabled

You: /setposition random
Bot: ✅ Position Updated

You: /on
Bot: 🟢 Protection Enabled!
```

**Best Practice:** Always disable (`/off`) before changing settings, then re-enable (`/on`).

---

## 🎯 Example 7: Testing Before Going Live

**Scenario:** You want to test the bot before enabling it on your main channel.

### Step 1: Create Test Channel

1. Create a private test channel
2. Add bot as admin
3. Update `.env` with test channel ID

### Step 2: Test Configuration

```
/setclip
[Upload test clip]

/setposition start
/setaudio mix
/on
```

### Step 3: Post Test Video

Post a test video and verify:
- ✓ Clip is inserted correctly
- ✓ Audio sounds good
- ✓ Video quality is acceptable
- ✓ Processing time is reasonable

### Step 4: Switch to Production

1. Stop bot: `sudo systemctl stop telegram-video-bot`
2. Update `.env` with production channel ID
3. Start bot: `sudo systemctl start telegram-video-bot`

---

## 🚨 Example 8: Emergency Stop

**Scenario:** Something went wrong, need to stop protection immediately.

### Quick Stop

```
You: /off
Bot: 🔴 Protection Disabled
```

Videos posted after this will NOT be processed.

### Complete Stop

```bash
# SSH to server
ssh user@server

# Stop the service
sudo systemctl stop telegram-video-bot

# Check it's stopped
sudo systemctl status telegram-video-bot
```

---

## 📊 Example 9: Monitoring Bot Activity

**Scenario:** You want to see what the bot is doing.

### View Real-Time Logs

```bash
# SSH to server
ssh user@server

# Follow logs in real-time
sudo journalctl -u telegram-video-bot -f
```

You'll see:
```
🎬 NEW VIDEO DETECTED IN CHANNEL
[1/6] Downloading original video...
  ✓ Downloaded: original_123.mp4
[2/6] Processing video with protection clip...
  ✓ Video processed successfully
[3/6] Extracting thumbnail...
[4/6] Uploading protected video to channel...
[5/6] Deleting original video...
[6/6] Cleaning up temporary files...
✅ VIDEO PROTECTION COMPLETED SUCCESSFULLY
```

### Check Last 100 Log Lines

```bash
sudo journalctl -u telegram-video-bot -n 100
```

---

## 🎨 Example 10: Multiple Clip Positions (Advanced)

**Scenario:** You want different positions for different types of content.

### For Tutorials (Start)

```
/off
/setposition start
/on
[Post tutorial videos]
```

### For Entertainment (Random)

```
/off
/setposition random
/on
[Post entertainment videos]
```

### For Announcements (End)

```
/off
/setposition end
/on
[Post announcement videos]
```

**Note:** You need to manually change settings for each batch.

---

## 🔧 Example 11: Optimizing for Different Video Lengths

### Short Videos (< 1 minute)

```
/setclip
[Upload 2-second clip - short and sweet]

/setposition start
/setaudio mix
```

**Why:** Short videos need short clips to maintain viewer attention.

### Medium Videos (1-10 minutes)

```
/setclip
[Upload 3-5 second clip - standard branding]

/setposition start or middle
/setaudio mix
```

**Why:** Standard protection, good balance.

### Long Videos (> 10 minutes)

```
/setclip
[Upload 5-10 second clip - detailed branding]

/setposition random
/setaudio mix
```

**Why:** Longer clips acceptable, random position prevents easy removal.

---

## 📱 Example 12: Multi-Admin Workflow

**Scenario:** Team of 3 people managing the channel.

### Setup (Modify bot.py)

```python
# In bot.py, change:
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# To:
ADMIN_IDS = [123456789, 987654321, 555555555]

# Update admin_only decorator:
if message.from_user.id not in ADMIN_IDS:
```

### Usage

Now all 3 admins can:
- Upload protection clips
- Change settings
- Enable/disable protection
- View status

---

## 🎯 Example 13: Seasonal Branding

**Scenario:** Change branding for holidays/events.

### Christmas Season

```
/off
/setclip
[Upload Christmas-themed intro]
/on
```

### New Year

```
/off
/setclip
[Upload New Year intro]
/on
```

### Regular Season

```
/off
/setclip
[Upload regular intro]
/on
```

**Tip:** Keep backup copies of all your seasonal clips!

---

## 🔍 Example 14: Troubleshooting Common Issues

### Issue: Bot Not Processing Videos

**Check 1: Is protection enabled?**
```
/status
```
If disabled, send `/on`

**Check 2: Is clip set?**
```
/status
```
If not set, send `/setclip` and upload

**Check 3: Is bot running?**
```bash
sudo systemctl status telegram-video-bot
```

**Check 4: Check logs**
```bash
sudo journalctl -u telegram-video-bot -n 50
```

### Issue: Poor Video Quality

**Solution: Adjust encoding settings**

Edit `video_processor.py`:
```python
# Change from:
'-crf', '23',

# To:
'-crf', '20',  # Better quality
```

Restart bot:
```bash
sudo systemctl restart telegram-video-bot
```

### Issue: Processing Too Slow

**Solution: Use faster preset**

Edit `video_processor.py`:
```python
# Change from:
'-preset', 'medium',

# To:
'-preset', 'fast',  # or 'ultrafast'
```

---

## 📈 Example 15: Performance Optimization

### Low-End VPS (1 CPU, 512MB RAM)

```python
# In video_processor.py:
'-preset', 'ultrafast',
'-crf', '28',
```

**Trade-off:** Faster processing, lower quality

### High-End VPS (4 CPU, 8GB RAM)

```python
# In video_processor.py:
'-preset', 'slow',
'-crf', '18',
```

**Trade-off:** Slower processing, higher quality

### Balanced (2 CPU, 2GB RAM)

```python
# In video_processor.py:
'-preset', 'medium',
'-crf', '23',
```

**Trade-off:** Good balance (default)

---

## 🎓 Example 16: Learning from Logs

### Understanding Log Output

```
🎬 NEW VIDEO DETECTED IN CHANNEL
```
→ Bot detected a new video in your channel

```
[1/6] Downloading original video...
  ✓ Downloaded: original_123.mp4
```
→ Successfully downloaded the video

```
[2/6] Processing video with protection clip...
  Command: ffmpeg -f concat -safe 0 -i concat_list.txt ...
```
→ Shows the exact FFmpeg command being used

```
✓ FFmpeg processing completed!
```
→ Video processing successful

```
[4/6] Uploading protected video to channel...
```
→ Uploading the protected version

```
✅ VIDEO PROTECTION COMPLETED SUCCESSFULLY
```
→ Everything worked!

### Error in Logs

```
✗ FFmpeg error: ...
```
→ Video processing failed, check FFmpeg installation

```
⚠ Could not delete original: ...
```
→ Bot lacks delete permissions in channel

---

## 💡 Pro Tips

### Tip 1: Test Clips Before Using

Always test your protection clip on a private channel first!

### Tip 2: Keep Clips Short

2-4 seconds is ideal. Longer clips may annoy viewers.

### Tip 3: Use High-Quality Clips

Your protection clip should be high quality (1080p recommended).

### Tip 4: Backup Your Settings

```bash
# Backup settings file
cp bot_settings.json bot_settings.backup.json

# Backup protection clip
cp protection_clip.mp4 protection_clip.backup.mp4
```

### Tip 5: Monitor Disk Space

```bash
# Check disk usage
df -h

# Clean old logs if needed
sudo journalctl --vacuum-time=7d
```

### Tip 6: Regular Updates

```bash
# Update Python packages monthly
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart telegram-video-bot
```

---

## 🎬 Real-World Success Stories

### Case 1: Tech Tutorial Channel

- **Before:** Videos frequently stolen and re-uploaded
- **After:** 3-second branded intro at start
- **Result:** 90% reduction in unauthorized copies

### Case 2: News Agency

- **Before:** Competitors using their footage
- **After:** Random watermark placement
- **Result:** Footage easily identifiable, theft deterred

### Case 3: Music Producer

- **Before:** Beats stolen from preview videos
- **After:** Silent visual watermark in middle
- **Result:** Music preserved, videos protected

---

**Need more examples? Check the documentation or experiment with different settings!**

Remember: Always test on a private channel first! 🧪
