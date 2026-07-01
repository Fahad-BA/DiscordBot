import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os
import asyncio
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class MusicBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="!")

    async def setup_hook(self) -> None:
        nodes = [wavelink.Node(uri=f"http://{os.getenv('LAVALINK_HOST')}:{os.getenv('LAVALINK_PORT')}", password='youshallnotpass')]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)
        await self.tree.sync()

bot = MusicBot()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    logger.info(f"Wavelink Node {payload.node.identifier} is ready!")

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    player: wavelink.Player = payload.player
    if not player:
        return
    
    track: wavelink.Playable = payload.track
    logger.info(f"Started playing: {track.title}")

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player: wavelink.Player = payload.player
    if not player:
        return

    # If the queue is not empty, play the next song
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)
        logger.info(f"Finished playing, moving to next track: {next_track.title}")
    else:
        logger.info("Finished playing, queue is empty.")

@bot.event
async def on_wavelink_track_exception(payload: wavelink.TrackExceptionEventPayload):
    logger.error(f"Track exception occurred: {payload.exception}")
    player: wavelink.Player = payload.player
    if not player.queue.is_empty:
        await player.play(player.queue.get())

@bot.event
async def on_wavelink_track_stuck(payload: wavelink.TrackStuckEventPayload):
    logger.warning(f"Track stuck: {payload.track.title} at {payload.threshold}ms")
    player: wavelink.Player = payload.player
    if not player.queue.is_empty:
        await player.play(player.queue.get())

@bot.tree.command(name="play", description="Play a song or playlist from YouTube or URL")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("You must be in a voice channel!")
    
    vc: wavelink.Player = interaction.guild.voice_client or await interaction.user.voice.channel.connect(cls=wavelink.Player)
    
    if vc.channel != interaction.user.voice.channel:
        return await interaction.followup.send("I am already in another voice channel!")

    # Set default volume if it's a new connection or at default 100
    if vc.volume == 100:
        await vc.set_volume(50)

    # Robust search logic
    tracks: wavelink.Search = await wavelink.Playable.search(search)
    if not tracks:
        return await interaction.followup.send(f"No results found for: `{search}`")

    if isinstance(tracks, wavelink.Playlist):
        # Add all tracks in playlist
        added = await vc.queue.put_wait(tracks)
        await interaction.followup.send(f"Added playlist **{tracks.name}** ({added} tracks) to the queue.")
    else:
        track: wavelink.Playable = tracks[0]
        await vc.queue.put_wait(track)
        await interaction.followup.send(f"Added **{track.title}** to the queue.")

    if not vc.playing:
        await vc.play(vc.queue.get())

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or not vc.playing:
        return await interaction.response.send_message("Nothing is playing!")
    await vc.pause(True)
    await interaction.response.send_message("Paused the music.")

@bot.tree.command(name="resume", description="Resume the current song")
async def resume(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or not vc.paused:
        return await interaction.response.send_message("Music is not paused!")
    await vc.pause(False)
    await interaction.response.send_message("Resumed the music.")

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("I'm not connected to a voice channel.")
    await vc.skip()
    await interaction.response.send_message("Skipped the current track.")

@bot.tree.command(name="stop", description="Stop the music and clear the queue")
async def stop(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Nothing to stop.")
    vc.queue.clear()
    await vc.stop()
    await interaction.response.send_message("Stopped and cleared the queue.")

@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or vc.queue.is_empty:
        return await interaction.response.send_message("The queue is empty.")
    
    description = ""
    for i, track in enumerate(vc.queue, start=1):
        description += f"{i}. {track.title}\n"
    
    embed = discord.Embed(title="Current Queue", description=description)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="Show the currently playing song")
async def nowplaying(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or not vc.current:
        return await interaction.response.send_message("Nothing is currently playing.")
    await interaction.response.send_message(f"Now playing: **{vc.current.title}**")

@bot.tree.command(name="volume", description="Change the volume (0-100)")
async def volume(interaction: discord.Interaction, level: int):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Not connected to a voice channel.")
    if not (0 <= level <= 100):
        return await interaction.response.send_message("Volume must be between 0 and 100.")
    await vc.set_volume(level)
    await interaction.response.send_message(f"Set volume to {level}%")

@bot.tree.command(name="loop", description="Toggle loop for the current song")
async def loop(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Not connected.")
    
    if vc.queue.mode == wavelink.QueueMode.loop:
        vc.queue.mode = wavelink.QueueMode.normal
        await interaction.response.send_message("Loop disabled.")
    else:
        vc.queue.mode = wavelink.QueueMode.loop
        await interaction.response.send_message("Loop enabled.")

@bot.tree.command(name="shuffle", description="Shuffle the queue")
async def shuffle(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or vc.queue.is_empty:
        return await interaction.response.send_message("Queue is empty.")
    vc.queue.shuffle()
    await interaction.response.send_message("Shuffled the queue.")

@bot.tree.command(name="disconnect", description="Disconnect the bot from voice")
async def disconnect(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("Not connected.")
    await vc.disconnect()
    await interaction.response.send_message("Disconnected.")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))