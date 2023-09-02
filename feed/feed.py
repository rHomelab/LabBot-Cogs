"""discord red-bot feed"""
import random

import discord
from redbot.core import commands, app_commands

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


@app_commands.context_menu(name="Feed user")
async def on_user(interaction: discord.Interaction, member: discord.User):
    """Feed user from user context"""
    await do_feed(interaction, member.mention)


@app_commands.context_menu(name="Feed user")
async def on_message(interaction: discord.Interaction, message: discord.Message):
    """Feed user from message context"""
    await do_feed(interaction, message.author.mention)


async def do_feed(interaction: discord.Interaction, mention: str):
    feed_text = f"Forces {random.choice(food)} down {mention}'s throat"
    allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False)
    await interaction.response.send_message(feed_text, allowed_mentions=allowed_mentions)


class FeedCog(commands.Cog):
    """Feed Cog"""

    @commands.command(name="feed")
    async def feed(self, ctx):
        """Feed your friends"""
        await ctx.send(
            "Feed can now be used from the context menu of any user or message.\nThis command is no longer functional."
        )
