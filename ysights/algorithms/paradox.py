from ysights.models.YDataHandler import YDataHandler
from collections import defaultdict
import networkx as nx
import numpy as np
from scipy.stats import norm
import random


def __generate_randomized_mappings(original_dict, N, seed=None):
    """
    Generate N randomized mappings of users to posts while preserving the original post-counts per user.
    This function shuffles the posts for each user and returns a list of dictionaries mapping users to their posts

    :param original_dict:
    :param N:
    :param seed:
    :return:
    """
    if seed is not None:
        random.seed(seed)

    # Step 1: Get post count per user and full list of post_ids
    user_post_counts = {user: len(posts) for user, posts in original_dict.items()}
    all_posts = [post for posts in original_dict.values() for post in posts]

    user_to_posts_list = []
    post_to_user_list = []

    for _ in range(N):
        random.shuffle(all_posts)
        shuffled_posts = iter(all_posts)

        user_to_posts = {}
        post_to_user = {}

        for user, count in user_post_counts.items():
            posts = [next(shuffled_posts) for _ in range(count)]
            user_to_posts[user] = posts
            for post in posts:
                post_to_user[post] = user

        user_to_posts_list.append(user_to_posts)
        post_to_user_list.append(post_to_user)

    return user_to_posts_list, post_to_user_list


def __stats(users_to_impressions_total, user_to_posts_read, user_to_posts, g):
    """
    Calculate the visibility paradox metric for each user in the graph.
    This function computes the difference between the number of posts suggested to a user by their neighbors
    and the number of posts suggested to their neighbors by the user.
    The result is a list of coefficients for each user, which can be used to analyze the visibility paradox.
    The higher the coefficient, the more posts a user has suggested to their neighbors compared to the posts suggested
    to them by their neighbors.

    :param users_to_impressions_total: the total number of impressions for each user
    :param user_to_posts_read: the posts suggested to each user
    :param user_to_posts: the posts associated with each user
    :param g: the social network graph
    :return:
    """

    delta = []
    for n in g.nodes():

        if n in users_to_impressions_total:
            read = {pid: None for pid in set(user_to_posts_read[n])}
            scores = []
            for v in g.neighbors(n):
                # cicla sui post di v e conta se compaiono in user_to_posts_read
                p_tot = 0

                # quanti contenuti del mio vicino mi sono stati suggeriti
                if v in user_to_posts:
                    for post in user_to_posts[v]:
                        if post in read:
                            p_tot += 1

                # quanti miei contenuti sono stati suggeriti al mio vicino
                v_tot = 0
                v_read = {pid: None for pid in set(user_to_posts_read[v])}
                if n in user_to_posts:
                    for post in user_to_posts[n]:
                        if post in v_read:
                            v_tot += 1

                # suggerimenti ricevuti - suggerimenti dei miei contenuti
                scores.append(p_tot - v_tot)

            delta.append((1 / nx.degree(g, n)) * sum(scores))
    return delta


def __user_impressions_mapping(post_recs, user_to_posts):
    """
    Create a mapping of users to the number of impressions they received for each post.

    :param post_recs:
    :param user_to_posts:
    :return:
    """
    users_to_i = defaultdict(list)

    for k, v in user_to_posts.items():
        for p in v:

            if p in post_recs:
                users_to_i[k].append(post_recs[p])

    return users_to_i


def __z_test(observed_mean, synthetic_means):
    """
    Perform a one-sample Z-test.

    Parameters:
    - observed_mean: float, the mean from the observed data
    - synthetic_means: list or array-like, the distribution of synthetic means under H0

    Returns:
    - z_score: float, the Z statistic
    - p_value: float, two-tailed p-value
    """
    synthetic_means = np.array(synthetic_means)
    mu = np.mean(synthetic_means)
    sigma = np.std(synthetic_means, ddof=0)  # population std

    if sigma == 0:
        raise ValueError("Standard deviation of synthetic means is zero — can't perform Z-test.")

    z_score = (observed_mean - mu) / sigma
    p_value = 2 * norm.sf(abs(z_score))  # two-tailed

    return z_score, p_value


def user_visibility_vs_neighbors(YDH: YDataHandler, g):
    """
    Calculate the visibility for each user in the graph and the average of its neighbors' visibilities.

    :param YDH:
    :param g:
    :return:
    """

    post_recs, user_to_posts_read = YDH.recommendations_per_post_per_user()
    posts = YDH.posts()

    post_to_users = {}
    user_to_posts = {}
    for pts in posts.get_posts():
        if int(pts.user_id) not in user_to_posts:
            user_to_posts[int(pts.user_id)] = [int(pts.id)]
        else:
            user_to_posts[int(pts.user_id)].append(int(pts.id))
        post_to_users[int(pts.id)] = int(pts.user_id)

    users_to_impressions = __user_impressions_mapping(post_recs, user_to_posts)
    users_to_impressions_total = {u: sum(v) for u, v in users_to_impressions.items()}

    u_imp = []
    n_avg_imp = []
    for user, i in users_to_impressions_total.items():
        u_imp.append(i)
        n = g.neighbors(user)
        tot = 0
        norm = 0
        for v in n:
            if v in users_to_impressions_total:
                tot += users_to_impressions_total[v]
            norm += 1
        tot /= norm
        n_avg_imp.append(tot)

    return u_imp, n_avg_imp


def visibility_paradox(YDH: YDataHandler, g, N=100):
    """
    Calculate the visibility paradox metric for a given YDataHandler and graph.

    :param YDH: YDataHandler, the data handler containing the YSocial simulation data
    :param g: networkx.Graph, the social network graph
    :param N: int, number of null models to generate for statistical testing
    :return:
    """

    post_recs, user_to_posts_read = YDH.recommendations_per_post_per_user()
    posts = YDH.posts()

    post_to_users = {}
    user_to_posts = {}
    for pts in posts.get_posts():
        if int(pts.user_id) not in user_to_posts:
            user_to_posts[int(pts.user_id)] = [int(pts.id)]
        else:
            user_to_posts[int(pts.user_id)].append(int(pts.id))
        post_to_users[int(pts.id)] = int(pts.user_id)

    users_to_impressions = __user_impressions_mapping(post_recs, user_to_posts)
    users_to_impressions_total = {u: sum(v) for u, v in users_to_impressions.items()}

    nodes_coeffs = __stats(users_to_impressions_total, user_to_posts_read, user_to_posts, g)

    if N > 0:
        # NULL Models #
        user_to_posts_list, post_to_user_list = __generate_randomized_mappings(user_to_posts, N)
        null_means_dist = []
        for i in range(len(user_to_posts_list)):
            u_to_p_n = user_to_posts_list[i]
            users_to_impressions_n = __user_impressions_mapping(post_recs, u_to_p_n)
            mean = np.mean(__stats(users_to_impressions_n, user_to_posts_read, u_to_p_n, g))
            null_means_dist.append(mean)

        z_score, p_value = __z_test(np.mean(nodes_coeffs), null_means_dist)

        return {
            "nodes_coefficients": nodes_coeffs,
            "paradox_score": np.mean(nodes_coeffs),
            "z_score": z_score,
            "p_value": p_value
        }

    return {
            "nodes_coefficients": nodes_coeffs,
            "paradox_score": np.mean(nodes_coeffs),
            "z_score": None,
            "p_value": None
        }


