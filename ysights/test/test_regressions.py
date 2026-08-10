import json
import os
import sqlite3
import tempfile
import unittest

import pandas as pd

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

        CREATE TABLE rounds (
            id INTEGER PRIMARY KEY,
            day INTEGER NOT NULL,
            hour INTEGER NOT NULL
        );

        CREATE TABLE user_mgmt (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
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

        CREATE TABLE post_topics (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL
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

        CREATE TABLE reported (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            to_uid INTEGER,
            to_post INTEGER,
            from_uid INTEGER,
            tid INTEGER
        );

        CREATE TABLE forum_chat_sessions (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            created_at INTEGER
        );

        CREATE TABLE forum_chat_messages (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            round INTEGER NOT NULL,
            reply_to INTEGER
        );
        """
    )

    cur.executemany(
        "INSERT INTO post VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (10, "post-10", None, 1, -1, 10, 1, None, None, None),
            (11, "post-11", None, 1, 10, 10, 3, None, None, None),
            (12, "post-12", None, 2, 10, 10, 5, None, None, None),
        ],
    )
    cur.executemany(
        "INSERT INTO rounds VALUES (?, ?, ?)",
        [
            (1, 0, 0),
            (3, 1, 0),
            (5, 2, 0),
        ],
    )
    cur.executemany(
        "INSERT INTO user_mgmt VALUES (?, ?)",
        [(1, "alice"), (2, "bob")],
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
        "INSERT INTO post_topics VALUES (?, ?, ?)",
        [(1, 10, 200), (2, 11, 200), (3, 12, 201)],
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
    cur.executemany(
        "INSERT INTO reported VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "abuse", 1, 10, 2, 10),
            (2, "spam", 1, 10, 2, 10),
        ],
    )
    cur.execute(
        "INSERT INTO forum_chat_sessions VALUES (?, ?, ?)",
        (1, "general", 1),
    )
    cur.executemany(
        "INSERT INTO forum_chat_messages VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 1, "hello forum", 1, None),
            (2, 1, 2, "reply forum", 5, 1),
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
        spread = topic_spread(self.handler)
        self.assertIn(200, spread)
        self.assertEqual(spread[200]["peak_period"], 1)
        self.assertEqual(spread[201]["peak_period"], 5)

        adoption = adoption_rate(self.handler)
        self.assertEqual(adoption[200], 1.0)
        self.assertEqual(adoption[201], 1.0)

        peaks = peak_engagement_time(self.handler)
        self.assertEqual(peaks, {200: 1, 201: 5})

        with self.assertRaises(NotImplementedError):
            sentiment_diffusion_metrics(None)

    def test_schema_capabilities_and_frames(self):
        schema = self.handler.schema()
        capabilities = self.handler.capabilities()

        self.assertIn("post", schema.tables)
        self.assertIn("forum_chat_messages", schema.tables)
        self.assertTrue(self.handler.has_table("post"))
        self.assertTrue(self.handler.supports_feature("microblog"))
        self.assertTrue(self.handler.supports_feature("forum"))
        self.assertTrue(capabilities["features"]["posts"])
        self.assertTrue(capabilities["features"]["forum_messages"])

        posts_df = self.handler.posts_frame()
        self.assertIsInstance(posts_df, pd.DataFrame)
        self.assertEqual(len(posts_df), 3)
        self.assertIn("tweet", posts_df.columns)

        users_df = self.handler.users_frame(columns=["id", "username"])
        self.assertIsInstance(users_df, pd.DataFrame)
        self.assertListEqual(list(users_df.columns), ["id", "username"])

        forum_messages_df = self.handler.forum_messages_frame()
        self.assertIsInstance(forum_messages_df, pd.DataFrame)
        self.assertEqual(len(forum_messages_df), 2)
        self.assertIn("message", forum_messages_df.columns)

        forum_sessions_df = self.handler.forum_sessions_frame()
        self.assertIsInstance(forum_sessions_df, pd.DataFrame)
        self.assertEqual(len(forum_sessions_df), 1)
        self.assertIn("title", forum_sessions_df.columns)

    def test_thread_reconstruction_and_metrics(self):
        self.assertEqual(self.handler.thread_ids(), [10])

        posts = self.handler.thread_posts(10).get_posts()
        self.assertEqual([post.id for post in posts], [10, 11, 12])

        graph = self.handler.thread_graph(10)
        self.assertEqual(graph.number_of_nodes(), 3)
        self.assertEqual(graph.number_of_edges(), 2)
        self.assertEqual(set(graph.successors(10)), {11, 12})

        metrics = self.handler.thread_metrics(10)
        self.assertEqual(metrics["thread_id"], 10)
        self.assertEqual(metrics["root_post_id"], 10)
        self.assertEqual(metrics["post_count"], 3)
        self.assertEqual(metrics["reply_count"], 2)
        self.assertEqual(metrics["participant_count"], 2)
        self.assertEqual(metrics["max_depth"], 1)
        self.assertEqual(metrics["branching_factor"], 2.0)
        self.assertEqual(metrics["average_reply_latency"], 3.0)
        self.assertEqual(metrics["median_reply_latency"], 3.0)
        self.assertEqual(metrics["thread_span_rounds"], 4)
        self.assertEqual(metrics["root_reply_count"], 2)
        self.assertEqual(metrics["root_reply_share"], 1.0)
        self.assertEqual(metrics["cascade_size"], 3)

        summaries = self.handler.thread_summaries()
        self.assertEqual(list(summaries.keys()), [10])
        self.assertEqual(summaries[10]["post_count"], 3)

    def test_time_series_analytics(self):
        timeline = self.handler.activity_timeline()
        self.assertEqual(list(timeline["period"]), [1, 3, 5])
        self.assertEqual(list(timeline["posts"]), [1, 1, 1])
        self.assertEqual(list(timeline["replies"]), [0, 1, 1])
        self.assertEqual(list(timeline["authors"]), [1, 1, 1])

        timeline_day = self.handler.activity_timeline(granularity="day")
        self.assertEqual(list(timeline_day["period"]), [0, 1, 2])
        self.assertEqual(list(timeline_day["posts"]), [1, 1, 1])

        bursts = self.handler.burst_windows(metric="posts", window_size=2)
        self.assertIn("z_score", bursts.columns)
        self.assertIn("is_burst", bursts.columns)
        self.assertEqual(len(bursts), 3)

        comparison = self.handler.compare_time_windows(
            metric="posts", window_a=(1, 3), window_b=(5, 5)
        )
        self.assertEqual(comparison["delta"], -1)
        self.assertEqual(comparison["window_a"]["value"], 2)
        self.assertEqual(comparison["window_b"]["value"], 1)

        topic_timeline = self.handler.topic_timeline(200)
        self.assertEqual(list(topic_timeline["period"]), [1, 3])
        self.assertEqual(list(topic_timeline["posts"]), [1, 1])

        topic_timeline_day = self.handler.topic_timeline(200, granularity="day")
        self.assertEqual(list(topic_timeline_day["period"]), [0, 1])
        self.assertEqual(list(topic_timeline_day["posts"]), [1, 1])

    def test_phase4_intelligence_analytics(self):
        lifecycle = self.handler.topic_lifecycle(200)
        self.assertEqual(lifecycle["topic_id"], 200)
        self.assertEqual(lifecycle["post_count"], 2)
        self.assertEqual(lifecycle["author_count"], 1)
        self.assertEqual(lifecycle["peak_period"], 1)
        self.assertEqual(lifecycle["adoption_rate"], 1.0)
        self.assertIn("timeline", lifecycle)
        self.assertEqual(list(lifecycle["timeline"]["period"]), [1, 3])

        post_profile = self.handler.post_semantic_profile(10)
        self.assertGreaterEqual(post_profile["token_count"], 1)
        self.assertIn("entropy_proxy", post_profile)

        forum_profile = self.handler.forum_message_semantic_profile(1)
        self.assertEqual(forum_profile["token_count"], 2)

        user_summary = self.handler.user_profile_summary(1)
        self.assertEqual(user_summary["segment"], "conversationalist")
        self.assertEqual(user_summary["post_count"], 2)
        self.assertEqual(user_summary["reply_count"], 1)
        self.assertEqual(user_summary["topic_counts"], {"sports": 2})

        drift = self.handler.profile_drift(1, split_round=2)
        self.assertEqual(drift["topic_jaccard"], 1.0)
        self.assertEqual(drift["post_count_delta"], 0)
        self.assertEqual(drift["segment_shift"], "observer->conversationalist")

        segments = self.handler.user_segments()
        self.assertEqual(set(segments["segment"]), {"conversationalist"})

        community = self.handler.community_metrics(graph_type="social")
        self.assertGreaterEqual(community["community_count"], 1)
        self.assertGreaterEqual(community["node_count"], 1)
        self.assertGreaterEqual(community["edge_count"], 1)
        self.assertGreaterEqual(community["cross_community_edge_ratio"], 0.0)
        self.assertLessEqual(community["cross_community_edge_ratio"], 1.0)

    def test_phase5_moderation_forum_and_reporting(self):
        moderation = self.handler.moderation_summary()
        self.assertEqual(moderation["report_count"], 2)
        self.assertEqual(moderation["unique_reported_posts"], 1)
        self.assertEqual(moderation["unique_reporters"], 1)
        self.assertEqual(moderation["report_types"], {"abuse": 1, "spam": 1})

        hotspots = self.handler.moderation_hotspots(top_n=2)
        self.assertEqual(list(hotspots["entity_type"]), ["post", "user"])
        self.assertEqual(list(hotspots["entity_id"]), [10, 1])

        session = self.handler.forum_session_summary(1)
        self.assertEqual(session["message_count"], 2)
        self.assertEqual(session["participant_count"], 2)
        self.assertEqual(session["reply_count"], 1)
        self.assertEqual(session["session_span"], 4)

        sessions = self.handler.forum_session_summaries()
        self.assertIn(1, sessions)
        self.assertEqual(sessions[1]["message_count"], 2)

        report = self.handler.summary_report()
        self.assertEqual(report["report_count"], 2)
        self.assertEqual(report["forum_session_count"], 1)
        self.assertEqual(report["forum_message_count"], 2)
        self.assertEqual(report["post_count"], 3)

        summary_frame = self.handler.summary_frame()
        self.assertIsInstance(summary_frame, pd.DataFrame)
        self.assertEqual(int(summary_frame.iloc[0]["report_count"]), 2)

        comparison = self.handler.compare_experiments(self.db_path)
        self.assertEqual(comparison["metrics"]["post_count"]["delta"], 0)
        self.assertEqual(comparison["metrics"]["report_count"]["delta"], 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "summary.csv")
            json_path = os.path.join(tmpdir, "summary.json")
            self.assertEqual(self.handler.export_summary_csv(csv_path), csv_path)
            self.assertEqual(self.handler.export_summary_json(json_path), json_path)
            self.assertTrue(os.path.exists(csv_path))
            self.assertTrue(os.path.exists(json_path))


if __name__ == "__main__":
    unittest.main()
