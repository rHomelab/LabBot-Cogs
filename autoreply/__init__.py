from .autoreply import AutoReplyCog

def setup(bot):
    bot.add_cog(AutoReplyCog(bot))