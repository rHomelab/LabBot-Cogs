"""discord red-bot verification"""
import discord
from redbot.core import commands, checks, Config


class VerificationCog(commands.Cog):
    """Verification Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "verify_message": "I agree",
            "verify_count": 0,
            "verify_role": None,
            "verify_channel": None
        }

        self.settings.register_guild(**default_guild_settings)

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
        verify_message = await self.settings.guild(ctx.guild).verify_message()
        verify_message = verify_message.replace('`', '')
        verify_count = await self.settings.guild(ctx.guild).verify_count()

        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.add_field(name="Verified", value=f"{verify_count} users")
        data.add_field(name="Message", value=f"`{verify_message}`")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " +
                           "send a purge status.")
