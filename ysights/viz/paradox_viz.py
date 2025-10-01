"""
Paradox Visualization Functions
================================

This module provides visualization functions for the visibility paradox analysis.
It includes density scatter plots, histograms, and population size effect visualizations
to help understand asymmetries in content visibility within social networks.

Functions:
    - paradox_density_scatter: 2D density scatter plot comparing user and neighbor visibility
    - paradox_histogram: Distribution of paradox scores across users
    - paradox_size_impact: Line plots showing how paradox varies with population fraction

Example:
    Visualizing the visibility paradox::

        from ysights import YDataHandler
        from ysights.algorithms import visibility_paradox, user_visibility_vs_neighbors
        from ysights.viz import paradox_density_scatter, paradox_histogram

        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()

        # Get visibility data
        user_vis, neighbor_vis = user_visibility_vs_neighbors(ydh, network)

        # Density scatter plot
        fig = paradox_density_scatter(
            user_vis, neighbor_vis,
            xlabel='User Impressions',
            ylabel='Avg Neighbor Impressions',
            title='Visibility Paradox'
        )
        fig.show()

        # Calculate full paradox with statistics
        paradox_results = visibility_paradox(ydh, network, N=100)

        # Histogram of paradox scores
        fig = paradox_histogram(paradox_results, bins=50)
        fig.show()

See Also:
    - :func:`ysights.algorithms.paradox.visibility_paradox`: Calculate paradox metrics
    - :func:`ysights.algorithms.paradox.user_visibility_vs_neighbors`: Get visibility data
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import alpha, gaussian_kde

from ysights.algorithms.paradox import visibility_paradox


def paradox_density_scatter(
    x, y, xlabel="Impressions", ylabel="Avg. Neighbors Impressions", title=""
):
    """

    :param x:
    :param y:
    :param xlabel:
    :param ylabel:
    :param title:
    :return:

    Example usage:
    >>> from ysights import algorithms, viz, YDataHandler
    >>> handler = YDataHandler("path_to_your_database.db")
    >>> network = handler.social_network()
    >>> x, y = algorithms.user_visibility_vs_neighbors(handler, network)
    >>> viz.paradox_density_scatter(x, y, xlabel='Impressions', ylabel='Avg. Neighbors Impressions', title="Visibility Paradox")
    """
    x = np.array(x)
    y = np.array(y)

    def probability_below_diagonal(x1, y1):
        """
        Calculate the probability of points below the diagonal line y = x.

        :param x1:
        :param y1:
        :return:
        """
        belowd = np.sum(y1 < x1)
        total = len(x1)
        return belowd / total if total > 0 else 0

    below = probability_below_diagonal(x, y)

    # Calculate the point density
    xy = np.vstack([x, y])
    z = gaussian_kde(xy)(xy)

    # Sort the points by density, so high density points are plotted on top
    idx = z.argsort()
    x, y, z = x[idx], y[idx], z[idx]

    # Create the scatter plot
    fig = plt.figure(figsize=(8, 6))
    scatter = plt.scatter(x, y, c=z, s=50, cmap="viridis")
    plt.plot()

    # Plot the x = y line
    min_val = min(np.min(x), np.min(y))
    max_val = np.max(y)
    plt.plot([min_val, max_val], [min_val, max_val], "r--", label="x = y")

    plt.colorbar(scatter, label="Density")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(f"{title} - Below Diagonal Probability: {below:.2f}")
    plt.grid(True)
    return fig


def paradox_histogram(x, bins=30, title="Friendship Paradox"):
    """
    Plot a histogram of the visibility paradox data.

    :param x:
    :param bins:
    :param title:
    :return:

    Example usage:
    >>> from ysights import algorithms, viz, YDataHandler
    >>> handler = YDataHandler("path_to_your_database.db")
    >>> network = handler.social_network()
    >>> results = algorithms.visibility_paradox(handler, network, N=0)
    >>> viz.paradox_histogram(results['nodes_coefficients'], bins=10, title="Visibility Paradox Histogram")
    """
    fig = plt.figure(figsize=(8, 5))
    plt.hist(x, bins=bins, color="skyblue", edgecolor="black", alpha=0.7)
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title(f"{title} - Score: {np.mean(x):.2f}")
    plt.grid(True)
    return fig


def paradox_size_impact(data):
    """
    Analyze the impact of network size on the visibility paradox.

    :param YDH: YDataHandler, the data handler containing the YSocial simulation data
    :param g: networkx.Graph, the social network graph
    :param N: int, number of null models to generate for statistical testing
    :return: dict with size impact results
    """
    # Placeholder for actual implementation
    # This function should analyze how the size of the network affects the visibility paradox

    x = sorted(data.keys())
    y = [data[k]["p_value"] for k in x]
    scores = [data[k]["paradox_score_avg"] for k in x]
    stds = np.array([data[k]["paradox_score_std"] for k in x])
    print(stds)

    fig, ax1 = plt.subplots()
    # fig = plt.figure(figsize=(8, 5))
    y = np.array(y)
    # Plot horizontal threshold lines
    ax1.spines["top"].set_visible(False)
    ax1.spines["left"].set_color("#999")

    ax1.loglog(x, y, "-", color="#999", label="p-values", zorder=1)
    # ax1.errorbar(
    #    x, y,
    #    yerr=stds,
    #    fmt='-',  # 'o' marker with a line
    #    color='#999',
    #    ecolor='#ccc',  # error bar color
    #    elinewidth=1,
    #    capsize=3,
    #    label='p-values',
    #    zorder=1
    # )

    ax1.tick_params(axis="y", labelcolor="#999")
    ax1.set_yscale("log")

    ax1.axhspan(0.05, 10, facecolor="red", alpha=0.05, zorder=1)
    ax1.axhspan(0.01, 0.05, facecolor="orange", alpha=0.1, zorder=1)
    ax1.axhspan(0.001, 0.01, facecolor="yellow", alpha=0.05, zorder=1)
    ax1.axhspan(0.0, 0.001, facecolor="green", alpha=0.05, zorder=1)

    ax1.axhline(y=0.05, color="red", linestyle="--", zorder=2, alpha=0.1)
    ax1.axhline(y=0.01, color="orange", linestyle="--", zorder=2, alpha=0.1)
    ax1.axhline(y=0.001, color="green", linestyle="--", zorder=2, alpha=0.1)

    ax2 = ax1.twinx()
    ax2.loglog(x, scores, color="blue", label="Paradox Score", zorder=1)
    ax2.tick_params(axis="y", labelcolor="blue")
    ax2.set_ylabel("Paradox Score", color="blue")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color("blue")
    ax2.spines["left"].set_color("#999")

    ax1.set_xlabel("%Population subject to recommendations")
    ax1.set_ylabel("p-value", color="#999")
    ax1.set_ylim(0, 1)
    ax2.set_ylim(0, 1)

    # Collect handles and labels from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    # Combine them
    all_lines = lines1 + lines2
    all_labels = labels1 + labels2

    # Set the combined legend
    ax1.legend(
        all_lines,
        all_labels,
        fontsize="small",
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.1),
    )

    plt.tight_layout()

    return fig
