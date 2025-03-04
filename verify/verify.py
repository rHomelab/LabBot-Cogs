"""discord red-bot verify"""

import logging
from datetime import timedelta
from typing import Optional

import discord
import Levenshtein as lev
from redbot.core import Config, checks, commands
from redbot.core.utils.mod import is_mod_or_superior

logger = logging.getLogger("red.rhomelab.verify")


class VerifyCog(commands.Cog):
    """Verify Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "blocks": [],
            "channel": None,
            "count": 0,
            "fuzziness": 0,
            "logchannel": None,
            "message": "I agree",
            "mintime": 60,
            "role": None,
            "tooquick": "That was quick, {user}! Are you sure you've read the rules?",
            "welcomechannel": None,
            "welcomemsg": "",
            "wrongmsg": "",
            "welcome_ignore_roles": [],
        }

        self.config.register_guild(**default_guild_settings, force_registration=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):  # noqa: PLR0911
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        guild = message.guild
        channel = await self.config.guild(guild).channel()
        if message.channel.id != channel:
            # User did not post verify message in channel
            return

        author = message.author
        if not isinstance(author, discord.Member) or author.bot or author.joined_at is None:
            # User is a bot. Ignore.
            return

        if await is_mod_or_superior(self.bot, message):
            # User is a mod/admin
            return

        if not guild.me.guild_permissions.manage_roles:
            # We don't have permission to manage roles
            return

        mintime = await self.config.guild(guild).mintime()
        minjoin = discord.utils.utcnow() - timedelta(seconds=mintime)
        if author.joined_at > minjoin:
            # User tried to verify too fast
            tooquick = await self.config.guild(guild).tooquick()
            tooquick = tooquick.format(user=author.mention)

            await self._log_verify_message(guild, author, None, failmessage="User tried too quickly")

            await message.channel.send(tooquick)
            return

        verify_msg = await self.config.guild(guild).message()
        verify_msg = verify_msg.lower()
        fuzziness_setting = await self.config.guild(guild).fuzziness()
        fuzziness_check = lev.distance(verify_msg, message.content.lower()) / len(verify_msg) * 100 > fuzziness_setting
        if message.content.lower() != verify_msg and fuzziness_check:
            # User did not post the perfect message.
            wrongmsg = await self.config.guild(guild).wrongmsg()

            await self._log_verify_message(guild, author, None, failmessage="User wrote wrong message")

            if not wrongmsg:
                # wrongmsg has not been configured
                return

            wrongmsg = wrongmsg.format(user=author.mention)
            await message.channel.send(wrongmsg)
            return

        if await self._verify_user(guild, author):
            await self._log_verify_message(guild, author, None)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Verification event"""
        if before.bot:
            # Member is a bot
            return

        guild = before.guild
        verify_role = await self.config.guild(guild).role()
        welcome_ignore_roles = await self.config.guild(guild).welcome_ignore_roles()

        if not verify_role:
            # Verify role is not set for this guild
            return

        if before.roles == after.roles:
            # Roles haven't changed
            return

        if verify_role in [role.id for role in before.roles] or verify_role not in [role.id for role in after.roles]:
            # Member already verified or not verified yet
            return

        for role in welcome_ignore_roles:
            if role in [role.id for role in before.roles]:
                # Member was in timeout previously; not newly verified.
                return

        count = await self.config.guild(guild).count()
        count += 1
        await self.config.guild(guild).count.set(count)

        welcomemsg = await self.config.guild(guild).welcomemsg()
        welcomechannel = await self.config.guild(guild).welcomechannel()
        if welcomechannel:
            welcomemsg = welcomemsg.format(user=after.mention)
            if channel := self._is_valid_channel(guild.get_channel(welcomechannel)):
                await channel.send(welcomemsg)
            else:
                logger.warning(f"Failed to get welcome channel {welcomechannel}, in guild {guild}")

    # Command groups

    @commands.group(name="verify")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def _verify(self, ctx: commands.Context):
        pass

    # Commands

    @_verify.command("message")
    async def verify_message(self, ctx: commands.GuildContext, *, message: str):
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
        ctx: commands.GuildContext,
        channel: Optional[discord.TextChannel] = None,
        *,
        message: Optional[str] = None,
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
    async def verify_tooquick(self, ctx: commands.GuildContext, message: str):
        """The message to reply if they're too quick at verifying

        Example:
        - `[p]verify tooquick "<message>"`
        - `[p]verify tooquick "Calm down. Wait a bit, yea?"`
        """
        await self.config.guild(ctx.guild).tooquick.set(message)
        await ctx.send("Too quick reply message set.")

    @_verify.command("wrongmsg")
    async def verify_wrongmsg(self, ctx: commands.GuildContext, message: str):
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
    async def verify_role(self, ctx: commands.GuildContext, role: discord.Role):
        """Sets the verified role

        Example:
        - `[p]verify role "<role id>"`
        """
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.send(f"Verify role set to `{role.name}`")

    @_verify.command("mintime")
    async def verify_mintime(self, ctx: commands.GuildContext, mintime: int):
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
    async def verify_channel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Sets the channel to post the message in to get the role

        Example:
        - `[p]verify channel <channel>`
        - `[p]verify channel #welcome`
        """
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Verify message channel set to `{channel.name}`")

    @_verify.command("logchannel")
    async def verify_logchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Sets the channel to post the verification logs

        Example:
        - `[p]verify logchannel <channel>`
        - `[p]verify logchannel #admin-log`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Verify log message channel set to `{channel.name}`")

    @_verify.command("block")
    async def verify_block(self, ctx: commands.GuildContext, user: discord.Member):
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
    async def verify_unlock(self, ctx: commands.GuildContext, user: discord.Member):
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

    @_verify.command("fuzziness")
    async def _set_fuzziness(self, ctx: commands.GuildContext, fuzziness: int):
        """Sets the threshold for fuzzy matching of the verify message
        This command takes the `fuzziness` arg as a number from 0 - 100, with 0 requiring an exact match
        Verify checks are case insensitive regardless of fuzziness level

        Example:
        - `[p]verify fuzziness <fuzziness>`
        - `[p]verify fuzziness 50`
        """
        if fuzziness not in range(101):
            await ctx.send("Number must be in range 0 - 100")
            return

        await self.config.guild(ctx.guild).fuzziness.set(fuzziness)
        await ctx.send(f"Fuzzy matching threshold for verification set to `{fuzziness}%`")

    @_verify.command("status")
    async def verify_status(self, ctx: commands.GuildContext):  # noqa: PLR0912, PLR0915
        """Status of the cog.
        The bot will display how many users it has verified
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]verify status`
        """
        blocked_users = await self.config.guild(ctx.guild).blocks()
        channel_id = await self.config.guild(ctx.guild).channel()
        count = await self.config.guild(ctx.guild).count()
        fuzziness = await self.config.guild(ctx.guild).fuzziness()
        log_id = await self.config.guild(ctx.guild).logchannel()

        message = await self.config.guild(ctx.guild).message()
        message = message.replace("`", "") if message else message

        mintime = await self.config.guild(ctx.guild).mintime()
        role_id = await self.config.guild(ctx.guild).role()
        welcome_ignore_roles = await self.config.guild(ctx.guild).welcome_ignore_roles()

        tooquick = await self.config.guild(ctx.guild).tooquick()
        tooquick = tooquick.replace("`", "") if tooquick else tooquick

        welcomechannel = await self.config.guild(ctx.guild).welcomechannel()

        welcomemsg = await self.config.guild(ctx.guild).welcomemsg()
        welcomemsg = welcomemsg.replace("`", "") if welcomemsg else welcomemsg

        wrongmsg = await self.config.guild(ctx.guild).wrongmsg()
        wrongmsg = wrongmsg.replace("`", "") if wrongmsg else wrongmsg

        embed = discord.Embed(colour=(await ctx.embed_colour()))
        embed.add_field(name="Verified", value=f"{count} users")

        if role_id:
            if role := ctx.guild.get_role(role_id):
                embed.add_field(name="Role", value=role.mention)
            else:
                embed.add_field(name="ERROR: role with ID not found", value=role_id)
        else:
            embed.add_field(name="ERROR: role ID missing", value="")

        if channel_id:
            if channel := self._is_valid_channel(ctx.guild.get_channel(channel_id)):
                embed.add_field(name="Channel", value=channel.mention)
            else:
                embed.add_field(name="ERROR: Channel with ID not found", value=channel_id)
        else:
            embed.add_field(name="ERROR: Channel ID missing", value="")

        if log_id:
            if log_channel := self._is_valid_channel(ctx.guild.get_channel(log_id)):
                embed.add_field(name="Log", value=log_channel.mention)
            else:
                embed.add_field(name="ERROR: Log channel with ID not found", value=log_id)
        else:
            embed.add_field(name="ERROR: Log channel ID missing", value="")
        embed.add_field(name="Min Time", value=f"{mintime} secs")
        embed.add_field(name="Message", value=f"`{message}`")
        embed.add_field(name="Too Quick Msg", value=f"`{tooquick}`")

        if wrongmsg:
            embed.add_field(name="Wrong Msg", value=f"`{wrongmsg}`")

        if welcomechannel and (welcome_channel := self._is_valid_channel(ctx.guild.get_channel(welcomechannel))):
            embed.add_field(name="Welcome Channel", value=welcome_channel.mention)

        if welcomemsg:
            embed.add_field(name="Welcome Msg", value=f"`{welcomemsg}`")

        if welcome_ignore_roles:
            welcome_ignore = ""
            for role in welcome_ignore_roles:
                if role and (discord_role := ctx.guild.get_role(role)):
                    welcome_ignore += f"{discord_role.name}, "
                else:
                    await ctx.send(f"ERROR: Welcome ignore role not found: {role}")
            embed.add_field(name="Welcome Ignore Roles", value=welcome_ignore.rstrip(", "))

        embed.add_field(name="# Users Blocked", value=f"`{len(blocked_users)}`")
        embed.add_field(name="Fuzzy Matching Threshold", value=f"`{fuzziness}%`")

        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send a verify status.")

    @commands.command(name="v")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def verify_manual(self, ctx: commands.GuildContext, user: discord.Member, *, reason: Optional[str] = None):
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

    # Helper functions

    def _is_valid_channel(self, channel: "discord.guild.GuildChannel | None"):
        if channel is not None and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            return channel
        return False

    async def _log_verify_message(
        self,
        guild: discord.Guild,
        user: discord.Member,
        verifier: Optional[discord.Member] = None,
        **kwargs,
    ):
        """Private method for logging a message to the logchannel"""
        failmessage = kwargs.get("failmessage", None)
        message = failmessage or "User Verified"

        log_id = await self.config.guild(guild).logchannel()
        if log_id:
            log = guild.get_channel(log_id)
            data = discord.Embed(color=discord.Color.orange())
            data.set_author(name=f"{message} - {user}", icon_url=user.display_avatar.url)
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
                if channel := self._is_valid_channel(log):
                    try:
                        await channel.send(embed=data)
                    except discord.Forbidden:
                        await channel.send(f"**{message}** - {user.id} - {user}")

    async def _verify_user(self, guild: discord.Guild, member: discord.Member):
        """Private method for verifying a user"""
        async with self.config.guild(guild).blocks() as blocked_users:
            if member.id in blocked_users:
                return False

        log_id = await self.config.guild(guild).logchannel()
        role_id = await self.config.guild(guild).role()
        if role := guild.get_role(role_id):
            await member.add_roles(role)
            return True
        elif log_id and (log_channel := self._is_valid_channel(guild.get_channel(log_id))):
            await log_channel.send(f"**User Not Verified Due To Error** - missing verified role. role_id: {role_id}")
        else:
            logger.warning(f"Failed to get log channel {log_id}, in guild {guild}")
        return False

    @_verify.group(name="welcomeignore")
    async def welcome_ignore(self, ctx: commands.Context):
        """Add, remove, or list roles from the welcomeignore roles list

        Users who transition from holding any one or more of these roles to holding the verified role will not be welcomed.

        For example:
        - Role `foo` is a role in the welcomeignore roles list.
        - Role `bar` is the verified role.

        Scenario A: User `abc` has role `foo`, then removes it and adds role `bar`. They will _not_ be welcomed.
        Scenario B: User `def` has role `baz`, then removes it and adds role `bar`. They _will_ be welcomed.

        This allows for easy usage with Homelab's [timeout cog](https://github.com/rHomelab/LabBot-Cogs#timeout).
        """
        if not ctx.invoked_subcommand:
            pass

    @welcome_ignore.command(name="add")
    async def welcome_ignore_add(self, ctx: commands.GuildContext, role: discord.Role):
        """Add a role to the welcomeignore roles list

        Example:
        - `[p]verify welcomeignore add myrole`
        """

        async with self.config.guild(ctx.guild).welcome_ignore_roles() as roles:
            roles.append(role.id)
        await ctx.tick()

    @welcome_ignore.command(name="remove")
    async def welcome_ignore_remove(self, ctx: commands.GuildContext, role: discord.Role):
        """Remove a role to the welcomeignore roles list

        Example:
        - `[p]verify welcomeignore remove myrole`
        """

        async with self.config.guild(ctx.guild).welcome_ignore_roles() as roles:
            roles.remove(role.id)
        await ctx.tick()

    @welcome_ignore.command(name="list")
    async def welcome_ignore_list(self, ctx: commands.GuildContext):
        """List roles in the welcomeignore roles list

        Example:
        - `[p]verify welcomeignore list`
        """

        roles_config = await self.config.guild(ctx.guild).welcome_ignore_roles()

        if roles_config:
            embed = discord.Embed(color=(await ctx.embed_colour()))

            for role in roles_config:
                if discord_role := ctx.guild.get_role(role):
                    embed.add_field(name="Role Name", value=discord_role.name, inline=True)
                    embed.add_field(name="Role ID", value=discord_role.id, inline=True)
                    embed.add_field(name="\u200b", value="\u200b", inline=True)  # ZWJ field
                else:
                    embed.add_field(name="ERROR: Role ID missing", value=role, inline=True)
                    embed.add_field(name="\u200b", value="\u200b", inline=True)  # ZWJ field
            await ctx.send(embed=embed)

        else:
            await ctx.send("No roles have been added to welcomeignore.")
