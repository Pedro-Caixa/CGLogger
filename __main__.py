import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from config import GUILD_ID

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

class Client(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        await self.load_extension('cogs.utilities')
        await self.load_extension('cogs.officers')
        await self.load_extension('cogs.events')

        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print(f"Commands synced to guild {GUILD_ID}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="-", intents=intents)

client.run(DISCORD_TOKEN)