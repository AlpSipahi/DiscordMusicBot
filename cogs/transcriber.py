import discord
from discord.ext import commands
import asyncio
import sys
import json
import os
import itertools

TRANSCRIBER_STATE_FILE = "transcriber_state.json"
TRANSCRIPT_OUTPUT_DIR = os.getenv("TRANSCRIPT_OUTPUT_DIR", "transcripts")


class Transcriber(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.transcribe_channel: discord.TextChannel | None = None
        self.ready_event = asyncio.Event()
        self.terminal_task_started = False
        self.load_state()
        os.makedirs(TRANSCRIPT_OUTPUT_DIR, exist_ok=True)

    def load_state(self):
        if os.path.isfile(TRANSCRIBER_STATE_FILE):
            try:
                with open(TRANSCRIBER_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                channel_id = data.get("transcribe_channel_id")
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if isinstance(channel, discord.TextChannel):
                        self.transcribe_channel = channel
                        print(f"ℹ️ Restored previously selected channel: #{channel.name} ({channel.id})")
            except Exception as e:
                print(f"⚠️ Failed to load state: {e}")

    def save_state(self):
        try:
            with open(TRANSCRIBER_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "transcribe_channel_id": self.transcribe_channel.id if self.transcribe_channel else None
                }, f)
        except Exception as e:
            print(f"⚠️ Failed to save state: {e}")

    async def terminal_input(self, prompt: str = ">> ") -> str:
        print(prompt, end="", flush=True)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sys.stdin.readline)

    def is_valid_index(self, raw: str, max_index: int) -> bool:
        return raw.isdigit() and 0 <= int(raw) < max_index

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        self.ready_event.set()

    async def cmd_channels(self):
        for guild in self.bot.guilds:
            print(f"\nServer: {guild.name} (ID: {guild.id})")
            for ch in guild.text_channels:
                print(f"  - #{ch.name} (ID: {ch.id})")
        print()

    async def cmd_changechannel(self):
        print("\nAvailable servers:")
        for idx, guild in enumerate(self.bot.guilds):
            print(f"[{idx}] {guild.name} (ID: {guild.id})")

        raw = (await self.terminal_input("Select a server by number: ")).strip()
        if not self.is_valid_index(raw, len(self.bot.guilds)):
            print("❌ Invalid index.")
            return

        selected_guild = self.bot.guilds[int(raw)]
        search_term = (await self.terminal_input(f"Search channel name in {selected_guild.name}: ")).lower().strip()

        matches = [ch for ch in selected_guild.text_channels if search_term in ch.name.lower()]
        if not matches:
            print("❌ No matching channels found.")
            return

        print(f"\nMatches in {selected_guild.name}:")
        for idx, ch in enumerate(matches):
            print(f"[{idx}] #{ch.name} (ID: {ch.id})")

        chan_raw = (await self.terminal_input("Select a channel by number: ")).strip()
        if not self.is_valid_index(chan_raw, len(matches)):
            print("❌ Invalid index.")
            return

        self.transcribe_channel = matches[int(chan_raw)]
        self.save_state()
        print(f"🟢 Monitoring #{self.transcribe_channel.name} ({self.transcribe_channel.id})")

        await self.cmd_preview()

    async def cmd_preview(self):
        if not self.transcribe_channel:
            print("❌ No channel selected.")
            return

        try:
            preview = [msg async for msg in self.transcribe_channel.history(limit=15, oldest_first=False)]
            if preview:
                print("\n📝 Last 15 messages preview:")
                for msg in reversed(preview):
                    print(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.display_name}: {msg.content}")
                print()
        except Exception as e:
            print(f"⚠️ Failed to preview messages: {e}")

    async def cmd_transcribe(self, limit: int | None = None):
        if not self.transcribe_channel:
            print("❌ No channel selected.")
            return

        if limit is None:
            limit_raw = (await self.terminal_input("Number of messages to fetch (0 for all, default 100): ")).strip()
            try:
                limit = int(limit_raw) if limit_raw else 100
            except ValueError:
                print("❌ Invalid number.")
                return

        try:
            from utils.html_renderer import generate_html_transcript
            spinner = itertools.cycle(["|", "/", "-", "\\"])
            done = False

            async def spinner_task():
                while not done:
                    sys.stdout.write(f"\r⏳ Generating transcript... {next(spinner)} ")
                    sys.stdout.flush()
                    await asyncio.sleep(0.2)
                sys.stdout.write("\r✅ Transcript generation complete!    \n")

            spinner_coro = asyncio.create_task(spinner_task())
            await generate_html_transcript(self.transcribe_channel, limit, output_dir=TRANSCRIPT_OUTPUT_DIR)
            done = True
            await spinner_coro

            print(f"✅ Transcript saved to {TRANSCRIPT_OUTPUT_DIR}.")
        except Exception as e:
            print(f"⚠️ Failed to generate transcript: {e}")

    async def cmd_transcribelatest(self):
        print("Fetching last 100 messages for transcript...")
        await self.cmd_transcribe(limit=100)

    async def start_terminal_loop(self):
        await self.ready_event.wait()

        if self.terminal_task_started:
            return
        self.terminal_task_started = True

        print("🟢 Terminal ready. Type 'help' for commands.\n", flush=True)

        while True:
            try:
                if self.bot.is_closed():
                    break

                if self.transcribe_channel:
                    print(f"ℹ️ Currently selected channel: #{self.transcribe_channel.name} ({self.transcribe_channel.id})")

                command = (await self.terminal_input()).strip().lower()

                if command in ("channels", "ch"):
                    await self.cmd_channels()

                elif command in ("changechannel", "c"):
                    await self.cmd_changechannel()

                elif command in ("transcribe", "t"):
                    await self.cmd_transcribe()

                elif command == "p":
                    await self.cmd_preview()

                elif command == "transcribelatest":
                    await self.cmd_transcribelatest()

                elif command in ("roles", "members", "giverole", "exitroles"):
                    roles_cog = self.bot.get_cog("Roles")
                    if roles_cog:
                        await self.forward_to_roles(roles_cog, command)
                    else:
                        print("⚠️ Roles cog not loaded.")

                elif command in ("exit", "quit", "q"):
                    print("👋 Exiting...")
                    await self.bot.close()
                    break

                elif command == "help":
                    print("Commands: channels (ch), changechannel (c), transcribe (t), preview (p), transcribelatest, roles, members, giverole, exitroles, exit (quit, q)")

                elif command == "":
                    continue

                else:
                    print("❓ Unknown command. Type 'help'.")

            except KeyboardInterrupt:
                print("\n👋 Interrupted. Shutting down...")
                await self.bot.close()
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")

    async def forward_to_roles(self, roles_cog, command: str):
        if command == "roles":
            await roles_cog.display_giveable_roles()
        elif command == "members":
            await roles_cog.display_members()
        elif command == "giverole":
            await roles_cog.give_role_terminal()
        elif command == "exitroles":
            print("🚪 Exiting role manager.")


async def setup(bot: commands.Bot):
    cog = Transcriber(bot)
    await bot.add_cog(cog)
    if sys.stdin.isatty() or os.getenv("LOCAL_TERMINAL") == "1":
        asyncio.create_task(cog.start_terminal_loop())
    else:
        print("⚠️ Skipping terminal input — not in an interactive environment.")
