import sys
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


class SentryCog(commands.Cog):
    """Sentry error reporting cog."""

    bot: Red
    _is_initialized: bool

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self._is_initialized = False

        self.config = Config.get_conf(self, identifier=34848138412384)
        default_global = {
            "environment": "",
        }
        self.config.register_global(**default_global)

        bot.before_invoke(self.before_invoke)
        bot.after_invoke(self.after_invoke)

    async def ensure_client_init(self, context: commands.context.Context):
        """Ensure client is initialised"""
        if self._is_initialized:
            return
        environment = await self.config.environment()
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

    @_sentry.command(name="test")
    async def sentry_test(self, context: commands.context.Context):
        """Test sentry"""
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
        capture_exception(value)

        transaction.finish()
