"""discord red-bot verify"""
from datetime import datetime, timedelta

import discord
from redbot.core import Config, checks, commands


class VerifyCog(commands.Cog):
    """Verify Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "message": "I agree",
            "count": 0,
            "role": None,
            "channel": None,
            "mintime": 60,
            "tooquick": "That was quick, {user}! Are you sure you've read the rules?",
            "wrongmsg": "",
            "logchannel": None,
            "welcomechannel": None,
            "welcomemsg": None,
            "blocks": [],
        }

        self.config.register_guild(**default_guild_settings)

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
        channel = await self.config.guild(server).channel()
        if message.channel.id != channel:
            # User did not post verify message in channel
            return

        if not server.me.guild_permissions.manage_roles:
            # We don't have permission to manage roles
            return

        mintime = await self.config.guild(server).mintime()
        minjoin = datetime.utcnow() - timedelta(seconds=mintime)
        if author.joined_at > minjoin:
            # User tried to verify too fast
            tooquick = await self.config.guild(server).tooquick()
            tooquick = tooquick.replace("{user}", f"{author.mention}")

            await self._log_verify_message(server, author, None, failmessage="User tried too quickly")

            await message.channel.send(tooquick)
            return

        verify_msg = await self.config.guild(server).message()
        if message.content != verify_msg:
            # User did not post the perfect message.
            wrongmsg = await self.config.guild(server).wrongmsg()

            await self._log_verify_message(server, author, None, failmessage="User wrote wrong message")

            if not wrongmsg:
                return
            wrongmsg = wrongmsg.replace("{user}", f"{author.mention}")
            await message.channel.send(wrongmsg)
            return

        if await self._verify_user(server, author):
            await self._log_verify_message(server, author, None)

            role_id = await self.config.guild(server).role()
            role = server.get_role(role_id)
            await self._cleanup(message, role)

    async def _cleanup(self, verify: discord.Message, role: discord.Role):
        # Deletion logic for the purge of messages
        def _should_delete(message):
            return (
                # Delete messages by the verify-ee
                message.author == verify.author
                or
                # Delete messages if it might mention the verify-ee
                (
                    # The user must be in the mentions
                    verify.author in message.mentions
                    and
                    # The mentions have all been verified
                    len([u for u in message.mentions if role not in u.roles]) == 0
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
    async def verify_message(self, ctx: commands.Context, *, message: str):
        """Sets the new verification message

        Example:
        - `[p]verify message "<message>"`
        - `[p]verify message "I agree"`
        """
        await self.config.guild(ctx.guild).message.set(message)
        await ctx.send("Verify message set.")

    @_verify.command("welcome")
    async def verify_welcome(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        *,
        message: str = None,
    ):
        """Sets the welcome message

        Example:
        - `[p]verify welcome <channel> "<message>"`
        - `[p]verify welcome #general "Welcome {user}!"`
        - `[p]verify welcome` to reset
        """
        welcome_channel = None
        if channel:
            welcome_channel = channel.id
        await self.config.guild(ctx.guild).welcomechannel.set(welcome_channel)
        await self.config.guild(ctx.guild).welcomemsg.set(message)

        await ctx.send("Welcome message set.")

    @_verify.command("tooquick")
    async def verify_tooquick(self, ctx: commands.Context, message: str):
        """The message to reply if they're too quick at verifying

        Example:
        - `[p]verify tooquick "<message>"`
        - `[p]verify tooquick "Calm down. Wait a bit, yea?"`
        """
        await self.config.guild(ctx.guild).tooquick.set(message)
        await ctx.send("Too quick reply message set.")

    @_verify.command("wrongmsg")
    async def verify_wrongmsg(self, ctx: commands.Context, message: str):
        """The message to reply if they input the wrong verify message.
        Using `{user}` in the message will mention the user and allow
        the message to be deleted automatically once the user is verified.

        Example:
        - `[p]verify wrongmsg "<message>"`
        - `[p]verify wrongmsg "{user} Wrong verification message!"`

        If `<message>` is empty, no message will be posted.
        """
        await self.config.guild(ctx.guild).wrongmsg.set(message)
        await ctx.send("Wrong verify message reply message set.")

    @_verify.command("role")
    async def verify_role(self, ctx: commands.Context, role: discord.Role):
        """Sets the verified role

        Example:
        - `[p]verify role "<role id>"`
        """
        await self.config.guild(ctx.guild).role.set(role.id)
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
            await ctx.send("Verify minimum time was below 0 seconds")
            return

        await self.config.guild(ctx.guild).mintime.set(mintime)
        await ctx.send(f"Verify minimum time set to {mintime} seconds")

    @_verify.command("channel")
    async def verify_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the channel to post the message in to get the role

        Example:
        - `[p]verify channel <channel>`
        - `[p]verify channel #welcome`
        """
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Verify message channel set to `{channel.name}`")

    @_verify.command("logchannel")
    async def verify_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the channel to post the verification logs

        Example:
        - `[p]verify logchannel <channel>`
        - `[p]verify logchannel #admin-log`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Verify log message channel set to `{channel.name}`")

    @_verify.command("block")
    async def verify_block(self, ctx: commands.Context, user: discord.Member):
        """Blocks the user from verification

        Example:
        - `[p]verify block 126694389572435968`
        - `[p]verify block @Sneezey#2695`
        """
        async with self.config.guild(ctx.guild).blocks() as blocked_users:
            if user.id not in blocked_users:
                blocked_users.append(user.id)
                await ctx.send(f"{user.mention} has been blocked from verifying")
            else:
                await ctx.send(f"{user.mention} has already been blocked from verifying")

    @_verify.command("unblock")
    async def verify_unlock(self, ctx: commands.Context, user: discord.Member):
        """Unblocks the user from verification

        Example:
        - `[p]verify unblock 126694389572435968`
        - `[p]verify unblock @Sneezey#2695`
        """
        async with self.config.guild(ctx.guild).blocks() as blocked_users:
            if user.id in blocked_users:
                blocked_users.remove(user.id)
                await ctx.send(f"{user.mention} has been unblocked from verifying")
            else:
                await ctx.send(f"{user.mention} wasn't blocked from verifying")

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

        count = await self.config.guild(ctx.guild).count()
        data.add_field(name="Verified", value=f"{count} users")

        role_id = await self.config.guild(ctx.guild).role()
        if role_id:
            role = ctx.guild.get_role(role_id)
            data.add_field(name="Role", value=role.mention)

        channel_id = await self.config.guild(ctx.guild).channel()
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)

            data.add_field(name="Channel", value=channel.mention)

        log_id = await self.config.guild(ctx.guild).logchannel()
        if log_id:
            log = ctx.guild.get_channel(log_id)

            data.add_field(name="Log", value=log.mention)

        mintime = await self.config.guild(ctx.guild).mintime()
        data.add_field(name="Min Time", value=f"{mintime} secs")

        message = await self.config.guild(ctx.guild).message()
        message = message.replace("`", "")
        data.add_field(name="Message", value=f"`{message}`")

        tooquick = await self.config.guild(ctx.guild).tooquick()
        tooquick = tooquick.replace("`", "")
        data.add_field(name="Too Quick Msg", value=f"`{tooquick}`")

        wrongmsg = await self.config.guild(ctx.guild).wrongmsg()
        if wrongmsg:
            wrongmsg = wrongmsg.replace("`", "")
            data.add_field(name="Wrong Msg", value=f"`{wrongmsg}`")

        welcomechannel = await self.config.guild(ctx.guild).welcomechannel()
        if welcomechannel:
            welcome = ctx.guild.get_channel(welcomechannel)
            data.add_field(name="Welcome Channel", value=welcome.mention)

        welcomemsg = await self.config.guild(ctx.guild).welcomemsg()
        if welcomemsg:
            welcomemsg = welcomemsg.replace("`", "")
            data.add_field(name="Welcome Msg", value=f"`{welcomemsg}`")

        async with self.config.guild(ctx.guild).blocks() as blocked_users:
            blocked_count = len(blocked_users)
            data.add_field(name="# Users Blocked", value=f"`{blocked_count}`")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send a verify status.")

    @commands.command(name="v")
    @commands.guild_only()
    @checks.mod()
    async def verify_manual(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Manually verifies a user

        Example:
        - `[p]v <id> [zt]`
        - `[p]v <@User> [bypass]`
        - `[p]v <User#1234>`
        """
        if user.bot:
            # User is a bot
            return

        role_id = await self.config.guild(ctx.guild).role()
        role = ctx.guild.get_role(role_id)
        if role in user.roles:
            # Already verified
            return

        if await self._verify_user(ctx.guild, user):
            await self._log_verify_message(ctx.guild, user, ctx.author, reason=reason)

    async def _verify_user(self, server: discord.Guild, user: discord.Member):
        """Private method for verifying a user"""
        async with self.config.guild(server).blocks() as blocked_users:
            if user.id in blocked_users:
                return False

        role_id = await self.config.guild(server).role()
        role = server.get_role(role_id)
        await user.add_roles(role)

        count = await self.config.guild(server).count()
        count += 1
        await self.config.guild(server).count.set(count)

        welcomemsg = await self.config.guild(server).welcomemsg()
        welcomechannel = await self.config.guild(server).welcomechannel()
        if welcomechannel:
            welcomemsg = welcomemsg.replace("{user}", user.mention)
            await server.get_channel(welcomechannel).send(welcomemsg)

        return True

    async def _log_verify_message(
        self,
        server: discord.Guild,
        user: discord.Member,
        verifier: discord.Member,
        **kwargs,
    ):
        """Private method for logging a message to the logchannel"""
        failmessage = kwargs.get("failmessage", None)
        message = failmessage or "User Verified"

        log_id = await self.config.guild(server).logchannel()
        if log_id:
            log = server.get_channel(log_id)
            data = discord.Embed(colour=discord.Colour.orange())
            data.set_author(name=f"{message} - {user}", icon_url=user.avatar_url)
            data.add_field(name="User", value=user.mention)
            data.add_field(name="ID", value=user.id)
            if not failmessage:
                if not verifier:
                    data.add_field(name="Verifier", value="Auto")
                else:
                    data.add_field(name="Verifier", value=verifier.mention)
            reason = kwargs.get("reason", False)
            if reason:
                data.add_field(name="Reason", value=reason)
            if log:
                try:
                    await log.send(embed=data)
                except discord.Forbidden:
                    await log.send(f"**{message}** - {user.id} - {user}")
