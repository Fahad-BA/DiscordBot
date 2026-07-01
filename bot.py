import discord
from discord.ext import commands, tasks
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

def is_url(string: str) -> bool:
    return string.startswith(('http://', 'https://'))

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        # If it's not a URL, use YouTube search
        search_query = url if is_url(url) else f"ytsearch:{url}"
        
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=not stream))
        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            raise e

        if 'entries' in data:
            if not data['entries']:
                raise Exception("No entries found")
            # take first item from a search result
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
        self.idle_start = None
        self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                if not self.loop_mode or not self.current:
                    # Get the next track from the queue
                    async with asyncio.timeout(300):  # 5 minutes timeout for queue wait
                        source = await self.queue.get()
                else:
                    # If looping, re-create the source from the current data
                    source = await YTDLSource.from_url(self.current.data['webpage_url'], loop=self.bot.loop, stream=True)

            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Disconnect if inactive for 5 minutes (no song in queue)
                logger.info(f"Player loop timeout for guild {self.guild.id}")
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
        intents.voice_states = True
        super().__init__(intents=intents, command_prefix="!")
        self.players = {}

    async def setup_hook(self) -> None:
        await self.tree.sync()
        self.check_idle_voice.start()

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

    @tasks.loop(minutes=1.0)
    async def check_idle_voice(self):
        for guild_id, player in list(self.players.items()):
            guild = self.get_guild(guild_id)
            if not guild:
                continue
            
            vc = guild.voice_client
            if not vc:
                continue

            # Check if bot is alone in the channel OR nothing is playing and queue is empty
            alone = len(vc.channel.members) == 1
            silent = not vc.is_playing() and player.queue.empty()

            if alone or silent:
                if player.idle_start is None:
                    player.idle_start = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - player.idle_start >= 300: # 5 minutes
                    logger.info(f"Disconnecting from guild {guild_id} due to inactivity.")
                    await self.cleanup(guild)
            else:
                player.idle_start = None

bot = MusicBot()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Streaming(name="/help", url="https://fhidan.com/simon"))

@bot.tree.command(name="help", description="عرض قائمة الأوامر والمساعدة")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="خدمة العملاء 🤵🏻‍♂️",
        description="هلا بك! أنا هنا عشان أخدمك في الأغاني. هذي الأوامر اللي أقدر أسويها، خلك معي أستاذي:",
        color=discord.Color.green()
    )
    
    commands_list = [
        ("`/play [رابط أو اسم]`", "تشغل لك اللي تبي، حط رابط المقطع أو بس اسمه وبجيبه لك."),
        ("`/pause`", "توقف المقطع اللي شغال حالياً شوي."),
        ("`/resume`", "تكمل تشغيل المقطع اللي وقفناه."),
        ("`/skip`", "تتعدى المقطع اللي شغال الحين ونروح للي بعده."),
        ("`/stop`", "توقف كل شيء وتمسح قائمة التشغيل، وتقلبها هدوء."),
        ("`/queue`", "توريك وش الأغاني اللي محترية دورها في القائمة."),
        ("`/nowplaying`", "تعلمك وش المقطع اللي قاعدين نسمعه الحين."),
        ("`/volume [0-100]`", "تغير قوة الصوت، اختر رقم من صفر لمية."),
        ("`/loop`", "تكرر المقطع الحالي عشان ما يخلص ونعيد فيه."),
        ("`/shuffle`", "تخربط ترتيب القائمة.. خلك عشوائي اليوم!"),
        ("`/disconnect`", "تطردني من الروم.. الله يسامحك، في أمان الله!"),
        ("`/help`", "تطلع لك هذي القائمة عشان ما تضيع وسط الأوامر.")
    ]
    
    for name, value in commands_list:
        embed.add_field(name=name, value=value, inline=False)
    
    embed.set_footer(text="تبشر بالسعد، لو احتجت شيء ثاني لا يردك إلا لسانك!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="تشغيل مقطع أو قائمة تشغيل من يوتيوب أو رابط")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("لازم تكون في قناة صوتية عشان أقدر أخدمك!")
    
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()
    
    if vc.channel != interaction.user.voice.channel:
        return await interaction.followup.send("أنا موجود في قناة صوتية ثانية حالياً!")

    if is_url(search):
        await interaction.followup.send("أبشر، قاعد أجهز الرابط اللي أرسلته...")
    else:
        await interaction.followup.send("أبشر، قاعد أبحث عن طلبك...")

    try:
        source = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
    except Exception as e:
        logger.error(f"Play error: {e}")
        return await interaction.edit_original_response(content="ما حصلت اللي تبي، تأكد من الرابط أو الكلمات اللي كتبتها.")

    player = bot.get_player(interaction.guild)
    await player.queue.put(source)
    
    await interaction.edit_original_response(content=f"أبشر، شغلت: **{source.title}** وأضفتها للقائمة.")

@bot.tree.command(name="pause", description="إيقاف مؤقت للأغنية")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("ما فيه شيء شغال حالياً!")
    vc.pause()
    await interaction.response.send_message("وقفت المقطع مؤقتاً.")

@bot.tree.command(name="resume", description="استكمال تشغيل الأغنية")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_paused():
        return await interaction.response.send_message("المقطع مو موقوف!")
    vc.resume()
    await interaction.response.send_message("رجعت أشغل المقطع.")

@bot.tree.command(name="skip", description="تخطي الأغنية الحالية")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_connected():
        return await interaction.response.send_message("أنا مو متصل بأي قناة صوتية.")
    
    if vc.is_playing():
        vc.stop()
        await interaction.response.send_message("تم تخطي المقطع.")
    else:
        await interaction.response.send_message("ما فيه شيء شغال عشان أتخطاه.")

@bot.tree.command(name="stop", description="إيقاف الموسيقى ومسح قائمة التشغيل")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("ما فيه شيء شغال حالياً.")
    
    if interaction.guild.id in bot.players:
        player = bot.players[interaction.guild.id]
        while not player.queue.empty():
            try:
                player.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    vc.stop()
    await interaction.response.send_message("وقفت كل شيء ومسحت القائمة.. هدوووووء!")

@bot.tree.command(name="queue", description="عرض قائمة التشغيل الحالية")
async def queue(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("القائمة فاضية، ما فيها شيء.")
    
    player = bot.players[interaction.guild.id]
    if player.queue.empty() and not player.current:
         return await interaction.response.send_message("القائمة فاضية، ما فيها شيء.")

    description = ""
    if player.current:
        description += f"**اللي شغال الحين:** {player.current.title}\n\n"
    
    queue_list = list(player.queue._queue)
    if queue_list:
        description += "**القائمة القادمة:**\n"
        for i, source in enumerate(queue_list[:10], start=1):
            description += f"{i}. {source.title}\n"
    
    embed = discord.Embed(title="قائمة المقاطع", description=description, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="عرض الأغنية الشغالة حالياً")
async def nowplaying(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players or not bot.players[interaction.guild.id].current:
        return await interaction.response.send_message("ما فيه شيء شغال الحين.")
    
    player = bot.players[interaction.guild.id]
    await interaction.response.send_message(f"نسمع الحين: **{player.current.title}**")

@bot.tree.command(name="volume", description="تغيير مستوى الصوت (0-100)")
async def volume(interaction: discord.Interaction, level: int):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("أنا مو متصل بقناة صوتية.")
    if not (0 <= level <= 100):
        return await interaction.response.send_message("مستوى الصوت لازم يكون بين 0 و 100.")
    
    vol = level / 100
    if interaction.guild.id in bot.players:
        bot.players[interaction.guild.id].volume = vol
    
    if vc.source:
        vc.source.volume = vol
        
    await interaction.response.send_message(f"غيرت مستوى الصوت لعيونك وصار: {level}%")

@bot.tree.command(name="loop", description="تبديل وضع التكرار للأغنية الحالية")
async def loop(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("ما فيه مشغل شغال حالياً.")
    
    player = bot.players[interaction.guild.id]
    player.loop_mode = not player.loop_mode
    status = "مفعل" if player.loop_mode else "معطل"
    await interaction.response.send_message(f"وضع التكرار الحين: {status}.")

@bot.tree.command(name="shuffle", description="تبديل ترتيب القائمة عشوائياً")
async def shuffle(interaction: discord.Interaction):
    if interaction.guild.id not in bot.players:
        return await interaction.response.send_message("القائمة فاضية.")
    
    player = bot.players[interaction.guild.id]
    if player.queue.empty():
        return await interaction.response.send_message("القائمة فاضية.")
    
    import random
    queue_list = list(player.queue._queue)
    random.shuffle(queue_list)
    player.queue._queue.clear()
    for item in queue_list:
        player.queue.put_nowait(item)
        
    await interaction.response.send_message("خربطت لك القائمة.. خلك عشوائي!")

@bot.tree.command(name="disconnect", description="فصل البوت من القناة الصوتية")
async def disconnect(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("أنا برا الروم أصلاً!")
    
    if interaction.guild.id in bot.players:
        del bot.players[interaction.guild.id]
        
    await vc.disconnect()
    await interaction.response.send_message("تم الفصل، فمان الله.")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
