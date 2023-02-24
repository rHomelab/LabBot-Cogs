from redbot.core.utils import get_end_user_data_statement

from .markov import Markov

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)

async def setup(bot):
    bot.add_cog(Markov(bot))
