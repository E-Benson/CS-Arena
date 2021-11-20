import requests
from requests_oauthlib import OAuth1
import pandas as pd
import datetime
import pytz
import numpy as np
import os
from multiprocessing import Process
import time
import math
import base64
from Tweeting.Creds import credentials
import logging


logger = logging.getLogger("TwitterSpamLogger")
info_handler = logging.FileHandler("TwitterSpamInfo.log")
info_handler.setLevel(logging.INFO)
debug_handler = logging.FileHandler("TwitterSpamDebug.log")
debug_handler.setLevel(logging.DEBUG)
logger.addHandler(info_handler)
logger.addHandler(debug_handler)
logger.setLevel(logging.DEBUG)
info_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s: %(funcName)s:\t%(message)s"))
debug_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s: %(funcName)s:\t%(message)s"))


def needs_internet(func):
    try:
        def _run(*args, **kwargs):
            func(*args, **kwargs)
        return _run
    except requests.exceptions.ConnectionError as exc:
        logger.error(f" No internet connection: Error: {exc.strerror}")


class Tweeter:
    """Handles all interaction with the Twitter API"""

    base_uri = "https://api.twitter.com/"
    auth_uri = "{}oauth2/token".format(base_uri)
    search_uri = "{}1.1/search/tweets.json".format(base_uri)
    status_uri = "{}1.1/statuses/update.json".format(base_uri)
    upload_uri = "https://upload.twitter.com/1.1/media/upload.json?"
    show_uri = "{}1.1/statuses/show.json".format(base_uri)

    def __init__(self, new_creds: dict = None):
        if new_creds is not None:
            self.creds = new_creds
        else:
            self.creds = credentials

    #@needs_internet
    def get_auth(self):
        """Helper function used to generate OAuth data"""
        auth = OAuth1(self.creds["consumer_key"], self.creds["consumer_key_secret"],
                      self.creds["access_token"], self.creds["access_token_secret"])
        return auth

    #@needs_internet
    def check_auth(self):
        """Verifies that the credentials are valid"""
        key_secret = "{}:{}".format(self.creds["consumer_key"], self.creds["consumer_key_secret"]).encode("ascii")
        b64_key = base64.b64encode(key_secret)
        b64_key = b64_key.decode("ascii")
        auth_headers = {
            "Authorization": "Basic {}".format(b64_key),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        auth_data = {
            "grant_type": "client_credentials"
        }
        res = requests.post(self.auth_uri, headers=auth_headers, data=auth_data)

        valid = res.status_code == 200
        logger.debug(f"Valid Twitter API credentials: {valid}")
        return valid

    def get_tweet(self, tweet_id: int):
        """
        Retrieve a single tweet by its ID
        :param tweet_id: ID number of the tweet being retrieved
        :return response: Tweet dictionary
        """
        headers = {
            "Authorization": "Bearer {}".format(self.creds["bearer_token"])
        }
        params = {
            "id": tweet_id
        }
        response = requests.get(self.show_uri, headers=headers, params=params)
        log_msg = "Tweet_ID: [{}], URL: [{}]".format(tweet_id, response.url)
        logger.debug(log_msg)
        return response.json()

    def search(self, query, count=10):
        """
        Searches Twitter using the query provided as a parameter and returns a list of tweets
        :param query: Phrase to be used for the search
        :param count: Number of tweets to return in list
        :return results: List of dictionaries containing all information about a tweet
        """
        search_headers = {
            "Authorization": "Bearer {}".format(self.creds["bearer_token"])
        }
        search_params = {
            "q": query,
            "result_type": "recent",
            "count": count
        }
        response = requests.get(self.search_uri, headers=search_headers, params=search_params)

        results = response.json()["statuses"]
        log_msg = "Query: [{}], Num Results: [{}], URL: [{}]".format(query, len(results), response.url)
        logger.debug(log_msg)
        return results

    def post_status(self, msg: str, media_id: int = None):
        """
        Post a regular tweet with or without an img
        :param msg: The body of the tweet being made
        :param media_id: ID of the img to include with the tweet
        :return status_id: ID of the status that was posted
        """
        status_params = {
            "status": msg
        }
        if media_id is not None:
            status_params["media_ids"] = "{}".format(media_id)
        response = requests.post(self.status_uri, params=status_params, auth=self.get_auth())
        try:
            msg = "Media_ID: [{}], Tweet_ID: [{}], URL: [{}]".format(media_id, response.json()["id"], response.url)
            logger.debug(msg)
            return response.json()["id"]
        except KeyError:
            msg = "Media_ID: [{}], URL: [{}],\nJSON: {}".format(media_id, response.url, response.json())
            logger.warning(msg)
            return None

    def reply_to(self, tweet_id: int, msg: str, media_id: int = None):
        """
        Replies to a certain tweet with the body content and media provided as parameters.
        :param tweet_id: ID of the tweet being replied to
        :param msg: Content of the tweet being posted
        :param media_id: ID for the media that has been uploaded to the API server
        :return valid_response: Boolean value telling if the tweet was successfully posted
        """
        status_params = {
            "status": msg,
            "in_reply_to_status_id": tweet_id
        }
        if media_id is not None:
            status_params["media_ids"] = "{}".format(media_id)
        response = requests.post(self.status_uri,  params=status_params, auth=self.get_auth())
        try:
            response_content = response.json()
            _ = response_content["id"]
            msg = "Media_ID: [{}], Tweet_ID: [{}], URL: [{}]".format(media_id, tweet_id, response.url)
            logger.debug(msg)
        except KeyError:
            err_msg = response.content
            msg = "Status_Code: {}, Response: {}".format(response.status_code, err_msg)
            logger.debug(msg)
        return response.status_code == 200

    def retweet(self, tweet_id: int):
        """
        Retweets the tweet with the ID provided as a parameter
        :param tweet_id: ID of tweet to be retweeted
        :return valid_response: Boolean value telling if the post was successful
        """
        retweet_uri = "{}1.1/statuses/retweet/{}.json".format(self.base_uri, tweet_id)
        retweet_headers = {
            "Authorization": "Bearer {}".format(self.creds["bearer_token"])
        }
        response = requests.post(retweet_uri, headers=retweet_headers, auth=self.get_auth())
        msg = "Tweet_ID: [{}], URL: [{}]".format(tweet_id, response.url)
        logger.debug(msg)
        return response.status_code == 200

    def init_media(self, fpath: str, file_size: int, file_type: str):
        """Prepare the Twitter API server to receive media data"""
        upload_params = {
            "command": "INIT",
            "total_bytes": file_size,
            "media_type": file_type
        }
        if file_size > 5120000:
            upload_params["media_category"] = "amplify_video"
        response = requests.post(self.upload_uri, params=upload_params, auth=self.get_auth())
        try:
            msg = "Image Path: [{}], Image Size: [{}], Media_ID: [{}], URL: [{}]".format(fpath, file_size,
                                                                                         response.json()["media_id"],
                                                                                         response.url, )
            logger.debug(msg)
        except KeyError:
            msg = "Image Path: [{}], Image Size: [{}], URL: [{}],  JSON:\n{}".format(fpath, file_size, response.url,
                                                                                     response.json())
            logger.warning(msg)
        try:
            return response.json()["media_id"]
        except KeyError:
            print(response.json())

    def await_upload(self, media_id: id):
        """
        Loops continuously until the media is finished uploading to the Twitter server
        :param media_id: ID of the media to check on
        :return: None
        """
        while True:
            info = self.upload_status(media_id)
            try:
                status = info["state"]
                log_msg = "Media_ID: [{}], Status: [{}]".format(media_id, status)
                logger.debug(log_msg)
            except KeyError:
                time.sleep(2)
                continue
            if status == "succeeded" or status == "failed":
                return
            time.sleep(info["check_after_secs"])

    def upload_status(self, media_id: int):
        """
        Checks the upload status of a media object to see if it has finished uploading
        :param media_id: ID of the media being uploaded
        :return processing_info: Dictionary containing the state and wait time for the upload
        """
        status_params = {
            "command": "STATUS",
            "media_id": media_id
        }
        response = requests.get(self.upload_uri, params=status_params, auth=self.get_auth())
        log_msg = "Media_ID: [{}], URL: [{}]".format(media_id, response.url)
        logger.debug(log_msg)
        try:
            return response.json()["processing_info"]
        except KeyError:
            return response.json()

    def chunk_media(self, fpath: str, media_id: int, file_size: int):
        """
        Breaks the file being uploaded into 1mb chunks and uploads them one by one, in order
        :param fpath: Path to the file being uploaded
        :param media_id: ID of the media being uploaded (from init_media())
        :param file_size: Size of the file in bytes
        :return: None
        """
        one_megabyte = 1000000
        num_chunks = 1 if file_size < one_megabyte else math.ceil(file_size / one_megabyte)
        _file = open(fpath, "rb")
        file_bytes = _file.read()
        log_msg = "File Path: [{}], File Size: [{}], Media_ID: [{}]".format(fpath, file_size, media_id)
        logger.debug(log_msg)
        for i in range(0, num_chunks):
            b = i * one_megabyte
            chunk = file_bytes[b:] if i == (num_chunks-1) else file_bytes[b:b+one_megabyte]
            self.append_media_chunk(chunk, media_id, i)
            log_msg = "Segment index: [{}/{}], Chunk start: [{}]".format(i, num_chunks, b)
            logger.debug(log_msg)
        _file.close()

    def append_media_chunk(self, file_bytes: bytes, media_id: int, segment_index: int):
        """
        Upload a single chunk of data to the Twitter API server
        :param file_bytes: Bytes object of the file's contents
        :param media_id: ID of the media being uploaded (from init_media())
        :param segment_index: The index of the chunk being uploaded (i/n)
        :return valid_response:
        """
        append_params = {
            "command": "APPEND",
            "media_id": media_id,
            "segment_index": segment_index
        }
        files = {"media": file_bytes}
        response = requests.post(self.upload_uri, files=files, params=append_params, auth=self.get_auth())
        log_msg = "Media_ID: [{}], Segment index: [{}], URL: [{}]".format(media_id, segment_index, response.url)
        logger.debug(log_msg)
        return response.status_code == 200

    def finalize_media(self, media_id: int):
        """Tells the Twitter API server that the media is done uploading"""
        finalize_params = {
            "command": "FINALIZE",
            "media_id": media_id
        }
        response = requests.post(self.upload_uri, params=finalize_params, auth=self.get_auth())
        try:
            msg = "Media_ID: [{}], Response Media_ID: [{}], URL: [{}]".format(media_id, response.json()["media_id"],
                                                                              response.url)
            logger.debug(msg)
        except KeyError:
            msg = "Media_ID: [{}], URL: [{}],  JSON:\n{}".format(media_id, response.url, response.json())
            logger.warning(msg)
        return response.json()["media_id"]

    def upload_media(self, fpath: str):
        """
        Wrapper function for simplifying the process of uploading media with a tweet.
        Gets the Twitter API server ready to receive media content and sends it.
        :param fpath: Path pointing to file to be uploaded with tweet
        :return final_media_id: ID for the media that was just uploaded
        """
        f_size = os.path.getsize(fpath)
        f_type = os.path.splitext(fpath)[1]
        media_id = self.init_media(fpath, f_size, f_type)
        self.chunk_media(fpath, media_id, f_size)
        final_media_id = self.finalize_media(media_id)
        # Wait for the file to upload to Twitter before making the tweet
        if f_type not in [".png", ".jpg", ".jpeg", ".gif"]:
            self.await_upload(final_media_id)
        msg = "Finalized image upload. Image Path: [{}], Media_ID".format(fpath, final_media_id)
        logger.debug(msg)
        return final_media_id


class Spammer:
    """Used to make searches and automatically reply to tweets"""

    def __init__(self, tweet_delay: int = 5, new_creds: dict = None):
        """
        Initializes the Spammer object
        :param tweet_delay: Number of minutes to wait in between each tweet
        """
        self.used_status_ids = list()
        self.statuses = pd.read_csv("statuses.csv")["status"]
        self.replies = pd.read_csv("replies.csv")["reply"]
        self.search_terms = pd.read_csv("hashtags.csv")["tag"]
        if new_creds is not None:
            self.twitter = Tweeter(new_creds=new_creds)
        else:
            self.twitter = Tweeter()
        self.stick_imgs = self.init_imgs()
        self.tweet_delay = tweet_delay

    def rand_status(self):
        """Returns a random status from self.statuses"""
        return np.random.choice(self.statuses)

    def rand_reply(self):
        """Returns a random reply from self.replies"""
        return np.random.choice(self.replies)

    def rand_img(self):
        """Returns a random image path from self.stick_imgs"""
        return np.random.choice(self.stick_imgs)

    def set_search_terms(self, search_terms: list):
        """Sets the list of search terms that will be used by the loop"""
        self.search_terms = search_terms

    def _spam_loop(self):
        """Loop container for starting the spam process"""
        while True:
            self.spam_search(self.search_terms)

    def start_spam(self):
        """Initiates the spam process as a concurrent subprocess"""
        Process(target=self._spam_loop).start()

    def start_status_spam(self):
        """Initiates the concurrent process for making regular tweets"""
        Process(target=self.spam_status_loop).start()

    @staticmethod
    def tweet_link(handle, _id):
        return "\t> https://twitter.com/{}/status/{}".format(handle, _id)

    @staticmethod
    def init_imgs():
        """Initializes the list of stick image paths"""
        imgs = list()
        for img in os.scandir("..\\stick_images"):
            imgs.append(img.path)
        return imgs

    @staticmethod
    def wait(minutes: int, process_name: str = ""):
        """Waits a certain number of minutes before finishing. Used to make delays easier."""
        while minutes > 0:
            mins = "minutes" if minutes != 1 else "minute"
            if (minutes > 5 and not minutes % 5) or minutes <= 5:
                print_out = "{} > Waiting {} more {}...".format(process_name, minutes, mins)
                print(print_out)
            time.sleep(60)
            minutes = minutes - 1

    @staticmethod
    def tweet_to_df(tweet: dict):
        """
        Creates the dictionary of data that will be used when adding a tweet to a Pandas DataFrame
        :param tweet: Dictionary of tweet data returned by the Twitter API
        :return data: Dictionary of relevant tweet data
        """
        now = pytz.utc.localize(datetime.datetime.utcnow())
        try:
            tweet = tweet["retweeted_status"]
        except KeyError:
            pass
        data = {
            "tweet_id": tweet["id"],
            "handle": tweet["user"]["screen_name"],
            "followers": tweet["user"]["followers_count"],
            "age": now - datetime.datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y"),
            "reply_to": tweet["in_reply_to_status_id"]
        }
        return data

    def iter_search_results(self, search_terms: list):
        """
        Iterates over the list of search_terms, returning the results from each search one at a time
        :param search_terms: List of strings to be used in Twitter search
        :return: None
        """
        for term in search_terms:
            term_dict = pd.DataFrame(columns=["tweet_id", "handle", "followers", "age", "reply_to"])
            term_results = self.twitter.search(term, count=25)
            for tweet in term_results:
                term_dict = term_dict.append(self.tweet_to_df(tweet), ignore_index=True)
            yield term_dict.sort_values(by="followers", ascending=False)

    def reply_to_tweet(self, tweet: pd.Series):
        """
        Replies to the tweet that's taken as a parameter using a random body of text from self.statuses
        :param tweet: Pandas Series object of tweet
        :return valid_response: Status code from twitter.reply_to() call
        """
        if tweet["tweet_id"] in self.used_status_ids:
            msg = "Already replied to tweet_id: [{}]\nused_status_ids: [{}]".format(tweet["tweet_id"],
                                                                                    self.used_status_ids)
            logger.warning(msg)
            return False
        content = "@{}\n{}".format(tweet["handle"], self.rand_reply())
        img_path = self.rand_img()
        media_id = self.twitter.upload_media(img_path)
        tweeted = self.twitter.reply_to(tweet["tweet_id"], content, media_id)
        self.used_status_ids.append(tweet["tweet_id"])
        return tweeted

    def spam_search(self, search_terms: list) -> None:
        """
        Slowly iterates over the list of search_terms and chooses the tweet from the user with the most followers to
        reply to
        :param search_terms: List of search_term strings
        :return: None
        """
        for tweet_df in self.iter_search_results(search_terms):
            lt_5m = tweet_df["age"] < datetime.timedelta(days=0, minutes=5, seconds=0)
            recent_tweets = tweet_df[lt_5m]
            if not len(recent_tweets):
                # Skip this search term if there were no recent tweets in the search results
                msg = "No recent search results"
                continue
            most_popular_tweet = recent_tweets.iloc[0]
            if most_popular_tweet["reply_to"] is not None:
                # If this tweet was a reply, get the tweet they replied to
                reply_to_data = self.twitter.get_tweet(most_popular_tweet["reply_to"])
                most_popular_tweet = self.tweet_to_df(reply_to_data)
            if not self.reply_to_tweet(most_popular_tweet):
                # reply_to_tweet received a bad status code
                msg = "Failed to reply to tweet. Tweet ID: [{}]".format(most_popular_tweet["tweet_id"])
                logger.warning(msg)
            else:
                msg = "Posted new reply: User: [@{}], Followers: [{:,}], Tweet age: [{}]".format(most_popular_tweet['handle'],
                                                                                                 most_popular_tweet['followers'],
                                                                                                 most_popular_tweet['age'])
                link = "\thttps://twitter.com/{}/status/{}".format(most_popular_tweet['handle'],
                                                                   most_popular_tweet['tweet_id'])
                logger.info(msg)
                logger.info(link)
                print("> Replied to user: {} ({:,} followers) - tweeted [{}] ago".format(most_popular_tweet['handle'],
                                                                                         most_popular_tweet['followers'],
                                                                                         most_popular_tweet['age']))
                print("\t> https://twitter.com/{}/status/{}".format(most_popular_tweet['handle'],
                                                                    most_popular_tweet['tweet_id']))
            # Prevent too much spamming on the twitter servers
            self.wait(self.tweet_delay, process_name="reply_loop")

    def post_status(self):
        """
        Post a random tweet with a random image
        :return tweet_id: ID of the tweet that was created
        """
        img_path = self.rand_img()
        media_id = self.twitter.upload_media(img_path)
        status = self.rand_status()
        tweet_id = self.twitter.post_status(status, media_id)
        if tweet_id is not None:
            msg = "Posted new status. Tweet_ID: [{}]".format(tweet_id)
            link = "\thttps://twitter.com/Trace34007811/status/{}".format(tweet_id)
            logger.info(msg)
            logger.info(link)
        else:
            msg = "Failed to post new status.".format(tweet_id)
            logger.warning(msg)
        return tweet_id

    def spam_status_loop(self):
        while True:
            self.post_status()
            self.wait(self.tweet_delay, process_name="status_loop")


sp = Spammer(tweet_delay=30)

if __name__ == "__main__":
    print(sp.twitter.check_auth())

    sp.start_spam()
    time.sleep(600)
    sp.start_status_spam()


