import discord
from discord.ext import commands, tasks
from LeaderboardCog import LeaderboardCog
from discord.errors import Forbidden
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded
import numpy as np


with open("key.txt", "r") as f:
    token = f.read()

print("Initializing server...")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
server = None
cogs = ["GamblerCog", "LeaderboardCog", "ArenaCog", "RewardsCog"]

for cog in cogs:
    bot.load_extension(cog)



async def notify_settings(member):
    global server
    msg = f"Welcome to the server {member.mention}! Please make sure you have \"Allow messages from server members\" enabled in your privacy settings to receive messages from the bot."
    general_channel = discord.utils.get(server.text_channels, name="general")
    await general_channel.send(msg)

@bot.event
async def on_ready():
    global server
    server = bot.guilds[0]
    g_cog = bot.get_cog("GamblerCog")
    ids = list()
    async for user in server.fetch_members(limit=50):
        #print(user.display_name, user.name, user.id)
        ids.append((user.id, user.display_name))
    #g_cog.bet.reset_points(ids)
    print("Server initialized.")
    main_loop.start()

@bot.event
async def on_member_join(member):
    uid = member.id
    print(uid, " Has joined the server as ", member.display_name)
    gambler_cog = bot.get_cog("GamblerCog")
    gambler_cog.bet.add_uid(uid, member.display_name)
    beginner_role = discord.utils.get(bot.guilds[0].roles, name="Beginner")
    await member.add_roles(beginner_role)
    print(gambler_cog.bet.points)
    # Send user a welcome message
    with open("Announcements/welcome.txt", "r") as f:
        content = f.read()
    try:
        await member.send(content)
    except Forbidden:
        print("========================")
        print("= Failure to send msg ==")
        print(member.display_name)
        print(member.id)
        print("------------------------")
        await notify_settings(member)

@bot.command(name="givepoints")
@commands.has_role("Admin")
async def give_points_cmd(ctx, user_mention, amount):
    admin = ctx.author
    if not user_mention or not amount:
        return
    if not len(ctx.message.mentions):
        await admin.send("User did not receive points: You must @ the user you wish to give points to")
        return
    user = ctx.message.mentions[0]
    try:
        _amount = int(amount)
    except ValueError:
        await admin.send("{0} did not receive points: Invalid amount".format(user.display_name))
        return
    if _amount < 1:
        await admin.send("You must give at least 1 point")
        return
    gambler = bot.get_cog("GamblerCog")
    gambler.bet.add_points(user.id, _amount)
    gambler.bet.save_csv()
    await user.send("You received {:,} points from {}".format(_amount, admin.display_name))


@bot.command(name="resetpoints")
@commands.has_role("Admin")
async def reset_points_cmd(ctx):
    global server
    admin = ctx.author
    ids = list()
    for user in server.members:
        ids.append((user.id, user.display_name))
    gambler = bot.get_cog("GamblerCog")
    gambler.bet.reset_points(ids)
    await admin.send("Leaderboard points have been reset")


@tasks.loop(seconds=35)
async def main_loop():
    mini_game_round = np.random.choice([False, True], p=[0.93, 0.07])
    if mini_game_round:
        mini_game_cog = np.random.choice(["BonusCog", "CoinflipCog", "GuessRarityCog"])
        try:
            bot.load_extension(mini_game_cog)
        except ExtensionAlreadyLoaded:
            pass
        cog = bot.get_cog(mini_game_cog)
        await cog.game_func()
        try:
            bot.unload_extension(mini_game_cog)
        except ExtensionNotLoaded:
            pass
    else:
        arena_cog = bot.get_cog("ArenaCog")
        await arena_cog.fight_func()

@bot.event
async def on_member_join(member):
    uid = member.id
    gambler_cog = bot.get_cog("GamblerCog")
    print(uid, " Has joined the server as ", member.display_name)
    gambler_cog.bet.add_uid(uid, member.display_name)
    beginner_role = discord.utils.get(bot.guilds[0].roles, name="Beginner")
    await member.add_roles(beginner_role)
    #print(bet.points)
    # Send user a welcome message
    with open("Announcements/welcome.txt", "r") as f:
        content = f.read()
    await member.send(content)


    



bot.run(token)
