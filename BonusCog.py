import discord
from discord.ext import commands, tasks
import asyncio
from numpy import random


def setup(bot: commands.Bot):
    bot.add_cog(BonusCog(bot))


class BonusCog(commands.Cog):
    server = None
    valid_channel_name = "betting"
    valid_channel = None
    bonus_round = False
    bonus_msg = None
    bonus_ids = list()
    bonus_amount = 0
    banner_png = "banners/bonusround.png"

    def __init__(self, bot):
        self.bot = bot
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)

    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.guilds[0]
        self.valid_channel = discord.utils.get(self.server.text_channels, name=self.valid_channel_name)
        #self.game_loop.start()
        print("\t> Bonus cog initialized")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if not self.bonus_round:
            return
        if self.bonus_msg is None:
            return
        if reaction.message.id != self.bonus_msg.id:
            return
        self.bonus_ids.append(user.id)
        confirmation_msg = "You have been entered for the bonus raffle. Good luck!"
        await user.send(confirmation_msg)

    @tasks.loop(minutes=30)
    async def game_loop(self):
        delay = random.randint(1, 60, 1)
        # Start bonus round every 30 to 90 minutes
        await asyncio.sleep(delay * 60)
        await self.bonus_func()

    async def game_func(self):
        gambler = self.bot.get_cog("GamblerCog")
        await self.announce_bonus()
        # Wait for people to enter the round
        await asyncio.sleep(30)
        # End the loop if no one joined the bonus round
        if not len(self.bonus_ids):
            return
        # Choose a winner and give them points
        winner_id = self.choose_winner()
        await self.gift_user(winner_id)
        # End the bonus round
        gambler.bet.save_csv()
        self.end_bonus()

    async def announce_bonus(self):
        bonus_ranges = [(1000, 10000), (25000, 50000), (100000, 250000)]
        bonus_probs = [0.79, 0.2, 0.01]
        bonus_index = random.choice([0, 1, 2], p=bonus_probs)
        self.bonus_amount = random.randint(bonus_ranges[bonus_index][0], bonus_ranges[bonus_index][1])
        self.bonus_round = True
        with open("bonus.png", "rb") as f:
            bonus_img = discord.File(f)
        embed = discord.Embed(color=discord.Colour.gold(),
                              description="""Bonus round starting! Add any reaction to this message in the next 30 seconds to enter for a chance to win **{:,}** points!
                                             Good luck!""".format(self.bonus_amount))
        self.bonus_msg = await self.valid_channel.send(embed=embed, file=bonus_img)

    def choose_winner(self):
        return random.choice(self.bonus_ids)

    async def gift_user(self, uid):
        gambler = self.bot.get_cog("GamblerCog")
        winning_user = discord.utils.get(self.server.members, id=uid)
        gambler.bet.add_points(uid, self.bonus_amount)
        msg = "Congratulations {}! You won the bonus round for **{:,}** points!".format(winning_user.mention,
                                                                                        self.bonus_amount)
        await self.valid_channel.send(msg)
        msg = "Congratulations, you won the bonus round for **{:,}** points!".format(self.bonus_amount)
        await winning_user.send(msg)

    def end_bonus(self):
        self.bonus_round = False
        self.bonus_ids = list()
        self.bonus_msg = None
        self.bonus_amount = 0
