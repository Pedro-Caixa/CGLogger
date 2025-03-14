# cogs/utilities.py
import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed
from utils.log_utils import log_command
from utils.sheets import search_in_sheet  # Import the search_in_sheet function

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
            fields=[("Latency", f"{latency}ms", True)],
        )
        await interaction.response.send_message(embed=embed)

        await log_command(
            bot=self.bot,
            command_name="ping",
            user=interaction.user,
            guild=interaction.guild,
            latency=f"{latency}ms",
        )

    @app_commands.command(name="greet", description="Greet a user")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def greet(self, interaction: discord.Interaction, user: discord.Member):
        embed = make_embed(
            type="Information",
            title="Greet Command",
            description=f"Hello, {user.mention}!",
            fields=[("User", user.display_name, True)],
        )
        await interaction.response.send_message(embed=embed)

        await log_command(
            bot=self.bot,
            command_name="greet",
            user=interaction.user,
            guild=interaction.guild,
            greeted_user=user.mention,
        )

    @app_commands.command(name="inspect", description="Search user in database")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def inspect(self, interaction: discord.Interaction, username: str):
        """Search for a user in the Google Sheet and display their career status"""
        result = search_in_sheet(username)
        
        if not result:
            embed = make_embed(
                type="Error",
                title="User Not Found",
                description=f"No records found for **{username}**",
            )
            await interaction.response.send_message(embed=embed)
            return

        rank = result[2]
        username = result[3]
        ep = result[4]
        cep = result[5]
        in_game_time = result[6]
        total_ep = result[7]
        total_cep = result[8]

        fields = [
            ("Rank", rank, True),
            ("EP", ep, True),
            ("CEP", cep, True),
            ("In-game Time", in_game_time, True),
            ("Total EP", total_ep, True),
            ("Total CEP", total_cep, True),
        ]

        embed = make_embed(
            type="Information",
            title=f"{username}'s Career Status",
            description="Here is the career status for the user:",
            fields=fields
        )

        await interaction.response.send_message(embed=embed)
        
        await log_command(
            bot=self.bot,
            command_name="inspect",
            user=interaction.user,
            guild=interaction.guild,
            searched_user=username,
            result=bool(result)
        )

async def setup(bot):
    await bot.add_cog(Utilities(bot))