from .labguard import LabGuard


async def setup(bot):
    await bot.add_cog(LabGuard(bot))
