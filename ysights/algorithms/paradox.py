"""
Visibility Paradox Analysis
============================

This module provides functions for analyzing the visibility paradox in social networks.
The visibility paradox describes situations where content created by agents receives
asymmetric visibility compared to content they see from their neighbors.

The module includes:
- Visibility paradox detection and statistical significance testing
- Comparison of user visibility vs. neighbor visibility
- Population-size effects on the paradox
- Null model generation for hypothesis testing

Key Concepts:
    The visibility paradox occurs when there's an imbalance between:
    1. How much of your neighbors' content you see (inbound recommendations)
    2. How much your neighbors see your content (outbound visibility)

    This can lead to situations where most users feel their content is under-represented
    in their neighbors' feeds, even though the aggregate statistics might suggest balance.

Example:
    Detecting the visibility paradox::

        from ysights import YDataHandler
        from ysights.algorithms.paradox import visibility_paradox, user_visibility_vs_neighbors

        # Initialize data handler and extract network
        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()

        # Calculate visibility paradox with statistical testing
        paradox_results = visibility_paradox(ydh, network, N=100)

        print(f"Paradox score: {paradox_results['paradox_score']:.4f}")
        print(f"Z-score: {paradox_results['z_score']:.4f}")
        print(f"P-value: {paradox_results['p_value']:.4f}")

        if paradox_results['p_value'] < 0.05:
            print("Visibility paradox detected (statistically significant)")

        # Compare user visibility with neighbor averages
        user_vis, neighbor_vis = user_visibility_vs_neighbors(ydh, network)

        import numpy as np
        print(f"Average user visibility: {np.mean(user_vis):.2f}")
        print(f"Average neighbor visibility: {np.mean(neighbor_vis):.2f}")

References:
    The visibility paradox is related to concepts from:
    - Friendship paradox (Feld, 1991)
    - Attention inequality in social networks
    - Filter bubble and echo chamber effects

See Also:
    :func:`visibility_paradox`: Main function for paradox detection
    :func:`user_visibility_vs_neighbors`: Compare visibility metrics
    :func:`visibility_paradox_population_size_null`: Analyze population size effects
"""

import random
from collections import defaultdict

import networkx as nx
import numpy as np
import tqdm
from scipy.stats import norm

from ysights.models.YDataHandler import YDataHandler


def __stratified_node_sampling_by_degree_bins(G, percentage, seed=None, bins=None):
    """
    Sample a percentage of nodes from the graph G stratified by node degree bins.

    :param G: A NetworkX graph
    :param percentage: float between 0 and 1 indicating the percentage of nodes to sample
    :param seed: Random seed for reproducibility (optional)
    :param bins: Optional list of degree bin edges. If None, logarithmic bins will be used.
    :return: A set of sampled node IDs
    """
    if seed is not None:
        random.seed(seed)

    if not (0 < percentage <= 1):
        raise ValueError("Percentage must be between 0 and 1.")

    # Get degree for each node
    degrees = dict(G.degree())
    degree_values = np.array(list(degrees.values()))

    # Define bins (logarithmic by default)
    if bins is None:
        max_deg = max(degree_values)
        bins = np.unique(
            np.logspace(0, np.log10(max_deg + 1), num=5, dtype=int)
        )  # e.g., 4 bins

    # Group nodes by bin
    bin_to_nodes = defaultdict(list)
    for node, deg in degrees.items():
        for i in range(len(bins) - 1):
            if bins[i] <= deg < bins[i + 1]:
                bin_to_nodes[i].append(node)
                break

    # Sample from each bin
    sampled_nodes = set()
    total_target = int(percentage * G.number_of_nodes())

    for group in bin_to_nodes.values():
        sample_size = int(round(len(group) * percentage))
        if sample_size > len(group):
            sample_size = len(group)
        sampled_nodes.update(random.sample(group, sample_size))

    # Adjust to match target size exactly (optional)
    if len(sampled_nodes) < total_target:
        remaining = list(set(G.nodes()) - sampled_nodes)
        sampled_nodes.update(
            random.sample(remaining, total_target - len(sampled_nodes))
        )
    elif len(sampled_nodes) > total_target:
        sampled_nodes = set(random.sample(list(sampled_nodes), total_target))

    return sampled_nodes


def __generate_randomized_mappings(original_dict, N, seed=None, x=1.0, g=None):
    """
    Generate N randomized mappings of users to posts while preserving the original post-counts per user.
    A percentage x of users will have their mappings randomized, while the rest will retain the original mapping.

    :param original_dict: dict mapping user to list of posts
    :param N: number of randomized mappings to generate
    :param seed: optional random seed
    :param x: fraction of users to randomize (between 0 and 1)
    :return: (list of user_to_posts dicts, list of post_to_user dicts)
    """
    if seed is not None:
        random.seed(seed)

    users = list(original_dict.keys())
    user_to_posts_list = []
    post_to_user_list = []

    for _ in range(N):
        # Sample x% of users to randomize
        num_to_randomize = int(len(users) * x)
        if x == 1:
            randomized_users = set(users)
        else:
            randomized_users = __stratified_node_sampling_by_degree_bins(g, x)
        # randomized_users = set(random.sample(users, num_to_randomize)) if x < 1 else set(users)
        # static_users = set(users) - randomized_users

        # Extract only posts from randomized users
        randomized_posts = [
            post
            for user in randomized_users
            if user in original_dict
            for post in original_dict[user]
        ]

        random.shuffle(randomized_posts)
        shuffled_posts = iter(randomized_posts)

        user_to_posts = {}
        post_to_user = {}

        # Assign shuffled posts to randomized users
        for user in users:
            if user in randomized_users:
                count = len(original_dict[user])
                posts = [next(shuffled_posts) for _ in range(count)]
            else:
                posts = original_dict[user]
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
        raise ValueError(
            "Standard deviation of synthetic means is zero — can't perform Z-test."
        )

    z_score = (observed_mean - mu) / sigma
    p_value = 2 * norm.sf(abs(z_score))  # two-tailed

    return z_score, p_value


def __z_test_two_distributions(x, y):
    """
    Perform a two-sample Z-test to compare the means of two distributions.

    Parameters:
    - x: list or array-like, first distribution
    - y: list or array-like, second distribution

    Returns:
    - z_score: float, the Z statistic
    - p_value: float, two-tailed p-value
    """
    x = np.array(x)
    y = np.array(y)

    mu_x = np.mean(x)
    mu_y = np.mean(y)
    sigma_x = np.std(x, ddof=0)  # population std
    sigma_y = np.std(y, ddof=0)  # population std

    if sigma_x == 0 or sigma_y == 0:
        raise ValueError("Standard deviation of one or both distributions is zero.")

    n_x = len(x)
    n_y = len(y)

    z_score = (mu_x - mu_y) / np.sqrt((sigma_x**2 / n_x) + (sigma_y**2 / n_y))
    p_value = 2 * norm.sf(abs(z_score))  # two-tailed

    return z_score, p_value


def __mann_whitney_u_test(x, y):
    """
    Perform a Mann-Whitney U test to compare the distributions of two independent samples.

    Parameters:
    - x: list or array-like, first sample
    - y: list or array-like, second sample

    Returns:
    - u_statistic: float, the U statistic
    - p_value: float, two-tailed p-value
    """
    from scipy.stats import mannwhitneyu

    u_statistic, p_value = mannwhitneyu(x, y, alternative="two-sided")

    return u_statistic, p_value


def user_visibility_vs_neighbors(YDH: YDataHandler, g, node_ids=False):
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

        try:
            pts.user_id = int(pts.user_id)
            pts.id = int(pts.id)
        except Exception:
            pass

        if pts.user_id not in user_to_posts:
            user_to_posts[pts.user_id] = [pts.id]
        else:
            user_to_posts[pts.user_id].append(pts.id)
        post_to_users[pts.id] = pts.user_id

    users_to_impressions = __user_impressions_mapping(post_recs, user_to_posts)
    users_to_impressions_total = {u: sum(v) for u, v in users_to_impressions.items()}

    u_imp = []
    n_avg_imp = []
    ids = []
    for user, i in users_to_impressions_total.items():
        u_imp.append(i)
        ids.append(user)
        if user not in g.nodes:
            n_avg_imp.append(0)
            continue

        n = g.neighbors(user)
        tot = 0
        norm = 0
        for v in n:
            if v in users_to_impressions_total:
                tot += users_to_impressions_total[v]
            norm += 1
        tot = tot / norm if norm != 0 else 0
        n_avg_imp.append(tot)

    if node_ids:
        return ids, u_imp, n_avg_imp
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
        try:
            pts.user_id = int(pts.user_id)
            pts.id = int(pts.id)
        except Exception:
            pass

        if pts.user_id not in user_to_posts:
            user_to_posts[pts.user_id] = [pts.id]
        else:
            user_to_posts[pts.user_id].append(pts.id)
        post_to_users[pts.id] = pts.user_id

    users_to_impressions = __user_impressions_mapping(post_recs, user_to_posts)
    users_to_impressions_total = {u: sum(v) for u, v in users_to_impressions.items()}

    nodes_coeffs = __stats(
        users_to_impressions_total, user_to_posts_read, user_to_posts, g
    )

    if N > 0:
        # NULL Models #
        user_to_posts_list, post_to_user_list = __generate_randomized_mappings(
            user_to_posts, N, x=1
        )
        null_means_dist = []
        for i in range(len(user_to_posts_list)):
            u_to_p_n = user_to_posts_list[i]
            users_to_impressions_n = __user_impressions_mapping(post_recs, u_to_p_n)
            mean = np.mean(
                __stats(users_to_impressions_n, user_to_posts_read, u_to_p_n, g)
            )
            null_means_dist.append(mean)

        z_score, p_value = __z_test(np.mean(nodes_coeffs), null_means_dist)

        return {
            "nodes_coefficients": nodes_coeffs,
            "paradox_score": np.mean(nodes_coeffs),
            "z_score": z_score,
            "p_value": p_value,
        }

    return {
        "nodes_coefficients": nodes_coeffs,
        "paradox_score": np.mean(nodes_coeffs),
        "z_score": None,
        "p_value": None,
    }


def __visibility_paradox_sub_population(YDH: YDataHandler, g, N=100, x=0.1):
    post_recs, user_to_posts_read = YDH.recommendations_per_post_per_user()
    posts = YDH.posts()

    post_to_users = {}
    user_to_posts = {}
    for pts in posts.get_posts():
        try:
            pts.user_id = int(pts.user_id)
            pts.id = int(pts.id)
        except Exception:
            pass

        if pts.user_id not in user_to_posts:
            user_to_posts[pts.user_id] = [pts.id]
        else:
            user_to_posts[pts.user_id].append(pts.id)
        post_to_users[pts.id] = pts.user_id

    # null model generation
    user_to_posts_list, post_to_user_list = __generate_randomized_mappings(
        user_to_posts, N, x=1
    )
    null_means_dist = []
    for i in range(len(user_to_posts_list)):
        u_to_p_n = user_to_posts_list[i]
        users_to_impressions_n = __user_impressions_mapping(post_recs, u_to_p_n)
        mean = np.mean(__stats(users_to_impressions_n, user_to_posts_read, u_to_p_n, g))
        null_means_dist.append(mean)

    # generate a randomized mapping of users to posts for x% of the users
    user_to_posts_list_partial, post_to_user_list_partial = (
        __generate_randomized_mappings(user_to_posts, N, x=1 - x, g=g)
    )
    partial_means_dist = []
    for i in range(len(user_to_posts_list_partial)):
        u_to_p_p = user_to_posts_list_partial[i]
        users_to_impressions_p = __user_impressions_mapping(post_recs, u_to_p_p)
        mean = np.mean(__stats(users_to_impressions_p, user_to_posts_read, u_to_p_p, g))
        partial_means_dist.append(mean)

    # calculate the z-score and p-value for the partial mapping
    z_score, p_value = __mann_whitney_u_test(
        partial_means_dist, null_means_dist
    )  # __z_test_two_distributions(partial_means_dist, null_means_dist)
    return {
        "z_score": z_score,
        "p_value": p_value,
        "paradox_score_avg": np.mean(partial_means_dist),
        "paradox_score_std": np.std(partial_means_dist),
    }


def visibility_paradox_population_size_null(
    YDH: YDataHandler,
    g,
    N=10,
    subject_to_rec=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
):
    """
    Calculate the visibility paradox metric for a given YDataHandler and graph,
    considering the population size.

    :param YDH: YDataHandler, the data handler containing the YSocial simulation data
    :param g: networkx.Graph, the social network graph
    :param N: int, number of null models to generate for statistical testing
    :param x: float, fraction of users to randomize (between 0 and 1)
    :return:
    """
    results = {}
    for fraction in tqdm.tqdm(subject_to_rec):
        results[fraction] = __visibility_paradox_sub_population(YDH, g, N=N, x=fraction)

    return results


def __stats_with_degrees(users_to_impressions_total, user_to_posts_read, user_to_posts, g):
    """
    Calculate the visibility paradox metric for each user in the graph along with their degree.
    
    :param users_to_impressions_total: the total number of impressions for each user
    :param user_to_posts_read: the posts suggested to each user
    :param user_to_posts: the posts associated with each user
    :param g: the social network graph
    :return: tuple of (list of coefficients, list of degrees, list of node ids)
    """
    
    delta = []
    degrees = []
    node_ids = []
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
            
            node_degree = nx.degree(g, n)
            delta.append((1 / node_degree) * sum(scores))
            degrees.append(node_degree)
            node_ids.append(n)
    
    return delta, degrees, node_ids


def visibility_paradox_per_degree_class(YDH: YDataHandler, g, N=100, bins=None, num_bins=10):
    """
    Calculate the statistical significance of the visibility paradox per degree class.
    
    This function computes the paradox score and its statistical significance for each 
    degree class (bin) of nodes. By default, it uses linear binning but allows users 
    to specify custom bin edges.
    
    :param YDH: YDataHandler, the data handler containing the YSocial simulation data
    :param g: networkx.Graph, the social network graph
    :param N: int, number of null models to generate for statistical testing
    :param bins: array-like, optional bin edges for degree binning. If None, linear bins are created.
    :param num_bins: int, number of bins to create if bins is None (default: 10)
    :return: dict with keys:
        - 'bin_edges': array of bin edges
        - 'bin_centers': array of bin centers for plotting
        - 'paradox_scores': average paradox score per bin
        - 'z_scores': z-score per bin (statistical significance)
        - 'p_values': p-value per bin
        - 'bin_counts': number of nodes in each bin
    
    Example:
        >>> from ysights import YDataHandler
        >>> from ysights.algorithms.paradox import visibility_paradox_per_degree_class
        >>> 
        >>> ydh = YDataHandler('path/to/database.db')
        >>> network = ydh.social_network()
        >>> 
        >>> # Using default linear binning
        >>> results = visibility_paradox_per_degree_class(ydh, network, N=100, num_bins=10)
        >>> 
        >>> # Using custom bin edges
        >>> custom_bins = [0, 5, 10, 20, 50, 100]
        >>> results = visibility_paradox_per_degree_class(ydh, network, N=100, bins=custom_bins)
    """
    
    post_recs, user_to_posts_read = YDH.recommendations_per_post_per_user()
    posts = YDH.posts()
    
    post_to_users = {}
    user_to_posts = {}
    for pts in posts.get_posts():
        try:
            pts.user_id = int(pts.user_id)
            pts.id = int(pts.id)
        except Exception:
            pass
        
        if pts.user_id not in user_to_posts:
            user_to_posts[pts.user_id] = [pts.id]
        else:
            user_to_posts[pts.user_id].append(pts.id)
        post_to_users[pts.id] = pts.user_id
    
    users_to_impressions = __user_impressions_mapping(post_recs, user_to_posts)
    users_to_impressions_total = {u: sum(v) for u, v in users_to_impressions.items()}
    
    # Get coefficients with degrees for the observed data
    nodes_coeffs, node_degrees, node_ids = __stats_with_degrees(
        users_to_impressions_total, user_to_posts_read, user_to_posts, g
    )
    
    # Create bins if not provided (linear binning by default)
    if bins is None:
        min_deg = min(node_degrees) if node_degrees else 0
        max_deg = max(node_degrees) if node_degrees else 1
        bins = np.linspace(min_deg, max_deg, num_bins + 1)
    
    bins = np.array(bins)
    
    # Bin the observed data
    bin_indices = np.digitize(node_degrees, bins) - 1
    
    # Initialize result containers
    paradox_scores = []
    z_scores = []
    p_values = []
    bin_counts = []
    bin_centers = []
    
    # Generate null models
    if N > 0:
        user_to_posts_list, post_to_user_list = __generate_randomized_mappings(
            user_to_posts, N, x=1
        )
        
        # Collect null distributions for each bin
        null_distributions = defaultdict(list)
        
        for i in range(len(user_to_posts_list)):
            u_to_p_n = user_to_posts_list[i]
            users_to_impressions_n = __user_impressions_mapping(post_recs, u_to_p_n)
            coeffs_null, degrees_null, _ = __stats_with_degrees(
                users_to_impressions_n, user_to_posts_read, u_to_p_n, g
            )
            
            # Bin the null data using the same bins
            bin_indices_null = np.digitize(degrees_null, bins) - 1
            
            # Aggregate by bin
            for bin_idx in range(len(bins) - 1):
                bin_mask = bin_indices_null == bin_idx
                if np.any(bin_mask):
                    # Get coefficients for this bin and compute mean
                    bin_coeffs_null = np.array(coeffs_null)[bin_mask]
                    null_distributions[bin_idx].append(np.mean(bin_coeffs_null))
    
    # Compute statistics per bin
    for bin_idx in range(len(bins) - 1):
        bin_mask = np.array(bin_indices) == bin_idx
        bin_coeffs = np.array(nodes_coeffs)[bin_mask]
        
        if len(bin_coeffs) > 0:
            observed_mean = np.mean(bin_coeffs)
            paradox_scores.append(observed_mean)
            bin_counts.append(len(bin_coeffs))
            bin_centers.append((bins[bin_idx] + bins[bin_idx + 1]) / 2)
            
            if N > 0 and bin_idx in null_distributions and len(null_distributions[bin_idx]) > 0:
                try:
                    z_score, p_value = __z_test(observed_mean, null_distributions[bin_idx])
                    z_scores.append(z_score)
                    p_values.append(p_value)
                except ValueError:
                    # Handle case where standard deviation is zero
                    z_scores.append(np.nan)
                    p_values.append(np.nan)
            else:
                z_scores.append(np.nan)
                p_values.append(np.nan)
        else:
            # Empty bin
            paradox_scores.append(np.nan)
            z_scores.append(np.nan)
            p_values.append(np.nan)
            bin_counts.append(0)
            bin_centers.append((bins[bin_idx] + bins[bin_idx + 1]) / 2)
    
    return {
        'bin_edges': bins,
        'bin_centers': np.array(bin_centers),
        'paradox_scores': np.array(paradox_scores),
        'z_scores': np.array(z_scores),
        'p_values': np.array(p_values),
        'bin_counts': np.array(bin_counts),
    }
