"""discord red-bot roleinfo cog"""
import discord
from redbot.core import commands


class RoleInfoCog(commands.Cog):
    @commands.command("roleinfo")
    async def role_info_cmd(self, ctx: commands.Context, role: discord.Role):
        """Displays info about a role in the server

        Example:
        - `[p]roleinfo <role>`
        - `[p]roleinfo 266858186336632831`
        - `[p]roleinfo verified`
        - `[p]roleinfo @verified`
        """
        embed = self.make_role_embed(role)
        await ctx.send(embed=embed)

    async def make_role_embed(self, role: discord.Role) -> discord.Embed:
        embed = discord.Embed(title=f"Role info", colour=role.colour, timestamp=role.created_at)
        embed.add_field(name="Name", value=role.name)
        embed.add_field(name="Members", value=len(role.members))
        embed.add_field(name="Hoist", value="Yes" if role.hoist else "No")
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No")
        embed.add_field(name="Position", value=role.position + 1)
        embed.add_field(name="ID", value=role.id)
        embed.set_footer("Created")
        return embed
