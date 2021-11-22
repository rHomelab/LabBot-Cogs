import sys
from logging import Logger, getLogger
from typing import Optional

from discord import Message
from discord.channel import TextChannel
from discord.ext.commands.errors import CommandInvokeError
from redbot.core import checks, commands
from redbot.core.bot import Config, Red
from sentry_sdk import capture_exception
from sentry_sdk import init as sentry_init
from sentry_sdk import start_transaction
from sentry_sdk.api import set_tag, set_user
from sentry_sdk.tracing import Transaction
from sentry_sdk.utils import BadDsn


class SentryCog(commands.Cog):
    """Sentry error reporting cog."""

    logger: Logger
    bot: Red
    _is_initialized: bool

    def __init__(self, bot: Red):
        super().__init__()
        self.logger = getLogger("sentry")

        self.bot = bot
        self._is_initialized = False

        self.config = Config.get_conf(self, identifier=34848138412384)
        default_global = {
            "environment": "",
            "log_level": "WARNING",
        }
        self.config.register_global(**default_global)

        bot.before_invoke(self.before_invoke)
        bot.after_invoke(self.after_invoke)
        self.logger.debug("Registered before/after hooks")

    async def ensure_client_init(self, context: commands.context.Context):
        """Ensure client is initialised"""
        if self._is_initialized:
            return
        log_level = await self.config.log_level()
        try:
            self.logger.setLevel(log_level)
        except ValueError:
            self.logger.error("Failed to set log level to '%s'", log_level)

        self.logger.debug("Initialising sentry client")
        environment = await self.config.environment()
        keys = await self.bot.get_shared_api_tokens("sentry")
        dsn = keys.get("dsn", None)
        try:
            # pylint: disable=abstract-class-instantiated
            sentry_init(
                dsn=dsn,
                environment=environment,
                traces_sample_rate=1,
                integrations=[],
                default_integrations=False,
            )
        except BadDsn:
            self.logger.error("Failed to initialise sentry client with DSN '%s'", dsn)
        else:
            self.logger.debug("Initialised sentry client with %s env=%s", dsn, environment)
            self._is_initialized = True

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke)
        return super().cog_unload()

    @checks.mod()
    @commands.group(name="sentry", pass_context=True)
    async def _sentry(self, ctx: commands.context.Context):
        """Command group for sentry settings"""

    @_sentry.command(name="set_env")
    async def sentry_set_env(self, context: commands.context.Context, new_value: str):
        """Set sentry environment"""
        await self.config.environment.set(new_value)
        await context.send(f"Sentry environment has been changed to '{new_value}'!")

    @_sentry.command(name="get_env")
    async def sentry_get_env(self, context: commands.context.Context):
        """Get sentry environment"""
        environment_val = await self.config.environment()
        await context.send(f"The Sentry environment is '{environment_val}'")

    @_sentry.command(name="set_log_level")
    async def sentry_set_log_level(self, context: commands.context.Context, new_value: str):
        """Set sentry log_level"""
        await self.config.log_level.set(new_value.upper())
        await context.send(f"Sentry log_level has been changed to '{new_value.upper()}'!")
        self.logger.setLevel(new_value.upper())

    @_sentry.command(name="get_log_level")
    async def sentry_get_log_level(self, context: commands.context.Context):
        """Get sentry log_level"""
        log_level_val = await self.config.log_level()
        await context.send(f"The Sentry log_level is '{log_level_val}'")

    @_sentry.command(name="test")
    async def sentry_test(self, context: commands.context.Context):
        """Test sentry"""
        await context.send("An exception will now be raised. Check Sentry to confirm.")
        raise ValueError("test error")

    async def before_invoke(self, context: commands.context.Context):
        """Method invoked before any red command. Start a transaction."""
        await self.ensure_client_init(context)
        msg: Message = context.message
        # set_user applies to the current scope, so it also applies to the transaction
        set_user(
            {
                "id": msg.author.id,
                "username": msg.author.display_name,
            }
        )
        transaction = start_transaction(op="command", name="Command %s" % context.command.name)
        transaction.set_tag("discord_message", msg.content)
        if context.command:
            transaction.set_tag("discord_command", context.command.name)
        if msg.guild:
            transaction.set_tag("discord_guild", msg.guild.name)
        if isinstance(msg.channel, TextChannel):
            transaction.set_tag("discord_channel", msg.channel.name)
            transaction.set_tag("discord_channel_id", msg.channel.id)
        setattr(context, "__sentry_transaction", transaction)

    async def after_invoke(self, context: commands.context.Context):
        """Method invoked after any red command. Checks if the command failed, and
        then tries to send the last exception to sentry."""
        await self.ensure_client_init(context)
        transaction: Optional[Transaction] = getattr(context, "__sentry_transaction", None)
        if not transaction:
            self.logger.debug("post-command: no transaction, discarding")
            return
        transaction.set_status("ok")
        msg: Message = context.message
        set_user(
            {
                "id": msg.author.id,
                "username": msg.author.display_name,
            }
        )
        set_tag("discord_message", msg.content)
        if context.command:
            set_tag("discord_command", context.command.name)
        if msg.guild:
            set_tag("discord_guild", msg.guild.name)
        if isinstance(msg.channel, TextChannel):
            set_tag("discord_channel", msg.channel.name)
            set_tag("discord_channel_id", msg.channel.id)

        if not context.command_failed:
            self.logger.debug("post-command: sending successful transaction")
            transaction.finish()
            return
        exc_type, value, _ = sys.exc_info()
        if not exc_type:
            transaction.finish()
            return
        if isinstance(value, CommandInvokeError):
            value = value.original

        transaction.set_status("unknown_error")
        self.logger.debug("post-command: capturing error")
        capture_exception(value)

        transaction.finish()
