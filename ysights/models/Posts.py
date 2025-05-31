import json


class Post:
    def __init__(self, row):
        """
        Initialize a Post object with data from a database row.
        :param row:
        """
        self.id = row[0]
        self.text = row[1]
        self.user_id = row[3]
        self.comment_to = row[4]
        self.thread_id = row[5]
        self.round = row[6]
        self.news_id = row[7]
        self.shared_from = row[8]
        self.image_id = row[9]

        self.sentiment = {}
        self.hashtags = []
        self.topics = []
        self.mentions = []
        self.toxicity = {}
        self.emotions = []

    def enrich_post(self, cursor, dimensions=["sentiment", "hashtags"]):
        """
        Enrich the post with additional data from the database based on specified dimensions.
        :param cursor:
        :param dimensions:
        :return:
        """
        for dimension in dimensions:
            if dimension == "sentiment":
                self.__enrich_post_sentiment(cursor)
            elif dimension == "hashtags":
                self.__enrich_post_hashtags(cursor)
            elif dimension == "mentions":
                self.__enrich_post_mentions(cursor)
            elif dimension == "emotions":
                self.__enrich_post_emotions(cursor)
            elif dimension == "topics":
                self.__enrich_post_topics(cursor)
            elif dimension == "toxicity":
                self.__enrich_post_toxicity(cursor)
            elif dimension == "all":
                self.__enrich_post_sentiment(cursor)
                self.__enrich_post_hashtags(cursor)
                self.__enrich_post_mentions(cursor)
                self.__enrich_post_emotions(cursor)
                self.__enrich_post_topics(cursor)
                self.__enrich_post_toxicity(cursor)
            else:
                raise ValueError(f"Unknown dimension: {dimension}")

    def __enrich_post_sentiment(self, cursor):
        """Enrich the post with additional data from the database."""
        cursor.execute(
            "SELECT neg, pos, neu, compound FROM post_sentiment WHERE post_id = ?",
            (self.id,),
        )
        user_data = cursor.fetchone()
        if user_data:
            self.sentiment = {
                "neg": user_data[0],
                "pos": user_data[1],
                "neu": user_data[2],
                "compound": user_data[3],
            }

    def __enrich_post_hashtags(self, cursor):
        """Enrich the post with hashtags from the database."""
        cursor.execute(
            "SELECT h.hashtag FROM post_hashtags as ph, hashtags as h WHERE ph.post_id = ? and h.id = ph.hashtag_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.hashtags = [row[0] for row in user_data]

    def __enrich_post_mentions(self, cursor):
        """Enrich the post with mentions from the database."""
        cursor.execute(
            "SELECT m.user_id FROM mentions as m WHERE m.post_id = ?", (self.id,)
        )
        user_data = cursor.fetchall()
        if user_data:
            self.mentions = [row[0] for row in user_data]

    def __enrich_post_emotions(self, cursor):
        """Enrich the post with emotions from the database."""
        cursor.execute(
            "SELECT e.emotion FROM post_emotions as pe, emotions as e WHERE pe.post_id = ? and e.id = pe.emotion_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.emotions = [row[0] for row in user_data]

    def __enrich_post_topics(self, cursor):
        """Enrich the post with topics from the database."""
        cursor.execute(
            "SELECT t.interest FROM post_topics as pt, interests as t WHERE pt.post_id = ? and t.iid = pt.topic_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.topics = [row[0] for row in user_data]

    def __enrich_post_toxicity(self, cursor):
        """Enrich the post with toxicity data from the database."""
        cursor.execute(
            "SELECT toxicity FROM post_toxicity WHERE post_id = ?", (self.id,)
        )
        user_data = cursor.fetchone()
        if user_data:
            self.toxicity = {
                "toxicity": user_data[2],
                "severe_toxicity": user_data[3],
                "identity_attack": user_data[4],
                "insult": user_data[5],
                "profanity": user_data[6],
                "threat": user_data[7],
                "sexual_explicit": user_data[8],
                "flirtation": user_data[9],
            }

    def __repr__(self):
        return f"Post(id={self.id}, text={self.text}, user_id={self.user_id}, sentiment={self.sentiment}, hashtags={self.hashtags}, topics={self.topics}, mentions={self.mentions}, emotions={self.emotions}, toxicity={self.toxicity})"

    def __str__(self):
        return json.dumps(
            {
                "id": self.id,
                "text": self.text,
                "user_id": self.user_id,
                "sentiment": self.sentiment,
                "hashtags": self.hashtags,
                "topics": self.topics,
                "mentions": self.mentions,
                "emotions": self.emotions,
                "toxicity": self.toxicity,
            }
        )


class Posts:
    """
    A class to represent a collection of posts.
    This class is used to manage and interact with multiple posts.
    """

    def __init__(self):
        self.posts = []

    def add_post(self, post):
        """Add a post to the collection."""
        self.posts.append(post)

    def get_posts(self):
        """Return the list of posts."""
        return self.posts

    def __repr__(self):
        return f"Posts({self.posts})"
