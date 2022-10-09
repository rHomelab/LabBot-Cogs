import discord
from redbot.core import Config, checks, commands


class Timeout(commands.Cog):
    """Timeout a user"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=539343858187161140)
        default_guild = {
            "logchannel": "",
            "report": "",
            "timeoutrole": ""
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(
            roles=[]
        )

    @commands.guild_only()
    @commands.group()
    async def timeoutset(self, ctx: commands.Context):
        """Change the configurations for `[p]timeout`."""
        if not ctx.invoked_subcommand:
            pass

    @timeoutset.command(name="logchannel")
    @checks.mod()
    async def timeoutsetlogchannel(self, ctx, channel: discord.TextChannel):
        """Set the log channel for any reports etc.

        Example:
        - `[p]timeoutset logchannel #mod-log`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.message.add_reaction("✅")

    @timeoutset.command(name="report")
    @checks.mod()
    async def timeoutsetreport(self, ctx, choice):
        """Whether to send a report when a user is added or removed from timeout.

        These reports will be sent in the form of an embed with timeout reason to the configured log channel.
        Set log channel with `[p]timeoutset logchannel`.

        Example:
        - `[p]timeoutset report [choice]`

        Possible choices are:
        - `true` or `yes`: Reports will be sent.
        - `false` or `no`: Reports will not be sent.
        """

        if str.lower(choice) in ['true', 'yes']:
            await self.config.guild(ctx.guild).report.set(True)
            await ctx.message.add_reaction("✅")
        elif str.lower(choice) in ['false', 'no']:
            await self.config.guild(ctx.guild).report.set(False)
            await ctx.message.add_reaction("✅")
        else:
            await ctx.send('Choices: true/yes or false/no')

    @timeoutset.command(name="role")
    @checks.mod()
    async def timeoutsetrole(self, ctx, role: discord.Role):
        """Set the timeout role.

        Example:
        - `[p]timeoutset role MyRole`
        """
        await self.config.guild(ctx.guild).timeoutrole.set(role.id)
        await ctx.message.add_reaction("✅")

    @timeoutset.command(name="list")
    @checks.mod()
    async def timeoutsetlist(self, ctx):
        """List current settings."""

        log_channel = await self.config.guild(ctx.guild).logchannel()
        timeout_role = ctx.guild.get_role(await self.config.guild(ctx.guild).timeoutrole())

        await ctx.send(
            "Log channel: " + str(f"<#{log_channel}>") +"\n"+
            "Send reports: " + str(await self.config.guild(ctx.guild).report()) +"\n"+
            "Timeout role: " + str(timeout_role.name)
        )


    @commands.command()
    @checks.mod()
    async def timeout(self, ctx, user: discord.Member, *, reason=""):
        """Timeouts a user or returns them from timeout if they are currently in timeout.

        See and edit current configuration with `[p]timeoutset`.

        Example:
        - `[p]timeout @user`
        """
        author = ctx.author
        everyone_role = ctx.guild.default_role

        # Notify and stop if command author tries to timeout themselves,
        # or if the bot can't do that.
        if author == user:
            await ctx.send("I cannot let you do that. Self-harm is bad \N{PENSIVE FACE}")
            return

        if ctx.guild.me.top_role <= user.top_role or user == ctx.guild.owner:
            await ctx.send("I cannot do that due to Discord hierarchy rules.")
            return

        # Find the timeout role in server
        timeout_role_data = await self.config.guild(ctx.guild).timeoutrole()
        timeout_role = ctx.guild.get_role(timeout_role_data)

        # Retrieve log channel
        log_channel_config = await self.config.guild(ctx.guild).logchannel()
        log_channel = ctx.guild.get_channel(log_channel_config)

        # Check if user already in timeout.
        # Remove & restore if so, else timeout.
        if user.roles == [everyone_role, timeout_role]:

            # Fetch and define user's previous roles.
            user_roles = []
            for role in await self.config.member(user).roles():
                user_roles.append(ctx.guild.get_role(role))

            # Replace user's roles with their previous roles.
            try:
                await user.edit(roles=user_roles)
            except discord.HTTPException as error:
                await ctx.send("Something went wrong!")
                raise Exception(error) from error
            except discord.Forbidden:
                await ctx.send("Whoops, looks like I don't have permission to do that.")
            else:
                await ctx.message.add_reaction("✅")

                # Clear user's roles from config
                await self.config.member(user).clear()

                # Send report to channel
                if await self.config.guild(ctx.guild).report():
                    embed = discord.Embed(color=(await ctx.embed_colour()), description=reason)
                    embed.set_footer(text=f"Sent in #{ctx.channel}")

                    if user.avatar_url:
                        embed.set_author(name=f"User removed from timeout: {user.display_name}", icon_url=user.avatar_url)
                    else:
                        embed.set_author(name=user.display_name)

                    await log_channel.send(embed=embed)

        else:
            # Store the user's roles
            user_roles = []
            for role in user.roles:
                user_roles.append(role.id)

            await self.config.member(user).roles.set(user_roles)

            # Replace all of a user's roles with timeout role
            try:
                await user.edit(roles=[timeout_role])
            except discord.HTTPException:
                await ctx.send("Be sure to set the timeout role first using `[p]timeoutset role`")
            except discord.Forbidden:
                await ctx.send("Whoops, looks like I don't have permission to do that.")
            else:
                await ctx.message.add_reaction("✅")

            # Send report to channel
            if await self.config.guild(ctx.guild).report():
                embed = discord.Embed(color=(await ctx.embed_colour()), description=reason)
                embed.set_footer(text=f"Sent in #{ctx.channel}")

                if user.avatar_url:
                    embed.set_author(name=f"User added to timeout: {user.display_name}", icon_url=user.avatar_url)
                else:
                    embed.set_author(name=user.display_name)

                await log_channel.send(embed=embed)
