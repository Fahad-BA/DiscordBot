# Discord Music Bot

A production-grade Discord music bot built with Python, `discord.py`, and `Wavelink`.

## Setup Instructions

1. **Initialize Virtual Environment:**
   ```bash
   cd /home/fahad/DiscordBot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration:**
   - Copy `.env.example` to `.env`.
   - Fill in your `DISCORD_TOKEN` and Lavalink node details.

3. **Systemd Service:**
   - Copy `discordbot.service` to `/etc/systemd/system/`.
   - Reload systemd: `sudo systemctl daemon-reload`.
   - Enable and start: `sudo systemctl enable --now discordbot`.

## Lavalink Setup
Tomorrow, we will configure the Lavalink server (Java-based) to handle the audio processing.