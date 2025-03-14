import discord
from datetime import datetime

def make_embed(
    type: str, 
    title: str,  # Customizable title
    description: str = None, 
    fields: list[tuple[str, str, bool]] = None, 
    ) -> discord.Embed:
    """
    Create a customizable embed with a specific type, title, and optional fields.

    :param type: The type of embed (Success, Error, Warn, Information, Default).
    :param title: The title of the embed.
    :param description: The description of the embed.
    :param fields: A list of tuples (name, value, inline) to add fields to the embed.
    :param footer: The footer text for the embed.
    :return: A discord.Embed object.
    """
    colors = {
        "Success": discord.Color.green(),
        "Error": discord.Color.red(),
        "Warn": discord.Color.gold(),
        "Information": discord.Color.blue(),
        "Default": discord.Color.blurple(),
    }

    embed = discord.Embed(
        title=title,
        description=description,
        color=colors.get(type, discord.Color.blurple()), 
    )

    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

    embed.set_footer(text=f"CG Systems | {title}") 
    embed.timestamp = datetime.now()
    return embed