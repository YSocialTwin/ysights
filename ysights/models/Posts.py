import json
from collections import defaultdict


class Post:
    """
    Represents a social media post in the YSocial simulation.

    This class encapsulates all properties of a post including text content,
    metadata, and enriched features such as sentiment, hashtags, topics, mentions,
    emotions, toxicity scores, and reactions.

    :param row: A database row tuple containing post data in a specific order:
                [id, text, ?, user_id, comment_to, thread_id, round, news_id, shared_from, image_id]
    :type row: tuple

    :ivar int id: Unique identifier for the post
    :ivar str text: The text content of the post
    :ivar int user_id: ID of the agent who created the post
    :ivar int comment_to: ID of the post this is commenting on (None if not a comment)
    :ivar int thread_id: ID of the thread this post belongs to
    :ivar int round: Simulation round when the post was created
    :ivar int news_id: ID of the news article this post references (if applicable)
    :ivar int shared_from: ID of the original post if this is a share
    :ivar int image_id: ID of the attached image (if applicable)
    :ivar dict sentiment: Sentiment analysis scores (neg, pos, neu, compound)
    :ivar list hashtags: List of hashtags used in the post
    :ivar list topics: List of topics associated with the post
    :ivar list mentions: List of user IDs mentioned in the post
    :ivar dict toxicity: Toxicity scores across multiple dimensions
    :ivar list emotions: List of emotions detected in the post
    :ivar dict reactions: Dictionary mapping reaction types to their counts

    Example:
        Creating and enriching a post::

            from ysights.models.Posts import Post
            from ysights import YDataHandler

            # Example database row
            row = (123, 'Hello world! #greeting', None, 5, None, 1, 10, None, None, None)
            post = Post(row)

            print(f"Post ID: {post.id}")
            print(f"Text: {post.text}")
            print(f"Author: {post.user_id}")

            # Enrich post with additional data from database
            # (requires database cursor)
            ydh = YDataHandler('path/to/database.db')
            posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment', 'hashtags'])

            for post in posts.get_posts():
                print(f"Sentiment: {post.sentiment}")
                print(f"Hashtags: {post.hashtags}")

    See Also:
        :class:`Posts`: Collection class for managing multiple posts
        :meth:`enrich_post`: Method to enrich post with additional data
    """

    def __init__(self, row):
        """
        Initialize a Post object with data from a database row.

        :param row: Database row containing post data
        :type row: tuple
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
        self.reactions = defaultdict(int)

    def enrich_post(self, cursor, dimensions=["all"]):
        """
        Enrich the post with additional data from the database.

        This method retrieves and attaches additional information to the post based on
        specified dimensions. Each dimension corresponds to a different type of metadata
        that can be retrieved from the database.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        :param dimensions: List of dimensions to enrich. Options include:
                          'sentiment', 'hashtags', 'mentions', 'emotions',
                          'topics', 'toxicity', 'reactions', or 'all' for everything
        :type dimensions: list[str]
        :raises ValueError: If an unknown dimension is specified

        Example::

            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Enrich with specific dimensions
            posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment', 'hashtags'])

            # Or enrich with all available data
            all_posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['all'])

            for post in all_posts.get_posts():
                print(f"Sentiment: {post.sentiment}")
                print(f"Topics: {post.topics}")
                print(f"Emotions: {post.emotions}")
                print(f"Reactions: {dict(post.reactions)}")

        Note:
            The 'all' dimension will enrich the post with all available metadata,
            which may be slower but provides complete information.
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
            elif dimension == "reactions":
                self.__enrich_post_reactions(cursor)
            elif dimension == "all":
                self.__enrich_post_sentiment(cursor)
                self.__enrich_post_hashtags(cursor)
                self.__enrich_post_mentions(cursor)
                self.__enrich_post_emotions(cursor)
                self.__enrich_post_topics(cursor)
                self.__enrich_post_toxicity(cursor)
                self.__enrich_post_reactions(cursor)
            else:
                raise ValueError(f"Unknown dimension: {dimension}")

    def __enrich_post_sentiment(self, cursor):
        """
        Enrich the post with sentiment analysis data from the database.

        Retrieves and attaches sentiment scores including negative, positive,
        neutral, and compound sentiment values.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
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
        """
        Enrich the post with hashtags from the database.

        Retrieves all hashtags associated with this post.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
        cursor.execute(
            "SELECT h.hashtag FROM post_hashtags as ph, hashtags as h WHERE ph.post_id = ? and h.id = ph.hashtag_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.hashtags = [row[0] for row in user_data]

    def __enrich_post_mentions(self, cursor):
        """
        Enrich the post with user mentions from the database.

        Retrieves IDs of all users mentioned in this post.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
        cursor.execute(
            "SELECT m.user_id FROM mentions as m WHERE m.post_id = ?", (self.id,)
        )
        user_data = cursor.fetchall()
        if user_data:
            self.mentions = [row[0] for row in user_data]

    def __enrich_post_emotions(self, cursor):
        """
        Enrich the post with emotion detection data from the database.

        Retrieves all emotions detected in this post's content.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
        cursor.execute(
            "SELECT e.emotion FROM post_emotions as pe, emotions as e WHERE pe.post_id = ? and e.id = pe.emotion_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.emotions = [row[0] for row in user_data]

    def __enrich_post_topics(self, cursor):
        """
        Enrich the post with topic classification data from the database.

        Retrieves all topics/interests associated with this post's content.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
        cursor.execute(
            "SELECT t.interest FROM post_topics as pt, interests as t WHERE pt.post_id = ? and t.iid = pt.topic_id",
            (self.id,),
        )
        user_data = cursor.fetchall()
        if user_data:
            self.topics = [row[0] for row in user_data]

    def __enrich_post_toxicity(self, cursor):
        """
        Enrich the post with toxicity analysis data from the database.

        Retrieves comprehensive toxicity scores including overall toxicity,
        severe toxicity, identity attacks, insults, profanity, threats,
        sexual content, and flirtation.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
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

    def __enrich_post_reactions(self, cursor):
        """
        Enrich the post with reaction data from the database.

        Retrieves and counts all reactions (likes, loves, etc.) received by this post.

        :param cursor: Database cursor for executing queries
        :type cursor: sqlite3.Cursor
        """
        cursor.execute("SELECT type FROM reactions WHERE post_id = ?", (self.id,))
        user_data = cursor.fetchall()

        if user_data:
            for row in user_data:
                self.reactions[row[0]] += 1

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
    A container class for managing a collection of Post objects.

    This class provides methods to add posts to the collection and retrieve
    the list of posts. It serves as a convenient way to group and manipulate
    multiple posts from a YSocial simulation.

    :ivar list posts: Internal list storing all Post objects

    Example:
        Managing a collection of posts::

            from ysights import YDataHandler
            from ysights.models.Posts import Posts, Post

            # Create a posts collection
            posts = Posts()

            # Add posts manually
            row = (1, 'Hello world!', None, 5, None, 1, 10, None, None, None)
            post = Post(row)
            posts.add_post(post)

            # Or retrieve posts from database
            ydh = YDataHandler('path/to/database.db')
            agent_posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment'])

            # Get list of all posts
            post_list = agent_posts.get_posts()
            print(f"Total posts: {len(post_list)}")

            # Iterate through posts
            for post in post_list:
                print(f"Post {post.id}: {post.text[:50]}...")
                if post.sentiment:
                    print(f"  Sentiment: {post.sentiment}")

    See Also:
        :class:`Post`: Individual post class
        :meth:`ysights.models.YDataHandler.YDataHandler.posts`: Retrieve all posts from database
        :meth:`ysights.models.YDataHandler.YDataHandler.posts_by_agent`: Retrieve posts by specific agent
    """

    def __init__(self):
        """
        Initialize an empty Posts collection.
        """
        self.posts = []

    def add_post(self, post):
        """
        Add a post to the collection.

        :param post: The Post object to add to the collection
        :type post: Post

        Example::

            posts = Posts()
            post = Post(row_data)
            posts.add_post(post)
        """
        self.posts.append(post)

    def get_posts(self):
        """
        Retrieve the list of all posts in the collection.

        :return: List of all Post objects in this collection
        :rtype: list[Post]

        Example::

            posts = Posts()
            # ... add posts ...
            post_list = posts.get_posts()
            for post in post_list:
                print(f"{post.id}: {post.text}")
        """
        return self.posts

    def __repr__(self):
        return f"Posts({self.posts})"
