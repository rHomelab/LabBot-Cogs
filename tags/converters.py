from redbot.core import commands
from redbot.core.utils.mod import is_mod_or_superior

from .exceptions import TagConversionFailed, TagNotFound
from .logging_configuration import LoggingConfiguration


async def logging_event_name_converter(self, ctx: commands.Context, arg: str) -> str:
    """
    Command arg converter.
    Converts to a logging event name, as defined in :LoggingConfiguration.VALID_FLAGS:.
    """
    arg = arg.lower()
    if arg in LoggingConfiguration.VALID_FLAGS.keys():
        return arg
    else:
        raise commands.BadArgument(
            message=(
                f"`{arg}` is not a valid event name.\n"
                "Please refer to the documentation for this cog for an exhaustive list of event names."
            )
        )


class TagNameConverter(commands.clean_content):
    """
    Converter class for use in command args.
    Makes sure the provided argument is a valid tag name (applies length and allowed character rules)
    """

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        converted = await super().convert(ctx, argument.lower())
        lowered = converted.lower().strip()

        if not lowered:
            raise commands.BadArgument("Missing tag name.")

        if len(lowered) > 100:
            raise commands.BadArgument("Tag name is a maximum of 100 characters.")

        first_word = lowered.split()[0]

        # get tag command.
        root = ctx.bot.get_command("tag")
        if first_word in root.all_commands:
            raise commands.BadArgument("This tag name starts with a reserved word.")

        return lowered


async def tag_converter(ctx: commands.Context, argument: str) -> dict:
    """
    Converter for use in command args.
    Fetches a tag by name from config.
    """
    tag_name = TagNameConverter().convert(ctx, argument)
    print("successfully converted to tag name")
    try:
        print("trying to get tag")
        tag = await ctx.cog.get_tag(ctx.guild, tag_name)
        print("got tag, returning...")
        return tag
    except TagNotFound:
        print("didn't find a tag")
        raise TagConversionFailed
