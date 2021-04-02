from .permsbackup import PermsBackupCog


def setup(bot):
    bot.add_cog(PermsBackupCog(bot))
