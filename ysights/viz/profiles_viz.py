import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np


def profile_similarity_distribution(
    similarities: list[dict], population_names: list[str]
):
    """
    Plot the binned distribution of similarity values of the populations passed as a list of dictionaries.

    :param similarities: list of dictionaries containing similarity values for each population
    :param population_names: list of names corresponding to each population in the similarities list
    :return:
    """

    # Set the figure size
    fig = plt.figure(figsize=(10, 6))
    # Create a histogram of the similarity values
    for k, similarity in enumerate(similarities):
        plt.hist(
            list(similarity.values()), bins=20, alpha=0.7, label=population_names[k]
        )

    # Set the title and labels
    plt.title("Distribution of Similarity Values")
    plt.xlabel("Similarity Value")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    return fig


def profile_similarity_vs_degree(
    similarities: list[dict], gs: list, population_names: list[str]
):
    """
    Plot a scatter plot of similarity values vs. node degree for each population.

    :param similarities: list of dictionaries containing similarity values for each population
    :param gs: list of graphs corresponding to each population in the similarities list
    :param population_names: list of names corresponding to each population in the similarities list
    :return: matplotlib figure object
    """
    # plot a scatter plot of the similarity values vs. node degree
    fig = plt.figure(figsize=(10, 6))
    # Create a scatter plot
    for k, similarity in enumerate(similarities):
        degrees = [gs[k].degree(n) for n in similarity.keys()]
        plt.scatter(
            degrees, list(similarity.values()), alpha=0.7, label=population_names[k]
        )

    # Set the title and labels
    plt.title("Similarity Values vs. Node Degree")
    plt.xlabel("Node Degree")
    plt.ylabel("Similarity Value")
    plt.legend()
    plt.tight_layout()
    return fig


def binned_similarity_per_degree(
    similarities: list[dict], gs: list, population_names: list[str], bins=10
):
    """
    Plot the binned similarity values per degree for each population.

    :param similarities: list of dictionaries containing similarity values for each population
    :param gs: list of graphs corresponding to each population in the similarities list
    :param population_names: list of names corresponding to each population in the similarities list
    :param bins: number of bins to use for the histogram
    :return: matplotlib figure object
    """

    def compute_binned_similarity(degrees, similarity, bin_size=5):
        binned_similarity = defaultdict(lambda: defaultdict(float))
        binned_values = defaultdict(list)

        for i in range(len(degrees)):
            bin_index = (degrees[i] // bin_size) * bin_size
            sim_val = similarity[list(similarity.keys())[i]]
            binned_similarity[bin_index]["sum"] += sim_val
            binned_similarity[bin_index]["count"] += 1
            binned_values[bin_index].append(sim_val)

        binned_avg = []
        binned_std = []
        bins = []

        for bin_index in sorted(binned_similarity.keys()):
            count = binned_similarity[bin_index]["count"]
            avg = binned_similarity[bin_index]["sum"] / count
            std = np.std(binned_values[bin_index])
            bins.append(bin_index)
            binned_avg.append(avg)
            binned_std.append(std)

        return bins, binned_avg, binned_std

    # Round 1
    fig = plt.figure(figsize=(10, 6))

    for k, similarity in enumerate(similarities):
        degrees = [gs[k].degree(n) for n in similarity.keys()]
        bns, avg, std = compute_binned_similarity(degrees, similarity, bin_size=bins)
        plt.errorbar(bns, avg, yerr=std, fmt="o", alpha=0.7, label=population_names[k])

    # Labels and legend
    plt.title("Average Similarity Value per Binned Node Degree")
    plt.xlabel("Node Degree (Binned, Size = 10)")
    plt.ylabel("Average Similarity Value")
    plt.legend()
    plt.semilogx()
    plt.grid(True)
    plt.tight_layout()
    return fig
