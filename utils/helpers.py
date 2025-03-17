import discord
from utils.embed_utils import make_embed

def format_username(member: discord.Member) -> str:
    """Extract formatted username from member's nickname or name."""
    nick_or_name = member.nick or member.name
    nick_parts = [part.strip() for part in nick_or_name.split("|")]
    return nick_parts[1] if len(nick_parts) > 1 else nick_or_name

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