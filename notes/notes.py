"""discord red-bot notes"""
from redbot.core import commands, Config, checks


class NotesCog(commands.Cog):
    """Notes Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=127318281)

        default_guild_settings = {
            "notes": [],
            "warnings": []
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="notes")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _notes(self, ctx: commands.Context):
        pass
