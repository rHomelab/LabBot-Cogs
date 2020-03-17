"""discord red-bot enforcer"""
import discord
from redbot.core import commands, Config, checks


class EnforcerCog(commands.Cog):
    """Enforcer Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=987342593)
        self.attributes = {
            "enabled": {
                "type": "bool"
            },
            "minchars": {
                "type": "number"
            },
            "notext": {
                "type": "bool"
            },
            "nomedia": {
                "type": "bool"
            },
            "requiremedia": {
                "type": "bool"
            },
            "minimumdiscordage": {
                "type": "number"
            },
            "minimumguildage": {
                "type": "number"
            }
        }

        default_guild_settings = {
            "channels": []
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="enforcer")
    @commands.guild_only()
    @checks.admin()
    async def _enforcer(self, ctx: commands.Context):
        pass

    async def _validate_attribute_value(self, attribute: str, value: str):
        attribute_type = self.attributes[attribute]["type"]

        if attribute_type == "bool":
            if value in [
                "true",
                "1",
                "yes",
                "y"
            ]:
                return True
            elif value in [
                "false",
                "0",
                "no",
                "n"
            ]:
                return False
            else:
                raise ValueError()
        elif attribute_type == "number":
            value = int(value)

            return value

        return None

    async def _reset_attribute(self, channel: discord.TextChannel, attribute):
        async with self.settings.guild(channel.guild).channels() as li:
            for ch in li:
                if ch["id"] == channel.id:
                    del ch[attribute]

    async def _set_attribute(
        self,
        channel: discord.TextChannel,
        attribute,
        value
    ):
        added = False
        async with self.settings.guild(channel.guild).channels() as li:
            for ch in li:
                if ch["id"] == channel.id:
                    ch[attribute] = value
                    added = True
                    break

            if added is False:
                li.append({
                    "id": channel.id,
                    attribute: value
                })

    @_enforcer.command("configure")
    async def enforcer_configure(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        attribute: str,
        *,
        value: str
    ):
        """Allows configuration of a channel

        Example:
        - `[p]enforcer configure <channel> <attribute> <value?>`

        If `<value>` is not provided, the attribute will be reset.
        """
        attribute = attribute.lower()

        if attribute not in self.attributes:
            await ctx.send("That attribute is not configurable.")
            return

        if value is None:
            await self._reset_attribute(channel, attribute)
            await ctx.send("That attribute has been reset.")
            return

        try:
            value = await self._validate_attribute_value(attribute, value)
        except ValueError:
            await ctx.send("The given value is invalid for that attribute.")
            return

        await self._set_attribute(channel, attribute, value)
        await ctx.send(f"Channel has now configured the {attribute} attribute.")
