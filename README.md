# 🇸🇦 Simon's Bot | بوت سايمون

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.4.0-blue.svg)](https://discordpy.readthedocs.io/)
[![yt--dlp](https://img.shields.io/badge/yt--dlp-latest-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, professional Discord music bot built for the "Fakhama" experience. This bot bypasses the complexity of external audio servers like Lavalink, opting for a high-fidelity **Native Stream** architecture using `yt-dlp` and `FFmpeg`.

Developed specifically for the Najdi Saudi community, featuring authentic local responses and optimized for bare-metal hosting.

---

## ✨ Features | المميزات

- **🚀 Native Direct Streaming**: Uses `stream=True` with `FFmpeg` for near-instant playback and zero disk overhead.
- **🇸🇦 Najdi Saudi Localization**: Authentic Arabic responses (e.g., "أبشر قاعد أبحث", "هذاني شغلت الأغنيه", "في أمان الله").
- **🔋 Intelligent Idle Management**: Automatically disconnects after 5 minutes of inactivity to save server resources.
- **🛠️ Bare-Metal Optimized**: Designed to run as a robust `systemd` service on Linux home servers.
- **🎧 High Fidelity**: Powered by `yt-dlp` to fetch the best available audio quality.

---

## 🛠️ Tech Stack | التقنيات المستخدمة

- **Language**: Python 3.12+
- **Library**: [discord.py](https://github.com/Rapptz/discord.py)
- **Audio Extraction**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Media Engine**: FFmpeg (Direct Streaming)
- **Deployment**: Systemd (Linux Service)
- **Hosting**: Riyadh Bare-Metal Home Server

---

## 🚀 Installation | التثبيت

### 1. System Requirements
Ensure you have Python 3.12 and FFmpeg installed on your server:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv ffmpeg
```

### 2. Clone and Setup
```bash
git clone https://github.com/Fahad-BA/DiscordBot.git
cd DiscordBot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
DISCORD_TOKEN=your_token_here
```

---

## 🖥️ Systemd Configuration | الإعداد كخدمة نظام

To ensure the bot remains "Always-On" and restarts automatically on failure, use the provided `discordbot.service` file.

### 1. Install the Service
```bash
sudo cp discordbot.service /etc/systemd/system/
```

### 2. Manage the Bot
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable bot to start on boot
sudo systemctl enable discordbot

# Start the bot
sudo systemctl start discordbot

# Check status
systemctl status discordbot
```

---

## 💬 Localization & Commands | الأوامر والتعريب

| Command | Action | Local Response |
| :--- | :--- | :--- |
| `!play` | Search and play music | "أبشر قاعد أبحث" ثم "هذاني شغلت الأغنيه" |
| `!stop` | Stop music and leave | "في أمان الله" |
| `!skip` | Skip current track | "تم، اللي بعده" |
| `Error` | Song not found | "ماحصلت الأغنيه اللي تبيها" |

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

---

**Built with ☕ in Riyadh, Saudi Arabia.**