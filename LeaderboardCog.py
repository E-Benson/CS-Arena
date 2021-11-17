import discord
from discord.ext import commands, tasks
from PointsLeaderBoard import LeaderboardPrinter
from Leaderboard import Leaderboard


def setup(bot: commands.Bot):
    bot.add_cog(LeaderboardCog(bot))


class LeaderboardCog(commands.Cog):
    lb_printer = LeaderboardPrinter(leaderboard_size=25)
    points_lb_png = "PointsLeaderboard.png"
    stick_lb_png = "Leaderboard.png"
    stick_lb = Leaderboard()
    valid_channel_name = "leaderboard"
    valid_channel = None
    elite_max = 5
    veteran_max = 15
    intermediate_max = 25

    def __init__(self, bot):
        self.bot = bot
        self.server = None
        self.ranks = dict()
        self.rank_names = ["Beginner", "Intermediate", "Veteran", "Elite"]

    #
    # Initialize variables after the bot has connected
    #
    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        for _rank in self.rank_names:
            self.ranks[_rank] = discord.utils.get(self.server.roles, name=_rank)
        self.leader_loop.start()
        print("\t> Leaderboard cog initialized.")

    #
    # Check to see if a user is an admin in the server
    #
    @staticmethod
    def is_admin(member: discord.Member):
        if member is None:
            return False
        return "Admin" in [r.name for r in member.roles]

    #
    # Go through a list of users who are supposed to have a certain rank, and sort that out
    #
    async def reassign_roles(self, rank_ids: list, role: discord.Role):
        c_ranks = await self.get_by_role(role)
        c_ranks_ids = [user.id for user in c_ranks]
        for uid in rank_ids:
            # Reassign user's role if they aren't already this rank
            if uid not in c_ranks_ids:
                user = self.server.get_member(uid)
                if user is not None and not self.is_admin(user) and not user.bot:
                    c_user_rank = self.get_user_rank(user.roles)
                    if c_user_rank is not None:
                        await user.remove_roles(c_user_rank)
                    await user.add_roles(role)
            else:
                c_ranks_ids.remove(uid)
        for uid in c_ranks_ids:
            # Remove this rank from users who no longer fall into it
            user = self.server.get_member(uid)
            if not self.is_admin(user) and not user.bot:
                c_user_rank = self.get_user_rank(user.roles)
                await user.remove_roles(c_user_rank)

    #
    # Get a list of users based on their current role in the server
    #
    async def get_by_role(self, role: discord.Role):
        users = list()
        for user in self.server.members:
            if role in [r for r in list(user.roles)]:
                users.append(user)
        return users

    #
    # Pull the user's current rank from their list of roles
    #
    def get_user_rank(self, roles: list):
        for role in roles:
            if role.name in self.rank_names:
                return role
        return None

    #
    # Loop for changing users' ranks based on their leaderboard position
    #
    @tasks.loop(hours=1)
    async def leader_loop(self):

        try:
            # Send leaderboard images to the channel
            self.stick_lb.make_leaderboard()
            with open(self.stick_lb_png, "rb") as f:
                await self.valid_channel.send(file=discord.File(f))
            rank_ids = await self.points_leaderboard()
            # Adjust roles according to rank
            num_ranks = len(rank_ids)
            if num_ranks >= 1:
                # assign elites
                print("\t\t> Assigning elites")
                e_role = discord.utils.get(self.server.roles, name="Elite")
                await self.reassign_roles(rank_ids[: self.elite_max], e_role)
            if num_ranks >= self.elite_max:
                # assign veterans
                print("\t\t> Assigning veterans")
                v_role = discord.utils.get(self.server.roles, name="Veteran")
                await self.reassign_roles(rank_ids[self.elite_max: self.veteran_max], v_role)
            if num_ranks >= self.veteran_max:
                # assign intermediates
                print("\t\t> Assigning intermediates")
                i_role = discord.utils.get(self.server.roles, name="Intermediate")
                await self.reassign_roles(rank_ids[self.veteran_max: self.intermediate_max], i_role)
            if num_ranks > self.intermediate_max:
                # assign beginners
                print("\t\t> Assigning beginners")
                b_role = discord.utils.get(self.server.roles, name="Beginner")
                await self.reassign_roles(rank_ids[self.intermediate_max:], b_role)
            print("\t\t> All roles assigned.")
        except KeyError:
            # Happens on the first round of start up
            pass
    #
    # Displays the points leaderboard in the leaderboard channel
    #
    async def points_leaderboard(self, send=True):
        in_order = self.get_points_leaderboard_df()
        max_len = 25 if len(in_order) > 25 else len(in_order)
        self.lb_printer.set_size(max_len)
        self.lb_printer.make_leaderboard(in_order)
        with open(self.points_lb_png, "rb") as f:
            leaderboard_file = discord.File(f)
        if send:
            await self.valid_channel.send(file=leaderboard_file)
        return in_order.index

    #
    # Sorts the points dataframe from the Gambler object in descending order
    #
    def get_points_leaderboard_df(self):
        gambler = self.bot.get_cog("GamblerCog")
        in_order = gambler.bet.points.sort_values(by="points", ascending=False)
        # Remove Admins and bot from leaderboard data
        in_order = in_order.drop([int(893151604272926721)])  # Bot id
        return in_order

    #
    # Displays the points leadersboard in the leaderboard channel
    #
    @commands.command(name="pointleaders",
                      aliases=["pl", "Pointleaders", "pointsleaders", "PointLeaders", "POINTLEADERS", "POINTSLEADERS"],
                      brief="Display the top users with the most points.",
                      description="""Sends a picture of the current leaderboard rankings based on total points for each user to
                                     the "leaderboard" channel""")
    async def point_leader_cmd(self, ctx):
        if ctx.channel != self.valid_channel:
            return
        await self.points_leaderboard()

    #
    # Displays the CryptoStykz leaderboard in the leaderboard channel
    #
    @commands.command(name="leaders",
                      aliases=["Leaders", "LEADERS", "lEADERS"],
                      brief="Display the top 5 Cryptostykz with the most wins",
                      description="""The bot will reply with a message containing the leaderboard with the top 5 highest ranked
                                     Cryptostykz with the most matches won""")
    async def leaderboard_cmd(self, ctx):
        print("fuk")
        if ctx.channel != self.valid_channel:
            return
        print("fek")
        self.stick_lb.make_leaderboard()
        with open(self.stick_lb_png, "rb") as f:
            image = discord.File(f)
            await ctx.send(file=image)

    #
    # Command for telling the user where they are on the leader board
    #
    @commands.command(name="myrank",
                      aliases=["mr", "MyRank", "Myrank", "MYRANK", "mYRANK", "mYrANK"],
                      brief="Sends a direct message to you with your current rank on the points leaderboard.",
                      description="""Sends you a direct message telling you where you currently are on the points leaderboard. 
                                     Works in any channel.""")
    async def my_points_cmd(self, ctx):
        user = ctx.author
        gambler_cog = self.bot.get_cog("GamblerCog")
        in_order = gambler_cog.bet.points.sort_values(by="points", ascending=False)
        in_order = in_order.drop([int(904834295556890636)])  # Ignore the CryptoStykz bot for the leaderboard
        ranking = in_order.index.get_loc(user.id)
        msg = f"You are currently rank **{ranking}** of {len(in_order)}"
        await user.send(msg)
