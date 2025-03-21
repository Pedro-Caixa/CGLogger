import discord
from discord.ext import commands
import re
from config import ACTIVITY_CHANNEL, EVENT_LOG_CHANNELS
from utils.embed_utils import make_embed
import asyncio

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            embed = make_embed(
                type="Information",
                title="Welcome to Coruscant Guard",
                description=(
                    f"Greetings {member.mention}, congratulations on graduating from the academy\n\n"
                    "We're happy to see you here and hope you can have a great career in this division\n"
                    "Before you start, here are some tips:\n\n"
                    "- Read the rules in https://discord.com/channels/1269671417192910860/1269676696638849114.\n"
                    "- Read all the documents before deploying in-game https://discord.com/channels/1269671417192910860/1324764708108238868.\n"
                    "- Stay up to date with the CG announcements https://discord.com/channels/1269671417192910860/1269671419076284463\n\n"
                    "MANDATORY: Change your server username to: ```[ST] | Username | YOUR TIMEZONE```"
                    "If you have any questions, feel free to ask in the Q&A channel https://discord.com/channels/1269671417192910860/1345502070593028178"
                ),
                icon_url=self.bot.user.display_avatar.url
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            print(f"Não foi possível enviar uma mensagem direta para {member.name}")

        channel = discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            await channel.send(f"Welcome, {member.mention}!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith("-"):
            return

        if message.channel.id in [ACTIVITY_CHANNEL] + EVENT_LOG_CHANNELS:
            if message.channel.id == ACTIVITY_CHANNEL:
                required_fields = ["Username:", "Time Started:", "Time Ended:", "Time logged:", "Total time logged:", "Proof:"]
                if any(f not in message.content for f in required_fields) or len(message.attachments) < 2:
                    warning_msg = await message.channel.send(
                        f"{message.author.mention}, the format of your message is incorrect. Please use the following format:\n"
                        "```Username: @User\n"
                        "Time Started: 6:17pm EST\n"
                        "Time Ended: 7:42pm EST\n"
                        "Time logged: 85\n"
                        "Total time logged: 85\n"
                        "Proof: attached-image1.jpg, attached-image2.jpg```"
                    )
                    await asyncio.sleep(20)
                    await message.delete()
                    await warning_msg.delete()
            else:
                is_company_event = any(
                    kw in message.channel.name for kw in ["hound-event-logs", "riot-event-logs", "shock-event-logs"]
                )

                point_type = "CEP" if is_company_event else "EP"
                ep_field = f"{point_type} for event:"
                required_fields = ["Event:", "Hosted by:", "Attendees:", "Proof:", ep_field]

                if any(f not in message.content for f in required_fields):
                    warning_msg = await message.channel.send(
                        f"{message.author.mention}, the format of your message is incorrect. Please use the following format:\n"
                        "```Event: Weekly Meetup\n"
                        "Hosted by: @[XO] | Caxseii | BRT\n"
                        "Supervisor: @[XO] | SupervisorName\n"
                        "Co-host: @[XO] | CoHostName\n"
                        "Attendees: @[XO] | Caxseii | BRT\n"
                        "Notes: Regular weekly meeting\n"
                        "Proof: attached-image.jpg\n"
                        f"{point_type} for event: 2\n"
                        "Extra points: @Mention (2)\n"
                        "Ping: @EventManager```"
                    )
                    await asyncio.sleep(20)
                    await message.delete()
                    await warning_msg.delete()

async def setup(bot):
    await bot.add_cog(Events(bot))