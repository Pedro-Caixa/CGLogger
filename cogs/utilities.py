import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed
from utils.sheets import get_row_by_username, get_cell_color, client, sheets, add_cep, add_new_user
from utils.log_utils import log_command
from utils.helpers import format_username

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def _get_quota_data(self, username, row_index):
        """Retrieve quota data for a user from the Google Sheet."""
        try:
            spreadsheet = client.open_by_key(sheets["Main"])
            worksheet = spreadsheet.worksheet("Main Sheet")
            row_values = worksheet.row_values(row_index)

            def get_status(column_index):
                value = row_values[column_index - 1] if len(row_values) >= column_index else "N/A"
                color = get_cell_color("Main", username, column_index)
                status = "✅" if color == "#b7e1cd" else "❌"
                return value, status

            return {
                "EP": get_status(5),
                "CEP": get_status(6),
                "IGT": get_status(7)
            }
        except Exception as e:
            print(f"Error fetching quota data: {e}")
            return None

    async def _send_loading(self, ctx):
        """
        For text commands: send a loading message and return it.
        For slash commands: defer the response and return None.
        """
        if ctx.interaction:
            await ctx.defer()
            return None
        else:
            return await ctx.send("Loading sheet information...")

    async def _send_response(self, ctx, type=None, description=None, loading_message=None, embed=None):
        """Send an embed response, handling loading message deletion if needed."""
        embed = embed or make_embed(type=type, title=type, description=description)
        if ctx.interaction:
            await ctx.interaction.edit_original_response(embed=embed)
        else:
            if loading_message:
                await loading_message.delete()
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping(self, ctx: commands.Context):
        """Returns the bot's latency."""
        latency = round(self.bot.latency * 1000)
        embed = make_embed(
            type="Success",
            title="Pong!",
            description=f"Bot latency is {latency}ms"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="quota",
        description="Check user's quota status."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def quota(
        self, 
        ctx: commands.Context, 
        member: discord.Member = None, 
        *, 
        username: str = None
    ):
        """
        Check a user's quota by retrieving their row from Google Sheets.
        
        If no member or username is provided, defaults to the command author's nickname.
        """
        if member is not None:
            username = format_username(member)
        elif username is not None:
            username = username.strip()
        else:
            username = format_username(ctx.author)
        
        loading_message = await self._send_loading(ctx)
        
        user_row_index = get_row_by_username("Main", username)
        if not user_row_index:
            return await self._send_response(
                ctx, 
                "Error", 
                f"Username '{username}' not found in the sheet.", 
                loading_message
            )

        user_row_color = get_cell_color("Main", username, 4)
        excused, failed = user_row_color == "#351c75", user_row_color == "#ff0000"

        quota_data = self._get_quota_data(username, user_row_index)
        if not quota_data:
            return await self._send_response(
                ctx, 
                "Error", 
                "Failed to retrieve quota data.", 
                loading_message
            )

        ep_value, ep_status = quota_data["EP"]
        cep_value, cep_status = quota_data["CEP"]
        igt_value, igt_status = quota_data["IGT"]

        embed = make_embed(
            type="Info" if excused else "Error" if failed else "Success",
            title=f"{username}'s Quota{' (Excused)' if excused else ''}",
            description="Here is the user's quota status:"
        )
        embed.add_field(name=f"EP {ep_status}", value=ep_value, inline=True)
        embed.add_field(name=f"CEP {cep_status}", value=cep_value, inline=True)
        embed.add_field(name=f"In-game Time {igt_status}", value=igt_value, inline=True)

        await self._send_response(ctx, embed=embed, loading_message=loading_message)

        await log_command(
            bot=self.bot,
            command_name="quota",
            user=ctx.author,
            guild=ctx.guild,
            Parameters=username,
            EP_Status=ep_status,
            CEP_Status=cep_status,
            IGT_Status=igt_status
        )



    @commands.hybrid_command(name="leaderboard", description="Show the top 10 users in the leaderboard")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def leaderboard(self, ctx: commands.Context):
        """Retrieve and display the top 10 users from the leaderboard."""
        try:
            spreadsheet = client.open_by_key(sheets["Leaderboard"])
            worksheet = spreadsheet.worksheet("Leaderboard")
            rows = worksheet.get_all_values()[5:15]

            if not rows:
                raise commands.CommandError("No data found in the leaderboard.")

            embed = make_embed(
                type="Info",
                title="🏆 Leaderboard",
                description="Here are the top 10 users in the leaderboard:"
            )

            medals = ["🥇", "🥈", "🥉"]
            for i, row in enumerate(rows):
                position, username, points = row
                medal = medals[i] if i < 3 else ""
                embed.add_field(
                    name=f"{medal} {position}. {username}",
                    value=f"Event Points: {points}",
                    inline=False
                )
            embed.color = discord.Color.yellow()
            await ctx.send(embed=embed)

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Error",
                description=f"Failed to retrieve leaderboard data: {str(e)}"
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = make_embed(
                type="Error",
                title="Command Cooldown",
                description=f"❌ {ctx.command.name} is on cooldown! Wait {error.retry_after:.1f}s."
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        """Handle slash command cooldowns."""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, commands.CommandOnCooldown):
            embed = make_embed(
                type="Error",
                title="Command Cooldown",
                description=f"❌ {interaction.command.name} is on cooldown! Wait {error.retry_after:.1f}s."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utilities(bot))