"""discord red-bot feed"""

import random

import discord
from redbot.core import app_commands, commands

food = (
    "🍇",
    "🍈",
    "🍉",
    "🍊",
    "🍋",
    "🍌",
    "🍍",
    "🥭",
    "🍎",
    "🍏",
    "🍐",
    "🍑",
    "🍒",
    "🍓",
    "🥝",
    "🍅",
    "🥥",
    "🥑",
    "🍆",
    "🥔",
    "🥕",
    "🌽",
    "🌶️",
    "🥒",
    "🥬",
    "🥦",
    "🧄",
    "🧅",
    "🍄",
    "🥜",
    "🌰",
    "🍞",
    "🥐",
    "🥖",
    "🥨",
    "🥯",
    "🥞",
    "🧇",
    "🧀",
    "🍖",
    "🍗",
    "🥩",
    "🥓",
    "🍔",
    "🍟",
    "🍕",
    "🌭",
    "🥪",
    "🌮",
    "🌯",
    "🥙",
    "🧆",
    "🥚",
    "🍳",
    "🥘",
    "🍲",
    "🥣",
    "🥗",
    "🍿",
    "🧈",
    "🧂",
    "🥫",
    "🍱",
    "🍘",
    "🍙",
    "🍚",
    "🍛",
    "🍜",
    "🍝",
    "🍠",
    "🍢",
    "🍣",
    "🍤",
    "🍥",
    "🥮",
    "🍡",
    "🥟",
    "🥠",
    "🥡",
    "🦪",
    "🍦",
    "🍧",
    "🍨",
    "🍩",
    "🍪",
    "🎂",
    "🍰",
    "🧁",
    "🥧",
    "🍫",
    "🍬",
    "🍭",
    "🍮",
    "🍯",
    "🍼",
    "🥛",
    "☕",
    "🍵",
    "🍶",
    "🍾",
    "🍷",
    "🍸",
    "🍹",
    "🍺",
    "🍻",
    "🥂",
    "🥃",
    "🥤",
    "🧃",
    "🧉",
    "🧊",
)

allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False)


def get_fed(mention: str) -> str:
    return f"Forces {random.choice(food)} down {mention}'s throat"


@app_commands.context_menu(name="Feed user")
async def on_user(interaction: discord.Interaction, member: discord.User):
    """Feed user from user context"""
    await interaction.response.send_message(get_fed(member.mention), allowed_mentions=allowed_mentions)


@app_commands.context_menu(name="Feed user")
async def on_message(interaction: discord.Interaction, message: discord.Message):
    """Feed user from message context"""
    await interaction.response.send_message(get_fed(message.author.mention), allowed_mentions=allowed_mentions)


class FeedCog(commands.Cog):
    """Feed Cog"""

    @commands.command(name="feed")
    async def feed(self, ctx, member: discord.Member):
        """Feed your friends
        Example:
        - `[p]feed <member>`
        """
        await ctx.send(get_fed(member.mention), allowed_mentions=allowed_mentions)
