import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed  # Import the embed utility function

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = make_embed(
            type="Success",
            title="Ping Command",
            description=f"Pong! Latency is {latency}ms.",
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))