import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed
from utils.sheets import get_row_by_username, get_cell_color
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

    @app_commands.command(name="quota", description="Check user's quota status based on row colors")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def quota(self, interaction: discord.Interaction, username: str):
        """Check the quota status based on the user's row colors."""
        try:
            user_row_index = get_row_by_username("Main", username)
            if not user_row_index:
                embed = make_embed(
                    type="Error",
                    title="Error",
                    description=f"Username '{username}' not found in the sheet."
                )
                await interaction.response.send_message(embed=embed)
                return

            user_row_color = get_cell_color("Main", username, 4)
            if user_row_color == "#351c75":
                embed = make_embed(
                    type="Success",
                    title="Quota Status",
                    description=f"User '{username}' is exempt due to row color."
                )
                await interaction.response.send_message(embed=embed)
                return

            row_5_color = get_cell_color("Main", username, 5)
            row_6_color = get_cell_color("Main", username, 6)
            row_7_color = get_cell_color("Main", username, 7)

            if row_5_color == "#e06666" or row_6_color == "#e06666" or row_7_color == "#e06666":
                embed = make_embed(
                    type="Error",
                    title="Quota Status",
                    description=f"User '{username}' failed due to red color in rows 5, 6, or 7."
                )
                await interaction.response.send_message(embed=embed)
                return

            if row_5_color == "#b7e1cd" and row_6_color == "#b7e1cd" and row_7_color == "#b7e1cd":
                embed = make_embed(
                    type="Success",
                    title="Quota Status",
                    description=f"User '{username}' passed the quota check."
                )
                await interaction.response.send_message(embed=embed)
            else:
                embed = make_embed(
                    type="Error",
                    title="Quota Status",
                    description=f"User '{username}' did not pass the quota check due to inconsistent colors."
                )
                await interaction.response.send_message(embed=embed)

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Error",
                description=f"An error occurred: {e}"
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
