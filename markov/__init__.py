from .markov import Markov

async def setup(bot):
    bot.add_cog(Markov(bot))
