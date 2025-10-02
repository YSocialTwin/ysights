"""
Agent Profile Analysis
=======================

This module provides functions for analyzing agent interest profiles and their
similarity within social networks. It helps understand how agents' interests
align with their network neighbors and community structure.

Example:
    Analyzing profile similarity in a social network::

        from ysights import YDataHandler
        from ysights.algorithms.profiles import profile_topics_similarity

        # Initialize data handler and extract network
        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()

        # Calculate interest similarity between neighbors
        similarities = profile_topics_similarity(ydh, network, limit=2)

        # Analyze results
        for agent_id, similarity_score in similarities.items():
            print(f"Agent {agent_id} has {similarity_score:.2%} interest overlap with neighbors")
"""

from collections import defaultdict

from ysights.models.YDataHandler import YDataHandler


def profile_topics_similarity(
    YDH: YDataHandler, g, limit=2, from_round=None, to_round=None
):
    """
    Compute interest-based similarity between agents and their network neighbors.

    This function calculates how well each agent's interests align with those of
    their neighbors in the social network. It filters out rare interests, normalizes
    interest distributions, and computes the fraction of neighbors sharing the
    agent's most frequent interests.

    :param YDH: YDataHandler instance for database operations
    :type YDH: YDataHandler
    :param g: Social network graph where nodes represent agents and edges represent connections
    :type g: networkx.Graph
    :param limit: Minimum count threshold for including an interest (interests appearing
                  fewer times are filtered out)
    :type limit: int
    :param from_round: Starting round for filtering interests (inclusive), None for no lower bound
    :type from_round: int, optional
    :param to_round: Ending round for filtering interests (inclusive), None for no upper bound
    :type to_round: int, optional
    :return: Dictionary mapping agent IDs to their similarity scores with neighbors.
             Similarity score represents the fraction of neighbors sharing at least
             one of the agent's most frequent interests (range: 0.0 to 1.0)
    :rtype: dict[int, float]

    Example::

        from ysights import YDataHandler
        from ysights.algorithms.profiles import profile_topics_similarity
        import networkx as nx

        # Initialize data handler and extract social network
        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()

        # Calculate similarity for all agents
        similarities = profile_topics_similarity(ydh, network, limit=2)

        # Find agents with high neighbor similarity
        high_similarity = {k: v for k, v in similarities.items() if v > 0.7}
        print(f"{len(high_similarity)} agents have >70% interest overlap with neighbors")

        # Calculate for specific time period
        early_sim = profile_topics_similarity(ydh, network, limit=2,
                                             from_round=0, to_round=500)
        late_sim = profile_topics_similarity(ydh, network, limit=2,
                                            from_round=500, to_round=1000)

        # Compare evolution
        for agent_id in early_sim:
            if agent_id in late_sim:
                change = late_sim[agent_id] - early_sim[agent_id]
                if abs(change) > 0.2:
                    print(f"Agent {agent_id} similarity changed by {change:.2%}")

    Note:
        - Interests are normalized per agent, so agents with many posts don't
          dominate the similarity calculation
        - The `limit` parameter helps focus on significant interests by filtering
          out occasional or accidental topic matches
        - Agents with no qualifying interests (after filtering) are excluded from results

    See Also:
        :meth:`ysights.models.YDataHandler.YDataHandler.agent_interests`: Get agent interests
        :meth:`ysights.models.YDataHandler.YDataHandler.social_network`: Extract social network
    """
    # get the count of each interest per user
    query = "SELECT u.user_id, i.interest FROM user_interest as u, interests as i WHERE u.interest_id = i.iid"
    if from_round is not None:
        query += f" and u.round_id >= {from_round}"
    if to_round is not None:
        query += f" and u.round_id <= {to_round}"

    data = YDH.custom_query(query)

    interest_count = defaultdict(lambda: defaultdict(float))
    for row in data:
        user_id = row[0]
        interest = (
            row[1].strip().lower()
        )  # Assuming interests are stored as a comma-separated string
        interest_count[user_id][interest] += 1

        # remove rare interests from the interest_count
    for user_id, interests in interest_count.items():
        for interest, count in list(interests.items()):
            if count < limit:
                del interests[interest]

    # normalize the interest counts per user
    for user_id, interests in interest_count.items():
        total = sum(interests.values())
        for interest in interests:
            interests[interest] /= total

    similarity = defaultdict(lambda: defaultdict(float))

    for n in g.nodes():
        neighbors = list(g.neighbors(n))
        if len(interest_count[n].keys()) > 0:
            n_most_frequent_interest = sorted(
                interest_count[n].items(), key=lambda x: x[1], reverse=True
            )
            neighbors_interests = []
            for neighbor in neighbors:
                if len(interest_count[neighbor].keys()) > 0:
                    n_most_frequent_interests = sorted(
                        interest_count[neighbor].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                    neighbors_interests.append(n_most_frequent_interests)

            # compute the percentage of neighbors with the same most frequent interest
            if len(neighbors_interests) > 0:
                similarity[n] = 0

                for ni in neighbors_interests:
                    for iis in ni:
                        if iis[0] in {k[0]: None for k in n_most_frequent_interest}:
                            similarity[n] += 1
                            break

                similarity[n] /= len(neighbors_interests)
    return similarity
