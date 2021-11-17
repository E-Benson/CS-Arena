import discord
from discord.ext import commands, tasks
from Gambler import Gambler
import pandas as pd
import numpy as np


def setup(bot: commands.Bot):
    bot.add_cog(RewardsCog(bot))


class RewardsCog(commands.Cog):
    valid_channel = None
    valid_channel_name = "betting"
    wallet_csv = "wallet_list.csv"
    winner_csv = "winners.csv"

    def __init__(self, bot):
        self.bot = bot
        self.server = None
        self.wallets = self.init_wallets()
        self.winners = self.init_winners()
        print(self.wallets)

    def init_wallets(self):
        try:
            df = pd.read_csv(self.wallet_csv, dtype={"uid": np.uint64, "name": str, "wallet": str})
        except FileNotFoundError:
            df = pd.DataFrame(columns=["uid", "name", "wallet"])
        df = df.set_index("uid")
        return df

    def init_winners(self):
        try:
            df = pd.read_csv(self.winner_csv, dtype={"uid": np.uint64, "name": str, "points": np.uint64})
            df = df.set_index("uid")
        except FileNotFoundError:
            df = self.reset_winners()
        return df

    def reset_winners(self):
        return pd.DataFrame(columns=["uid", "name", "points"]).set_index("uid")

    def add_winner(self, user):
        gambler_cog = self.bot.get_cog("GamblerCog")
        points = gambler_cog.bet.get_points(user.id)
        self.winners.loc[user.id, "name"] = user.display_name
        self.winners.loc[user.id, "points"] = points

    def get_wallet(self, user):
        try:
            return self.wallets.loc[user.id, "wallet"]
        except KeyError:
            return None

    async def add_wallet(self, user: discord.User, address: str):
        if self.get_wallet(user) is not None:
            self.wallets.loc[user.id, "wallet"] = address
            await user.send(f"Your wallet address has been changed to: {address}")
        else:
            self.wallets.loc[user.id, "wallet"] = address
            self.wallets.loc[user.id, "name"] = user.display_name
            await user.send(f"Your wallet has been set to: {address}")

    @commands.command(name="wallet")
    async def wallet_cmd(self, ctx: commands.Context, wallet: str):
        user = ctx.author
        if len(wallet) != 42:
            user.send(
                "Wallet not added: incorrect length.\nexample:``!newwallet 0xC86719E8Cd209dEB52714A88C7Fa9D1E8E188a04``")
            return
        if not wallet.startswith("0x") and not wallet.startswith("0X"):
            user.send(
                "Wallet not added: make sure it starts with \"0x\"\nexample: ``!newwallet 0xC86719E8Cd209dEB52714A88C7Fa9D1E8E188a04``")
            return
        await self.add_wallet(user, wallet)
        self.wallets.to_csv(self.wallet_csv)

    #@commands.has_role("Admin")
    @commands.command(name="newwinners")
    async def weekly_winner_cmd(self, ctx):
        admin = ctx.author
        if not len(ctx.message.mentions):
            await admin.send("You must @ the user you want to announce as the winner")
            return
        for user in ctx.message.mentions:
            address = self.get_wallet(user)
            if address is None:
                await admin.send(f">>> **WARNING**: This user ({user.display_name}) does not have a wallet set up.")
            else:
                await admin.send(f">>> User: **{user.display_name}**\naddress: **{address}**")
            self.add_winner(user)
        print(self.winners)

    @commands.command(name="newweek")
    async def new_week_cmd(self, ctx):
        self.winners = self.reset_winners()
        await ctx.author.send("Weekly winners have been reset.")
