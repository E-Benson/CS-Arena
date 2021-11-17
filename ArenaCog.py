import discord
from discord.ext import commands, tasks
from Arena import Arena
import Stitch
from numpy import random
import asyncio


def setup(bot: commands.Bot):
    bot.add_cog(ArenaCog(bot))


class ArenaCog(commands.Cog):
    server = None
    valid_channel = None
    valid_channel_name = "dueling"
    bet_channel = None
    bet_channel_name = "betting"
    stick_img_path = "stick_images/{}.png"
    leaderboard = None

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.arena = Arena(["cryptostykz_v3.1.csv"])

    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        self.bet_channel = discord.utils.get(self.server.text_channels, name=self.bet_channel_name)
        self.leaderboard = self.bot.get_cog("LeaderboardCog").stick_lb
        #self.fight_loop.start()
        print("\t> Arena cog intialized")

    @staticmethod
    def clean_snum(s_num: str):
        s_num = "".join([c for c in s_num if c.isdigit()])
        if s_num.find("#") < 0:
            s_num = "#{}".format(s_num)
        return s_num

    @staticmethod
    async def add_reactions(msg: discord.Message, reactions: list):
        for r in reactions:
            await msg.add_reaction(r)

    #
    # Create the message body for the !specs command
    #
    def specs(self, s_num: str):
        s_num = self.clean_snum(s_num)
        if self.arena.verify_stick(s_num):
            stick = self.arena.get_stick(s_num)
            msg = f">>> **CryptoStykz {s_num}**\n"
            msg += f"Overall rarity: **{stick['rarity']}**\n"
            msg += f"Background: {stick['bg']}\n"
            msg += f"Body: {stick['body']}\n"
            msg += f"Miscellaneous: {stick['misc']}\n"
            msg += f"Hand: {stick['hand']}"
            return msg
        else:
            return f"Invalid stick number \"{s_num}\""
    #
    # Displays a CryptoStykz' image in the designated channel
    #
    async def _show_stick(self, ch, s_num: str):
        if s_num is None:
            return
        s_num = self.clean_snum(s_num)
        stick = self.arena.get_stick(s_num)
        stick_hash = stick["hash"]
        with open(self.stick_img_path.format(stick_hash), "rb") as f:
            image = discord.File(f)
            await ch.send(file=image)

    #
    # Creates the image with two CryptoStykz and their numbers at the bottom, and sends it to the betting channel
    #
    async def vs_screen(self, s1: str, s2: str):
        s1_hash = self.arena.get_stick(s1)["hash"]
        s2_hash = self.arena.get_stick(s2)["hash"]
        s1_path = self.stick_img_path.format(s1_hash)
        s2_path = self.stick_img_path.format(s2_hash)
        s1_name = f"CryptoStykz {s1}"
        s2_name = f"CryptoStykz {s2}"
        img = Stitch.vs_screen(s1_name, s1_path, s2_name, s2_path)
        img.save("vs_screen.png")
        with open("vs_screen.png", "rb") as f:
            _file = discord.File(f)
            await self.bet_channel.send(file=_file)

    async def announce_fight(self, gambler, s1, s2):
        gambler.set_s1(s1)
        gambler.set_s2(s2)
        msg = "Battle is about to begin! You have 30 seconds to place your bets!\n"
        # Begin betting period
        await self.bot.change_presence(activity=discord.Game(name=f"{s1} vs {s2}"))
        #await self.bet_channel.send(msg)
        gambler.begin_period()
        # Display sticks for upcoming fight
        msg += f"**CryptoStykz {s1}** ({self.arena.get_stick(s1)['rarity']}) vs **CryptoStykz {s2}** ({self.arena.get_stick(s2)['rarity']})"
        embed = discord.Embed(color=discord.Colour.gold(),
                              description=msg)
        await self.bet_channel.send(embed=embed)
        await self.vs_screen(s1, s2)
        # Place quick bets
        await self.bet_channel.send(embed=discord.Embed(color=discord.Colour.gold(), description=
            "Quick bets: (🌘 25%)   (🌗 50%)   (🌖 75%)   (🌕 100%)\n*Wait for the bot to finishing reacting before adding your own.*"))
        msg = f">>> Quick bets for **{s1}**"
        s1_quick_bets_msg = await self.bet_channel.send(msg)
        gambler.set_s1_msg(s1_quick_bets_msg)
        await self.add_reactions(s1_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])
        msg = f">>> Quick bets for **{s2}**"
        s2_quick_bets_msg = await self.bet_channel.send(msg)
        gambler.set_s2_msg(s2_quick_bets_msg)
        await self.add_reactions(s2_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])

    @staticmethod
    def end_bet_period(gambler):
        gambler.end_period()
        gambler.set_s1_msg(None)
        gambler.set_s2_msg(None)

    async def display_payout_ratio(self, gambler, s1, s2):
        s1_pool = gambler.bet.get_pool(s1)
        s2_pool = gambler.bet.get_pool(s2)
        msg = "Betting period has ended, **bets are final!**"
        if not s1_pool or not s2_pool:
            msg += "\nPayouts are at **{} : {}** odds".format(1, 1)
        elif s1_pool > s2_pool:
            # ratio = round(s1_pool / s2_pool, 1)# s2 s1
            ratio = gambler.bet.get_ratio(s2_pool, s1_pool)
            msg += "\nPayouts are at **{} : {}** odds".format(ratio, 1)
        else:
            # ratio = round(s2_pool / s1_pool, 1)
            ratio = gambler.bet.get_ratio(s1_pool, s2_pool)
            msg = "Payouts are at **{} : {}** odds".format(1, ratio)
        msg += "\n**{}**: {:,} points   -   **{}**: {:,} points".format(s1, int(s1_pool), s2, int(s2_pool))
        await self.bet_channel.send(embed=discord.Embed(color=discord.Colour.gold(),
                                                        description=msg))

    async def fight_round(self, gambler, s1, s2):
        rounds = self.arena.do_fight()
        match_winner = self.arena.match_winner(rounds)
        msg = ""
        # Add each round to the print out message
        for _round, winner in enumerate(rounds):
            msg += f"Round {_round + 1} goes to {winner}\n"
        msg += f"**{match_winner} won the match!**"
        # Update arena leaderboard
        self.leaderboard.update_leaderboard(rounds, [s1, s2])
        await self.bet_channel.send(embed=discord.Embed(color=discord.Colour.gold(),
                                                        description=msg))
        # Show winner image
        await self._show_stick(self.bet_channel, match_winner)
        return gambler.bet.declare_winner(match_winner)

    async def notify_players(self, gambler, betters):
        for uid in betters:
            points = gambler.bet.get_points(uid)
            user = discord.utils.get(self.server.members, id=uid)
            msg = "Points after bet: **{:,}**".format(points)
            await user.send(msg)

    @tasks.loop(seconds=30)
    async def fight_loop(self):
        await self.fight_func()

    async def fight_func(self):
        s1, s2 = self.arena.next_fight()
        if s1 is None or s2 is None:
            # Add a fight to the queue if it's empty
            s1, s2 = self.arena.random_fighers()
            self.arena.add_fight(s1, s2)
        else:
            gambler = self.bot.get_cog("GamblerCog")
            await self.announce_fight(gambler, s1, s2)
            # Wait for bets to be placed
            await asyncio.sleep(30)
            #msg = "Betting period has ended, bets are final!"
            #await self.bet_channel.send(msg)
            # End of bet period
            self.end_bet_period(gambler)
            # Display payouts
            await self.display_payout_ratio(gambler, s1, s2)
            # Small delay for delaying things...
            await asyncio.sleep(2)
            # Fight the next sticks in the arena
            betters = await self.fight_round(gambler, s1, s2)
            await self.notify_players(gambler, betters)
            # Update status to show that no fight is happening
            await self.bot.change_presence(activity=discord.Game(name=f"Waiting for next match"))
    """
    #
    # Loop for doing a match every 30 seconds
    #
    @tasks.loop(seconds=30)
    async def fight_loop(self):
        s1, s2 = self.arena.next_fight()
        if s1 is None or s2 is None:
            # Add a fight to the queue if it's empty
            s1, s2 = self.arena.random_fighers()
            self.arena.add_fight(s1, s2)
        else:
            gambler = self.bot.get_cog("GamblerCog")
            gambler.set_s1(s1)
            gambler.set_s2(s2)
            msg = "Battle is about to begin! You have 30 seconds to place your bets!\n"
            # Begin betting period
            await self.bot.change_presence(activity=discord.Game(name=f"{s1} vs {s2}"))
            await self.bet_channel.send(msg)
            gambler.begin_period()
            # Display sticks for upcoming fight
            msg = f"**CryptoStykz {s1}** ({self.arena.get_stick(s1)['rarity']}) vs **CryptoStykz {s2}** ({self.arena.get_stick(s2)['rarity']})"
            await self.bet_channel.send(msg)
            await self.vs_screen(s1, s2)
            # Place quick bets
            await self.bet_channel.send("Quick bets: (🌘 25%)   (🌗 50%)   (🌖 75%)   (🌕 100%)\n*Wait for the bot to finishing reacting before adding your own.*")
            msg = f">>> Quick bets for **{s1}**"
            s1_quick_bets_msg = await self.bet_channel.send(msg)
            gambler.set_s1_msg(s1_quick_bets_msg)
            await self.add_reactions(s1_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])
            msg = f">>> Quick bets for **{s2}**"
            s2_quick_bets_msg = await self.bet_channel.send(msg)
            gambler.set_s2_msg(s2_quick_bets_msg)
            await self.add_reactions(s2_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])
            # Wait for bets to be placed
            await asyncio.sleep(30)
            msg = "Betting period has ended, bets are final!"
            await self.bet_channel.send(msg)
            # End of bet period
            gambler.end_period()
            gambler.set_s1_msg(None)
            gambler.set_s2_msg(None)
            # Display payouts
            s1_pool = gambler.bet.get_pool(s1)
            s2_pool = gambler.bet.get_pool(s2)
            if not s1_pool or not s2_pool:
                msg = "Payouts are at **{} : {}** odds".format(1, 1)
            elif s1_pool > s2_pool:
                #ratio = round(s1_pool / s2_pool, 1)# s2 s1
                ratio = gambler.bet.get_ratio(s2_pool, s1_pool)
                msg = "Payouts are at **{} : {}** odds".format(ratio, 1)
            else:
                #ratio = round(s2_pool / s1_pool, 1)
                ratio = gambler.bet.get_ratio(s1_pool, s2_pool)
                msg = "Payouts are at **{} : {}** odds".format(1, ratio)
            msg += "\n**{}**: {:,} points   -   **{}**: {:,} points".format(s1, int(s1_pool), s2, int(s2_pool))
            await self.bet_channel.send(msg)
            # Small delay for delaying things...
            await asyncio.sleep(2)
            # Fight the next sticks in the arena
            rounds = self.arena.do_fight()
            match_winner = self.arena.match_winner(rounds)
            msg = ">>> "
            # Add each round to the print out message
            for _round, winner in enumerate(rounds):
                msg += f"Round {_round + 1} goes to {winner}\n"
            msg += f"**{match_winner} won the match!**"
            # Update arena leaderboard
            self.leaderboard.update_leaderboard(rounds, [s1, s2])
            await self.bet_channel.send(msg)
            betters = gambler.bet.declare_winner(match_winner)
            # Show winner image
            await self._show_stick(self.bet_channel, match_winner)
            for uid in betters:
                points = gambler.bet.get_points(uid)
                user = discord.utils.get(self.server.members, id=uid)
                msg = "Points after bet: **{:,}**".format(points)
                await user.send(msg)
            # Update status to show that no fight is happening
            await self.bot.change_presence(activity=discord.Game(name=f"Waiting for next match"))
    """

    #
    # Displays the specs for a given CryptoStykz #
    #
    @commands.command(name="specs", aliases=["Specs", "SPECS", "sPECS", "spec", "Spec", "SPEC", "sPEC"],
                      brief="Display the rarity of each component of a CryptoStyk",
                      description="""Sends a message back to you containing the rarity of each component of a CryptoStyk given its number
                                     !specs #119""")
    async def specs_cmd(self, ctx: commands.Context, s_num: str):
        if s_num is None:
            return
        if ctx.channel != self.valid_channel:
            return
        s_num = self.clean_snum(s_num)
        await ctx.send(self.specs(s_num))

    #
    # Shows the image for a given CryptoStykz #
    #
    @commands.command(name="display", aliases=["Display", "DISPLAY", "dISPLAY"],
                      brief="Shows the image for the CryptoStykz # you provided",
                      description="""Sends a message to the channel you called the command from. Only works in "betting" and 
                                     "dueling" channels.
                                     !display #560""")
    async def display_stick(self, ctx: commands.Context, s_num: str):
        if s_num is None:
            return
        if ctx.channel != self.valid_channel and ctx.channel != self.bet_channel:
            return
        s_num = self.clean_snum(s_num)
        stick = self.arena.get_stick(s_num)
        stick_hash = stick["hash"]
        with open(self.stick_img_path.format(stick_hash), "rb") as f:
            image = discord.File(f)
            await ctx.send(file=image)

    #
    # Runs the match between 2 CryptoStykz to determine a winner
    #
    @commands.command(name="fight", aliases=["Fight", "FIGHT", "fIGHT"],
                      brief="Fights 2 CryptoStkz against eachother",
                      description="To fight #175 against #300 use the command:\n!fight #175 #300")
    async def fight_cmd(self, ctx: commands.Context, s1: str, s2: str = None):
        if s1 is None:
            return

        s1 = self.clean_snum(s1)
        if s2 is not None:
            s2 = self.clean_snum(s2)
        valid = False
        msg = ""
        if ctx.channel != self.valid_channel:
            return
        if s2 is None:
            s2 = s1
            while s1 == s2:
                s2 = "#{}".format(random.randint(1, 999))
        if self.arena.verify_stick(s1):
            if self.arena.verify_stick(s2):
                valid = True
            else:
                msg += f"Invalid stick number: \"{s2}\""
        else:
            msg += f"Invalid stick number: \"{s1}\""

        if valid:
            msg = f">>> **{s1} vs {s2}**\n"
            s1_r = self.arena.get_stick(s1)["rarity"]
            s2_r = self.arena.get_stick(s2)["rarity"]
            if self.arena.get_stick(s1).hash == self.arena.get_stick(s2).hash:
                await ctx.send("Please use 2 different CryptoStykz #'s")
                return
            msg += f"{s1} has a rarity of **{s1_r}** and {s2} has a rarity of **{s2_r}**\n"
            rounds = self.arena.fight_sticks(s1, s2)
            match_winner = self.arena.match_winner(rounds)
            for _round, winner in enumerate(rounds):
                msg += f"Round {_round + 1} goes to {winner}\n"
            msg += f"{match_winner} won the match!"
            self.leaderboard.update_leaderboard(rounds, [s1, s2])
            await ctx.send(msg)
            await self.display_stick(ctx, match_winner)
        else:
            await ctx.send(msg)

    #
    # Chooses a random pair of CryptoStykz to fight
    #
    @commands.command(name="rfight", aliases=["rf", "RFIGHT", "Rfight", "rFIGHT"],
                      brief="Fight two random CryptoStykz",
                      description="""Randomly select two different CryptoStykz to fight each other""")
    async def rfight_cmd(self, ctx: commands.Context):
        if ctx.channel != self.valid_channel:
            return
        fighters = self.arena.random_fighers()
        await self.fight_cmd(ctx, fighters[0], fighters[1])

