import tweepy
from pprint import pprint
import datetime
import pytz
import pandas as pd
import numpy as np

from Tweeting.TwitterAuth import credentials

class SpamBot:

    def __init__(self):
        self.client = tweepy.Client(bearer_token=credentials["bearer_token"],
                                    access_token=credentials["access_token"],
                                    access_token_secret=credentials["access_token_secret"])
        auth = tweepy.OAuthHandler(credentials["key"],
                                   credentials["key_secret"])
        auth.set_access_token(credentials["access_token"],
                              credentials["access_token_secret"])
        self.api = tweepy.API(auth)
        self.hashtags = self.mk_tags_df()

    @staticmethod
    def mk_tags_df():
        tags = pd.read_csv("hashtags.csv")
        tags["post_count"] = 0
        return tags

    def search(self, query: str, count: int = 100):
        #return self.client.search_recent_tweets(query, count=count)
        return self.api.search_tweets(q=query, count=count)

    def tweet(self, content: str, reply_to_id: int = None):
        params = {
            "status": content,
        }
        if reply_to_id is not None:
            params["in_reply_to_status_id"] = reply_to_id
        self.api.update_status(**params)

    @staticmethod
    def tweet_to_df(tweet: tweepy.Tweet):
        author = tweet.user
        now = datetime.datetime.now(pytz.timezone("America/New_York"))
        data = {
            "at": author.screen_name,
            "followers": author.followers_count,
            "age": now - tweet.created_at,
            "id": tweet.id
        }
        return data

    def get_tweet(self, tweet_id: int):
        #tweet_res = self.client.get_tweet(tweet_id)
        #return tweet_res.data
        return self.api.get_status(tweet_id)

    def spam(self):

        for tag in self.hashtags["tag"][:3]:
            results = self.search(tag, count=25)
            tweet_df = pd.DataFrame(columns=["at", "followers", "age", "id"])
            #print(results)
            for tweet in results:
                #print(tweet)
                tweet_data = self.tweet_to_df(tweet)
                tweet_df = tweet_df.append(tweet_data, ignore_index=True)
            sorted_tweets = tweet_df.sort_values(by="followers", ascending=False)
            #print(sorted_tweets)
            num1 = sorted_tweets.iloc[0]
            popular = self.api.get_status(num1["id"])
            print(f"{num1['at']} - {num1.followers} - {num1.id} - {tag}")
            print(popular._json.keys())
            print("\n\n")




class Tweeter:

    def __init__(self):
        auth = tweepy.OAuthHandler("y3hp1MIlxYzchJ5DfppmwQcsl",
                                   "ajHL8pO7pvGUST8PrmFj8MKObgbNMYWMaKj2uqbr9kbFPPNxxq")
        auth.set_access_token("1443038355776753672-ltpw9knng4XDbJypj6b1M6vgiTNLHV",
                              "zMVEfMgWhG5V7iU9309ahS56WusdLTF5nteXCBRJN0KoP")
        self.api = tweepy.API(auth)
        self.used_tweet_ids = list()
        self.img_base_path = "../stick_images/"
        self.img_paths = self.mk_stick_paths()
        self.statuses = pd.read_csv("statuses.csv")

    @staticmethod
    def mk_tags_df():
        tags = pd.read_csv("hashtags.csv")
        tags["post_count"] = 0

    def rand_img(self):
        return np.random.choice(self.img_paths)

    def rand_status(self):
        return np.random.choice(self.statuses["status"])

    def mk_stick_paths(self):
        import os
        img_paths = list()
        for stick_img in os.scandir(self.img_base_path):
            img_paths.append(stick_img.path)
        return img_paths
    @staticmethod
    def mk_reply_msg(search_term: str, handle: str):
        msg = """@{}
Check out CryptoStykz on #OpenSea. An army of unique stickfigures with weapons, skins, backgrounds, and more!
opensea.io/collection/cryptostykz
You can bet on NFT fights in the Discord server to earn free NFTs!
https://discord.gg/sH7Ze9faTv
#cryptostykz #opensea #nfts
              """.format(handle)
        print("Msg length: ", len(msg))
        return msg

    def tweet(self, msg, img=None, url=None, reply_to=None):
        params = {
            "status": msg,
            "in_reply_to_status_id": reply_to,
            "attachment_url": url
        }
        if img is None:
            self.api.update_status(**params)
        else:
            params["filename"] = img
            self.api.update_status_with_media(**params)

    def search(self, query, count=25):
        x = self.api.search_tweets(q=query, count=count)
        #print(x)
        return x

    def reply_to(self, id, msg, img=None):
        params = {
            "status": msg,
            "in_reply_to_status_id": id
        }
        if id in self.used_tweet_ids:
            print(f"!!!!!\n\tAlready replied to status {id}")
            return
        self.used_tweet_ids.append(id)
        if img is None:
            self.api.update_status(**params)
        else:
            params["filename"] = img
            self.api.update_status_with_media(**params)

    def tweet_to_df(self, tweet: tweepy.Tweet):
        author = tweet.user
        now = datetime.datetime.now(pytz.timezone("America/New_York"))
        data = {
            "at": author.screen_name,
            "followers": author.followers_count,
            "age": now - tweet.created_at,
            "id": tweet.id,
            "id_str": tweet.id_str
        }
        return data

    def sspam(self, search_list: list):
        search_results = dict(list( zip(search_list,
                                        [pd.DataFrame(columns=["at", "followers", "age", "id"])] * len(search_list)) ))
        # Aggregate tweets for each search term
        for search_term in search_list:
            results = self.search(search_term)
            tweet_df = pd.DataFrame(columns=["at", "followers", "age", "id"])
            for tweet in results:
                tweet_df = tweet_df.append(self.tweet_to_df(tweet), ignore_index=True)
            search_results[search_term] = tweet_df.sort_values(by="followers", ascending=False)
        pprint(search_results)
        # Find best tweet to reply to for each search term
        for search_term in search_results:
            recent_tweets = search_results[search_term]["age"] < datetime.timedelta(days=0, minutes=5)
            best_tweets = search_results[search_term][recent_tweets]
            if len(best_tweets) < 1:
                continue
            best_tweet = best_tweets.iloc[0]
            #print(search_term)
            print(best_tweet)
            print("\n")
            msg = self.mk_reply_msg(search_term, best_tweet["at"])
            img = self.rand_img()
            if best_tweet["id"] in self.used_tweet_ids:
                continue
            try:
                self.reply_to(best_tweet["id_str"], msg, img=img)
            except tweepy.errors.TweepyException:
                print("Message too long, skipped...")


    def spam_status(self):
        status = self.rand_status()
        img = self.rand_img()
        self.tweet(status, img=img)


    def spam(self):
        now = datetime.datetime.now(pytz.timezone("America/New_York"))
        hashtags = ["#NFTThailand"]
        for tag in hashtags:
            results = self.search(tag)
            tweet_df = pd.DataFrame(columns=["at", "followers", "age", "id"])
            for tweet in results:
                author = tweet.user
                followers = author.followers_count
                at = author.screen_name
                posted = tweet.created_at
                age = now - posted
                tweet_df = tweet_df.append({"at": at, "followers": followers, "age": age, "id": tweet.id},
                                           ignore_index=True)
                if followers > 5000:
                    print(f"\n=== {at} - {followers} - {tweet.id} ===")
                    print(tweet.text)
            print(tag)
            dfs = tweet_df.sort_values(by="followers", ascending=False)
            print(dfs)
            #print(tweet_df.sort_values(by="followers", ascending=False))


#t = SpamBot()
#x = t.spam()

#sts = pd.read_csv("statuses.csv")

t = Tweeter()
#t.sspam(["drop your #nft", "#opensea", "#BuyingNFTs", "\"looking for nfts\"", "#NFTdrop", "#NFTcommunity"])
#s = sts.iloc[0]
#t.tweet(sts.iloc[0])
#print("{}".format(s["status"]))
import time

from multiprocessing import Process
import asyncio


def search_spam():
    global t
    searches = ["drop your #nft", "#opensea", "#BuyingNFTs", "\"looking for nfts\"", "#NFTdrop", "#NFTcommunity"]
    while True:
        t.sspam(searches)
        time.sleep(300)


def status_spam():
    global t
    while True:
        t.spam_status()
        time.sleep(1800)

if __name__ == "__main__":
    Process(target=search_spam).start()
    Process(target=status_spam).start()
