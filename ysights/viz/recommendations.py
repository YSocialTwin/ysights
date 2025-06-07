import matplotlib.pyplot as plt
from ysights.models.YDataHandler import YDataHandler
from collections import defaultdict


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
