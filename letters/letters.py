import re

from redbot.core import commands


# Define numbers -> emotes tuple
nums = (':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:')

class Letters(commands.Cog):
    """Letters cog"""

    @commands.command()
    async def letters(self, ctx, *, msg):
        """Outputs large emote letters (\"regional indicators\") from input text.
        Accepts A-Z, 0-9, and whitespace only.

        Example:
        - `[p]letters I'd like this text as emotes 123`
        """

        # Grab message content
        input = msg.lower()

        # Ensure it doesn't contain any special chars, numbers, etc.
        regexp = re.compile(r'[^a-zA-Z0-9 ]')
        if regexp.search(input):
            await ctx.send('This cog accepts only A-Z, 0-9, and whitespace characters.')

        else:
            # Initialise letters var
            letters = ''

            # For each char in input
            for char in input:

                # Double space if char is space
                if char == ' ':
                    letters += '  '

                # Convert to regional indicator emote if letter
                elif not char.isdigit():
                    letters += f":regional_indicator_{char}: "

                # Convert to number emote if number
                elif char.isdigit():
                    letters += f"{nums[int(char)]} "

            # Replace =>3 spaces with two
            letters = re.sub(' {3,}', '  ', letters)

            # Define and send message
            output = f"{letters}\n```{letters}```"
            await ctx.send(output)
