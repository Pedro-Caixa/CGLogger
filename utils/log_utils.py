import discord
from discord.ext import commands
from config import LOG_CHANNELS
async def log_command(bot: commands.Bot, command_name: str, user: discord.User, guild: discord.Guild, **kwargs):
    """
    Log command usage to all specified log channels using an embed.

    :param bot: The bot instance.
    :param command_name: The name of the command that was executed.
    :param user: The user who executed the command.
    :param guild: The guild where the command was executed.
    :param kwargs: Additional information to include in the log (e.g., parameters, success/failure).
    """
    embed = discord.Embed(
        title="Command Executed",
        description=f"**Command:** `{command_name}`",
        color=discord.Color.blue(),
    )

    embed.set_author(
        name=f"{user.name} ({user.id})",
        icon_url=user.display_avatar.url,
    )

    embed.add_field(name="Guild", value=f"{guild.name} (`{guild.id}`)", inline=False)

    for key, value in kwargs.items():
        embed.add_field(name=key.capitalize(), value=value, inline=False)

    embed.timestamp = discord.utils.utcnow()

    for channel_id in LOG_CHANNELS:
        channel = bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)