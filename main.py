import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')


intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix = "c!", intents=intents)

GUILD_ID = discord.Object(id=1321191809422196796)


@client.tree.command(name="hello", description = "yeah", guild = GUILD_ID)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")


client.run(DISCORD_TOKEN)