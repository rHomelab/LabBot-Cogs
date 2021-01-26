from .quotes import QuotesCog


def setup(bot):
    bot.add_cog(QuotesCog(bot))
