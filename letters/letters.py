import re

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify


class Letters(commands.Cog):
    """Letters cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def letters(self, ctx, msg: discord.Message):
        """Outputs large emote letters (\"regional indicators\") based on input text.
        Accepts A-Z only.

        Example:
        - `[p]letters I'd like this text as emotes`
        """

        # Grab message content
        input = msg.content

        # Ensure it doesn't contain any special chars, numbers, etc.
        regexp = re.compile(r'[^a-zA-Z ]')
        if regexp.search(input):
            await ctx.send('This cog accepts only A-Z and whitespace characters.')

        else:
            # Initialise letters var
            letters=''
            # For each char in input
            for letter in input:
                # Add double space if char is space
                if letter == ' ':
                    letters+='  '
                # Else add letter as regional indicator emote
                else: 
                    letters+=f":regional_indicator_{letter}: "
            
            # Define and send message
            output = f"{letters}\n`{letters}`"
            await ctx.send(output)
