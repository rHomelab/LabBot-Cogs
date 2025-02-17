import sys
from logging import Logger, getLogger
from typing import Optional

from discord import Message
from discord.channel import TextChannel
from discord.ext.commands.errors import CommandInvokeError
from redbot.core import checks, commands
from redbot.core.bot import Config, Red
from sentry_sdk.client import Client
from sentry_sdk.hub import Hub
from sentry_sdk.tracing import Transaction
from sentry_sdk.utils import BadDsn


class SentryCog(commands.Cog):
    """Sentry error reporting cog."""

    logger: Logger
    bot: Red
    _is_initialized: bool
    client: Optional[Client]

    def __init__(self, bot: Red):
        super().__init__()
        self.logger = getLogger("red.rhomelab.sentry")

        self.bot = bot
        self.client = None

        self.config = Config.get_conf(self, identifier=34848138412384)
        default_global = {
            "environment": "",
            "log_level": "WARNING",
        }
        self.config.register_global(**default_global)

        bot.before_invoke(self.before_invoke)
        bot.after_invoke(self.after_invoke)
        self.logger.debug("Registered before/after hooks")

    # pylint: disable=unused-argument
    async def ensure_client_init(self, context: commands.context.Context):
        """Ensure client is initialised"""
        if self.client:
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
            self.client = Client(
                dsn=dsn,
                environment=environment,
                traces_sample_rate=1,
                integrations=[],
                default_integrations=False,
            )
            self.client.options["debug"] = log_level.upper() == "DEBUG"
        except BadDsn:
            self.logger.error("Failed to initialise sentry client with DSN '%s'", dsn)
        else:
            self.logger.debug("Initialised sentry client with %s env=%s", dsn, environment)

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke)
        return super().cog_unload()

    @checks.mod()
    @commands.group(name="sentry", pass_context=True)
    async def _sentry(self, ctx: commands.context.Context):
        """Command group for sentry settings"""

    @_sentry.command(name="set_env")  # type: ignore
    async def sentry_set_env(self, context: commands.context.Context, new_value: str):
        """Set sentry environment"""
        await self.config.environment.set(new_value)
        await context.send(f"Sentry environment has been changed to '{new_value}'")

    @_sentry.command(name="get_env")  # type: ignore
    async def sentry_get_env(self, context: commands.context.Context):
        """Get sentry environment"""
        environment_val = await self.config.environment()
        if environment_val:
            message = f"The Sentry environment is '{environment_val}'"
        else:
            message = f"The Sentry environment is unset. See `{context.prefix}sentry set_env`."
        await context.send(message)

    @_sentry.command(name="set_log_level")  # type: ignore
    async def sentry_set_log_level(self, context: commands.context.Context, new_value: str):
        """Set sentry log_level"""
        new_value = new_value.upper()
        if self.client:
            self.client.options["debug"] = new_value == "DEBUG"
        else:
            self.logger.warning("Sentry client not initialised yet")
            await context.send("Sentry client not initialised yet")
        try:
            self.logger.setLevel(new_value)
            await self.config.log_level.set(new_value)
            await context.send(f"Sentry log_level has been changed to '{new_value}'")
        except ValueError as error:
            self.logger.warning(f"Could not change log level to '{new_value}': ", exc_info=error)
            await context.send("Sentry log_level could not be changed.\n" + f"{new_value} is not a valid logging level.")

    @_sentry.command(name="get_log_level")  # type: ignore
    async def sentry_get_log_level(self, context: commands.context.Context):
        """Get sentry log_level"""
        log_level_val = await self.config.log_level()
        await context.send(f"The Sentry log_level is '{log_level_val}'")

    @_sentry.command(name="test")  # type: ignore
    async def sentry_test(self, context: commands.context.Context):
        """Test sentry"""
        await context.send("An exception will now be raised. Check Sentry to confirm.")
        raise ValueError("test error")

    async def before_invoke(self, context: commands.context.Context):
        """Method invoked before any red command. Start a transaction."""
        await self.ensure_client_init(context)
        msg: Message = context.message
        with Hub(self.client) as hub:
            # set_user applies to the current scope, so it also applies to the transaction
            hub.scope.set_user(
                {
                    "id": msg.author.id,
                    "username": msg.author.display_name,
                }
            )
            transaction = hub.start_transaction(op="command", name=f"Command {context.command.name}")
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
        with Hub(self.client) as hub:
            transaction.set_status("ok")
            msg: Message = context.message
            hub.scope.set_user(
                {
                    "id": msg.author.id,
                    "username": msg.author.display_name,
                }
            )
            hub.scope.set_tag("discord_message", msg.content)
            if context.command:
                hub.scope.set_tag("discord_command", context.command.name)
            if msg.guild:
                hub.scope.set_tag("discord_guild", msg.guild.name)
            if isinstance(msg.channel, TextChannel):
                hub.scope.set_tag("discord_channel", msg.channel.name)
                hub.scope.set_tag("discord_channel_id", msg.channel.id)

            if not context.command_failed:
                self.logger.debug("post-command: sending successful transaction")
                transaction.finish(hub)
                return
            exc_type, value, _ = sys.exc_info()
            if not exc_type:
                transaction.finish(hub)
                return
            if isinstance(value, CommandInvokeError):
                value = value.original

            transaction.set_status("unknown_error")
            self.logger.debug("post-command: capturing error")
            hub.capture_exception(value)

            transaction.finish(hub)
