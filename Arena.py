import pandas as pd
from pandas import Series
from numpy.random import choice
import queue

class Arena:

    def __init__(self, csv_list: list, num_rounds=5):
        self.csv_list = csv_list
        self.num_rounds = num_rounds
        self.stick_df = self.build_stick_dataframe()
        self.fight_q = queue.Queue()

    def add_fight(self, s1: str, s2: str):
        self.fight_q.put((s1, s2))

    def do_fight(self):
        if self.fight_q.qsize():
            s1, s2 = self.fight_q.get()
            return self.fight_sticks(s1, s2)

    def next_fight(self):
        if self.fight_q.qsize():
            return self.fight_q.queue[0]
        return (None, None)

    def stick_in_next(self, snum):
        return snum in self.next_fight()

    def in_next(self, snum):
        snum_b = f"#{snum}"
        next_pair = self.next_fight()
        if snum in next_pair:
            return True
        if snum_b in next_pair:
            return True
        return False

    def q_len(self):
        return len(self.fight_q.queue)

    def in_q(self, matchup):
        return matchup in self.fight_q.queue

    def build_stick_dataframe(self):
        types = {"hash": str,
                 "s_num": str,
                 "rarity": float,
                 "bg": str,
                 "body": str,
                 "misc": str,
                 "hand": str}
        df = pd.read_csv(self.csv_list[0], dtype=types).dropna()
        if len(self.csv_list) > 1:
            for csv in self.csv_list[1:]:
                tmp_df = pd.read_csv(csv, dtype=types).dropna()
                df = pd.concat([df, tmp_df])

        def parse_rarity(s):
            s = s[1:-1]
            rarity = s.split(",")[-1]
            return float(rarity)

        for col in ["bg", "body", "misc", "hand"]:
            df[col] = df[col].apply(parse_rarity)
        return df.set_index("s_num")

    def verify_stick(self, stick_number: str) -> bool:
        try:
            self.get_stick(stick_number)
            return True
        except KeyError:
            return False

    def get_stick(self, stick_number: str) -> Series:
        num_str = f"CryptoStykz {stick_number}"
        try:
            return self.stick_df.loc[num_str]
        except KeyError:
            num_str = f"CryptoStykz #{stick_number}"
            return self.stick_df.loc[num_str]

    def calc_odds(self, low_rarity: float, high_rarity: float, sway: float) -> float:
        return (1 - (low_rarity / (high_rarity + sway))) / 2 + 0.5
        #return 0.5 + (1 - (low_rarity / high_rarity)) / 2

    def calc_sway(self, low_rarity: float, high_rarity: float) -> float:
        return (1 - (low_rarity / high_rarity)) / 2

    def fight_round(self, snum1: str, snum2: str, category: str) -> str:
        s1 = self.get_stick(snum1)
        s2 = self.get_stick(snum2)
        rarer = [s1, s2] if s1[category] < s2[category] else [s2, s1]
        overall_rarer = 0 if rarer[0]["rarity"] < rarer[1]["rarity"] else 1
        # underdog chance
        if choice([False, True], p=[0.99, 0.01]):
            return rarer[1].name.split(" ")[-1]
        # get the odds of the rarer stick winning
        sway = self.calc_sway(rarer[overall_rarer]["rarity"], rarer[overall_rarer * -1 + 1]["rarity"])
        low_rarity = rarer[0][category]
        high_rarity = rarer[1][category]
        #print("cat: {:<10} low_r: {:<10} high_r: {:<10} sway: {:10.3f}".format(category, low_rarity, high_rarity, sway))
        winning_odds = self.calc_odds(low_rarity, high_rarity, sway)
        print("\t{:<20}: {:<10.2%}\t{:<20}: {:<10.2%}".format(rarer[0].name, winning_odds, rarer[1].name, 1 - winning_odds))
        # choose the rarer one or less rare one based on the winning odds
        winner = choice([r.name for r in rarer], p=[winning_odds, 1 - winning_odds])
        return winner.split(" ")[-1]

    def fight_sticks(self, snum1: str, snum2: str) -> list:
        rounds = list()
        print(f"{snum1}  vs  {snum2}")
        for category in self.stick_df.columns[1:]:
            rounds.append(self.fight_round(snum1, snum2, category))
        return rounds

    def match_winner(self, rounds: list) -> str:
        fighters = set(rounds)
        if len(fighters) == 1:
            return fighters.pop()
        else:
            results = [(rounds.count(fighter), fighter) for fighter in fighters]
            return max(results)[1]

    # Randomly select 2 different stick numbers
    def random_fighers(self):
        fighters = choice(self.stick_df.index, size=2, replace=False)
        return list(map(lambda x: x.split(" ")[-1], fighters))

    def to_string(self):
        msg = ""
        if not self.fight_q.qsize():
            return "No fights currently in queue."
        ns1, ns2 = self.next_fight()
        msg += f"Next up: {ns1} vs {ns2}\n"
        fight_list = list(self.fight_q.queue)[:5]
        for i, (s1, s2) in enumerate(fight_list):
            msg += f"**{i + 1}.** {s1} vs {s2}\n"
        return msg



if __name__ == "__main__":
    arena = Arena(["cryptostykz_v3.1.csv"])
    rounds = arena.fight_sticks("#1", "#2")
    print(rounds)