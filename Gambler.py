import pandas as pd
import numpy as np
from discord import User


class Bet:

    def __init__(self, user: User, s_num: str, amount: int):
        self.uid = user.id
        self.name = user.display_name
        self.snum = s_num
        self.amount = amount
        self.winnings = 0

    def lost(self):
        self.winnings = int((-1) * self.amount)

    def won(self, ratio: float):
        self.winnings = int(ratio * self.amount)

    def to_dict(self):
        return {
            "uid": self.uid,
            "name": self.name,
            "s_num": self.snum,
            "amount": self.amount,
            "winnings": self.winnings
        }


class Gambler:
    init_points = 500
    weekly_bonus_points = 1000
    redemption_points = 100
    max_payout_ratio = 1000
    max_points = int(1e16)
    points_csv = "user_points.csv"

    def __init__(self):
        self.points = self.init_points_df()
        self.bets = self.new_bets()
        self.last_bets = None

    def init_points_df(self):
        try:
            df = pd.read_csv(self.points_csv)#, dtype={"uid": np.int64, "points": np.uint64})
            df = df.set_index("uid")
            df.loc[:, "points"] = df["points"].astype(np.uint64)
            return df
        except FileNotFoundError:
            return self.new_points([], [])

    def save_csv(self):
        self.points.to_csv(self.points_csv)

    def new_bets(self):
        df = pd.DataFrame(columns=["uid", "name", "s_num", "amount"])
        df["uid"] = df["uid"].astype(np.int64)
        df = df.set_index("uid")
        return df

    def new_points(self, id_list, name_list):
        df = pd.DataFrame({"uid": id_list, "name": name_list, "points": np.cast[np.uint64](self.init_points)})
        #df["points"] = df["points"].astype(int)
        df = df.set_index("uid")
        return df

    def reset_points(self, id_list):
        names = [t[1] for t in id_list]
        ids = [t[0] for t in id_list]
        self.points = self.new_points(ids, names)

    def add_uid(self, uid, name):
        _uid = int(uid)
        self.points.loc[_uid, "points"] = np.cast[np.uint64](self.init_points)
        self.points.loc[_uid:, "points"] = self.points["points"].astype(np.uint64)
        self.points.loc[_uid, "name"] = name

    def add_points(self, uid, inc):
        _uid = int(uid)
        new_total = self.points.loc[_uid, "points"] + inc
        self.points.loc[_uid, "points"] = int(self.points.loc[_uid, "points"] + inc)#inc
        if new_total > self.max_points:
            new_total = self.max_points
        self.points.loc[_uid, "points"] = new_total

    def sub_points(self, uid, inc):
        _uid = int(uid)
        self.points.loc[_uid, "points"] -= inc
        if not self.points.loc[_uid]["points"]:
            self.points.loc[_uid, "points"] = self.redemption_points

    def get_points(self, uid):
        _uid = np.cast[np.int64](uid)
        return self.points.loc[uid]["points"]

    def weekly_bonus(self):
        self.points = self.points.add(self.weekly_bonus_points)

    def update_winners(self, winners, ratio):
        if not len(winners):
            return
        for i, bet in winners.iterrows():
            uid = np.cast[np.int64](bet.uid)
            inc = int(bet["amount"] * ratio)
            print(f"> Updating winner: {bet['name']}, bet: {bet['amount']}, ratio: {ratio}, winnings: {inc}")
            self.add_points(uid, inc)

    def update_losers(self, losers):
        if not len(losers):
            return
        for i, bet in losers.iterrows():
            uid = np.cast[np.int64](bet.uid)
            print(f"> Updating loser: {bet['name']}, bet: {bet['amount']}")
            self.sub_points(uid, bet.amount)

    def bet_placed(self, uid):
        if not len(self.bets):
            return False
        try:
            if uid in self.bets["uid"].to_numpy():
                return True
            return False
        except KeyError:
            return False

    def get_ratio(self, w_pool, l_pool):
        if l_pool > w_pool:
            ratio = round(l_pool / w_pool, 3)
            if ratio > self.max_payout_ratio:
                return self.max_payout_ratio
            return ratio
        return 1

    def add_bet(self, uid, name, snum, amount):
        data = {"uid": np.cast[np.int64](uid),
                "name": name,
                "s_num": snum,
                "amount": np.cast[np.int64](amount)}
        self.bets = self.bets.append(data, ignore_index=True)

    def get_pool(self, snum):
        betters = self.bets["s_num"] == snum
        return self.bets[betters]["amount"].sum()

    def declare_winner(self, snum):
        if not len(self.bets):
            return []
        winners = self.bets["s_num"] == snum
        losers = winners.apply(lambda x: not x)
        win_bets = self.bets[winners]
        lose_bets = self.bets[losers]
        print(self.bets)
        if len(win_bets):
            win_pool = win_bets["amount"].sum()
            if not len(lose_bets):
                total_bets = win_pool
                lose_pool = total_bets
            else:
                lose_pool = lose_bets["amount"].sum()
            ratio = self.get_ratio(win_pool, lose_pool)
            self.update_winners(win_bets, ratio)
        self.update_losers(lose_bets)
        self.points.to_csv(self.points_csv, index=True)

        uids = list(self.bets.uid)
        self.bets = self.new_bets()
        return uids

    def verify_points(self, uid, amount):
        points = self.points[uid]["points"]
        return amount <= points

    def get_rank(self, uid):
        in_order = self.sort_points()
        rank = in_order.index.get_loc(uid)
        return rank + 1

    def sort_points(self):
        in_order = self.points.sort_values(by="points", ascending=False)
        try:
            # Remove the bot from the list of points
            in_order = in_order.drop([int(893151604272926721)])
        except KeyError:
            pass
        return in_order

