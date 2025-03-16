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
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content
            
            required_fields = [
                "Event:", "Hosted by:", "Attendees:", 
                "Proof:", "EP for event:"
            ]
            
            missing_fields = [field for field in required_fields if field not in content]
            if missing_fields:
                raise commands.CommandError(f"Missing required fields: {', '.join(missing_fields)}")
            
            ep_match = re.search(r"EP for event:\s*(\d+)", content)
            if not ep_match:
                raise commands.CommandError("Invalid EP value format in message")
            ep_value = int(ep_match.group(1))

            host_match = re.search(r"Hosted by:\s*(.+)", content)
            if not host_match:
                raise commands.CommandError("Missing or invalid host information")
            host_parts = [p.strip() for p in host_match.group(1).split("|")]

            host_mention = re.search(r"<@!(\d+)>", host_parts[0])
            if host_mention:
                user_id = int(host_mention.group(1))
                member = await ctx.guild.fetch_member(user_id)
                host_nickname = member.nick if member.nick else member.name 
            else:
                host_nickname = host_parts[0]

            attendees_match = re.search(r"Attendees:\s*([<@!>\d]+)", content)
            if not attendees_match:
                raise commands.CommandError("Missing attendees list")
            
            raw_attendees = []
            attendees_match = re.search(r"Attendees:\s*(.*)", content)
            if not attendees_match:
                raise commands.CommandError("Missing attendees list")
            
            attendees_line = attendees_match.group(1)
            attendee_mentions = re.findall(r"<@!?(\d+)>", attendees_line)
            
            if not attendee_mentions:
                raise commands.CommandError("No valid attendee mentions found")
            
            raw_attendees = []
            for attendee_id in attendee_mentions:
                member = await ctx.guild.fetch_member(int(attendee_id))
                attendee_nickname = member.nick if member.nick else member.name

                nickname_parts = [part.strip() for part in attendee_nickname.split("|")]
                attendee_name = nickname_parts[1] if len(nickname_parts) > 1 else attendee_nickname
                raw_attendees.append(attendee_name)
            
            attendee_lines = [f"• {username}" for username in raw_attendees]
            attendee_list = "\n".join(attendee_lines[:10])
            if len(raw_attendees) > 10:
                attendee_list += f"\n• ...and {len(raw_attendees)-10} more"

            embed = make_embed(
                type="Success",
                title="Event Logged!",
                description=(
                    f"**Host:** {host_nickname}\n"
                    f"**EP Value:** {ep_value}\n"
                    f"**Attendees ({len(raw_attendees)}):**\n{attendee_list}\n"
                    f"**Linked Message:** [Jump to Message]({replied_message.jump_url})\n"
                    f"**Logged by:** {ctx.author.name}"
                )
            )
            
            await ctx.send(embed=embed)
            
            await log_command(
                bot=self.bot,
                command_name="logevent",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=(
                    f"EP: {ep_value} | Host: {host_nickname} | "
                    f"Attendees: {len(raw_attendees)} | Message: {replied_message.id}"
                ),
                EP_Value=ep_value,
                Host=host_nickname,
                Attendees=len(raw_attendees)
            )

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Logging Failed",
                description=f"Error: {str(e)}\n\n**Required format example:**\n"
                            "```Event: Weekly Meetup\n"
                            "Hosted by: @[XO] | Caxseii | BRT\n"
                            "Attendees: @[XO] | Caxseii | BRT\n"
                            "Notes: Regular weekly meeting\n"
                            "Proof: attached-image.jpg\n"
                            "EP for event: 2\n"
                            "Ping: @EventManager```"
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
