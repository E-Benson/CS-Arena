import discord
from discord.ext import commands, tasks
import asyncio
from numpy import random
import numpy as np
import pandas as pd


def setup(bot: commands.Bot):
    bot.add_cog(GuessRarityCog(bot))


class GuessRarityCog(commands.Cog):

    server = None
    valid_channel_name = "betting"
    valid_channel = None
    bonus_round = False
    banner_png = "banners/guessrarity.png"
    snum = None
    _hash = None
    rarity = 0
    prize = 0

    def __init__(self, bot):
        self.bot = bot
        self.server = self.bot.guilds[0]
        self.guesses = self.init_guesses()
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)

    @staticmethod
    def choose_prize():
        prize_range = [(3000, 5000), (10000, 20000), (50000, 100000)]
        range_index = np.random.choice([0, 1, 2], p=[0.65, 0.3, 0.05])
        prize = np.random.randint(prize_range[range_index][0], prize_range[range_index][1])
        return prize

    def init_guesses(self):
        df = pd.DataFrame(columns=["uid", "name", "guess"])
        df = df.set_index("uid")
        return df

    def add_guess(self, user, guess):
        self.guesses.loc[user.id, "guess"] = np.cast[np.float64](guess)
        self.guesses.loc[user.id, "name"] = user.display_name

    def has_guessed(self, user):
        try:
            _ = self.guesses.index.get_loc(user.id)
            return True
        except KeyError:
            return False

    def choose_stick(self):
        arena_cog = self.bot.get_cog("ArenaCog")
        stick_nums = list(arena_cog.arena.stick_df.index)
        stick = np.random.choice(stick_nums)
        self.snum = stick.split(" ")[-1]
        self._hash = arena_cog.arena.stick_df.loc[stick, "hash"]
        self.rarity = arena_cog.arena.stick_df.loc[stick, "rarity"].astype(np.float64)

    async def announce_game(self):
        self.prize = self.choose_prize()
        # Send banner and into message
        embed = discord.Embed(color=discord.Colour.gold(),
                              description="""**Guess the rarity** is starting for **{:,}** points!
                                             You'll have 30 seconds to take a guess, good luck!
                                             Use the ``!guess`` command to place your guess. (``!guess 0.921``)"""
                                          .format(self.prize))
        with open(self.banner_png, "rb") as f:
            img = discord.File(f)
        await self.valid_channel.send(file=img, embed=embed)
        await asyncio.sleep(3)
        # Send CryptoStykz image
        self.choose_stick()
        path = "stick_images/{}.png".format(self._hash)
        with open(path, "rb") as f:
            img = discord.File(f)
        embed = discord.Embed(color=discord.Colour.gold(),
                              description="What is the **overall rarity** of this CryptoStykz NFT?")
        self.bonus_round = True
        await self.valid_channel.send(file=img, embed=embed)

    def find_winner(self):
        self.guesses.loc[:, "diff"] = self.guesses["guess"] - self.rarity
        self.guesses.loc[:, "diff"] = self.guesses["diff"].apply(abs)
        best_diff = self.guesses["diff"].min()
        best_guess = self.guesses["diff"] == best_diff
        return self.guesses[best_guess]

    async def notify_winner(self, user: discord.User):
        msg = "Congratulation! You won the Guess the Rarity minigame for **{:,}** points!".format(self.prize)
        gambler_cog = self.bot.get_cog("GamblerCog")
        gambler_cog.bet.add_points(user.id, self.prize)
        await user.send(msg)

    async def announce_winners(self, winners, payout):
        msg = f"The correct rarity was **{self.rarity}**"
        if len(winners) > 1:
            msg += f"\nCongratulations to these winners!"
            for i, winner in winners.itterrows():
                user = discord.utils.get(self.server.members, id=winner.name)
                await self.notify_winner(user)
                msg += "\n**{}** guessed **{:0.3f}**, and was only {:0.3f} away!".format(winner['name'],
                                                                                         winner['guess'],
                                                                                         winner['diff'])
        else:
            winner = winners.iloc[0]
            user = discord.utils.get(self.server.members, id=winner.name)
            await self.notify_winner(user)
            msg += "\nCongratulations to **{}**! Who guessed **{:0.3f}** and was only {:0.2f} away!".format(winner['name'],
                                                                                                            winner['guess'],
                                                                                                            winner['diff'])
        embed = discord.Embed(color=discord.Colour.gold(),
                              description=msg)
        await self.valid_channel.send(embed=embed)

    def end_game(self):
        self.rarity = 0
        self.snum = None
        self._hash = None
        self.guesses = self.init_guesses()

    @tasks.loop(seconds=90)
    async def game_loop(self):
        await self.game_func()

    async def game_func(self):
        await self.announce_game()
        await asyncio.sleep(30)
        self.bonus_round = False
        if not len(self.guesses):
            return
        winners = self.find_winner()
        await self.announce_winners(winners, 0)
        self.end_game()


    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        #self.game_loop.start()
        print("\t> Guess the Rarity cog initialized")


    @commands.command(name="guess")
    async def guess_cmd(self, ctx, guess):
        user = ctx.author
        #await self.announce_game()
        if not self.bonus_round:
            await user.send("Guess not placed: You can only place a guess during the guessing phase.")
            return
        if not guess:
            await user.send("Guess not placed: You must guess a rarity number (example: ``!guess 0.921```")
            return
        if self.has_guessed(user):
            await user.send("Guess not placed: You have already guessed a rarity.")
            #return
        try:
            _guess = np.cast[np.float64](guess)
        except ValueError:
            await user.send("Guess not placed: Could not find a number")
            return
        self.add_guess(user, guess)
        await user.send(f"Your guess was placed for **{guess}**")
        #self.choose_stick()
        #self.find_winner()
