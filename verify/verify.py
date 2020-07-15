"""discord red-bot verify"""
import discord
from datetime import timedelta, datetime
from redbot.core import commands, checks, Config


class VerifyCog(commands.Cog):
    """Verify Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "message": "I agree",
            "count": 0,
            "role": None,
            "channel": None,
            "mintime": 60,
            "tooquick": (
                "That was quick, {user}! Are you sure " +
                "you've read the rules?"
            ),
            "wrongmsg": "",
            "logchannel": None
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

        server = message.guild
        channel = await self.settings.guild(server).channel()
        if message.channel.id != channel:
            # User did not post verify message in channel
            return

        if not server.me.guild_permissions.manage_roles:
            # We don't have permission to manage roles
            return

        mintime = await self.settings.guild(server).mintime()
        minjoin = datetime.utcnow() - timedelta(seconds=mintime)
        if author.joined_at > minjoin:
            # User tried to verify too fast
            tooquick = await self.settings.guild(server).tooquick()
            tooquick = tooquick.replace("{user}", f"{author.mention}")
            await message.channel.send(tooquick)
            return

        verify_msg = await self.settings.guild(server).message()
        if message.content != verify_msg:
            # User did not post the perfect message.
            wrongmsg = await self.settings.guild(server).wrongmsg()
            if wrongmsg == "":
                return
            wrongmsg = wrongmsg.replace("{user}", f"{author.mention}")
            await message.channel.send(wrongmsg)
            return

        role_id = await self.settings.guild(server).role()
        role = server.get_role(role_id)
        await author.add_roles(role)

        log_id = await self.settings.guild(server).logchannel()
        if log_id is not None:
            log = server.get_channel(log_id)
            data = discord.Embed(color=discord.Color.orange())
            data.set_author(
                name=f"User Verified - {author}",
                icon_url=author.avatar_url
            )
            data.add_field(name="User", value=f"{author}")
            data.add_field(name="ID", value=f"{author.id}")
            data.add_field(name="Verifier", value="Auto")
            if log is not None:
                try:
                    await log.send(embed=data)
                except discord.Forbidden:
                    await log.send(
                        "**User Verified** - " +
                        f"{author.id} - {author}"
                    )

        count = await self.settings.guild(server).count()
        count += 1
        await self.settings.guild(server).count.set(count)

        await self._cleanup(message, role)

    async def _cleanup(self, verify: discord.Message, role: discord.Role):
        # Deletion logic for the purge of messages
        def _should_delete(m):
            return (
                # Delete messages by the verify-ee
                m.author == verify.author or
                # Delete messages if it might mention the verify-ee
                (
                    # The user must be in the mentions
                    verify.author in m.mentions and
                    # The mentions have all been verified
                    len([u for u in m.mentions if role not in u.roles]) == 0
                )
            )
        try:
            await verify.channel.purge(limit=100, check=_should_delete)
        except discord.errors.Forbidden:
            await verify.channel.send("I don't have permissions to cleanup!")

    @commands.group(name="verify")
    @commands.guild_only()
    @checks.mod()
    async def _verify(self, ctx: commands.Context):
        pass

    @_verify.command("message")
    async def verify_message(self, ctx: commands.Context, message: str):
        """Sets the new verification message

        Example:
        - `[p]verify message "<message>"`
        - `[p]verify message "I agree"`
        """
        await self.settings.guild(ctx.guild).message.set(message)
        await ctx.send("Verify message set.")

    @_verify.command("tooquick")
    async def verify_tooquick(self, ctx: commands.Context, message: str):
        """The message to reply if they're too quick at verifying

        Example:
        - `[p]verify tooquick "<message>"`
        - `[p]verify tooquick "Calm down. Wait a bit, yea?"`
        """
        await self.settings.guild(ctx.guild).tooquick.set(message)
        await ctx.send("Too quick reply message set.")

    @_verify.command("wrongmsg")
    async def verify_wrongmsg(self, ctx: commands.Context, message: str):
        """The message to reply if they input the wrong verify message

        Example:
        - `[p]verify wrongmsg "<message>"`
        - `[p]verify wrongmsg "Wrong verification message!"`

        If `<message>` is empty, no message will be posted.
        """
        await self.settings.guild(ctx.guild).wrongmsg.set(message)
        await ctx.send("Wrong verify message reply message set.")

    @_verify.command("role")
    async def verify_role(self, ctx: commands.Context, role: discord.Role):
        """Sets the verified role

        Example:
        - `[p]verify role "<role id>"`
        """
        await self.settings.guild(ctx.guild).role.set(role.id)
        await ctx.send(f"Verify role set to `{role.name}`")

    @_verify.command("mintime")
    async def verify_mintime(self, ctx: commands.Context, mintime: int):
        """
        Sets the minimum time a user must be in the discord server
        to be verified, using seconds as a unit.

        Example:
        - `[p]verify mintime <seconds>`
        - `[p]verify mintime 60`
        """
        if mintime < 0:
            # Not a valid value
            await ctx.send(f"Verify minimum time was below 0 seconds")
            return

        await self.settings.guild(ctx.guild).mintime.set(mintime)
        await ctx.send(f"Verify minimum time set to {mintime} seconds")

    @_verify.command("channel")
    async def verify_channel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
    ):
        """Sets the channel to post the message in to get the role

        Example:
        - `[p]verify channel <channel>`
        - `[p]verify channel #welcome`
        """
        await self.settings.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Verify message channel set to `{channel.name}`")

    @_verify.command("logchannel")
    async def verify_logchannel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
    ):
        """Sets the channel to post the verification logs

        Example:
        - `[p]verify logchannel <channel>`
        - `[p]verify logchannel #admin-log`
        """
        await self.settings.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Verify log message channel set to `{channel.name}`")

    @_verify.command("status")
    async def verify_status(self, ctx: commands.Context):
        """Status of the cog.
        The bot will display how many users it has verified
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]verify status`
        """
        data = discord.Embed(colour=(await ctx.embed_colour()))

        count = await self.settings.guild(ctx.guild).count()
        data.add_field(name="Verified", value=f"{count} users")

        role_id = await self.settings.guild(ctx.guild).role()
        if role_id is not None:
            role = ctx.guild.get_role(role_id)
            data.add_field(name="Role", value=f"@{role.name}")

        channel_id = await self.settings.guild(ctx.guild).channel()
        if channel_id is not None:
            channel = ctx.guild.get_channel(channel_id)

            data.add_field(name="Channel", value=f"#{channel.name}")

        log_id = await self.settings.guild(ctx.guild).logchannel()
        if log_id is not None:
            log = ctx.guild.get_channel(log_id)

            data.add_field(name="Log", value=f"#{log.name}")

        mintime = await self.settings.guild(ctx.guild).mintime()
        data.add_field(name="Min Time", value=f"{mintime} secs")

        message = await self.settings.guild(ctx.guild).message()
        message = message.replace('`', '')
        data.add_field(name="Message", value=f"`{message}`")

        tooquick = await self.settings.guild(ctx.guild).tooquick()
        tooquick = tooquick.replace('`', '')
        data.add_field(name="Too Quick Msg", value=f"`{tooquick}`")

        wrongmsg = await self.settings.guild(ctx.guild).wrongmsg()
        if wrongmsg != "":
            wrongmsg = wrongmsg.replace('`', '')
            data.add_field(name="Wrong Msg", value=f"`{wrongmsg}`")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send(
                "I need the `Embed links` permission to send a verify status."
            )
