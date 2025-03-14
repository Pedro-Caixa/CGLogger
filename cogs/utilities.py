import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed
from utils.sheets import get_row_by_username
from utils.log_utils import log_command

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping(self, interaction: discord.Interaction):
        """Returns the bot's latency."""
        latency = round(self.bot.latency * 1000)
        embed = make_embed(
            type="Success",
            title="Pong!",
            description=f"Bot latency is {latency}ms"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
