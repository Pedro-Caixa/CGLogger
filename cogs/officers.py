import os
import discord
import uuid
import asyncio
from discord.ext import commands
from discord import app_commands
import re
import aiohttp
from config import GUILD_ID, OFFICER_ROLES, STARTER_ROLES
from utils.embed_utils import make_embed
from utils.log_utils import log_command
from utils.sheets import add_ep, remove_ep, get_ep, find_user_sheet, batch_update_points, add_new_user
from utils.helpers import format_username
from discord.colour import Colour
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
        """Process attendee mentions and return a list of formatted usernames."""
        attendee_mentions = re.findall(r"<@!?(\d+)>", attendees_line)
        
        if not attendee_mentions:
            raise commands.CommandError("No valid attendee mentions found")
        
        raw_attendees = []
        for attendee_id in attendee_mentions:
            member = await ctx.guild.fetch_member(int(attendee_id))
            raw_attendees.append(format_username(member))
        
        return raw_attendees

    async def _process_extra_points(self, ctx, extra_points_line):
        """Process extra points mentions and return a list of tuples (username, points)."""
        extra_points_matches = re.findall(r"<@!?(\d+)>\s*\((\d+)\)", extra_points_line)
        
        if not extra_points_matches:
            raise commands.CommandError("No valid extra points mentions found")
        
        extra_points = []
        for user_id, points in extra_points_matches:
            member = await ctx.guild.fetch_member(int(user_id))
            username = format_username(member)
            points = int(points)
            if points > 5:
                raise commands.CommandError(f"Invalid extra points value for {username} (max 5)")
            extra_points.append((username, points))
        
        return extra_points

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
            
            is_company_event = any(
                kw in ctx.channel.name for kw in ["hound-event-logs", "riot-event-logs", "shock-event-logs"]
            )

            point_type = "CEP" if is_company_event else "EP"
            ep_field = f"{point_type} for event:"
            required_fields = ["Event:", "Hosted by:", "Attendees:", "Proof:", ep_field]
            if missing := [f for f in required_fields if f not in content]:
                raise commands.CommandError(f"Missing fields: {', '.join(missing)}")
            
            ep_pattern = rf"{point_type} for event:\s*(\d+)|{point_type} for Event:\s*(\d+)"
            ep_match = re.search(ep_pattern, content, re.IGNORECASE)

            if not ep_match or (ep_value := int(ep_match.group(1))) > 5:
                raise commands.CommandError(f"Invalid {point_type} value (max 5)")

            event_match = re.search(r"Event:\s*(.+)", content)
            if not event_match:
                raise commands.CommandError("Missing event information")
            
            event_type = event_match.group(1).strip()

            host_match = re.search(r"Hosted by:\s*(.+)", content)
            if not host_match and event_type != "SSU":
                raise commands.CommandError("Missing host information")
            
            host_name = None
            if event_type != "SSU":
                host_content = host_match.group(1)
                if host_mention := re.search(r"<@!?(\d+)>", host_content):
                    member = await ctx.guild.fetch_member(int(host_mention.group(1)))
                    host_name = format_username(member)
                else:
                    host_name = host_content.split("|")[1].strip() if "|" in host_content else host_content

            supervisor_match = re.search(r"Supervisor:\s*(.+)", content)
            supervisor_name = None
            if supervisor_match:
                supervisor_content = supervisor_match.group(1)
                if supervisor_mention := re.search(r"<@!?(\d+)>", supervisor_content):
                    member = await ctx.guild.fetch_member(int(supervisor_mention.group(1)))
                    supervisor_name = format_username(member)
                else:
                    supervisor_name = supervisor_content.split("|")[1].strip() if "|" in supervisor_content else supervisor_content

            cohost_match = re.search(r"Co-host:\s*(.+)", content)
            cohost_name = None
            if cohost_match:
                cohost_content = cohost_match.group(1)
                if cohost_mention := re.search(r"<@!?(\d+)>", cohost_content):
                    member = await ctx.guild.fetch_member(int(cohost_mention.group(1)))
                    cohost_name = format_username(member)
                else:
                    cohost_name = cohost_content.split("|")[1].strip() if "|" in cohost_content else cohost_content

            attendees_match = re.search(r"Attendees:\s*(.*)", content)
            if not attendees_match:
                raise commands.CommandError("Missing attendees list")
            
            raw_attendees = await self._process_attendees(ctx, attendees_match.group(1))
            attendee_list = self._format_attendee_list(raw_attendees)

            extra_points_match = re.search(r"Extra points:\s*(.*)", content)
            extra_points = []
            if extra_points_match:
                extra_points = await self._process_extra_points(ctx, extra_points_match.group(1))

            updates = []
            
            if event_type != "SSU" and host_name:
                host_sheet = find_user_sheet(host_name) or "Main"
                if host_sheet == "Officer":
                    updates.append({
                        "sheet": "Officer",
                        "worksheet_name": "Officer Sheet",
                        "username": host_name,
                        "header": "OP",
                        "amount": ep_value,
                        "is_add": True
                    })
                    event_columns = {
                        "Company": "Company Events Hosted",
                        "Wide": "Events Hosted"
                    }
                    if is_company_event:
                        updates.append({
                            "sheet": "Officer",
                            "worksheet_name": "Officer Sheet",
                            "username": host_name,
                            "header": event_columns["Company"],
                            "amount": 1,
                            "is_add": True
                        })
                    else:
                        updates.append({
                            "sheet": "Officer",
                            "worksheet_name": "Officer Sheet",
                            "username": host_name,
                            "header": event_columns["Wide"],
                            "amount": 1,
                            "is_add": True
                        })
                else:
                    updates.append({
                        "sheet": "Main",
                        "worksheet_name": "Main Sheet",
                        "username": host_name,
                        "header": point_type,
                        "amount": ep_value,
                        "is_add": True
                    })

                for attendee in raw_attendees:
                    attendee_sheet = find_user_sheet(attendee) or "Main"
                    header = "OP" if attendee_sheet == "Officer" else point_type
                    updates.append({
                        "sheet": attendee_sheet,
                        "worksheet_name": "Officer Sheet" if attendee_sheet == "Officer" else "Main Sheet",
                        "username": attendee,
                        "header": header,
                        "amount": ep_value,
                        "is_add": True
                    })
                else:
                    updates.append({
                        "sheet": "Main",
                        "worksheet_name": "Main Sheet",
                        "username": attendee,
                        "header": point_type,
                        "amount": ep_value,
                        "is_add": True
                    })

            if supervisor_name:
                supervisor_sheet = find_user_sheet(supervisor_name) or "Main"
                updates.append({
                    "sheet": supervisor_sheet,
                    "worksheet_name": "Officer Sheet" if supervisor_sheet == "Officer" else "Main Sheet",
                    "username": supervisor_name,
                    "header": "Supervisor",
                    "amount": ep_value,
                    "is_add": True
                })

            if cohost_name:
                cohost_sheet = find_user_sheet(cohost_name) or "Main"
                updates.append({
                    "sheet": cohost_sheet,
                    "worksheet_name": "Officer Sheet" if cohost_sheet == "Officer" else "Main Sheet",
                    "username": cohost_name,
                    "header": "Co-host",
                    "amount": ep_value,
                    "is_add": True
                })

            for username, points in extra_points:
                user_sheet = find_user_sheet(username) or "Main"
                if user_sheet == "Officer":
                    updates.append({
                        "sheet": "Officer",
                        "worksheet_name": "Officer Sheet",
                        "username": username,
                        "header": "OP",
                        "amount": points,
                        "is_add": True
                    })
                else:
                    updates.append({
                        "sheet": "Main",
                        "worksheet_name": "Main Sheet",
                        "username": username,
                        "header": point_type,
                        "amount": points,
                        "is_add": True
                    })

            batch_update_points(updates)
            event_id = str(uuid.uuid4())
            embed_color = Colour.red() if is_company_event else Colour.green()
            embed = make_embed(
                type="Success",
                title="Event Logged!",
                description=(
                    f"**Host:** {host_name if host_name else 'N/A'}\n"
                    f"**Supervisor:** {supervisor_name if supervisor_name else 'N/A'}\n"
                    f"**Co-host:** {cohost_name if cohost_name else 'N/A'}\n"
                    f"**{point_type} Value:** {ep_value}\n"
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
                    title=f"{'Company ' if is_company_event else ''}Event Archive: {event_type}",
                    description=(
                        f"**Host:** {host_name if host_name else 'N/A'}\n"
                        f"**Supervisor:** {supervisor_name if supervisor_name else 'N/A'}\n"
                        f"**Co-host:** {cohost_name if cohost_name else 'N/A'}\n"
                        f"**{point_type} Awarded:** {ep_value}\n"
                        f"**Attendees ({len(raw_attendees)}):**\n{attendee_list}\n"
                        f"**Channel:** {ctx.channel.mention}\n"
                        f"**Logged by:** {ctx.author.mention}\n"
                    )
                )
                archive_embed.colour = embed_color
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
                    f"{point_type}: {ep_value} | Host: {host_name if host_name else 'N/A'} | "
                    f"Supervisor: {supervisor_name if supervisor_name else 'N/A'} | "
                    f"Co-host: {cohost_name if cohost_name else 'N/A'} | "
                    f"Attendees: {len(raw_attendees)} | Event ID: {event_id}"
                ),
                EP_Value=ep_value,
                Host=host_name,
                Supervisor=supervisor_name,
                Co_host=cohost_name,
                Attendees=len(raw_attendees)
            )
        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Logging Failed",
                description=f"Error: {str(e)}\n\n**Required format example:**\n"
                            "```Event: Weekly Meetup\n"
                            "Hosted by: @[XO] | Caxseii | BRT\n"
                            "Supervisor: @[XO] | SupervisorName\n"
                            "Co-host: @[XO] | CoHostName\n"
                            "Attendees: @[XO] | Caxseii | BRT\n"
                            "Notes: Regular weekly meeting\n"
                            "Proof: attached-image.jpg\n"
                            "EP for event: 2\n"
                            "Extra points: @Mention (2)\n"
                            "Ping: @EventManager```"
            )
            error_msg = await ctx.send(embed=embed)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message], 5))
            return

        self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message, replied_message, success_msg], 5))

    @commands.hybrid_command(name="logtime", description="Log time from a formatted message")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_officer()
    @requires_reply()
    async def logtime(self, ctx: commands.Context):
        replied_message = None
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content

            if len(replied_message.attachments) < 2:
                raise commands.CommandError("At least two proof images are required")

            required_fields = ["Username:", "Time Started:", "Time Ended:", "Time logged:"]
            if missing := [f for f in required_fields if f not in content]:
                raise commands.CommandError(f"Missing fields: {', '.join(missing)}")

            username_match = re.search(r"Username:\s*(<@!?(\d+)>|\S+)", content)
            if not username_match:
                raise commands.CommandError("Invalid or missing username")
            
            user_id = username_match.group(2)
            if user_id:
                member = await ctx.guild.fetch_member(int(user_id))
                username = format_username(member)
            else:
                username = username_match.group(1)

            time_logged_match = re.search(r"Time logged:\s*(\d+)", content)
            if not time_logged_match:
                raise commands.CommandError("Invalid or missing time logged")
            
            time_logged = int(time_logged_match.group(1))

            updates = [{
                "sheet": find_user_sheet(username) or "Main",
                "worksheet_name": "Main Sheet",
                "username": username,
                "header": "In-game Time",
                "amount": time_logged,
                "is_add": True
            }]

            batch_update_points(updates)

            embed = make_embed(
                type="Success",
                title="Time Logged!",
                description=(
                    f"**Username:** {username}\n"
                    f"**Time Logged:** {time_logged} minutes\n"
                    f"**Logged by:** {ctx.author.name}"
                )
            )
            success_msg = await ctx.send(embed=embed)

            await log_command(
                bot=self.bot,
                command_name="logtime",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=f"Username: {username} | Time Logged: {time_logged} minutes",
                Time_Logged=time_logged
            )
        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Logging Failed",
                description=f"Error: {str(e)}\n\n**Required format example:**\n"
                            "```Username: @User\n"
                            "Time Started: 6:17pm EST\n"
                            "Time Ended: 7:42pm EST\n"
                            "Time logged: 85\n"
                            "Total time logged: 85\n"
                            "Proof: attached-image1.jpg, attached-image2.jpg```"
            )
            error_msg = await ctx.send(embed=embed)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message, error_msg], 5))
            return

        self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message, replied_message, success_msg], 5))
        
    @commands.hybrid_command(name="setupuser", description="Setup a new user with starter roles and nickname")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_officer()
    @requires_reply()
    async def setupuser(self, ctx: commands.Context):
        replied_message = None
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content
            print(f"Replied message content: {content}")

            username_match = re.search(r"Roblox Username:\s*(\S+)", content)
            print(f"Username match: {username_match}")

            if not username_match:
                raise commands.CommandError("Missing or invalid Roblox Username")

            roblox_username = username_match.group(1)
            print(f"Roblox Username: {roblox_username}")

            member = await ctx.guild.fetch_member(replied_message.author.id)
            print(f"Replied message author: {member}")

            await member.edit(roles=[], reason="Removing all roles before assigning starter roles")
            print(f"Removed all roles from {member.name}")

            roles = [ctx.guild.get_role(role_id) for role_id in STARTER_ROLES]
            await member.add_roles(*roles, reason="Assigned starter roles")
            print(f"Assigned roles to {member.name}: {[role.name for role in roles]}")
            add_new_user("Main", roblox_username)

            from config import STARTER_CHANNELS, WELCOME_CHANNEL
            for channel_id in STARTER_CHANNELS:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    ping_msg = await channel.send(f"{member.mention}")
                    await ping_msg.delete(delay=0.2)

            welcome_channel = ctx.guild.get_channel(WELCOME_CHANNEL)
            if welcome_channel:
                await welcome_channel.send(f"Attention Shock Troopers! Welcome our new shiny {member.mention} to the company!")

            embed = make_embed(
                type="Success",
                title="User Setup Complete",
                description=(
                    f"**Username:** {roblox_username}\n"
                    f"**Roles Assigned:** {', '.join([role.name for role in roles])}\n"
                    f"**Setup by:** {ctx.author.name}"
                )
            )
            success_msg = await ctx.send(embed=embed)

            await log_command(
                bot=self.bot,
                command_name="setupuser",
                user=ctx.author,
                guild=ctx.guild,
                Parameters=f"Roblox Username: {roblox_username} | Roles: {', '.join([role.name for role in roles])}",
                Roblox_Username=roblox_username,
                Roles_Assigned=[role.name for role in roles],
            )

            await success_msg.delete()
            await ctx.message.delete()
            await replied_message.delete()
            print("Deleted command, bot's success message, and replied messages")

        except Exception as e:
            embed = make_embed(
                type="Error",
                title="Setup Failed",
                description=f"Error: {str(e)}\n\n**Required format example:**\n"
                            "```Roblox Username: ExampleUser```"
            )
            error_msg = await ctx.send(embed=embed)
            self.bot.loop.create_task(delete_messages_after_delay(self.bot, [ctx.message, error_msg], 5))
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