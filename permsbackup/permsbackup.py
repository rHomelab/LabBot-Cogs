import discord
from redbot.core import Config, checks, commands


class PermsBackupCog(commands.Cog):
    """Permissions related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1651813192131121163157)

    @commands.group("perms")
    async def _perms(self, ctx: commands.Context):
        """Backup and duplicate channel permissions"""
        pass

    @commands.guild_only()
    @checks.mod()
    @_perms.command("backup")
    async def _perms_backup(self, ctx, channel: discord.TextChannel = None):
        """Backup the permissions for a channel"""
        if not channel:
            channel = ctx.channel

        async with self.config.guild(ctx.guild).channels() as channels:
            channels[channel.id] = {key.id: value for key, value in iter(channel.overwrites)}

        await ctx.send(f"Permissions stored for {channel.mention}")

    @commands.guild_only()
    @checks.mod()
    @_perms.command("backup")
    async def _perms_backup(self, ctx, channel: discord.TextChannel = None):
        """Backup the permissions for a channel"""
