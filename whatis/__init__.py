from .whatis import WhatIsCog


def setup(bot):
    bot.add_cog(WhatIsCog(bot))
