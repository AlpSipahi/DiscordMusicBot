import discord
from discord.ext import commands
import asyncio

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.terminal_task_started = False

    async def listen_for_terminal_commands(self):
        if self.terminal_task_started:
            return  # prevent multiple tasks
        self.terminal_task_started = True

        print("📋 Terminal Role Manager Ready. Type: roles, members, giverole, exitroles")

        while True:
            cmd = input(">> ").strip().lower()

            if cmd == "roles":
                await self.display_roles()
            elif cmd == "members":
                await self.display_members()
            elif cmd == "giverole":
                await self.give_role_terminal()
            elif cmd == "exitroles":
                print("🚪 Exiting role manager.")
                break
            else:
                print("❓ Unknown command. Available: roles, members, giverole, exitroles")

    async def display_roles(self):
        for guild in self.bot.guilds:
            print(f"\n📋 Roles in Guild: {guild.name} (ID: {guild.id})")
            for role in guild.roles:
                if role.name != "@everyone":
                    print(f" - {role.name} (ID: {role.id})")
        print()

    async def display_members(self):
        for guild in self.bot.guilds:
            print(f"\n👥 Members in Guild: {guild.name} (ID: {guild.id})")
            for member in guild.members:
                print(f" - {member} (ID: {member.id})")
        print()

    async def give_role_terminal(self):
        guild = self.bot.guilds[0]  # assuming one guild — can make this selectable if needed

        try:
            user_id_input = input("Enter User ID: ").strip()
            user_id = int(user_id_input)
            member = guild.get_member(user_id)
            if not member:
                print(f"❌ Member with ID {user_id} not found.")
                return

            role_id_input = input("Enter Role ID to give: ").strip()
            role_id = int(role_id_input)
            role = discord.utils.get(guild.roles, id=role_id)
            if not role:
                print(f"❌ Role with ID {role_id} not found.")
                return

            if role >= guild.me.top_role:
                print(f"❌ Cannot assign role '{role.name}' — it's higher than my top role.")
                return

            await member.add_roles(role)
            print(f"✅ Gave role '{role.name}' to {member.display_name} ({member.id})")

        except Exception as e:
            print(f"❌ Error: {e}")
            
            
    async def display_giveable_roles(self):
        print("\nGiveable Roles:")
        for role in self.roles_to_manage:
            print(f"  - {role.name} ({role.id})")
        print()

async def setup(bot):
    await bot.add_cog(Roles(bot))
