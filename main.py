import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}')
        
        try: 
            guild = discord.Object(id=1321191809422196796)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {synced} commands in {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="c!", intents=intents)

GUILD_ID = discord.Object(id=1321191809422196796)

@client.tree.command(name="hello", description="yeah", guild=GUILD_ID)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")

client.run(DISCORD_TOKEN)