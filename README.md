# 🎵 Simon FM

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.7.1-blue.svg)](https://discordpy.readthedocs.io/)
[![yt--dlp](https://img.shields.io/badge/yt--dlp-latest-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Discord music bot built for simplicity. Uses native direct streaming via `yt-dlp` and `FFmpeg` — no Lavalink, no external audio servers, no disk overhead.

---

## ✨ Features

- **🚀 Native Direct Streaming** — Near-instant playback using `stream=True` with FFmpeg. Zero disk writes.
- **📋 Full Queue Management** — Play, pause, resume, skip, stop, shuffle, loop, and view the queue.
- **🔊 Volume Control** — Adjust playback volume per server (0–100%).
- **🔋 Smart Idle Detection** — Automatically disconnects after 5 minutes of inactivity to save resources.
- **🎧 High Fidelity** — Fetches the best available audio quality via `yt-dlp`.
- **🆓 Free & Open Source** — No paywalls, no premium tiers.

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Library:** [discord.py](https://github.com/Rapptz/discord.py) 2.7.1
- **Audio Extraction:** [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Media Engine:** FFmpeg (Direct Streaming)
- **Environment:** python-dotenv

---

## 🚀 Installation

### 1. System Requirements

Python 3.12+ and FFmpeg:

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

### 4. Run the Bot

```bash
source venv/bin/activate
python bot.py
```

---

## 💬 Commands

| Command | Description |
| :--- | :--- |
| `/play [url or name]` | Play a track from a link or search by name |
| `/pause` | Pause the currently playing track |
| `/resume` | Resume the paused track |
| `/skip` | Skip the current track |
| `/stop` | Stop all playback and clear the queue |
| `/queue` | View the upcoming tracks in the queue |
| `/nowplaying` | Show the currently playing track |
| `/volume [0-100]` | Change the playback volume level |
| `/loop` | Toggle repeat mode for the current track |
| `/shuffle` | Randomize the order of the queue |
| `/disconnect` | Disconnect the bot from the voice channel |
| `/help` | Show the full list of available commands |

---

## 🌐 Links

- **Website:** [simon.fhidan.com](https://fhidan.com/simon)
- **Invite Bot:** [Add Simon FM to your server](https://fhidan.com/simon/invite.html)
- **Terms of Service:** [tos.html](https://fhidan.com/simon/tos.html)
- **Privacy Policy:** [privacy.html](https://fhidan.com/simon/privacy.html)

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Built with ❤️ in Riyadh.**
