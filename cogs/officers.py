import os
import discord
import uuid
import asyncio
from discord.ext import commands
from discord import app_commands
import re
import aiohttp
from config import GUILD_ID, OFFICER_ROLES
from utils.embed_utils import make_embed
from utils.log_utils import log_command
from utils.sheets import add_ep, remove_ep, get_ep
from utils.helpers import format_username
from dotenv import load_dotenv

load_dotenv()
EVENT_LOG_WEBHOOK = os.getenv('EVENT_LOG_WEBHOOK')


def validate_ep_amount(amount: int) -> discord.Embed | None:
    """Validate EP amount and return error embed if invalid."""
    if amount > 5:
        return make_embed(
            type="Error",
            title="Invalid EP Amount",
            description="EP amount cannot exceed 5. Please use a value between 1-5."
        )
    if amount <= 0:
        return make_embed(
            type="Error",
            title="Invalid EP Amount",
            description="EP amount must be greater than zero."
        )
    return None

async def delete_messages_after_delay(bot, messages, delay):
    await asyncio.sleep(delay)
    for msg in messages:
        if msg is not None:
            try:
                await msg.delete()
            except:
                pass

async def handle_permission_error(ctx, error):
    embed = make_embed(
        type="Error",
        title="Permission Denied",
        description="\n".join([
            "You don't have permission to use this command.",
            "Required roles: " + ", ".join([f"<@&{rid}>" for rid in OFFICER_ROLES])
        ])
    )
    error_msg = await ctx.send(embed=embed)
    await delete_messages_after_delay(ctx.bot, [ctx.message, error_msg], 5)


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

    async def _process_attendees(self, ctx, attendees_line):
        """Process attendee mentions into formatted list."""
        attendee_mentions = re.findall(r"<@!?(\d+)>", attendees_line)
        
        if not attendee_mentions:
            raise commands.CommandError("No valid attendee mentions found")
        
        raw_attendees = []
        for attendee_id in attendee_mentions:
            member = await ctx.guild.fetch_member(int(attendee_id))
            raw_attendees.append(format_username(member))
        
        return self._format_attendee_list(raw_attendees)

    def _format_attendee_list(self, attendees):
        """Format attendees list with truncation."""
        attendee_lines = [f"• {username}" for username in attendees[:10]]
        if len(attendees) > 10:
            attendee_lines.append(f"• ...and {len(attendees)-10} more")
        return "\n".join(attendee_lines)

    async def _handle_command_response(self, ctx, success, success_msg, error_msg, delete_delay=5):
        """Handle command response and message deletion."""
        if success:
            await ctx.send(embed=success_msg)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message], delete_delay))
        else:
            await ctx.send(embed=error_msg)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message], delete_delay))

    @commands.hybrid_command(name="logevent", description="Log an event from formatted message")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_officer()
    @requires_reply()
    async def logevent(self, ctx: commands.Context):
        replied_message = None
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content
            
            if not replied_message.attachments:
                raise commands.CommandError("Proof image required - attach at least one image")
            
            required_fields = ["Event:", "Hosted by:", "Attendees:", "Proof:", "EP for event:"]
            if missing := [f for f in required_fields if f not in content]:
                raise commands.CommandError(f"Missing fields: {', '.join(missing)}")
            
            ep_match = re.search(r"EP for event:\s*(\d+)", content)
            if not ep_match or (ep_value := int(ep_match.group(1))) > 5:
                raise commands.CommandError("Invalid EP value (max 5)")

            host_match = re.search(r"Hosted by:\s*(.+)", content)
            if not host_match:
                raise commands.CommandError("Missing host information")
            
            host_content = host_match.group(1)
            if host_mention := re.search(r"<@!?(\d+)>", host_content):
                member = await ctx.guild.fetch_member(int(host_mention.group(1)))
                host_name = format_username(member)
            else:
                host_name = host_content.split("|")[1].strip() if "|" in host_content else host_content

            attendees_match = re.search(r"Attendees:\s*(.*)", content)
            if not attendees_match:
                raise commands.CommandError("Missing attendees list")
            
            raw_attendees = await self._process_attendees(ctx, attendees_match.group(1))
            attendee_list = self._format_attendee_list(raw_attendees)

            event_id = str(uuid.uuid4())

            embed = make_embed(
                type="Success",
                title="Event Logged!",
                description=(
                    f"**Host:** {host_name}\n"
                    f"**EP Value:** {ep_value}\n"
                    f"**Attendees ({len(raw_attendees)}):**\n{attendee_list}\n"
                    f"**Linked Message:** [Jump to Message]({replied_message.jump_url})\n"
                    f"**Logged by:** {ctx.author.name}"
                )
            )
            success_msg = await ctx.send(embed=embed)

            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(EVENT_LOG_WEBHOOK, session=session)
                files = []
                
                for attachment in replied_message.attachments:
                    if attachment.content_type.startswith('image/'):
                        files.append(await attachment.to_file())
                
                archive_embed = make_embed(
                    type="Info",
                    title=f"Event Archive: {re.search(r'Event:\s*(.*)', content).group(1)}",
                    description=(
                        f"**Host:** {host_name}\n"
                        f"**EP Awarded:** {ep_value}\n"
                        f"**Attendees ({len(raw_attendees)}):**\n{attendee_list}\n"
                        f"**Logged by:** {ctx.author.mention}\n"
                    )
                )
                archive_embed.set_footer(text=f"Event ID: {event_id}", icon_url="https://cdn.discordapp.com/emojis/1155991227032936448.webp?size=128")
                if files:
                    archive_embed.set_image(url="attachment://" + files[0].filename)

                await webhook.send(
                    embed=archive_embed,
                    files=files,
                    username="Event Logger",
                    avatar_url=self.bot.user.display_avatar.url
                )
            
            await log_command(
                bot=self.bot,
                command_name="logevent",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=(
                    f"EP: {ep_value} | Host: {host_name} | "
                    f"Attendees: {len(raw_attendees)} | Event ID: {event_id}"
                ),
                EP_Value=ep_value,
                Host=host_name,
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
            error_msg = await ctx.send(embed=embed)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message], 5))
            return

        self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message, replied_message, success_msg], 5))

class EP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _ep_command_wrapper(self, ctx, member, amount, command_type):
        """Wrapper for EP commands handling common logic."""
        if (embed := validate_ep_amount(amount)):
            return await ctx.send(embed=embed), False
        
        username = format_username(member)
        command_handler = add_ep if command_type == "add" else remove_ep
        success = command_handler(username, amount)
        
        if success:
            await log_command(
                bot=self.bot,
                command_name=f"{command_type.capitalize()} Event Points",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=username,
                Ep_Amount=amount,
            )
        
        return success

    @commands.hybrid_group(name="ep", invoke_without_command=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ep(self, ctx):
        await ctx.send("Available subcommands: add, remove, view")

    @ep.command(name="add", description="Add Event Points to a member")
    @commands.has_any_role(*OFFICER_ROLES)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ep_add(self, ctx, member: discord.Member, amount: int):
        success = await self._ep_command_wrapper(ctx, member, amount, "add")
        
        if success:
            embed = make_embed(
                type="Success",
                title="EP Added",
                description=f"{amount} EP added to {member.mention}"
            )
        else:
            embed = make_embed(
                type="Error",
                title="EP Add Failed",
                description=f"Failed to add {amount} EP to {member.mention}"
            )
        
        message = await ctx.send(embed=embed)
        await delete_messages_after_delay(ctx.bot, [ctx.message, message], 5)

    @ep.command(name="remove", description="Remove Event Points from a member")
    @commands.has_any_role(*OFFICER_ROLES)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ep_remove(self, ctx, member: discord.Member, amount: int):
            success = await self._ep_command_wrapper(ctx, member, amount, "remove")
            if success:
                embed = make_embed(
                    type="Success",
                    title="EP Removed",
                    description=f"{amount} EP removed from {member.mention}"
                )
                embed.add_field(name="New EP Total", value=f"{get_ep(format_username(member))}", inline=True)
                message = await ctx.send(embed=embed)
                await delete_messages_after_delay(ctx.bot, [ctx.message, message], 5)
            else:
                message = await ctx.send(embed=make_embed(
                    type="Error",
                    title="EP Remove Failed",
                    description=f"Failed to remove {amount} EP from {member.mention}"
                ))
                await delete_messages_after_delay(ctx.bot, [ctx.message, message], 5)

    @ep.command(name="view", description="View Event Points of a member")
    @commands.cooldown(1, 15, commands.BucketType.user)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ep_view(self, ctx, member: discord.Member):
            username = format_username(member)
            ep_value = get_ep(username)
            if ep_value is not None:
                embed = make_embed(
                    type="Success",
                    title=f"{username}'s Event Point(s)",
                    description="User EP information"
                )
                embed.add_field(name="EP", value=ep_value, inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=make_embed(
                    type="Error",
                    title="EP View Failed",
                    description=f"Failed to retrieve EP for {member.mention}"
                ))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.MissingAnyRole, commands.MissingRole)):
            await handle_permission_error(ctx, error)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = make_embed(
                type="Error",
                title="Command Cooldown",
                description=f"❌ {ctx.command.name} is on cooldown! Wait {error.retry_after:.1f}s."
            )
            message = await ctx.send(embed=embed)
            await delete_messages_after_delay(ctx.bot, [ctx.message, message], 5)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        if isinstance(error, (app_commands.MissingRole, commands.MissingAnyRole)):
            await handle_permission_error(interaction, error)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = make_embed(
                type="Error",
                title="Command Cooldown",
                description=f"❌ {interaction.command.name} is on cooldown! Wait {error.retry_after:.1f}s."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await delete_messages_after_delay(interaction.client, [interaction.message], 5)

async def setup(bot):
    await bot.add_cog(Officers(bot))
    await bot.add_cog(EP(bot))