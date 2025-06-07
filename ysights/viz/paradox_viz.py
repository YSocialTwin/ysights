import numpy as np
from scipy.stats import gaussian_kde
import matplotlib.pyplot as plt


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
    >>> viz.paradox_histogram(results['nodes_coefficients'], bins=30, title="Visibility Paradox Histogram")
    """
    fig = plt.figure(figsize=(8, 5))
    plt.hist(x, bins=bins, color="skyblue", edgecolor="black", alpha=0.7)
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title(f"{title} - Score: {np.mean(x):.2f}")
    plt.grid(True)
    return fig
