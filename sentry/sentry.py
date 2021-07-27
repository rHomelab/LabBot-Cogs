import sys
from typing import Optional

from discord import Message
from discord.ext.commands.errors import CommandInvokeError
from redbot.core import commands, checks
from redbot.core.bot import Config, Red
from sentry_sdk import capture_exception
from sentry_sdk import init as sentry_init
from sentry_sdk import start_transaction
from sentry_sdk.api import set_tag, set_user
from sentry_sdk.tracing import Transaction

# Configure
# [p]set api sentry dsn,https://fooo@bar.baz/9


class SentryCog(commands.Cog):
    """Sentry error reporting cog."""

    bot: Red
    _is_initialized: bool

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self._is_initialized = False

        self.config = Config.get_conf(self, identifier=34848138412384)
        default_guild = {
            "environment": "",
        }
        self.config.register_guild(**default_guild)

        bot.before_invoke(self.before_invoke)
        bot.after_invoke(self.after_invoke)

    async def ensure_client_init(self, context: commands.context.Context):
        """Ensure client is initialised"""
        if self._is_initialized:
            return
        environment = ""
        if context.guild:
            environment = await self.config.guild(context.guild).environment()
        keys = await self.bot.get_shared_api_tokens("sentry")
        # pylint: disable=abstract-class-instantiated
        sentry_init(
            dsn=keys.get("dsn", None),
            environment=environment,
            traces_sample_rate=1,
            integrations=[],
            default_integrations=False,
        )
        self._is_initialized = True

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke)
        return super().cog_unload()

    @commands.command()
    @checks.mod()
    async def sentry_set_env(self, context: commands.context.Context, new_value: str):
        """Set sentry environment"""
        if not context.guild:
            await context.send((
                "Environment can only be changed from a discord server as "
                "it's a per-server setting."
            ))
            return
        await self.config.guild(context.guild).environment.set(new_value)
        await context.send(f"Value of environment has been changed to '{new_value}'!")

    @commands.command()
    @checks.mod()
    async def sentry_get_env(self, context: commands.context.Context):
        """Get sentry environment"""
        if not context.guild:
            await context.send((
                "Environment can only be changed from a discord server as "
                "it's a per-server setting."
            ))
            return
        environment_val = await self.config.guild(context.guild).environment()
        await context.send(f"The value of environment is '{environment_val}'")

    @commands.command()
    @checks.mod()
    async def sentry_test(self, context: commands.context.Context):
        """Test sentry"""
        raise ValueError("test error")

    async def before_invoke(self, context: commands.context.Context):
        """Method invoked before any red command. Start a transaction."""
        await self.ensure_client_init(context)
        msg: Message = context.message
        # set_user applies to the current scope, so it also applies to the transaction
        set_user({
            "id": msg.author.id,
            "username": msg.author.display_name,
        })
        transaction = start_transaction(op="command", name="Command %s" % context.command.name)
        transaction.set_tag("discord_message", msg.content)
        transaction.set_tag("discord_command", context.command.name)
        setattr(context, "__sentry_transaction", transaction)

    async def after_invoke(self, context: commands.context.Context):
        """Method invoked after any red command. Checks if the command failed, and
        then tries to send the last exception to sentry."""
        await self.ensure_client_init(context)
        transaction: Optional[Transaction] = getattr(context, "__sentry_transaction", None)
        if not transaction:
            return
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
        msg: Message = context.message
        set_user({
            "id": msg.author.id,
            "username": msg.author.display_name,
        })
        set_tag("discord_message", msg.content)
        set_tag("discord_command", context.command.name)
        capture_exception(value)

        transaction.finish()
