import json
import os
import sqlite3
import tempfile
import unittest

from ysights.algorithms.recommenders import sentiment_diffusion_metrics
from ysights.algorithms.topics import adoption_rate, peak_engagement_time, topic_spread
from ysights.models.Agents import Agent
from ysights.models.Posts import Post
from ysights.models.YDataHandler import YDataHandler


def _create_fixture_db():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = os.path.join(tmpdir.name, "ysights_regression.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE post (
            id INTEGER PRIMARY KEY,
            tweet TEXT NOT NULL,
            post_img TEXT,
            user_id INTEGER NOT NULL,
            comment_to INTEGER,
            thread_id INTEGER,
            round INTEGER,
            news_id INTEGER,
            shared_from INTEGER,
            image_id INTEGER
        );

        CREATE TABLE post_toxicity (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            toxicity REAL,
            severe_toxicity REAL,
            identity_attack REAL,
            insult REAL,
            profanity REAL,
            threat REAL,
            sexually_explicit REAL,
            flirtation REAL
        );

        CREATE TABLE recommendations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            post_ids TEXT NOT NULL,
            round INTEGER NOT NULL
        );

        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            round INTEGER NOT NULL
        );

        CREATE TABLE post_hashtags (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            hashtag_id INTEGER NOT NULL
        );

        CREATE TABLE hashtags (
            id INTEGER PRIMARY KEY,
            hashtag TEXT NOT NULL
        );

        CREATE TABLE user_interest (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            interest_id INTEGER NOT NULL,
            round_id INTEGER NOT NULL
        );

        CREATE TABLE interests (
            iid INTEGER PRIMARY KEY,
            interest TEXT NOT NULL
        );

        CREATE TABLE post_emotions (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            emotion_id INTEGER NOT NULL
        );

        CREATE TABLE emotions (
            id INTEGER PRIMARY KEY,
            emotion TEXT NOT NULL,
            icon TEXT
        );

        CREATE TABLE follow (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            follower_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            round INTEGER NOT NULL
        );

        CREATE TABLE mentions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            round INTEGER NOT NULL,
            answered INTEGER
        );
        """
    )

    cur.executemany(
        "INSERT INTO post VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (10, "post-10", None, 1, None, 1, 1, None, None, None),
            (11, "post-11", None, 1, None, 1, 5, None, None, None),
            (12, "post-12", None, 2, None, 1, 5, None, None, None),
        ],
    )
    cur.execute(
        "INSERT INTO post_toxicity VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 10, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8),
    )
    cur.executemany(
        "INSERT INTO recommendations VALUES (?, ?, ?, ?)",
        [
            (1, 1, "10|12", 1),
            (2, 1, "11", 5),
        ],
    )
    cur.executemany(
        "INSERT INTO reactions VALUES (?, ?, ?, ?, ?)",
        [
            (1, 10, 1, "like", 1),
            (2, 11, 1, "love", 5),
        ],
    )
    cur.executemany(
        "INSERT INTO hashtags VALUES (?, ?)",
        [(100, "alpha"), (101, "beta")],
    )
    cur.executemany(
        "INSERT INTO post_hashtags VALUES (?, ?, ?)",
        [(1, 10, 100), (2, 11, 101)],
    )
    cur.executemany(
        "INSERT INTO interests VALUES (?, ?)",
        [(200, "sports"), (201, "news")],
    )
    cur.executemany(
        "INSERT INTO user_interest VALUES (?, ?, ?, ?)",
        [(1, 1, 200, 1), (2, 1, 201, 5)],
    )
    cur.executemany(
        "INSERT INTO emotions VALUES (?, ?, ?)",
        [(300, "joy", None), (301, "sad", None)],
    )
    cur.executemany(
        "INSERT INTO post_emotions VALUES (?, ?, ?)",
        [(1, 10, 300), (2, 11, 301)],
    )
    cur.executemany(
        "INSERT INTO follow VALUES (?, ?, ?, ?, ?)",
        [
            (1, 1, 2, "follow", 1),
            (2, 1, 3, "follow", 5),
        ],
    )
    cur.executemany(
        "INSERT INTO mentions VALUES (?, ?, ?, ?, ?)",
        [
            (1, 20, 10, 1, 0),
            (2, 30, 11, 5, 0),
        ],
    )

    conn.commit()
    conn.close()
    return tmpdir, db_path


class RegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir, cls.db_path = _create_fixture_db()

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def setUp(self):
        self.handler = YDataHandler(self.db_path)

    def test_agent_str_returns_json_string(self):
        row = (
            1,
            "alice",
            None,
            None,
            "user",
            "moderate",
            32,
            0.7,
            0.6,
            0.8,
            0.5,
            0.4,
            0.5,
            "en",
            None,
            "college",
            0,
            0.5,
            "female",
            "USA",
            0.1,
            False,
            None,
            3.5,
            "teacher",
        )
        agent = Agent(row)

        payload = json.loads(str(agent))
        self.assertEqual(payload["id"], 1)
        self.assertEqual(payload["username"], "alice")
        self.assertEqual(payload["profession"], "teacher")

    def test_toxicity_enrichment_reads_all_columns(self):
        posts = self.handler.posts_by_agent(1, enrich_dimensions=["toxicity"]).get_posts()
        post = next(post for post in posts if post.id == 10)

        self.assertEqual(
            post.toxicity,
            {
                "toxicity": 0.1,
                "severe_toxicity": 0.2,
                "identity_attack": 0.3,
                "insult": 0.4,
                "profanity": 0.5,
                "threat": 0.6,
                "sexual_explicit": 0.7,
                "flirtation": 0.8,
            },
        )

    def test_agent_toxicity_reads_all_columns(self):
        toxicity = self.handler.agent_toxicity(1)

        self.assertEqual(
            toxicity,
            [
                {
                    "toxicity": 0.1,
                    "severe_toxicity": 0.2,
                    "identity_attack": 0.3,
                    "insult": 0.4,
                    "profanity": 0.5,
                    "threat": 0.6,
                    "sexual_explicit": 0.7,
                    "flirtation": 0.8,
                }
            ],
        )

    def test_one_sided_time_filters_are_respected(self):
        recommendations = self.handler.agent_recommendations(1)
        recommendations_from = self.handler.agent_recommendations(1, from_round=3)
        recommendations_to = self.handler.agent_recommendations(1, to_round=2)
        self.assertNotEqual(recommendations, recommendations_from)
        self.assertNotEqual(recommendations, recommendations_to)
        self.assertEqual(len(recommendations_from), 1)
        self.assertEqual(len(recommendations_to), 2)

        reactions = self.handler.agent_reactions(1)
        reactions_from = self.handler.agent_reactions(1, from_round=3)
        reactions_to = self.handler.agent_reactions(1, to_round=2)
        self.assertEqual(reactions_from, {"love": [11]})
        self.assertEqual(reactions_to, {"like": [10]})
        self.assertEqual(reactions, {"like": [10], "love": [11]})

        hashtags_from = self.handler.agent_hashtags(1, from_round=3)
        hashtags_to = self.handler.agent_hashtags(1, to_round=2)
        self.assertEqual(dict(hashtags_from), {"beta": 1})
        self.assertEqual(dict(hashtags_to), {"alpha": 1})

        interests_from = self.handler.agent_interests(1, from_round=3)
        interests_to = self.handler.agent_interests(1, to_round=2)
        self.assertEqual(dict(interests_from), {"news": 1})
        self.assertEqual(dict(interests_to), {"sports": 1})

        emotions_from = self.handler.agent_emotions(1, from_round=3)
        emotions_to = self.handler.agent_emotions(1, to_round=2)
        self.assertEqual(dict(emotions_from), {"sad": 1})
        self.assertEqual(dict(emotions_to), {"joy": 1})

        followers_from = self.handler.ego_network_follower(1, from_round=3)
        followers_to = self.handler.ego_network_follower(1, to_round=2)
        self.assertEqual(set(followers_from.successors(1)), {3})
        self.assertEqual(set(followers_to.successors(1)), {2})

        mentions_from = self.handler.mention_ego_network(1, from_round=3)
        mentions_to = self.handler.mention_ego_network(1, to_round=2)
        self.assertEqual(set(mentions_from.successors(1)), {30})
        self.assertEqual(set(mentions_to.successors(1)), {20})

    def test_placeholder_public_apis_raise(self):
        for func in (
            topic_spread,
            adoption_rate,
            peak_engagement_time,
            sentiment_diffusion_metrics,
        ):
            with self.assertRaises(NotImplementedError):
                func(None)


if __name__ == "__main__":
    unittest.main()
