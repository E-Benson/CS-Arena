import discord
from discord.ext import commands, tasks
from Gambler import Gambler


def setup(bot: commands.Bot):
    bot.add_cog(GamblerCog(bot))


class GamblerCog(commands.Cog):
    ratios = {
            "🌘": 0.25,
            "🌗": 0.5,
            "🌖": 0.75,
            "🌕": 1
            }
    max_queue_size = 100
    valid_channel = None
    valid_channel_name = "betting"

    def __init__(self, bot):
        self.bot = bot
        self.server = None
        self.bet = Gambler()
        self.bet_period = False
        self.s1_qb_msg = None
        self.s2_qb_msg = None
        self.s1 = None
        self.s2 = None

    #
    # Ensure that a user's input fits the CryptoStykz #xxx format
    #
    @staticmethod
    def clean_s_num(s_num):
        s_num = "".join([c for c in s_num if c.isdigit()])
        if s_num.find("#") < 0:
            s_num = "#{}".format(s_num)
        return s_num

    def begin_period(self):
        self.bet_period = True

    def end_period(self):
        self.bet_period = False

    def set_s1_msg(self, msg: discord.Message):
        self.s1_qb_msg = msg

    def set_s2_msg(self, msg: discord.Message):
        self.s2_qb_msg = msg

    def set_s1(self, s_num: str):
        self.s1 = s_num

    def set_s2(self, s_num: str):
        self.s2 = s_num

    #
    # Notify that this cog is active
    #
    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        print("\t> Gambler cog initialized")

    #
    # Handle the quick bets when users add a reaction to the quick bets message
    #
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return # Don't do anything when the bot adds a reaction
        if reaction.message.channel != self.valid_channel:
            return # Make sure the reaction was added in the same channel as the quick bets message
        if self.s1_qb_msg is None or self.s2_qb_msg is None:
            return # Make sure the quick bet message variables have been set
        if not self.bet_period:
            return # Don't do anything if the reaction wasn't added during the betting phase
        user_points = self.bet.get_points(user.id)
        s_num = None
        try:
            bet_amount = int(user_points * self.ratios[reaction.emoji])
        except KeyError:
            return # User reacted with unknown emoji
        if reaction.message.id == self.s1_qb_msg.id:
            s_num = self.s1
        elif reaction.message.id == self.s2_qb_msg.id:
            s_num = self.s2
        await self.place_bet(user, bet_amount, s_num)

    #
    # Command for placing a bet
    #
    @commands.command(name="bet",
                      aliases=["b", "BET", "bET", "Bet"],
                      brief="Places a bet for a given amount on the CryptoStykz # you provided.",
                      description="""Places a bet on the CryptoStykz # you provide for a specified amount of points. You can only
                                     bet with whole numbers, such as 1, 2, or 3, and NOT 1.1, 2.5, 3.2, etc. Only works in the 
                                     "betting" channel.
                                     !bet 2500 #194""")
    async def bet_cmd(self, ctx, _amount, s_num):
        if ctx.channel != self.valid_channel:
            return
        user = ctx.author
        await self.place_bet(user, _amount, s_num)

    #
    # Command for placing an all-in bet
    #
    @commands.command(name="allin",
                      aliases=["ALLIN", "aLLIN", "Allin"],
                      brief="Places a bet for all of your current points on a CryptoStykz' number in the next fight.",
                      description="""Places a bet for 100% of your current points on the CryptoStykz # you provided with the 
                                     command. You can only use this in the "betting" channel, and can only bet on CryptoStykz 
                                     that are in the next fight in queue.
                                     !allin #69""")
    async def allin_cmd(self, ctx, s_num):
        if s_num is None:
            return
        if ctx.channel != self.valid_channel:
            return
        user = ctx.author
        s_num = self.clean_s_num(s_num)
        points = self.bet.get_points(user.id)
        await self.bet_cmd(ctx, str(points), s_num)

    #
    # Command for a user to see how many points they currently have
    #
    @commands.command(name="mypoints",
                      aliases=["Mypoints", "MyPoints", "mp", "MYPOINTS", "mYPOINTS", "mYpOINTS"],
                      brief="Sends a private message to you with your current points total.",
                      description="""Sends a direct message to you telling you how many points you currently have. Works in any
                                     channel.""")
    async def points_cmd(self, ctx):
        user = ctx.author
        points = self.bet.get_points(user.id)
        msg = "You currently have {:,} points".format(points)
        await user.send(msg)


    #@commands.command(name="inspect")
    def get_rank(self, user: discord.Member):
        rank = self.bet.get_rank(user.id)
        return rank
    @commands.command(name="inspect")
    async def inspect_cmd(self, ctx, target):
        print(f"target: '{target}'")
        print(f"msg: '{ctx.message}")
        user = discord.utils.get(self.server.members, display_name=target)
        rank = self.bet.get_rank(user.id)
        points = self.bet.get_points(user.id)
        ctx.author.send(f"{user.display_name} currently has {points} at #{rank} on the leaderboard")

    #
    # Command to show off how many points a user has to the entire "fighting" channel
    #
    @commands.command(name="flex",
                      aliases=["Flex", "FLEX", "fLEX"],
                      brief="Show off your points to the other users.",
                      description="""Sends a message in the "betting" channel with your username and total points for everyone
                                     in the channel to see.""")
    async def flex_cmd(self, ctx):
        if ctx.channel != self.valid_channel:
            return
        user = ctx.author
        points = self.bet.get_points(user.id)
        msg = "{} has a whole {:,} points!".format(user.display_name, points)
        await self.valid_channel.send(msg)

    #
    # Adds a matchup to the fight queue
    #
    @commands.command(name="add", aliases=["ADD", "aDD", "Add"],
                      brief="Adds a pair of CryptoStykz NFTs to the fight queue.",
                      description="""Adds a pair of CryptoStykz NFTs to the end of the fight queue. If there are currently too
                                     many matchups already in the queue, you will have to try to add them again later.
                                     !add #130 #92""")
    async def add_cmd(self, ctx: commands.Context, s1: str, s2: str):
        if s1 is None or s2 is None:
            return
        if ctx.channel != self.valid_channel:
            return
        arena_cog = self.bot.get_cog("ArenaCog")
        s1 = self.clean_s_num(s1)
        s2 = self.clean_s_num(s2)
        if s1 == s2:
            await ctx.author.send("Match not added: Must add 2 different numbers to the fight queue")
            return
        if arena_cog.arena.q_len() > self.max_queue_size:
            await ctx.author.send("Match not added: There are already {} matches in the fight queue, please wait for the next fight to try again.")
            return
        if not arena_cog.arena.verify_stick(s1) or not arena_cog.arena.verify_stick(s2):
            await ctx.author.send("Match not added: Invalid CryptoStykz #")
            return
        if arena_cog.arena.in_q((s1, s2)):
            await ctx.author.send("Match not added: This pair of CryptoStykz is already in the fight queue.")
            return
        arena_cog.arena.add_fight(s1, s2)
        position = arena_cog.arena.fight_q.qsize()
        await ctx.send(f"Battle added! {position} in queue")

    #
    # Display the CryptoStykz #s for the upcoming fight
    #
    @commands.command(name="nextfight", aliases=["n", "next", "NEXT", "nEXT", "NEXTFIGHT", "nEXTFIGHT"],
                      brief="Sends a message in the \"fighting\" channel with the numbers for the CryptoStykz in the next fight.",
                      description="""Sends a message back with the numbers for the CryptoStykz in the next fight in queue. Only 
                                     works in the "betting" channel.""")
    async def next_fight_cmd(self, ctx: commands.Context):
        if ctx.channel != self.valid_channel:
            return
        arena_cog = self.bot.get_cog("ArenaCog")
        s1, s2 = arena_cog.arena.next_fight()
        if s1 is None or s2 is None:
            msg = "There are no fights currently in the queue"
        else:
            msg = f"**{s1}** vs **{s2}**"
        await ctx.send(msg)

    #
    # Display the specs for the 2 sticks in the upcoming match
    #
    @commands.command(name="nextspecs", aliases=["ns", "NEXTSPEC", "Nextspec", "NextSpec", "nEXTSPEC"],
                      brief="Shows the rarities for each property of each CryptoStykz NFT in the upcoming fight.",
                      description="""Sends a message in the "fighting" channel containing the rarity for each property of each
                                     CryptoStykz NFT in an upcoming fight. When the bot says "Place your bets", this command
                                     will show the specs for the sticks you will be betting on.""")
    async def next_specs_cmd(self, ctx: commands.Context):
        arena_cog = self.bot.get_cog("ArenaCog")
        ns1, ns2 = arena_cog.arena.next_fight()
        if not ns1 or not ns2:
            await ctx.send(
                "No fights are currently in the queue. Use the ``!add`` command to add your own matchup or a random one will be chosen.")
            return
        await ctx.send(f"Next up: **{ns1}** vs **{ns2}**")
        await ctx.send(arena_cog.specs(ns1))
        await ctx.send(arena_cog.specs(ns2))

    #
    # Shows up to the next 5 matchups in the fight queue
    #
    @commands.command(name="queue", aliases=["q", "Queue", "QUEUE", "qUEUE"],
                      brief="Shows up to the next 5 fights that are in the queue.",
                      description="""Sends a message back with the next matchups in the fight queue. It will show at most 5 matchups,
                                     but there may be more in the queue. Only works in the "betting" channel""")
    async def queue_cmd(self, ctx: commands.Context):
        if ctx.channel != self.valid_channel:
            return
        arena_cog = self.bot.get_cog("ArenaCog")
        msg = arena_cog.arena.to_string()
        await ctx.send(msg)

    #
    # Sends the specs of a CryptoStyk to a given channel
    #
    async def specs_cmd(self, ctx: commands.Context, s_num: str):
        if s_num is None:
            return
        if ctx.channel != self.valid_channel:
            return
        arena_cog = self.bot.get_cog("ArenaCog")
        s_num = self.clean_s_num(s_num)
        await ctx.send(arena_cog.specs(s_num))

    #
    # Adds a user's bet to the Gambler object
    #
    async def place_bet(self, user: discord.User, amount: int, s_num: str,):
        if amount is None or s_num is None:
            await user.send("Bet not placed: Error in bet command - Try placing your bet again or type '!help bet' for more information")
            return
        s_num = self.clean_s_num(s_num)
        if not self.bet_period:
            await user.send("Bet not placed: Placed bet outside of betting period.")
            return
        arena_cog = self.bot.get_cog("ArenaCog")
        if not arena_cog.arena.in_next(s_num):
            await user.send("Bet not placed: CryptoStykz # is not in the upcoming fight.")
            return
        if self.bet.bet_placed(user.id):
            await user.send("Bet not placed: You have already placed a bet on this fight.")
            return
        if isinstance(amount, str):
            amount = int("".join([c for c in amount if c.isdigit()]))
        points = self.bet.get_points(user.id)
        if amount > points:
            await user.send(f"Bet not placed: You have {points} in your wallet, but wagered {amount} points.")
            return
        if amount < 1:
            await user.send("Bet not placed: Amount must be more than 0 points")
            return
        self.bet.add_bet(user.id, user.display_name, s_num, amount)
        msg = "You bet **{:,}** points on **CryptoStykz {}**".format(amount, s_num)
        await user.send(msg)
