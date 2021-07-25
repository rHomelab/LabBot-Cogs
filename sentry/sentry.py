import sys
from typing import Optional

from discord.ext.commands.errors import CommandInvokeError
from redbot.core import commands
from redbot.core.bot import Red
from sentry_sdk import capture_exception
from sentry_sdk import init as sentry_init
from sentry_sdk import start_transaction
from sentry_sdk.api import set_tag
from sentry_sdk.tracing import Transaction


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
        bot.before_invoke(self.before_invoke)
        bot.after_invoke(self.after_invoke)

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke)
        return super().cog_unload()

    async def before_invoke(self, context: commands.context.Context, *args, **kwargs):
        """Method invoked before any red command. Start a transaction."""
        transaction = start_transaction(op="command", name="Command %s" % context.command.name)
        transaction.set_data("message", context.message.content)
        transaction.set_tag("message", context.message.content)
        setattr(context, "__sentry_transaction", transaction)

    async def after_invoke(self, context: commands.context.Context, *args, **kwargs):
        """Method invoked after any red command. Checks if the command failed, and
        then tries to send the last exception to sentry."""
        transaction: Optional[Transaction] = getattr(context, "__sentry_transaction", start_transaction())
        transaction.set_status("ok")

        if not context.command_failed:
            transaction.finish()
            return
        exc_type, value, _ = sys.exc_info()
        if not exc_type:
            transaction.finish()
            return
        if isinstance(value, CommandInvokeError):
            value = value.original

        transaction.set_status("unknown_error")
        set_tag("message", context.message.content)
        capture_exception(value)

        transaction.finish()
