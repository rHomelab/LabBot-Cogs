from .reddit import RedditCog


def setup(bot):
    bot.add_cog(RedditCog(bot))
