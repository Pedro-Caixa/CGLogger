import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from config import GUILD_ID

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

class Client(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('cogs.utilities')

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

        try:
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="c!", intents=intents)

client.run(DISCORD_TOKEN)