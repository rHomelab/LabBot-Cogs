from .feed import FeedCog

def setup(bot):
    bot.add_cog(FeedCog(bot))