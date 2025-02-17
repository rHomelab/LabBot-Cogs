"""discord red-bot roleinfo cog"""

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.mod import is_mod_or_superior as is_mod


class RoleInfoCog(commands.Cog):
    """Roleinfo cog"""

    bot: Red

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command("roleinfo")
    async def role_info_cmd(self, ctx: commands.Context, role: discord.Role):
        """Displays info about a role in the server

        Example:
        - `[p]roleinfo <role>`
        - `[p]roleinfo 266858186336632831`
        - `[p]roleinfo verified`
        - `[p]roleinfo @verified`
        """
        if isinstance(ctx.author, discord.Member):
            role_check = await is_mod(self.bot, ctx.author) or role <= max(ctx.author.roles)
            if role_check:
                embed = await self.make_role_embed(role)
                await ctx.send(embed=embed)
        else:
            await ctx.send("You can only use this command in a server.")

    async def make_role_embed(self, role: discord.Role) -> discord.Embed:
        """Generate the role info embed"""
        return (
            discord.Embed(title="Role info", colour=role.colour)
            .add_field(name="Name", value=role.name)
            .add_field(name="Members", value=len(role.members))
            .add_field(name="Hoist", value="Yes" if role.hoist else "No")
            .add_field(name="Mentionable", value="Yes" if role.mentionable else "No")
            .add_field(name="Position", value=len(role.guild.roles) - role.position)
            .add_field(name="ID", value=role.id)
            .add_field(name="Created at", value=f"<t:{int(role.created_at.timestamp())}:F>")
        )
