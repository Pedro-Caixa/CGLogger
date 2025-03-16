import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID
from utils.embed_utils import make_embed
from utils.sheets import get_row_by_username, get_cell_color, client, sheets
from utils.log_utils import log_command

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.hybrid_command(name="quota", description="Check user's quota status based on row colors")
    @commands.cooldown(1, 30, commands.BucketType.user)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def quota(self, ctx: commands.Context, username: str):
        try:
            if ctx.interaction:
                await ctx.defer()
                loading_message = await ctx.send("Loading sheet information...")
            else:
                loading_message = await ctx.send("Loading sheet information...")

            user_row_index = get_row_by_username("Main", username)
            if not user_row_index:
                embed = make_embed(
                    type="Error",
                    title="Error",
                    description=f"Username '{username}' not found in the sheet."
                )
                return await self.send_response(ctx, embed, loading_message)
                    
            user_row_color = get_cell_color("Main", username, 4)
            excused = user_row_color == "#351b75"
            failed = user_row_color == "#ff0000"

            spreadsheet = client.open_by_key(sheets["Main"])
            worksheet = spreadsheet.worksheet("Main Sheet")
            row_values = worksheet.row_values(user_row_index)

            ep_value  = row_values[4] if len(row_values) >= 5 else "N/A"
            cep_value = row_values[5] if len(row_values) >= 6 else "N/A"
            igt_value = row_values[6] if len(row_values) >= 7 else "N/A"

            ep_color  = get_cell_color("Main", username, 5)
            cep_color = get_cell_color("Main", username, 6)
            igt_color = get_cell_color("Main", username, 7)

            ep_status  = "✅" if ep_color  == "#b7e1cd" else "❌"
            cep_status = "✅" if cep_color == "#b7e1cd" else "❌"
            igt_status = "✅" if igt_color == "#b7e1cd" else "❌"

            embed = make_embed(
                type = "Info" if excused else "Error" if failed else "Success",
                title=f"{username}'s Quota{' (Excused)' if excused else ''}",
                description="Here is the user's quota status:"
            )
            embed.add_field(name=f"EP {ep_status}", value=ep_value, inline=True)
            embed.add_field(name=f"CEP {cep_status}", value=cep_value, inline=True)
            embed.add_field(name=f"In-game Time {igt_status}", value=igt_value, inline=True)

            await self.send_response(ctx, embed, loading_message)
            
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

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Error",
                description=f"An error occurred: {str(e)}"
            )
            await self.send_response(ctx, embed, loading_message)
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
        """Handle slash command cooldowns"""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, commands.CommandOnCooldown):
            embed = make_embed(
                type="Error",
                title="Command Cooldown",
                description=f"❌ {interaction.command.name} is on cooldown! Wait {error.retry_after:.1f}s."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    async def send_response(self, ctx: commands.Context, embed: discord.Embed, loading_message: discord.Message = None):
        if ctx.interaction:
            await ctx.interaction.edit_original_response(embed=embed)
        else:
            if loading_message:
                await loading_message.delete()
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))