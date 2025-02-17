import re
from typing import Optional

from redbot.core import commands

# Define numbers -> emotes tuple
nums = (":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:")

# Define specials -> emotes dict
specials = {"!": ":exclamation:", "?": ":question:", "#": ":hash:", "'": "'", ".": ".", ",": ","}

allowed_chars = re.compile(r"[^a-z0-9!?\'.#, ]")


def convert_char(char: str) -> str:
    """Convert character to discord emoji"""
    # Double space if char is space
    if char == " ":
        return "  "

    # Convert to number emote if number
    elif char.isdigit():
        return f"{nums[int(char)]} "

    # Convert to regional indicator emote if letter
    elif char.isalpha():
        return f":regional_indicator_{char}: "

    # Convert to character emote
    else:
        return f"{specials[char]} "


def correct_punctuation_spacing(input_str: str) -> str:
    return re.sub(r"([!?'.#,:]) ([!?'.#,])", r"\1\2", input_str)


def string_converter(input_str: str) -> str:
    """Convert a string to discord emojis"""
    # NOTE In future it would be ideal to convert this function to an advanced converter (https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html#advanced-converters)
    # So we can bootstrap the commands.clean_content converter and escape channel/user/role mentions
    # (currently there is no ping exploit; it just looks odd when converted)
    # However, the current version of the commands.clean_content converter doesn't actually work on an argument;
    #  it scans the whole message content.
    # This has been fixed in discord.py 2.0

    # Make the whole string lowercase
    input_str = input_str.lower()
    # Strip unsupported characters
    if allowed_chars.search(input_str):
        input_str = allowed_chars.sub("", input_str)

    # Convert characters to Discord emojis
    letters = "".join(map(convert_char, input_str))
    # Replace >= 3 spaces with two
    letters = re.sub(" {3,}", "  ", letters)
    # Correct punctuation spacing
    letters = correct_punctuation_spacing(correct_punctuation_spacing(letters))

    return letters


def raw_flag(argument: str) -> bool:
    """Raw flag converter"""
    if argument.lower() == "-raw":
        return True
    else:
        raise commands.BadArgument


class Letters(commands.Cog):
    """Letters cog"""

    @commands.command()
    async def letters(self, ctx: commands.Context, raw: Optional[raw_flag] = False, *, msg: string_converter):  # type: ignore
        """Outputs large emote letters (\"regional indicators\") from input text.

        The result can be outputted as raw emote code using `-raw` flag.

        Example:
        - `[p]letters I would like this text as emotes 123`
        - `[p]letters -raw I would like this text as raw emote code 123`
        """
        output = f"```{msg}```" if raw else msg

        # Ensure output isn't too long
        if len(output) > 2000:  # noqa: PLR2004
            return await ctx.send("Input too large.")

        # Send message
        await ctx.send(output)
