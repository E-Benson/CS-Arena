import discord
from discord.ext import commands, tasks


class SimpleCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="heh")
    async def heh_cmd(self, ctx):
        await ctx.send("hehehehehheheheh")

def setup(bot: commands.Bot):
    #global server
    #server = bot.guilds[0]
    #valid_channel = discord.utils.get(server.text_channels, name="leaderboard")
    bot.add_cog(SimpleCog(bot))
