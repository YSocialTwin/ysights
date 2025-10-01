"""
Global Trends Visualization Functions
======================================

This module provides visualization functions for aggregate statistics and
trends across the entire YSocial simulation. It includes functions for
analyzing content creation, user activity, reactions, hashtags, emotions,
topics, and engagement patterns over time.

Functions:
    - daily_contents_trends: Posts, articles, shares, and comments per day
    - contents_per_user_distributions: Distribution of content creation per user
    - daily_reactions_trends: Reactions distribution over time
    - trending_hashtags: Most popular hashtags
    - trending_emotions: Most expressed emotions
    - tending_topics: Most discussed topics
    - comments_per_post_distribution: Distribution of comment counts

Example:
    Visualizing global trends::

        from ysights import YDataHandler
        from ysights.viz import (
            daily_contents_trends,
            contents_per_user_distributions,
            trending_hashtags,
            trending_emotions
        )

        ydh = YDataHandler('path/to/database.db')

        # Daily content trends
        fig = daily_contents_trends(ydh)
        fig.suptitle('Content Production Over Time')
        fig.show()

        # Content distribution per user
        fig = contents_per_user_distributions(ydh)
        fig.show()

        # Top 10 trending hashtags
        fig = trending_hashtags(ydh, top_n=10)
        fig.show()

        # Emotion distribution
        fig = trending_emotions(ydh)
        fig.show()

See Also:
    - :mod:`ysights.viz.topics_viz`: Topic-specific visualizations
    - :mod:`ysights.viz.recommendations`: Recommendation system visualizations
"""

from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from ysights.models.YDataHandler import YDataHandler


def daily_contents_trends(YDH: YDataHandler):
    """
    Plot the distribution of posts, articles, shares, and comments per day.
    This function retrieves the count of posts, articles, shares, and comments from the database,
    grouped by day, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :return: A matplotlib figure object containing the plot of daily content distributions.
    """

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
    SELECT r.day, count(p.id)
    FROM post AS p
    JOIN rounds AS r ON p.round = r.id
    where p.news_id is null
    and p.comment_to == -1
    GROUP BY r.day
    ORDER BY r.day ASC
    """

    rows = YDH.custom_query(query)
    posts = [r[1] for r in rows[:-1]]

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
           SELECT r.day, count(p.id)
           FROM post AS p
            JOIN rounds AS r ON p.round = r.id
           where p.news_id is not null
           GROUP BY r.day
           ORDER BY r.day ASC
           """
    rows = YDH.custom_query(query)
    articles = [r[1] for r in rows[:-1]]

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
           SELECT r.day, count(p.id)
           FROM post AS p
            JOIN rounds AS r ON p.round = r.id
           where p.shared_from != -1
           GROUP BY r.day
           ORDER BY r.day ASC
           """
    rows = YDH.custom_query(query)
    shares = [r[1] for r in rows[:-1]]

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
           SELECT r.day, count(p.id)
           FROM post AS p
            JOIN rounds AS r ON p.round = r.id
           where p.comment_to != -1
           GROUP BY r.day
           ORDER BY r.day ASC
           """
    rows = YDH.custom_query(query)
    comments = [r[1] for r in rows[:-1]]

    fig = plt.figure(figsize=(10, 6))
    plt.plot(posts, label="Posts")
    if len(articles) > 0:
        plt.plot(articles, label="Articles")
    if len(shares) > 0:
        plt.plot(shares, label="Shares")
    plt.plot(comments, label="Comments")
    plt.xlabel("Day")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    return fig


def daily_reactions_trends(YDH: YDataHandler, smooth_days=None):
    """
    Plot the distribution of reactions per day.
    This function retrieves the count of reactions from the database,
    grouped by day, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :param smooth_days: If specified, the data will be smoothed over this number of days.
    :return: A matplotlib figure object containing the plot of daily reaction distributions.
    """

    # get the distribution of reactions per day, get the day id from the rounds table
    query = """
            SELECT rd.day, count(r.id)
            FROM reactions AS r
            JOIN rounds AS rd ON r.round = rd.id
            where r.type == 'like'
            GROUP BY rd.day
            ORDER BY rd.day ASC
    """

    rows = YDH.custom_query(query)
    like_reactions = [r[1] for r in rows[:-1]]

    query = """
            SELECT rd.day, count(r.id)
            FROM reactions AS r
            JOIN rounds AS rd ON r.round = rd.id
            where r.type == 'dislike'
            GROUP BY rd.day
            ORDER BY rd.day ASC 
            """

    rows = YDH.custom_query(query)
    dislike_reactions = [r[1] for r in rows[:-1]]

    fig = plt.figure(figsize=(6, 3))
    ax = fig.add_subplot(111)

    if smooth_days is None:
        plt.scatter(range(len(like_reactions)), like_reactions, label="Likes")
        plt.scatter(range(len(dislike_reactions)), dislike_reactions, label="Dislikes")
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.xlabel("Day", fontsize=12)
        plt.ylabel("Reactions", fontsize=12)
        plt.legend(fontsize=12)
        plt.tight_layout()

    else:
        like_reactions_smooth = []
        dislike_reactions_smooth = []
        for i in range(0, len(like_reactions), smooth_days):
            like_reactions_smooth.append(sum(like_reactions[i : i + smooth_days]))
            dislike_reactions_smooth.append(sum(dislike_reactions[i : i + smooth_days]))

        plt.plot(like_reactions_smooth[:-1], label="Likes")
        plt.plot(dislike_reactions_smooth[:-1], label="Dislikes")
        plt.xlabel("Week", fontsize=12)
        plt.ylabel("Reactions", fontsize=12)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.legend(fontsize=12)
        plt.tight_layout()

    return fig


def contents_per_user_distributions(YDH: YDataHandler):
    """
    Plot the distribution of posts, articles, shares, and comments per user.
    This function retrieves the count of posts, articles, shares, and comments from the database,
    grouped by user, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :return: A matplotlib figure object containing the plot of content distributions per user.
    """

    # get the distribution of posts per user
    query = """
    SELECT u.id, count(p.id)
    FROM post AS p
    JOIN user_mgmt AS u ON p.user_id = u.id
    where p.news_id is null
    and p.comment_to == -1
    GROUP BY u.id
    ORDER BY count(p.id) DESC
    """

    rows = YDH.custom_query(query)
    posts_per_user = defaultdict(int)
    for r in rows:
        posts_per_user[r[1]] += 1

    # compute the distribution of comments per user
    query = """
            SELECT u.id, count(p.id)
            FROM post AS p
            JOIN user_mgmt AS u ON p.user_id = u.id
            where p.comment_to != -1
            GROUP BY u.id
            ORDER BY count(p.id) DESC
            """

    rows = YDH.custom_query(query)
    comments_per_user = defaultdict(int)
    for r in rows:
        comments_per_user[r[1]] += 1

    # compute the distribution of hashtags frequency
    query = """
           SELECT hashtag_id, count(post_id)
           FROM post_hashtags
           GROUP BY hashtag_id
           ORDER BY count(post_id) DESC
           """

    rows = YDH.custom_query(query)
    hashtags_freq = defaultdict(int)
    for r in rows:
        hashtags_freq[r[1]] += 1

    # compute the distribution of mentions frequency
    query = """
           SELECT user_id, count(id)
           FROM mentions
           GROUP BY user_id
           ORDER BY count(id) DESC
           """

    rows = YDH.custom_query(query)
    mentions_freq = defaultdict(int)
    for r in rows:
        mentions_freq[r[1]] += 1

    # compute the distribution of thread length
    query = """
           SELECT thread_id, count(id)
           FROM post
           WHERE comment_to != -1
           GROUP BY thread_id
           ORDER BY count(id) DESC
           """

    rows = YDH.custom_query(query)
    thread_length = defaultdict(int)
    for r in rows:
        thread_length[r[1]] += 1

    # compute the distribution of article shares
    query = """
           SELECT shared_from, count(id)
           FROM post
           WHERE shared_from != -1
           GROUP BY shared_from
           ORDER BY count(id) DESC
           """
    rows = YDH.custom_query(query)
    article_shares = defaultdict(int)
    for r in rows:
        article_shares[r[1]] += 1

    posts_per_user = dict(sorted(posts_per_user.items(), key=lambda x: x[0]))
    comments_per_user = dict(sorted(comments_per_user.items(), key=lambda x: x[0]))

    posts_per_user_cdf = np.cumsum(list(posts_per_user.values())) / sum(
        posts_per_user.values()
    )
    comments_per_user_cdf = np.cumsum(list(comments_per_user.values())) / sum(
        comments_per_user.values()
    )

    hashtags_freq = dict(sorted(hashtags_freq.items(), key=lambda x: x[0]))
    hashtags_freq_cdf = np.cumsum(list(hashtags_freq.values())) / sum(
        hashtags_freq.values()
    )

    mentions_freq = dict(sorted(mentions_freq.items(), key=lambda x: x[0]))
    mentions_freq_cdf = np.cumsum(list(mentions_freq.values())) / sum(
        mentions_freq.values()
    )

    thread_freq = dict(sorted(thread_length.items(), key=lambda x: x[0]))
    thread_freq_cdf = np.cumsum(list(thread_freq.values())) / sum(thread_freq.values())

    shares_freq = dict(sorted(article_shares.items(), key=lambda x: x[0]))
    shares_freq_cdf = np.cumsum(list(article_shares.values())) / sum(
        article_shares.values()
    )

    fig = plt.figure(figsize=(10, 3))
    if len(posts_per_user.keys()) > 0:
        plt.loglog(
            list(posts_per_user.keys()),
            1 - np.array(list(posts_per_user_cdf)),
            label="Posts",
        )

    if len(comments_per_user.keys()) > 0:
        plt.loglog(
            list(comments_per_user.keys()),
            1 - np.array(list(comments_per_user_cdf)),
            label="Comments",
        )

    if len(hashtags_freq.keys()) > 0:
        plt.loglog(
            list(hashtags_freq.keys()),
            1 - np.array(list(hashtags_freq_cdf)),
            label="Hashtags",
        )

    if len(mentions_freq.keys()) > 0:
        plt.loglog(
            list(mentions_freq.keys()),
            1 - np.array(list(mentions_freq_cdf)),
            label="Mentions",
        )

    if len(thread_freq.keys()) > 0:
        plt.loglog(
            list(thread_freq.keys()),
            1 - np.array(list(thread_freq_cdf)),
            label="Threads",
        )

    if len(shares_freq.keys()) > 0:
        plt.loglog(
            list(shares_freq.keys()),
            1 - np.array(list(shares_freq_cdf)),
            label="Shares",
        )

    plt.xlabel("#Contents", fontsize=12)
    plt.ylabel("P(X > x)", fontsize=12)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.legend(fontsize=12)
    return fig


def trending_hashtags(YDH: YDataHandler, limit=10, leaning=None):
    """
    Plot the top trending hashtags over time.
    This function retrieves the top trending hashtags from the database,
    grouped by day, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :param limit: The number of top trending hashtags to plot
    :param leaning: Optional parameter to filter hashtags by user leaning (e.g., 'democrat', 'republican').
                    If None, all hashtags are considered.
    :return: A matplotlib figure object containing the plot of trending hashtags.
    """

    query = """
            SELECT h.hashtag, count(ph.post_id)
            FROM hashtags AS h
            JOIN post_hashtags AS ph ON h.id = ph.hashtag_id
            JOIN post AS p ON ph.post_id = p.id
            JOIN user_mgmt AS u ON p.user_id = u.id
            """

    if leaning is not None:
        query += f" WHERE u.leaning = {leaning} "

    query += f"""
            GROUP BY h.id
            ORDER BY count(ph.post_id) DESC
            LIMIT {limit}
            """

    rows = YDH.custom_query(query)

    hashtags = [r[0] for r in rows]
    counts = [r[1] for r in rows]

    fig = plt.figure(figsize=(5, 3))
    plt.barh(hashtags[::-1], counts[::-1])
    plt.xlabel("Count", fontsize=12)
    plt.gca().invert_xaxis()

    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    return fig


def trending_emotions(YDH: YDataHandler, limit=10, leaning=None):
    """
    Plot the top trending hashtags over time.
    This function retrieves the top trending hashtags from the database,
    grouped by day, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :param limit: The number of top trending hashtags to plot
    :param leaning: Optional parameter to filter hashtags by user leaning (e.g., 'democrat', 'republican').
                    If None, all hashtags are considered.
    :return: A matplotlib figure object containing the plot of trending hashtags.
    """

    query = """
            SELECT h.emotion, count(ph.post_id)
            FROM emotions AS h
            JOIN post_emotions AS ph ON h.id = ph.emotion_id
            JOIN post AS p ON ph.post_id = p.id
            JOIN user_mgmt AS u ON p.user_id = u.id
            """

    if leaning is not None:
        query += f" WHERE u.leaning = {leaning} "

    query += f"""
            GROUP BY h.id
            ORDER BY count(ph.post_id) DESC
            LIMIT {limit}
            """

    rows = YDH.custom_query(query)

    hashtags = [r[0] for r in rows]
    counts = [r[1] for r in rows]

    fig = plt.figure(figsize=(5, 3))
    plt.barh(hashtags[::-1], counts[::-1])
    plt.xlabel("Count", fontsize=12)
    plt.gca().invert_xaxis()

    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    return fig


def tending_topics(YDH: YDataHandler, limit=10, leaning=None):
    """
    Plot the top trending topics over time.
    This function retrieves the top trending topics from the database,
    grouped by day, and plots them on a single graph.

    :param YDH: YDataHandler instance for database operations
    :param limit: The number of top trending topics to plot
    :param leaning: Optional parameter to filter topics by user leaning (e.g., 'democrat', 'republican').
                    If None, all topics are considered.
    :return: A matplotlib figure object containing the plot of trending topics.
    """

    query = """
            SELECT h.interest, count(ph.user_id)
            FROM interests AS h
            JOIN user_interest AS ph ON h.iid = ph.interest_id
            JOIN user_mgmt AS u ON ph.user_id = u.id
            """

    if leaning is not None:
        query += f" WHERE u.leaning = {leaning} "

    query += f"""
            GROUP BY h.iid
            ORDER BY count(ph.user_id) DESC
            LIMIT {limit}
            """

    rows = YDH.custom_query(query)

    topics = [r[0] for r in rows]
    counts = [r[1] for r in rows]

    fig = plt.figure(figsize=(5, 3))
    plt.barh(topics[::-1], counts[::-1])
    plt.xlabel("Count", fontsize=12)
    plt.gca().invert_xaxis()

    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    return fig


def comments_per_post_distribution(YDH: YDataHandler):
    """
    Plot the distribution of comments per post.
    This function retrieves the count of comments for each post from the database,
    and plots the distribution on a histogram.

    :param YDH: YDataHandler instance for database operations
    :return: A matplotlib figure object containing the histogram of comments per post.
    """

    query = """
            SELECT p.id, count(c.id)
            FROM post AS p
            JOIN post AS c ON p.id = c.comment_to
            GROUP BY p.id
            ORDER BY count(c.id) DESC
            """

    rows = YDH.custom_query(query)
    comments_per_post = defaultdict(int)
    for r in rows:
        comments_per_post[r[1]] += 1

    # plot the distribution of comments per post
    fig = plt.figure(figsize=(6, 3))
    plt.loglog(list(comments_per_post.keys()), list(comments_per_post.values()))
    plt.xlabel("Comments", fontsize=12)
    plt.ylabel("Posts", fontsize=12)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    return fig
