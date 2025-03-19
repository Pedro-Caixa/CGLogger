import discord
from discord.ext import commands
from utils.embed_utils import make_embed

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

async def setup(bot):
    await bot.add_cog(Events(bot))