import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# yt-dlp configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicPlayer:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.current = None
        self.loop_mode = False
        self.volume = 0.5
        self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                if not self.loop_mode or not self.current:
                    # Get the next track from the queue
                    async with asyncio.timeout(300):  # 5 minutes timeout
                        source = await self.queue.get()
                else:
                    # If looping, re-create the source from the current data
                    source = await YTDLSource.from_url(self.current.data['webpage_url'], loop=self.bot.loop, stream=True)

            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Disconnect if inactive
                return self.destroy(self.guild)

            self.current = source
            if self.guild.voice_client:
                self.guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
                source.volume = self.volume
            
            await self.next.wait()

            # Clean up the current player
            self.current = None

    def destroy(self, guild):
        return self.bot.loop.create_task(self.bot.cleanup(guild))

class MusicBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="!")
        self.players = {}

    async def setup_hook(self) -> None:
        await self.tree.sync()

    def get_player(self, guild):
        try:
            player = self.players[guild.id]
        except KeyError:
            player = MusicPlayer(self, guild)
            self.players[guild.id] = player
        return player

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass
        try:
            del self.players[guild.id]
        except KeyError:
            pass

bot = MusicBot()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.tree.command(name="play", description="Play a song or playlist from YouTube or URL")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("You must be in a voice channel!")
    
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()
    
    if vc.channel != interaction.user.voice.channel:
        return await interaction.followup.send("I am already in another voice channel!")

    try:
        source = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
    except Exception as e:
        return await interaction.followup.send(f"An error occurred: {e}")

    player = bot.get_player(interaction.guild)
    await player.queue.put(source)
    
    await interaction.followup.send(f"Added **{source.title}** to the queue.")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("Nothing is playing!")
    vc.pause()
    await interaction.response.send_message("Paused the music.")

@bot.tree.command(name="resume", description="Resume the current song")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_paused():
        return await interaction.response.send_message("Music is not paused!")
    vc.resume()
    await interaction.response.send_message("Resumed the music.")

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_connected():
        return await interaction.response.send_message("I'm not connected to a voice channel.")
    
    if vc.is_playing():
        vc.stop()
        await interaction.response.send_message("Skipped the current track.")
    else:
        await interaction.response.send_message("Nothing is currently playing.")

@bot.tree.command(name="stop", description="Stop the music and clear the queue")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Nothing to stop.")
    
    if interaction.guild.id in bot.players:
        player = bot.players[interaction.guild.id]
        # Clear the queue
        while not player.queue.empty():
            try:
                player.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    vc.stop()
    await interaction.response.send_message("Stopped and cleared the queue.")

@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("The queue is empty.")
    
    player = bot.players[interaction.guild.id]
    if player.queue.empty() and not player.current:
         return await interaction.response.send_message("The queue is empty.")

    description = ""
    if player.current:
        description += f"**Now Playing:** {player.current.title}\n\n"
    
    # We can't iterate over asyncio.Queue directly, so we look at the internal list
    # or just show a message. For robustness, we'll show up to 10.
    queue_list = list(player.queue._queue)
    if queue_list:
        description += "**Up Next:**\n"
        for i, source in enumerate(queue_list[:10], start=1):
            description += f"{i}. {source.title}\n"
    
    embed = discord.Embed(title="Current Queue", description=description)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="Show the currently playing song")
async def nowplaying(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players or not bot.players[interaction.guild.id].current:
        return await interaction.response.send_message("Nothing is currently playing.")
    
    player = bot.players[interaction.guild.id]
    await interaction.response.send_message(f"Now playing: **{player.current.title}**")

@bot.tree.command(name="volume", description="Change the volume (0-100)")
async def volume(interaction: discord.Interaction, level: int):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Not connected to a voice channel.")
    if not (0 <= level <= 100):
        return await interaction.response.send_message("Volume must be between 0 and 100.")
    
    vol = level / 100
    if interaction.guild.id in bot.players:
        bot.players[interaction.guild.id].volume = vol
    
    if vc.source:
        vc.source.volume = vol
        
    await interaction.response.send_message(f"Set volume to {level}%")

@bot.tree.command(name="loop", description="Toggle loop for the current song")
async def loop(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("No player found.")
    
    player = bot.players[interaction.guild.id]
    player.loop_mode = not player.loop_mode
    status = "enabled" if player.loop_mode else "disabled"
    await interaction.response.send_message(f"Loop {status}.")

@bot.tree.command(name="shuffle", description="Shuffle the queue")
async def shuffle(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("Queue is empty.")
    
    player = bot.players[interaction.guild.id]
    if player.queue.empty():
        return await interaction.response.send_message("Queue is empty.")
    
    import random
    queue_list = list(player.queue._queue)
    random.shuffle(queue_list)
    player.queue._queue.clear()
    for item in queue_list:
        player.queue.put_nowait(item)
        
    await interaction.response.send_message("Shuffled the queue.")

@bot.tree.command(name="disconnect", description="Disconnect the bot from voice")
async def disconnect(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Not connected.")
    
    if interaction.guild.id in bot.players:
        del bot.players[interaction.guild.id]
        
    await vc.disconnect()
    await interaction.response.send_message("Disconnected.")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
