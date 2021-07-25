import sys

from discord.ext.commands.errors import CommandInvokeError
from redbot.core import commands
from redbot.core.bot import Red
from sentry_sdk import capture_exception, start_transaction
from sentry_sdk import init as sentry_init
from sentry_sdk.api import set_tag


class SentryCog(commands.Cog):
    """Sentry error reporting cog."""

    bot: Red

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        # pylint: disable=abstract-class-instantiated
        sentry_init(
            traces_sample_rate=1,
            integrations=[],
            default_integrations=False,
        )
        bot.after_invoke(SentryCog.after_invoke)

    @staticmethod
    async def after_invoke(context: commands.context.Context, *args, **kwargs):
        """Method invoked after any red command. Checks if the command failed, and
        then tries to send the last exception to sentry."""
        if not context.command_failed:
            return
        exc_type, value, _ = sys.exc_info()
        if not exc_type:
            return
        if isinstance(value, CommandInvokeError):
            value = value.original
        set_tag("message", context.message)
        capture_exception(value)
