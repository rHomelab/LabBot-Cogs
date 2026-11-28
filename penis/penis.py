import random

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify

DONG_DISTRIBUTION_CONST = 30
SMALL_DONG_CONST = 6
BIG_DONG_CONST = DONG_DISTRIBUTION_CONST - SMALL_DONG_CONST


class Penis(commands.Cog):
    """Penis related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=928374651,
            force_registration=True
        )
        self.config.register_guild(mod_behaviour=False)

    @commands.command()
    @commands.guild_only()
    async def penis(self, ctx, *users: discord.Member):
        """Detects user's penis length.

        This is 100% accurate.
        Enter multiple users for an accurate comparison!
        """

        dongs = {}
        msg = ""

        if not users:
            users = (ctx.author,)

        mod_behaviour = await self.config.guild(ctx.guild).mod_behaviour()

        for user in users:
            is_mod = mod_behaviour and (
                user.id == ctx.guild.owner_id
                or await self.bot.is_mod(user)
            )

            if is_mod:
                dongs[user] = ("8=D", True)
            else:
                rng = random.Random(user.id)
                dong = "8{}D".format(
                    "=" * rng.randint(0, DONG_DISTRIBUTION_CONST)
                )
                dongs[user] = (dong, False)

        dongs = sorted(
            dongs.items(),
            key=lambda x: x[1][0]
        )

        for user, (dong, is_mod) in dongs:
            if is_mod:
                msg += (
                    f"**{user.display_name}'s size:**\n"
                    f"{dong}\n"
                    "woah, now that's NOT a dong!\n"
                )
            elif len(dong) <= SMALL_DONG_CONST:
                msg += (
                    f"**{user.display_name}'s size:**\n"
                    f"{dong}\n"
                    "lol small\n"
                )
            elif len(dong) <= BIG_DONG_CONST:
                msg += (
                    f"**{user.display_name}'s size:**\n"
                    f"{dong}\n"
                )
            else:
                msg += (
                    f"**{user.display_name}'s size:**\n"
                    f"{dong}\n"
                    "wow, now that's a dong!\n"
                )

        for page in pagify(msg):
            await ctx.send(page)

    @commands.command() # pyright: ignore[reportArgumentType]
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def penis_state(self, ctx) :
        """Toggle moderator behaviour."""

        config = self.config.guild(ctx.guild)
        current = await config.mod_behaviour()
        new_value = not current

        await config.mod_behaviour.set(new_value)

        if new_value:
            status = "enabled"
        else:
            status = "disabled"

        await ctx.send(
            f"The truth has been **{status}**."
        )


async def setup(bot):
    await bot.add_cog(Penis(bot))
