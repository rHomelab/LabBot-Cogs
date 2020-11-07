"""discord red-bot nicknamer cog"""
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import escape
from string import ascii_letters, digits
import discord


class NicknamerCog(commands.Cog):
    """nicknamer Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1092901)

        default_guild_settings = {
            "nne": False
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Member updates their profile
        """
        if after.nick is None:
            # Nick has been reset
            return

        if not self._is_valid_nick(after.guild, after.nick):
            # New nickname is now not allowed
            if not self._is_valid_nick(after.guild, before.nick):
                # Old nickname is also not allowed
                await after.edit(nick=None)
            else:
                # Old nickname is allowed
                await after.edit(nick=before.nick)

    def _is_valid_nick(self, guild, nickname: str):
        """
        Checks if nickname is valid for a guild
        """
        if nickname is None:
            return True
        if nickname[0] in ascii_letters:
            # Nickname is not alphabetic
            return True
        if nickname[0] in digits:
            # Nickname is not numeric
            return True
        return False
