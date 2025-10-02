"""
Recommendation System Visualization Functions
==============================================

This module provides visualization functions for analyzing recommendation
system behavior in YSocial simulations. It helps visualize recommendation
distributions, correlations with engagement metrics, and system balance.

Functions:
    - recommendations_per_post_distribution: Distribution of recommendation counts
    - recommendations_vs_reactions: Correlation between recommendations and reactions
    - recommendations_vs_comments: Correlation between recommendations and comments

Example:
    Visualizing recommendation patterns::

        from ysights import YDataHandler
        from ysights.viz import (
            recommendations_per_post_distribution,
            recommendations_vs_reactions,
            recommendations_vs_comments
        )

        ydh = YDataHandler('path/to/database.db')

        # Distribution of recommendations
        fig = recommendations_per_post_distribution(ydh)
        fig.show()

        # Recommendations vs reactions
        fig = recommendations_vs_reactions(ydh)
        fig.show()

        # Recommendations vs comments
        fig = recommendations_vs_comments(ydh)
        fig.show()

See Also:
    - :mod:`ysights.algorithms.recommenders`: Recommendation system metrics
    - :mod:`ysights.viz.global_trends`: Global content trends
"""

from collections import defaultdict

import matplotlib.pyplot as plt
import pandas as pd

from ysights.models.YDataHandler import YDataHandler


def recommendations_per_post_distribution(YDH: YDataHandler):
    """
    Plot the distribution of recommendations per post.

    :param YDH: YDataHandler instance for database operations
    :return: a matplotlib figure showing the distribution of recommendations per post
    """

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
        SELECT r.post_ids
        FROM recommendations AS r
    """

    rows = YDH.custom_query(query)
    posts_recs = defaultdict(int)
    for r in rows:
        for p in r[0].split("|"):
            posts_recs[p] += 1

    rec_count = defaultdict(int)
    for k, v in posts_recs.items():
        rec_count[v] += 1

    # sort the dictionary by key
    rec_count = dict(sorted(rec_count.items(), key=lambda x: x[0]))

    # plot the distribution of recommendations per post
    fig = plt.figure(figsize=(6, 3))
    plt.loglog(list(rec_count.keys()), list(rec_count.values()))
    plt.xlabel("Recommendations", fontsize=12)
    plt.ylabel("Posts", fontsize=12)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    return fig


def recommendations_vs_reactions(YDH: YDataHandler, density=False):
    """
    Plot the relationship between recommendations and reactions.

    :param YDH: YDataHandler instance for database operations
    :param density: if True, use hexbin plot for density visualization
    :return: a matplotlib figure showing the relationship between recommendations and reactions
    """

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
        SELECT r.post_ids
        FROM recommendations AS r
    """

    rows = YDH.custom_query(query)
    posts_recs = defaultdict(int)
    for r in rows:
        for p in r[0].split("|"):
            if p != "":
                posts_recs[int(p)] += 1

    i = [str(k) for k in posts_recs.keys() if k != ""]
    pids = ",".join(i)

    query = f"""
        SELECT p.id, count(r.id)
        FROM post AS p
        JOIN reactions AS r ON p.id = r.post_id
        WHERE p.id IN ({pids})
        GROUP BY p.id
        """
    rows = YDH.custom_query(query)

    posts_reactions = defaultdict(int)

    for r in rows:
        posts_reactions[r[0]] += r[1]

    keys = list(set(posts_recs.keys()) & set(posts_reactions.keys()))
    x = []
    y = []
    for k in keys:
        x.append(posts_recs[k])
        y.append(posts_reactions[k])

    fig = plt.figure(figsize=(6, 3))

    if not density:
        plt.scatter(x, y, alpha=0.5)
        plt.xlabel("#Recommendations", fontsize=12)
        plt.ylabel("#Reactions", fontsize=12)
        plt.xscale("log")
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.tight_layout()

    else:
        df = pd.DataFrame.from_dict(posts_recs, orient="index", columns=["rec_count"])
        df["reactions"] = df.index.map(posts_reactions)
        df = df.dropna()

        df = df[df["reactions"] > 0]
        df = df[df["rec_count"] > 0]
        plt.hexbin(df["rec_count"], df["reactions"], gridsize=6, cmap="PuBu", mincnt=1)
        plt.colorbar(label="Counts")
        plt.xlabel("Recommendations", fontsize=12)
        plt.ylabel("Reactions", fontsize=12)
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.tight_layout()

    return fig


def recommendations_vs_comments(YDH: YDataHandler, density=False):
    """
    Plot the relationship between recommendations and comments.

    :param YDH: YDataHandler instance for database operations
    :param density: if True, use hexbin plot for density visualization
    :return: a matplotlib figure showing the relationship between recommendations and comments
    """

    # get the distribution of posts per day, get the day id from the rounds table
    query = """
        SELECT r.post_ids
        FROM recommendations AS r
    """

    rows = YDH.custom_query(query)
    posts_recs = defaultdict(int)
    for r in rows:
        for p in r[0].split("|"):
            if p != "":
                posts_recs[int(p)] += 1

    i = [str(k) for k in posts_recs.keys() if k != ""]
    pids = ",".join(i)

    query = f"""
        SELECT p.id, count(c.id)
        FROM post AS p
        JOIN post AS c ON p.id = c.comment_to
        WHERE p.id IN ({pids})
        GROUP BY p.id
    """
    rows = YDH.custom_query(query)
    posts_comments = defaultdict(int)

    for r in rows:
        posts_comments[r[0]] += r[1]

    keys = list(set(posts_recs.keys()) & set(posts_comments.keys()))
    x = []
    y = []
    for k in keys:
        x.append(posts_recs[k])
        y.append(posts_comments[k])

    fig = plt.figure(figsize=(6, 3))

    if not density:
        plt.scatter(x, y, alpha=0.5)
        plt.xlabel("#Recommendations", fontsize=12)
        plt.ylabel("#Comments", fontsize=12)
        plt.xscale("log")
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.tight_layout()

    else:
        df = pd.DataFrame.from_dict(posts_recs, orient="index", columns=["rec_count"])
        df["comments"] = df.index.map(posts_comments)
        df = df.dropna()

        df = df[df["comments"] > 0]
        df = df[df["rec_count"] > 0]
        plt.hexbin(df["rec_count"], df["comments"], gridsize=6, cmap="PuBu", mincnt=1)
        plt.colorbar(label="Counts")
        plt.xlabel("Recommendations", fontsize=12)
        plt.ylabel("Comments", fontsize=12)
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.tight_layout()

    return fig
