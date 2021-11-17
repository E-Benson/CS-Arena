import discord
#from discord_components import Button, ButtonStyle, DiscordComponents, Interaction
from discord.ext import commands, tasks
from Leaderboard import Leaderboard
from PointsLeaderBoard import LeaderboardPrinter
from Arena import Arena
from numpy import random
import asyncio
from Gambler import Gambler
import os
import Stitch


with open("key.txt", "r") as f:
    token = f.read()


def init_channels():
    _channels = dict()
    for ch in bot.guilds[0].text_channels:
        _channels[ch.name] = ch
    return _channels


def snum2num(snum):
    nums = "".join([c for c in snum if c.isdigit()])
    return int(nums)


def get_member_ids(guild):
    ids = list()
    for user in guild.fetch_members(limit=150):
        ids.append(user.id)
    return ids


def clean_snum(snum):
    snum = "".join([c for c in snum if c.isdigit()])
    if snum.find("#") < 0:
        snum = "#{}".format(snum)
    return snum


def set_global_sticks(s1, s2):
    global gs1, gs2
    gs1 = s1
    gs2 = s2


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
server = None

stick_csv_path = "cryptostykz_v3.1.csv"
stick_img_path = "stick_images/{}.png"
client = discord.Client()
leaderboard = Leaderboard()
point_leaderboard = LeaderboardPrinter(leaderboard_size=25)
point_leaderboard_png = "PointsLeaderboard.png"
arena = Arena(["cryptostykz_v3.1.csv"])
channels = {}

bet_period = False
bet = Gambler()
s1_quick_bets_msg = None
gs1 = None
s2_quick_bets_msg = None
gs2 = None

bonus_round = False
bonus_msg = None
bonus_ids = list()

async def announce():
    with open("Announcements/rules.txt", "r") as f:
        rules = f.read()

    for channel in bot.guilds[0].text_channels:
        if channel.name == "faq":
            for _file in os.scandir("announcements/faq/"):
                with open(_file, "r") as f:
                    embed = discord.Embed()
                    content = f.read()
                    embed.description = content
                    await channel.send(embed=embed)
        if channel.name == "commands":
            for _file in os.scandir("announcements/commands/"):
                with open(_file, "r") as f:
                    embed = discord.Embed()
                    content = f.read()
                    embed.description = content
                    await channel.send(embed=embed)
        if channel.name == "rules":
            await channel.send(rules)


@bot.event
async def on_ready():
    global channels, server
    print(f"{bot.user} has connected to the server.")
    server = bot.guilds[0]
    #print(server.member_count)
    ids = list()
    async for user in server.fetch_members(limit=50):
        print(user.display_name, user.name,  user.id)
        ids.append((user.id, user.display_name))
    channels = init_channels()
    #bet.reset_points(ids)
    await announce()
    print(bet.points)

    role = discord.utils.get(server.roles, name="Elite")
    print(role)


def is_admin(member):
    if member is None:
        return False
    return "Admin" in [r.name for r in member.roles]

@bot.event
async def on_reaction_add(reaction, user):
    global gs1, gs2, bonus_msg
    ratios = {
        "🌘": 0.25,
        "🌗": 0.5,
        "🌖": 0.75,
        "🌕": 1
    }
    if user.bot:
        return
    if reaction.message.channel.id != channels["fighting"].id:
        return
    points = bet.get_points(user.id)
    # Handle quick bets
    if s1_quick_bets_msg is not None and s2_quick_bets_msg is not None:
        try:
            amount = int(points * ratios[reaction.emoji])
        except KeyError:
            return
        snum = None
        if reaction.message.id == s1_quick_bets_msg.id:
            snum = gs1
        elif reaction.message.id == s2_quick_bets_msg.id:
            snum = gs2
        if snum and amount > 0:
            await place_bet(user, amount, snum)
    # Handle bonus rounds
    if bonus_round:
        print("Bonus round entry attempted")
        if bonus_msg is not None:
            print("Checking for correct msg id")
            if reaction.message.id == bonus_msg.id:
                bonus_ids.append(user.id)
                print(bonus_ids)
                confirmation_msg = "You have entered the bonus round. Good luck!"
                await user.send(confirmation_msg)

@bot.event
async def on_member_join(member):
    uid = member.id
    print(uid, " Has joined the server as ", member.display_name)
    bet.add_uid(uid, member.display_name)
    beginner_role = discord.utils.get(bot.guilds[0].roles, name="Beginner")
    await member.add_roles(beginner_role)
    print(bet.points)
    # Send user a welcome message
    with open("Announcements/welcome.txt", "r") as f:
        content = f.read()
    await member.send(content)



async def vs_screen(ch, s1, s2):
    s1_hash = arena.get_stick(s1)["hash"]
    s2_hash = arena.get_stick(s2)["hash"]
    s1_path = stick_img_path.format(s1_hash)
    s2_path = stick_img_path.format(s2_hash)
    s1_name = f"CryptoStykz {s1}"
    s2_name = f"CryptoStykz {s2}"
    img = Stitch.vs_screen(s1_name, s1_path, s2_name, s2_path)
    img.save("vs_screen.png")
    with open("vs_screen.png", "rb") as f:
        _file = discord.File(f)
        await ch.send(file=_file)

async def add_reactions(msg, reactions):
    for r in reactions:
        await msg.add_reaction(r)


async def get_by_role(role_name):
    global server
    users = list()
    for user in server.members:
        user_roles = list(user.roles)
        if role_name in [r for r in user_roles]:
            users.append(user)
    return users


@bot.command(name="givepoints")
@commands.has_role("Admin")
async def give_points_cmd(ctx, user_mention, amount):
    if not user_mention or not amount:
        return
    if not len(ctx.message.mentions):
        await ctx.author.send("User did not receive points: You must @ the user you wish to give points to")
        return
    user = ctx.message.mentions[0]
    admin = ctx.author
    try:
        _amount = int(amount)
    except ValueError:
        await admin.send("{0} did not receive points: Invalid amount".format(user.display_name))
        return
    bet.add_points(user.id, _amount)
    await user.send("You received {:,} points from {}".format(_amount, admin.display_name))


@bot.command(name="resetpoints")
@commands.has_role("Admin")
async def reset_points_cmd(ctx):
    global server
    admin = ctx.author
    ids = list()
    for user in server.members:
        ids.append((user.id, user.display_name))
    bet.reset_points(ids)
    await admin.send("Leaderboard points have been reset")

async def reassign_roles(server, rank_ids, role):
    c_ranks = await get_by_role(role)
    c_ranks_ids = [user.id for user in c_ranks]
    for uid in rank_ids:
        # Reassign user's role if they aren't already this rank
        if uid not in c_ranks_ids:
            user = server.get_member(uid)
            if user is not None and not is_admin(user) and not user.bot:
                c_rank = user.roles
                for rank in c_rank[1:]:
                    await user.remove_roles(rank)
                await user.add_roles(role)
        else:
            c_ranks_ids.remove(uid)
    for uid in c_ranks_ids:
        # Remove this rank from users who no longer fall into it
        user = server.get_member(uid)
        if not is_admin(user) and not user.bot:
            c_rank = user.roles
            await user.remove_roles(c_rank)


@tasks.loop(hours=1)
async def leader_loop():
    elite_max = 5
    veteran_max = 25
    intermediate_max = 50
    try:
        ch = channels["leaderboard"]

        # Send leaderboard images to the channel
        leaderboard.make_leaderboard()
        with open(leaderboard.png_name, "rb") as f:
            await ch.send(file=discord.File(f))
        rank_ids = await points_leaderboard(ch)
        # Adjust roles according to rank
        server = bot.guilds[0]
        num_ranks = len(rank_ids)
        if num_ranks >= 1:
            # assign elites
            print("Assigning elites")
            e_role = discord.utils.get(server.roles, name="Elite")
            await reassign_roles(server, rank_ids[ : elite_max], e_role)
        if num_ranks >= elite_max:
            # assign veterans
            print("Assigning vets")
            v_role = discord.utils.get(server.roles, name="Veteran")
            await reassign_roles(server, rank_ids[elite_max : veteran_max], v_role)
        if num_ranks >= veteran_max:
            # assign intermediates
            print("Assigning intermediates")
            i_role = discord.utils.get(server.roles, name="Intermediate")
            await reassign_roles(server, rank_ids[veteran_max : intermediate_max], i_role)
        if num_ranks > intermediate_max:
            # assign beginners
            b_role = discord.utils.get(server.roles, name="Beginner")
            await reassign_roles(server, rank_ids[intermediate_max : ], b_role)
    except KeyError:
        # Happens on the first round of start up
        pass


@tasks.loop(minutes=30)
#@tasks.loop(seconds=15)
async def bonus_loop():
    global bonus_round, bonus_msg, bonus_ids

    #print("Bonus round starting")
    try:
        ch = channels["fighting"]
        server = bot.guilds[0]
    except KeyError:
        return
    delay = random.randint(1, 60, 1)
    # Start bonus round every 30 to 90 minutes
    await asyncio.sleep(delay * 60)
    bonus_ranges = [(1000, 10000), (25000, 50000), (100000, 250000)]
    bonus_probs = [0.75, 0.2, 0.05]
    bonus_index = random.choice([0, 1, 2], p=bonus_probs)
    bonus_amount = random.randint(bonus_ranges[bonus_index][0], bonus_ranges[bonus_index][1])
    #print("Bonus amount: ", bonus_amount)
    bonus_round = True
    msg = """>>> Bonus round starting! do something for **{:,}** points!
    Add any reaction to this message in the next 30 seconds to enter for a chance to win!
    Good luck!""".format(bonus_amount)
    bonus_msg = await ch.send(msg)
    #print(bonus_msg.id, bonus_round)
    # Wait for people to enter the round
    await asyncio.sleep(30)
    # End the loop if no one joined the bonus round
    if not len(bonus_ids):
        return
    winner_id = random.choice(bonus_ids)
    winning_user = discord.utils.get(server.members, id=winner_id)
    bet.add_points(winner_id, bonus_amount)
    msg = f"Congratulations {winning_user.mention}! You won the bonus round for **{bonus_amount}** points!"
    await ch.send(msg)
    msg = f"Congratulations, you won the bonus round for **{bonus_amount}** points!"
    await winning_user.send(msg)

    bonus_round = False
    bonus_ids = list()
    bonus_msg = None


@bot.command(name="myrank",
             aliases=["mr", "MyRank", "Myrank", "MYRANK", "mYRANK", "mYrANK"],
             brief="Sends a direct message to you with your current rank on the points leaderboard.",
             description="""Sends you a direct message telling you where you currently are on the points leaderboard. 
                            Works in any channel.""")
async def my_points_cmd(ctx):
    user = ctx.author
    in_order = bet.points.sort_values(by="points", ascending=False)
    in_order = in_order.drop([int(893151604272926721)])
    ranking = in_order.index.get_loc(user.id)
    msg = f"You are currently rank **{ranking}** of {len(in_order)}"
    await user.send(msg)

#@tasks.loop(minutes=1)
@tasks.loop(seconds=30)
async def fight_loop():
    global bet_period, s1_quick_bets_msg, s2_quick_bets_msg
    s1, s2 = arena.next_fight()

    if s1 is None or s2 is None:
        # Add a fight to the queue if it's empty
        s1, s2 = arena.random_fighers()
        arena.add_fight(s1, s2)
    else:
        ch = channels["fighting"]
        msg = "Battle is about to begin! You have 30 seconds to place your bets!\n"
        # Begin betting period
        await bot.change_presence(activity=discord.Game(name=f"{s1} vs {s2}"))
        await ch.send(msg)
        bet_period = True
        # Display sticks for upcoming fight
        msg = f"**CryptoStykz {s1}** ({arena.get_stick(s1)['rarity']}) vs **CryptoStykz {s2}** ({arena.get_stick(s2)['rarity']})"
        await ch.send(msg)
        await vs_screen(ch, s1, s2)
        # Place quick bets
        set_global_sticks(s1, s2)
        await ch.send("Quick bets: (🌘 25%)   (🌗 50%)   (🌖 75%)   (🌕 100%)")
        msg = f">>> Quick bets for **{s1}**"
        s1_quick_bets_msg = await ch.send(msg)
        await add_reactions(s1_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])
        msg = f">>> Quick bets for **{s2}**"
        s2_quick_bets_msg = await ch.send(msg)
        await add_reactions(s2_quick_bets_msg, ["🌘", "🌗", "🌖", "🌕"])
        # Wait for bets to be placed
        await asyncio.sleep(30)
        msg = "Betting period has ended, bets are final!"
        await ch.send(msg)
        # End of bet period
        bet_period = False
        s1_quick_bets_msg = None
        s2_quick_bets_msg = None

        # Display payouts
        s1_pool = bet.get_pool(s1)
        s2_pool = bet.get_pool(s2)
        if not s1_pool or not s2_pool:
            msg = "Payouts are at **{} : {}** odds".format(1, 1)
        elif s1_pool > s2_pool:
            ratio = round(s1_pool / s2_pool, 1)
            msg = "Payouts are at **{} : {}** odds".format(ratio, 1)
        else:
            ratio = round(s2_pool / s1_pool, 1)
            msg = "Payouts are at **{} : {}** odds".format(1, ratio)
        msg += "\n**{}**: {:,} points   -   **{}**: {:,} points".format(s1, int(s1_pool), s2, int(s2_pool))
        await ch.send(msg)
        # Small delay for delaying things...
        await asyncio.sleep(2)
        # Fight the next sticks in the arena
        rounds = arena.do_fight()
        match_winner = arena.match_winner(rounds)
        msg = ">>> "
        # Add each round to the print out message
        for _round, winner in enumerate(rounds):
            msg += f"Round {_round + 1} goes to {winner}\n"
        msg += f"**{match_winner} won the match!**"
        # Update arena leaderboard
        leaderboard.update_leaderboard(rounds, [s1, s2])
        await channels["fighting"].send(msg)
        betters = bet.declare_winner(match_winner)
        # Show winner image
        await _show_stick(ch, match_winner)
        for uid in betters:
            points = bet.get_points(uid)
            user = discord.utils.get(bot.guilds[0].members, id=uid)
            msg = "Points after bet: **{:,}**".format(points)
            await user.send(msg)
        # Update status to show that no fight is happening
        await bot.change_presence(activity=discord.Game(name=f"Waiting for next match"))


@bot.command(name="bet",
             aliases=["b", "BET", "bET", "Bet"],
             brief="Places a bet for a given amount on the CryptoStykz # you provided.",
             description="""Places a bet on the CryptoStykz # you provide for a specified amount of points. You can only
                            bet with whole numbers, such as 1, 2, or 3, and NOT 1.1, 2.5, 3.2, etc. Only works in the 
                            "fighting" channel.
                            !bet 2500 #194""")
async def bet_cmd(ctx, _amount, snum):
    if ctx.channel.name != "fighting":
        return
    user = ctx.author
    await place_bet(user, _amount, snum)


async def place_bet(user, _amount, snum):
    if _amount is None or snum is None:
        await user.send("Bet not placed: Error in bet command. Type '!help bet' or '!help' for more information")
        return
    snum = clean_snum(snum)
    if not bet_period:
        await user.send("Bet not placed: Placed bet outside of betting period.")
        return
    if not arena.in_next(snum):
        await user.send("Bet not placed: CryptoStykz # is not in the upcoming fight.")
        return
    if bet.bet_placed(user.id):
        await user.send("Bet not placed: You have already placed a bet on this fight.")
        return
    if isinstance(_amount, str):
        amount = int("".join([c for c in _amount if c.isdigit()]))
    else:
        amount = _amount
    points = bet.get_points(user.id)
    if amount > points:
        await user.send(f"Bet not placed: You have {points} in your wallet, but wagered {amount} points.")
        return
    if amount < 1:
        await user.send("Bet not placed: Amount must be more than 0 points")
        return
    bet.add_bet(user.id, user.display_name, snum, amount)
    msg = "You bet **{:,}** points on **CryptoStykz {}**".format(amount, snum)
    await user.send(msg)


@bot.command(name="allin",
             aliases=["ALLIN", "aLLIN", "Allin"],
             brief="Places a bet for all of your current points on a CryptoStykz' number in the next fight.",
             description="""Places a bet for 100% of your current points on the CryptoStykz # you provided with the 
                            command. You can only use this in the "fighting" channel, and can only bet on CryptoStykz 
                            that are in the next fight in queue.
                            !allin #69""")
async def allin_cmd(ctx, snum):
    if snum is None:
        return
    if ctx.channel.name != "fighting":
        return
    user = ctx.author
    snum = clean_snum(snum)
    points = bet.get_points(user.id)
    await bet_cmd(ctx, str(points), snum)


@bot.command(name="add",
             aliases=["ADD", "aDD", "Add"],
             brief="Adds a pair of CryptoStykz NFTs to the fight queue.",
             description="""Adds a pair of CryptoStykz NFTs to the end of the fight queue. If there are currently too
                            many matchups already in the queue, you will have to try to add them again later.
                            !add #130 #92""")
async def add_cmd(ctx, s1, s2):
    if s1 is None or s2 is None:
        return
    if ctx.channel.name != "fighting":
        return
    s1 = clean_snum(s1)
    s2 = clean_snum(s2)
    arena.add_fight(s1, s2)
    position = arena.fight_q.qsize()
    await ctx.send(f"Battle added! {position} in queue")


@bot.command(name="nextfight",
             aliases=["n", "next", "NEXT", "nEXT", "NEXTFIGHT", "nEXTFIGHT"],
             brief="Sends a message in the \"fighting\" channel with the numbers for the CryptoStykz in the next fight.",
             description="""Sends a message back with the numbers for the CryptoStykz in the next fight in queue. Only 
                            works in the "fighting" channel.""")
async def next_fight_cmd(ctx):
    if ctx.channel.name != "fighting":
        return
    s1, s2 = arena.next_fight()
    if s1 is None or s2 is None:
        msg = "There are no fights currently in the queue"
    else:
        msg = f"**{s1}** vs **{s2}**"
    await ctx.send(msg)


@bot.command(name="nextspecs",
            aliases=["ns", "NEXTSPEC", "Nextspec", "NextSpec", "nEXTSPEC"],
             brief="Shows the rarities for each property of each CryptoStykz NFT in the upcoming fight.",
             description="""Sends a message in the "fighting" channel containing the rarity for each property of each
                            CryptoStykz NFT in an upcoming fight. When the bot says "Place your bets", this command
                            will show the specs for the sticks you will be betting on.""")
async def next_specs_cmd(ctx):
    ns1, ns2 = arena.next_fight()
    if not ns1 or not ns2:
        await ctx.send("No fights are currently in the queue. Use the ``!add`` command to add your own matchup or a random one will be chosen.")
        return
    await ctx.send(f"Next up: **{ns1}** vs **{ns2}**")
    await ctx.send(_specs(ns1))
    await ctx.send(_specs(ns2))


@bot.command(name="mypoints",
             aliases=["Mypoints", "MyPoints", "mp", "MYPOINTS", "mYPOINTS", "mYpOINTS"],
             brief="Sends a private message to you with your current points total.",
             description="""Sends a direct message to you telling you how many points you currently have. Works in any
                            channel.""")
async def points_cmd(ctx):
    user = ctx.author
    points = bet.get_points(user.id)
    msg = "You currently have {:,} points".format(points)
    await user.send(msg)


@bot.command(name="flex",
             aliases=["Flex", "FLEX", "fLEX"],
             brief="Show off your points to the other users.",
             description="""Sends a message in the "fighting" channel with your username and total points for everyone
                            in the channel to see.""")
async def flex_cmd(ctx):
    if ctx.channel.name != "fighting":
        return
    user = ctx.author
    points = bet.get_points(user.id)
    msg = "{} has a whole {:,} points!".format(user.display_name, points)
    await ctx.send(msg)


@bot.command(name="queue",
             aliases=["q", "Queue", "QUEUE", "qUEUE"],
             brief="Shows up to the next 5 fights that are in the queue.",
             description="""Sends a message back with the next matchups in the fight queue. It will show at most 5 matchups,
                            but there may be more in the queue. Only works in the "fighting" channel""")
async def queue_cmd(ctx):
    if ctx.channel.name != "fighting":
        return
    msg = arena.to_string()
    await ctx.send(msg)


@bot.command(name="fight",
             aliases=["Fight", "FIGHT", "fIGHT"],
             brief="Fights 2 CryptoStkz against eachother",
             description="To fight #175 against #300 use the command:\n!fight #175 #300")
async def fight_cmd(ctx, s1, s2=None):
    if s1 is None:
        return
    s1 = clean_snum(s1)
    if s2 is not None:
        print("pre s2: ", s2)
        s2 = clean_snum(s2)
        print("post s2: ", s2)
    valid = False
    msg = ""
    if ctx.channel.name != "dueling":
        return
    if s2 is None:
        s2 = s1
        while s1 == s2:
            s2 = "#{}".format(random.randint(1, 999))
    if arena.verify_stick(s1):
        if arena.verify_stick(s2):
            valid = True
        else:
            msg += f"Invalid stick number: \"{s2}\""
    else:
        msg += f"Invalid stick number: \"{s1}\""

    if valid:
        msg = f">>> **{s1} vs {s2}**\n"
        s1_r = arena.get_stick(s1)["rarity"]
        s2_r = arena.get_stick(s2)["rarity"]
        if arena.get_stick(s1).hash == arena.get_stick(s2).hash:
            await ctx.send("Please use 2 different CryptoStykz #'s")
            return
        msg += f"{s1} has a rarity of **{s1_r}** and {s2} has a rarity of **{s2_r}**\n"
        rounds = arena.fight_sticks(s1, s2)
        match_winner = arena.match_winner(rounds)
        for _round, winner in enumerate(rounds):
            msg += f"Round {_round + 1} goes to {winner}\n"
        msg += f"{match_winner} won the match!"
        leaderboard.update_leaderboard(rounds, [s1, s2])
        await ctx.send(msg)
        await display_stick(ctx, match_winner)
    else:
        await ctx.send(msg)


@bot.command(name="rfight",
             aliases=["rf", "RFIGHT", "Rfight", "rFIGHT"],
             brief="Fight two random CryptoStykz",
             description="""Randomly select two different CryptoStykz to fight each other""")
async def rfight_cmd(ctx):
    if ctx.channel.name != "dueling":
        return
    fighters = arena.random_fighers()
    await fight_cmd(ctx, fighters[0], fighters[1])


@bot.command(name="display",
             aliases=["Display", "DISPLAY", "dISPLAY"],
             brief="Shows the image for the CryptoStykz # you provided",
             description="""Sends a message to the channel you called the command from. Only works in "fighting" and 
                            "dueling" channels.
                            !display #560""")
async def display_stick(ctx, s_num):
    if s_num is None:
        return
    if ctx.channel.name != "fighting" and ctx.channel.name != "dueling":
        return
    s_num = clean_snum(s_num)
    stick = arena.get_stick(s_num)
    stick_hash = stick["hash"]
    with open(stick_img_path.format(stick_hash), "rb") as f:
        image = discord.File(f)
        await ctx.send(file=image)

async def _show_stick(ch, s_num):
    if s_num is None:
        return
    s_num = clean_snum(s_num)
    stick = arena.get_stick(s_num)
    stick_hash = stick["hash"]
    with open(stick_img_path.format(stick_hash), "rb") as f:
        image = discord.File(f)
        await ch.send(file=image)


@bot.command(name="specs",
             aliases=["Specs", "SPECS", "sPECS", "spec", "Spec", "SPEC", "sPEC"],
             brief="Display the rarity of each component of a CryptoStyk",
             description="""Sends a message back to you containing the rarity of each component of a CryptoStyk given its number
                            !specs #119""")
async def specs_cmd(ctx, snum):
    if snum is None:
        return
    if ctx.channel.name != "fighting" and ctx.channel.name != "dueling":
        return
    snum = clean_snum(snum)
    await ctx.send(_specs(snum))


def _specs(snum):
    snum = clean_snum(snum)
    if arena.verify_stick(snum):
        stick = arena.get_stick(snum)
        msg = f">>> **CryptoStykz {snum}**\n"
        msg += f"Overall rarity: **{stick['rarity']}**\n"
        msg += f"Background: {stick['bg']}\n"
        msg += f"Body: {stick['body']}\n"
        msg += f"Miscellaneous: {stick['misc']}\n"
        msg += f"Hand: {stick['hand']}"
        return msg
    else:
        return f"Invalid stick number \"{snum}\""


@bot.command(name="leaders",
             aliases=["Leaders", "LEADERS", "lEADERS"],
             brief="Display the top 5 Cryptostykz with the most wins",
             description="""The bot will reply with a message containing the leaderboard with the top 5 highest ranked
                            Cryptostykz with the most matches won""")
async def leaderboard_cmd(ctx):
    if ctx.channel.name != "leaderboard":
        return
    leaderboard.make_leaderboard()
    with open(leaderboard.png_name, "rb") as f:
        image = discord.File(f)
        await ctx.send(file=image)


@bot.command(name="pointleaders",
             aliases=["pl", "Pointleaders", "pointsleaders", "PointLeaders", "POINTLEADERS", "POINTSLEADERS"],
             brief="Display the top users with the most points.",
             description="""Sends a picture of the current leaderboard rankings based on total points for each user to
                            the "leaderboard" channel""")
async def point_leader_cmd(ctx):
    if ctx.channel.name != "leaderboard":
        return
    await points_leaderboard(ctx)
    """
    in_order = get_points_leaderboard_df()
    point_leaderboard.make_leaderboard(in_order)
    with open("PointsLeaderboard.png", "rb") as f:
        img = discord.File(f)
        await ctx.send(file=img)
    """


async def points_leaderboard(ch, send=True):
    in_order = get_points_leaderboard_df()
    max_len = 25 if len(in_order) > 25 else len(in_order)
    point_leaderboard.set_size(max_len)
    point_leaderboard.make_leaderboard(in_order)
    with open(point_leaderboard_png, "rb") as f:
        leaderboard_file = discord.File(f)
    if send:
        await ch.send(file=leaderboard_file)
    return in_order.index


def get_points_leaderboard_df():
    in_order = bet.points.sort_values(by="points", ascending=False)
    # Remove Admins and bot from leaderboard data
    # in_order = in_order.drop([int(892799939296518165)]) # Dean
    # in_order = in_order.drop([int(330862459382398981)]) # Me
    in_order = in_order.drop([int(893151604272926721)])  # Bot id
    return in_order



bonus_loop.start()
leader_loop.start()
fight_loop.start()
bot.run(token)

