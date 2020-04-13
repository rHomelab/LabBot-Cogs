"""discord red-bot reactrole cog"""
import discord
from redbot.core import checks, commands, Config


class ReactRoleCog(commands.Cog):
    """ReactRole Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=124123498)

        default_guild_settings = {
            "roles": []
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Member adds reaction to a message
        """
        if not payload.member:
            # TODO Log error
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Guild shouldn't be none
            return

        async with self.settings.guild(guild).roles() as li:
            for item in li:
                if (
                    item["message"] == payload.message_id and
                    item["reaction"] == str(payload.emoji)
                ):
                    role = guild.get_role(item["role"])
                    await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Member removes reaction from a message
        """
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Guild shouldn't be none
            return

        member = guild.get_member(payload.user_id)

        async with self.settings.guild(guild).roles() as li:
            for item in li:
                if (
                    item["message"] == payload.message_id and
                    item["reaction"] == str(payload.emoji)
                ):
                    role = guild.get_role(item["role"])
                    await member.remove_roles(role)

    @commands.group(name="reactrole")
    @commands.guild_only()
    @checks.mod()
    async def _reactrole(self, ctx: commands.Context):
        pass

    @_reactrole.command("add")
    async def add_reactrole(
        self,
        ctx: commands.Context,
        message: discord.Message,
        reaction: str,
        role: discord.Role
    ):
        """Creates a new react role

        Example:
        - `[p]reactrole add <message id> <reaction> <role>`
        """
        async with self.settings.guild(ctx.guild).roles() as li:
            added = False

            for item in li:
                # Check if a result already exists
                if (
                    item["message"] == message.id and
                    item["reaction"] == str(reaction) and
                    item["role"] == role.id
                ):
                    added = True

            if added:
                await ctx.send("React Role already exists.")
            else:
                try:
                    await message.add_reaction(str(reaction))

                    li.append({
                        "message": message.id,
                        "reaction": str(reaction),
                        "role": role.id
                    })
                    await ctx.send("Configured React Role.")
                except Exception:
                    await ctx.send("Unable to add emoji message to message")

    @_reactrole.command("remove")
    async def remove_reactrole(
        self,
        ctx: commands.Context,
        message: discord.Message,
        reaction: str,
        role: discord.Role
    ):
        """Removes a configured react role

        Example:
        - `[p]reactrole remove <message id> <reaction> <role>`
        """
        async with self.settings.guild(ctx.guild).roles() as li:
            exists = False

            for item in li:
                # Check if a result already exists
                if (
                    item["message"] == message.id and
                    item["reaction"] == str(reaction) and
                    item["role"] == role.id
                ):
                    exists = item

            li.remove(exists)

            if exists:
                await ctx.send("React Role removed.")
            else:
                await ctx.send("React Role didn't exist.")
