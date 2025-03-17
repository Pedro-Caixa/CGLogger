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
from dotenv import load_dotenv

EVENT_LOG_WEBHOOK = os.getenv('EVENT_LOG_WEBHOOK')

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

    async def delete_messages_after_delay(self, messages, delay):
        await asyncio.sleep(delay)
        for msg in messages:
            if msg is not None:
                try:
                    await msg.delete()
                except:
                    pass

    @commands.hybrid_command(name="logevent", description="Log an event from formatted message")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_officer()
    @requires_reply()
    async def logevent(self, ctx: commands.Context):
        replied_message = None
        success_msg = None
        try:
            # Fetch referenced message and validate
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            content = replied_message.content
            
            if not replied_message.attachments:
                raise commands.CommandError("Proof image is required - attach at least one image to the message")
            
            # Validate required fields
            required_fields = ["Event:", "Hosted by:", "Attendees:", "Proof:", "EP for event:"]
            missing_fields = [field for field in required_fields if field not in content]
            if missing_fields:
                raise commands.CommandError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Extract and validate EP value
            ep_match = re.search(r"EP for event:\s*(\d+)", content)
            if not ep_match:
                raise commands.CommandError("Invalid EP value format in message")
            ep_value = int(ep_match.group(1))
            if ep_value > 5:
                raise commands.CommandError("EP value cannot exceed 5. Please correct and try again.")

            # Process host information
            host_match = re.search(r"Hosted by:\s*(.+)", content)
            if not host_match:
                raise commands.CommandError("Missing or invalid host information")
            
            host_content = host_match.group(1)
            host_mention = re.search(r"<@!?(\d+)>", host_content)
            
            if host_mention:
                user_id = int(host_mention.group(1))
                member = await ctx.guild.fetch_member(user_id)
                nick_or_name = member.nick or member.name
                nick_parts = [part.strip() for part in nick_or_name.split("|")]
                host_name = nick_parts[1] if len(nick_parts) > 1 else nick_or_name
            else:
                host_parts = [p.strip() for p in host_content.split("|")]
                host_name = host_parts[1] if len(host_parts) > 1 else host_content

            # Process attendees
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
                attendee_nickname = member.nick or member.name
                nickname_parts = [part.strip() for part in attendee_nickname.split("|")]
                attendee_name = nickname_parts[1] if len(nickname_parts) > 1 else attendee_nickname
                raw_attendees.append(attendee_name)
            
            # Format attendee list
            attendee_lines = [f"• {username}" for username in raw_attendees]
            attendee_list = "\n".join(attendee_lines[:10])
            if len(raw_attendees) > 10:
                attendee_list += f"\n• ...and {len(raw_attendees)-10} more"

            # Generate unique event ID
            event_id = str(uuid.uuid4())

            # Send success embed
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

            # Send to archive webhook
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
                archive_embed.set_footer(text=f"Event ID: {event_id}", icon_url = "https://cdn.discordapp.com/emojis/1155991227032936448.webp?size=128")
                
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
            
            messages_to_delete = [ctx.message]
            self.bot.loop.create_task(self.delete_messages_after_delay(messages_to_delete, 5))
            return

        messages_to_delete = [ctx.message, replied_message, success_msg]
        self.bot.loop.create_task(self.delete_messages_after_delay(messages_to_delete, 5))

async def setup(bot):
    await bot.add_cog(Officers(bot))