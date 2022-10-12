import logging
from datetime import datetime as dt

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.mod import is_mod_or_superior as is_mod
from redbot.core.utils.predicates import ReactionPredicate

log = logging.getLogger("red.rhomelab.timeout")


class Timeout(commands.Cog):
    """Timeout a user"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=539343858187161140)
        default_guild = {
            "logchannel": None,
            "report": False,
            "timeoutrole": None,
            "timeout_channel": None
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(
            roles=[]
        )

        self.actor: str = None
        self.target: str = None

    # Helper functions

    async def member_data_cleanup(self, ctx: commands.Context):
        """Remove data stored for members who are no longer in the guild
        This helps avoid permanently storing role lists for members who left whilst in timeout.
        """

        member_data = await self.config.all_members(ctx.guild)

        for member in member_data:
            # If member not found in guild...
            if ctx.guild.get_member(member) is None:
                # Clear member data
                await self.config.member_from_ids(ctx.guild.id, member).clear()

    async def report_handler(self, ctx: commands.Context, user: discord.Member, action_info: dict):
        """Build and send embed reports"""

        # Retrieve log channel
        log_channel_config = await self.config.guild(ctx.guild).logchannel()
        log_channel = ctx.guild.get_channel(log_channel_config)

        # Build embed
        embed = discord.Embed(
            description=f"{user.mention} ({user.id})",
            color=(await ctx.embed_colour()),
            timestamp=dt.utcnow()
        )
        embed.add_field(
            name="Moderator",
            value=ctx.author.mention,
            inline=False
        )
        embed.add_field(
            name="Reason",
            value=action_info["reason"],
            inline=False
        )

        if user.display_avatar:
            embed.set_author(
                name=f"{user} {action_info['action']} timeout",
                icon_url=user.display_avatar.url)
        else:
            embed.set_author(
                name=f"{user} {action_info['action']} timeout"
            )

        # Send embed
        await log_channel.send(embed=embed)

    async def timeout_add(
            self, ctx: commands.Context,
            user: discord.Member,
            reason: str,
            timeout_role: discord.Role,
            timeout_roleset: list[discord.Role]):
        """Retrieve and save user's roles, then add user to timeout"""
        # Catch users already holding timeout role.
        # This could be caused by an error in this cog's logic or,
        # more likely, someone manually adding the user to the role.
        if timeout_role in user.roles:
            await ctx.send(
                "Something went wrong! Is the user already in timeout? Please check the console for more information."
            )
            log.warning(
                f"Something went wrong while trying to add user {self.target} to timeout.\n" +
                f"Current roles: {user.roles}\n" +
                f"Attempted new roles: {timeout_roleset}"
            )
            return

        # Store the user's current roles
        user_roles = [r.id for r in user.roles]

        await self.config.member(user).roles.set(user_roles)

        # Replace all of a user's roles with timeout roleset
        try:
            await user.edit(roles=timeout_roleset)
            log.info("User %s added to timeout by %s.", self.target, self.actor)
        except AttributeError:
            await ctx.send(f"Please set the timeout role with `{ctx.clean_prefix}timeoutset role`.")
            return
        except discord.Forbidden as error:
            await ctx.send("Whoops, looks like I don't have permission to do that.")
            log.exception(
                f"Something went wrong while trying to add user {self.target} to timeout.\n" +
                f"Current roles: {user.roles}\n" +
                f"Attempted new roles: {timeout_roleset}", exc_info=error
            )
        except discord.HTTPException as error:
            await ctx.send("Something went wrong! Please check the console for more information.")
            log.exception(
                f"Something went wrong while trying to add user {self.target} to timeout.\n" +
                f"Current roles: {user.roles}\n" +
                f"Attempted new roles: {timeout_roleset}", exc_info=error
            )
        else:
            await ctx.tick()

            # Send report to channel
            if await self.config.guild(ctx.guild).report():
                action_info = {
                    "reason": reason,
                    "action": "added to"
                }
                await self.report_handler(ctx, user, action_info)

    async def timeout_remove(self, ctx: commands.Context, user: discord.Member, reason: str):
        """Remove user from timeout"""

        # Retrieve timeout channel
        timeout_channel_config = await self.config.guild(ctx.guild).timeout_channel()
        timeout_channel = ctx.guild.get_channel(timeout_channel_config)

        # Fetch and define user's previous roles.
        user_roles = []
        for role in await self.config.member(user).roles():
            user_roles.append(ctx.guild.get_role(role))

        # Replace user's roles with their previous roles.
        try:
            await user.edit(roles=user_roles)
            log.info("User %s removed from timeout by %s.", self.target, self.actor)
        except discord.Forbidden as error:
            await ctx.send("Whoops, looks like I don't have permission to do that.")
            log.exception(
                f"Something went wrong while trying to remove user {self.target} from timeout.\n" +
                f"Current roles: {user.roles}\n" +
                f"Attempted new roles: {user_roles}", exc_info=error
            )
        except discord.HTTPException as error:
            await ctx.send("Something went wrong! Please check the console for more information.")
            log.exception(
                f"Something went wrong while trying to remove user {self.target} from timeout.\n" +
                f"Current roles: {user.roles}\n" +
                f"Attempted new roles: {user_roles}", exc_info=error
            )
        else:
            await ctx.tick()

            # Clear user's roles from config
            await self.config.member(user).clear()

            # Send report to channel
            if await self.config.guild(ctx.guild).report():
                action_info = {
                    "reason": reason,
                    "action": "removed from"
                }
                await self.report_handler(ctx, user, action_info)

            # Ask if user wishes to clear the timeout channel if they've defined one
            if timeout_channel:
                archive_query = await ctx.send(f"Do you wish to clear the contents of {timeout_channel.mention}?")
                start_adding_reactions(archive_query, ReactionPredicate.YES_OR_NO_EMOJIS)

                pred = ReactionPredicate.yes_or_no(archive_query, ctx.author)
                await ctx.bot.wait_for("reaction_add", check=pred)
                if pred.result is True:
                    purge = await timeout_channel.purge(bulk=True)
                    await ctx.send(f"Cleared {len(purge)} messages from {timeout_channel.mention}.")

    # Commands

    @commands.guild_only()
    @commands.group()
    async def timeoutset(self, ctx: commands.Context):
        """Change the configurations for `[p]timeout`."""
        if not ctx.invoked_subcommand:
            pass

    @timeoutset.command(name="logchannel")
    @checks.mod()
    async def timeoutset_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the log channel for any reports etc.

        Example:
        - `[p]timeoutset logchannel #mod-log`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.tick()

    @timeoutset.command(name="report", usage="<enable|disable>")
    @checks.mod()
    async def timeoutset_report(self, ctx: commands.Context, choice: str):
        """Whether to send a report when a user's timeout status is updated.

        These reports will be sent to the configured log channel as an embed.
        The embed will specify the user's details and the moderator who executed the command.

        Set log channel with `[p]timeoutset logchannel` before enabling reporting.

        Example:
        - `[p]timeoutset report enable`
        - `[p]timeoutset report disable`
        """

        # Ensure log channel has been defined
        log_channel = await self.config.guild(ctx.guild).logchannel()

        if str.lower(choice) == "enable":
            if log_channel:
                await self.config.guild(ctx.guild).report.set(True)
                await ctx.tick()
            else:
                await ctx.send(
                    "You must set the log channel before enabling reports.\n" +
                    f"Set the log channel with `{ctx.clean_prefix}timeoutset logchannel`."
                )

        elif str.lower(choice) == "disable":
            await self.config.guild(ctx.guild).report.set(False)
            await ctx.tick()

        else:
            await ctx.send("Setting must be `enable` or `disable`.")

    @timeoutset.command(name="role")
    @checks.mod()
    async def timeoutset_role(self, ctx: commands.Context, role: discord.Role):
        """Set the timeout role.

        Example:
        - `[p]timeoutset role MyRole`
        """
        await self.config.guild(ctx.guild).timeoutrole.set(role.id)
        await ctx.tick()

    @timeoutset.command(name="timeoutchannel")
    @checks.mod()
    async def timeoutset_timeout_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the timeout channel.

        This is required if you wish to optionaly purge the channel upon removing a user from timeout.

        Example:
        - `[p]timeoutset timeoutchannel #timeout`
        """
        await self.config.guild(ctx.guild).timeout_channel.set(channel.id)
        await ctx.tick()

    @timeoutset.command(name="list", aliases=["show", "view", "settings"])
    @checks.mod()
    async def timeoutset_list(self, ctx: commands.Context):
        """Show current settings."""

        log_channel = await self.config.guild(ctx.guild).logchannel()
        report = await self.config.guild(ctx.guild).report()
        timeout_role = ctx.guild.get_role(await self.config.guild(ctx.guild).timeoutrole())
        timeout_channel = await self.config.guild(ctx.guild).timeout_channel()

        if log_channel:
            log_channel = f"<#{log_channel}>"
        else:
            log_channel = "Unconfigured"

        if timeout_role:
            timeout_role = timeout_role.name
        else:
            timeout_role = "Unconfigured"

        if report:
            report = "Enabled"
        else:
            report = "Disabled"

        if timeout_channel:
            timeout_channel = f"<#{timeout_channel}>"
        else:
            timeout_channel = "Unconfigured"

        # Build embed
        embed = discord.Embed(
            color=(await ctx.embed_colour())
        )
        embed.set_author(
            name="Timeout Cog Settings",
            icon_url=ctx.guild.me.display_avatar.url
        )
        embed.add_field(
            name="Log Channel",
            value=log_channel,
            inline=True
        )
        embed.add_field(
            name="Send Reports",
            value=report,
            inline=True
        )
        embed.add_field(
            name="Timeout Role",
            value=timeout_role,
            inline=True
        )
        embed.add_field(
            name="Timeout Channel",
            value=timeout_channel,
            inline=True
        )

        # Send embed
        await ctx.send(embed=embed)

    @commands.command()
    @checks.mod()
    async def timeout(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Timeouts a user or returns them from timeout if they are currently in timeout.

        See and edit current configuration with `[p]timeoutset`.

        Examples:
        - `[p]timeout @user`
        - `[p]timeout @user Spamming chat`

        If the user is not already in timeout, their roles will be stored, stripped, and replaced with the timeout role.
        If the user is already in timeout, they will be removed from the timeout role and have their former roles restored.

        The cog determines that user is currently in timeout if the user's only role is the configured timeout role.
        """
        author = ctx.author
        everyone_role = ctx.guild.default_role

        # Set actor & target strings for logging
        self.actor = f"{ctx.author.name}({ctx.author.id})"
        self.target = f"{user.name}({user.id})"

        # Find the timeout role in server
        timeout_role_data = await self.config.guild(ctx.guild).timeoutrole()
        timeout_role = ctx.guild.get_role(timeout_role_data)

        # Notify and stop if command author tries to timeout themselves,
        # another mod, or if the bot can't do that due to Discord role heirarchy.
        if author == user:
            await ctx.message.add_reaction("🚫")
            await ctx.send("I cannot let you do that. Self-harm is bad \N{PENSIVE FACE}")
            return

        if ctx.guild.me.top_role <= user.top_role or user == ctx.guild.owner:
            await ctx.message.add_reaction("🚫")
            await ctx.send("I cannot do that due to Discord hierarchy rules.")
            return

        # Create a list containing the timeout role so we can
        # add the boost role to it if the user is a booster.
        # This is necessary since you cannot remove the boost
        # role, so we must ensure we avoid attempting to do so.
        booster_role = ctx.guild.premium_subscriber_role
        timeout_roleset = {timeout_role}
        if booster_role in user.roles:
            timeout_roleset.add(booster_role)

        if await is_mod(ctx.bot, user):
            await ctx.message.add_reaction("🚫")
            await ctx.send("Nice try. I can't timeout other moderators or admins.")
            return

        # Assign reason string if not specified by user
        if reason is None:
            reason = "Unspecified"

        # Check if user already in timeout.
        # Remove & restore if so, else add to timeout.
        if set(user.roles) == {everyone_role} | timeout_roleset:
            await self.timeout_remove(ctx, user, reason)

        else:
            await self.timeout_add(ctx, user, reason, timeout_role, list(timeout_roleset))

        # Run member data cleanup
        await self.member_data_cleanup(ctx)
