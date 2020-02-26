"""discord red-bot verification"""
from redbot.core import commands, checks, Config


class VerificationCog(commands.Cog):
    """Verification Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1522109312)

        default_guild_settings = {
            "verify_message": "I agree",
            "verify_count": 0,
            "verify_role": None
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
