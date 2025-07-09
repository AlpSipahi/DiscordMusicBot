import discord
from discord.ext import commands
import yt_dlp
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}

    def get_queue(self, guild_id):
        return self.queue.setdefault(guild_id, [])

    def cleanup(self, guild_id):
        if guild_id in self.queue:
            del self.queue[guild_id]

    async def play_next(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if queue:
            url, title = queue.pop(0)
            await self._play_stream(ctx, url, title)
        else:
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            self.cleanup(ctx.guild.id)
            await ctx.send("🚪 Left the voice channel (queue is empty).")

    async def _play_stream(self, ctx, stream_url, title):
        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        vc = ctx.voice_client
        if not vc:
            await ctx.send("⚠️ Bot is not connected to a voice channel.")
            return

        def after_play(error):
            if error:
                print(f"[ERROR] Playback error: {error}")
            fut = asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"[ERROR] Exception in after_play: {e}")

        try:
            audio_source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
            vc.play(audio_source, after=after_play)
            asyncio.run_coroutine_threadsafe(ctx.send(f"🎶 Now playing: **{title}**"), self.bot.loop)
            print(f"[INFO] Started playing: {title}")
        except Exception as e:
            print(f"[ERROR] Failed to play stream: {e}")
            asyncio.run_coroutine_threadsafe(ctx.send(f"⚠️ Failed to play audio: {e}"), self.bot.loop)

    @commands.command()
    async def play(self, ctx, *, url: str):
        print(f"[COMMAND] play called by {ctx.author} in guild {ctx.guild}")

        # Check if user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ You must be in a voice channel to use this command.")
            print("[WARN] User not in voice channel")
            return

        voice_channel = ctx.author.voice.channel
        vc = ctx.voice_client

        try:
            # Connect or move the bot to the user's voice channel
            if vc is None:
                print(f"[INFO] Connecting to voice channel: {voice_channel}")
                vc = await voice_channel.connect()
            elif vc.channel != voice_channel:
                print(f"[INFO] Moving from {vc.channel} to {voice_channel}")
                await vc.move_to(voice_channel)
        except Exception as e:
            await ctx.send(f"⚠️ Could not connect to voice channel: {e}")
            print(f"[ERROR] Voice connection failed: {e}")
            return

        # yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'skip_download': True,
            'forceurl': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                stream_url = info['url']
                title = info.get('title', 'Unknown Title')
            print(f"[INFO] Extracted URL: {stream_url}, Title: {title}")
        except Exception as e:
            await ctx.send(f"⚠️ Failed to retrieve audio info: {e}")
            print(f"[ERROR] yt-dlp extract_info failed: {e}")
            return

        queue = self.get_queue(ctx.guild.id)

        if vc.is_playing() or vc.is_paused():
            queue.append((stream_url, title))
            await ctx.send(f"➕ Added to queue: **{title}**")
            print(f"[INFO] Added to queue: {title}")
        else:
            await self._play_stream(ctx, stream_url, title)

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("⏭️ Skipped current song.")
            print("[INFO] Song skipped.")
        else:
            await ctx.send("⚠️ Nothing is currently playing.")

    @commands.command()
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Paused the music.")
            print("[INFO] Music paused.")
        else:
            await ctx.send("⚠️ Nothing is currently playing.")

    @commands.command()
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Resumed the music.")
            print("[INFO] Music resumed.")
        else:
            await ctx.send("⚠️ The music is not paused.")

    @commands.command()
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await vc.disconnect()
            self.cleanup(ctx.guild.id)
            await ctx.send("⏹️ Stopped the music and left the voice channel.")
            print("[INFO] Music stopped and disconnected.")
        else:
            await ctx.send("⚠️ Nothing is playing.")

async def setup(bot):
    await bot.add_cog(Music(bot))
