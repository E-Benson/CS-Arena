import discord
from discord.ext import commands, tasks
import asyncio
from numpy import random
import numpy as np
import pandas as pd


def setup(bot: commands.Bot):
    bot.add_cog(CoinflipCog(bot))


class CoinflipCog(commands.Cog):
    ratios = {
        "🌘": 0.25,
        "🌗": 0.5,
        "🌖": 0.75,
        "🌕": 1
    }
    server = None
    valid_channel_name = "betting"
    valid_channel = None
    bonus_round = False
    red_msg = None
    yellow_msg = None
    banner_png = "banners/coinflip.png"

    def __init__(self, bot):
        self.bot = bot
        self.bets = self.init_bets()
        self.ratio = 0
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)

    @staticmethod
    def init_bets():
        df = pd.DataFrame(columns=["uid", "name", "amount", "color"])
        df = df.set_index("uid")
        return df

    @staticmethod
    def choose_ratio():
        bonus_ratios = [2.2, 2.5, 3, 5, 10]
        bonus_probs = [0.65, 0.20, 0.10, 0.04, 0.01]
        return random.choice(bonus_ratios, p=bonus_probs)

    @staticmethod
    def flip_coin():
        return random.choice(["red", "yellow"], p=[0.5, 0.5])

    @staticmethod
    async def add_reactions(msg: discord.Message, reactions: list):
        for r in reactions:
            await msg.add_reaction(r)

    def add_bet(self, user, amount, color):
        self.bets.loc[user.id, "name"] = user.display_name
        self.bets.loc[user.id, "amount"] = np.cast[np.uint64](amount)
        self.bets.loc[user.id, "color"] = color
        print(self.bets)

    async def announce_flip(self):
        self.ratio = self.choose_ratio()
        embed = discord.Embed(color=discord.Colour.gold(),
                              description=f""">>> Coinflip for a **{self.ratio}x** payout!
                                              Use the ``!flip`` command to bet on red or yellow! (``!flip 1000 red``)
                                              Quick bets: (🌘 25%)   (🌗 50%)   (🌖 75%)   (🌕 100%)
                                              *Wait for the bot to finishing reacting before adding your own.*""")
        with open(self.banner_png, "rb") as f:
            banner_img = discord.File(f)
            self.bonus_round = True
        # Send banner and message about event in valid channel
        await self.valid_channel.send(file=banner_img, embed=embed)
        self.red_msg = await self.valid_channel.send("Quick bets for: :red_circle: :red_circle: :red_circle: :red_circle: :red_circle: ")
        await self.add_reactions(self.red_msg, ["🌘", "🌗", "🌖", "🌕"])
        self.yellow_msg = await self.valid_channel.send("Quick bets for: :yellow_circle: :yellow_circle: :yellow_circle: :yellow_circle: :yellow_circle: ")
        await self.add_reactions(self.yellow_msg, ["🌘", "🌗", "🌖", "🌕"])

    async def announce_result(self, clr):
        emoji = f":{clr}_circle:"
        msg = "The winning color is: {0} {0} {0} {0} {0}".format(emoji)
        embed = discord.Embed(color=discord.Colour.gold(),
                              description=msg)
        await self.valid_channel.send(embed=embed)

    async def update_winners(self, winners: pd.DataFrame):
        gambler_cog = self.bot.get_cog("GamblerCog")
        for i, bet in winners.iterrows():
            inc = np.cast[np.uint64](bet["amount"] * self.ratio)
            user = discord.utils.get(self.server.members, id=bet.name)
            gambler_cog.bet.add_points(user.id, inc)
            points = gambler_cog.bet.get_points(user.id)
            await user.send(f"You won **{inc}** points on the coinflip!\nCurrent points: **{points}**")

    async def update_losers(self, losers: pd.DataFrame):
        gambler_cog = self.bot.get_cog("GamblerCog")
        for i, bet in losers.iterrows():
            user = discord.utils.get(self.server.members, id=bet.name)
            gambler_cog.bet.sub_points(user.id, bet["amount"])
            points = gambler_cog.bet.get_points(user.id)
            await user.send(f"You lost **{bet['amount']}** points on the coinflip!\nCurrent points: **{points}**")

    def end_flip(self):
        self.bets = self.init_bets()
        self.bonus_round = False
        self.red_msg = None
        self.yellow_msg = None
        self.ratio = 0

    @commands.Cog.listener()
    async def on_ready(self):
        #self.server = self.bot.guilds[0]
        #self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        #self.game_loop.start()
        print("\t> Coinflip cog initialized")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return  # Don't do anything when the bot adds a reaction
        if reaction.message.channel != self.valid_channel:
            return  # Make sure the reaction was added in the same channel as the quick bets message
        if self.red_msg is None or self.yellow_msg is None:
            return  # Make sure the quick bet message variables have been set
        if not self.bonus_round:
            return  # Don't do anything if the reaction wasn't added during the betting phase
        color = None
        if reaction.message == self.red_msg:
            color = "red"
        elif reaction.message == self.yellow_msg:
            color = "yellow"
        if color is None:
            return
        gambler_cog = self.bot.get_cog("GamblerCog")
        user_points = gambler_cog.bet.get_points(user.id)
        try:
            bet_amount = int(user_points * self.ratios[reaction.emoji])
        except KeyError:
            return  # User reacted with unknown emoji
        await self.place_flip_bet(user, bet_amount, color)

    @tasks.loop(seconds=90)
    async def game_loop(self):
        await self.game_func()

    async def game_func(self):
        await self.announce_flip()
        # Wait for users to place their bets
        await asyncio.sleep(30)
        winning_color = self.flip_coin()
        _winners = self.bets["color"].to_numpy() == winning_color
        _losers = self.bets["color"] != winning_color
        await self.announce_result(winning_color)
        await self.update_winners(self.bets[_winners])
        await self.update_losers(self.bets[_losers])
        self.end_flip()

    @commands.command(name="flip")
    async def flip_cmd(self, ctx, amount, color):
        user = ctx.author
        await self.place_flip_bet(user, amount, color)

    async def place_flip_bet(self, user, amount, color):
        if not amount or not color:
            await user.send("Error in flip command: Try using the command again or use ``!help flip`` for more information.")
            return
        if not self.bonus_round:
            await user.send("Bet not placed: You can only use this command during a coinflip round.")
            return
        if isinstance(amount, str):
            if len([c for c in amount if c.isalpha()]):
                await user.send("Invalid amount: you must only use numbers to bet points")
                return
        try:
            _ = self.bets.index.get_loc(user.id)
            await user.send("Bet not placed: You have already placed a bet for this coinflip!")
            return
        except KeyError:
            pass
        try:
            amount = int(amount)
        except ValueError:
            await user.send("Invalid amount: could not determine your amount, use ``!help flip`` for more information")
            return
        gambler_cog = self.bot.get_cog("GamblerCog")
        points = gambler_cog.bet.get_points(user.id)
        if amount > points:
            await user.send("Invalid amount: You can't bet more points than you have")
            return
        if color == "r": color = "red"
        if color == "y": color = "yellow"
        if color != "red" and color != "yellow":
            await user.send("Invalid color: You must use 'red' or 'r' to bet on red, and 'yellow' or 'y' to be on yellow")
            return
        self.add_bet(user, amount, color)
        await user.send("You bet **{:,}** on **{}**".format(amount, color))

