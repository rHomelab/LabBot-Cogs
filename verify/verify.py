"""discord red-bot verify"""
import discord
from redbot.core import commands, checks, Config


class VerifyCog(commands.Cog):
    """Verify Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "verify_message": "I agree",
            "verify_count": 0,
            "verify_role": None,
            "verify_channel": None,
            "verify_mintime": 60
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            # User is a bot. Ignore.
            return

        # TODO Check for verify message#

    @commands.group(name="verify")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _verify(self, ctx: commands.Context):
        pass

    @_verify.command("message")
    async def verify_message(self, ctx: commands.Context, message: str):
        """Sets the new verification message

        Example:
        - `[p]verify message "<message>"`
        - `[p]verify message "I agree"`
        """
        await self.settings.guild(ctx.guild).verify_message.set(message)
        await ctx.send("Verify message set.")

    @_verify.command("role")
    async def verify_role(self, ctx: commands.Context, role: discord.Role):
        """Sets the verified role

        Example:
        - `[p]verify role "<role id>"`
        """
        await self.settings.guild(ctx.guild).verify_role.set(role.id)
        await ctx.send(f"Verify role set to `{role.name}`")

    @_verify.command("mintime")
    async def verify_mintime(self, ctx: commands.Context, mintime: int):
        """
        Sets the minimum time a user must be in the discord server
        to be verified

        Example:
        - `[p]verify mintime <seconds>`
        - `[p]verify mintime 60`
        """
        if mintime < 0:
            # Not a valid value
            await ctx.send(f"Verify minimum time was below 0 seconds")
            return

        await self.settings.guild(ctx.guild).verify_mintime.set(mintime)
        await ctx.send(f"Verify minimum time set to {mintime} seconds")

    @_verify.command("channel")
    async def verify_channel(self,
                             ctx: commands.Context,
                             channel: discord.TextChannel):
        """Sets the channel to post the message in to get the role

        Example:
        - `[p]verify channel <channel>`
        - `[p]verify channel #welcome`
        """
        await self.settings.guild(ctx.guild).verify_channel.set(channel.id)
        await ctx.send(f"Verify message channel set to `{channel.name}`")

    @_verify.command("status")
    async def verify_status(self, ctx: commands.Context):
        """Status of the bot.
        The bot will display how many users it has verified
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]verify status`
        """
        data = discord.Embed(colour=(await ctx.embed_colour()))

        count = await self.settings.guild(ctx.guild).verify_count()
        data.add_field(name="Verified", value=f"{count} users")

        role_id = await self.settings.guild(ctx.guild).verify_role()
        if role_id is not None:
            role = ctx.guild.get_role(role_id)
            data.add_field(name="Role", value=f"@{role.name}")

        channel_id = await self.settings.guild(ctx.guild).verify_channel()
        if channel_id is not None:
            channel = ctx.guild.get_channel(channel_id)

            data.add_field(name="Channel", value=f"#{channel.name}")

        mintime = await self.settings.guild(ctx.guild).verify_mintime()
        data.add_field(name="Min Time", value=f"{mintime} secs")

        message = await self.settings.guild(ctx.guild).verify_message()
        message = message.replace('`', '')
        data.add_field(name="Message", value=f"`{message}`")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " +
                           "send a purge status.")
