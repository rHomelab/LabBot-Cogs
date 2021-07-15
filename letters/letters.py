import re

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

def convert_string(input_str: str) -> str:
    """Convert a string to discord emojis"""
    # Strip unsupported characters
    if allowed_chars.search(input_str):
        input_str = allowed_chars.sub("", input_str)

    # Convert characters to Discord emojis
    letters = "".join(map(convert_char, input_str))
    # Replace >= 3 spaces with two
    letters = re.sub(" {3,}", "  ", letters)
    # Correct punctuation spacing
    letters = re.sub(r"[!?\'.#,:] ([!?\'.#,])", r":\1", letters)

    return letters

class Letters(commands.Cog):
    """Letters cog"""

    @commands.command()
    async def letters(self, ctx, *, msg):
        """Outputs large emote letters (\"regional indicators\") from input text.

        The result can be outputted as raw emote code using `-raw` flag.

        Example:
        - `[p]letters I would like this text as emotes 123`
        - `[p]letters -raw I would like this text as raw emote code 123`
        """

        # Grab message content
        input = msg.lower()

        # Check for raw flag
        raw = False
        if input.startswith("-raw"):
            raw = True
            input = input.lstrip("-raw").lstrip()

        # Define output
        letters = convert_string(input)
        output = f"```{letters}```" if raw else letters

        # Ensure output isn't too long
        if len(output) > 2000:
            return await ctx.send("Input too large.")

        # Send message
        await ctx.send(output)
