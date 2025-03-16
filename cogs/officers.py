import discord
from discord.ext import commands
from discord import app_commands
import re
from config import GUILD_ID, OFFICER_ROLES
from utils.embed_utils import make_embed
from utils.log_utils import log_command

class Officers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_officer():
        async def predicate(ctx):
            if any(role.id in OFFICER_ROLES for role in ctx.author.roles):
                return True
            raise commands.MissingAnyRole(OFFICER_ROLES)
        return commands.check(predicate)
    
    def requires_reply():
        async def predicate(ctx):
            if not ctx.message.reference:
                raise commands.CommandError("This command must be used as a reply to a formatted message")
            return True
        return commands.check(predicate)

    @commands.hybrid_command(name="logevent", description="Log an event from formatted message")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_officer()
    @requires_reply()
    async def logevent(self, ctx: commands.Context):
        """Logs an event using formatted message data"""
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content
            
            required_fields = [
                "Event:", "Hosted by:", "Attendees:",
                "Notes:", "Proof:", "EP for event:", "Ping:"
            ]
            
            missing_fields = [field for field in required_fields if field not in content]
            if missing_fields:
                raise commands.CommandError(f"Missing required fields: {', '.join(missing_fields)}")
            
            ep_match = re.search(r"EP for event:\s*(\d+)", content)
            if not ep_match:
                raise commands.CommandError("Invalid EP value format in message")
            
            ep_value = int(ep_match.group(1))
            
            embed = make_embed(
                type="Success",
                title="Event Logged!",
                description=(
                    f"**EP Value:** {ep_value}\n"
                    f"**Linked Message:** [Jump to Message]({replied_message.jump_url})\n"
                    f"**Logged by:** {ctx.author.mention}"
                )
            )
            
            await ctx.send(embed=embed)
            
            await log_command(
                bot=self.bot,
                command_name="logevent",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=f"EP: {ep_value} | Message: {replied_message.id}",
                EP_Value=ep_value
            )

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Logging Failed",
                description=f"Error: {str(e)}\n\n**Required format:**\n"
                            "```Event:\nHosted by:\nAttendees:\nNotes:\nProof:\nEP for event:\nPing:```"
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            role_mentions = [f"<@&{rid}>" for rid in OFFICER_ROLES if ctx.guild.get_role(rid)]
            embed = make_embed(
                type="Error",
                title="Permission Denied",
                description=f"Requires roles: {', '.join(role_mentions)}"
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.CommandError):
            embed = make_embed(
                type="Error",
                title="Format Error",
                description=str(error)
            )
            await ctx.send(embed=embed, delete_after=15)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingAnyRole):
            role_mentions = [f"<@&{rid}>" for rid in OFFICER_ROLES if interaction.guild.get_role(rid)]
            embed = make_embed(
                type="Error",
                title="Permission Denied",
                description=f"Requires roles: {', '.join(role_mentions)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        elif isinstance(error, commands.CommandError):
            embed = make_embed(
                type="Error",
                title="Format Error",
                description=str(error)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)

async def setup(bot):
    await bot.add_cog(Officers(bot))